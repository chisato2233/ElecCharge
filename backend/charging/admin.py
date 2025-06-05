from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django import forms
from .models import ChargingPile, ChargingRequest, ChargingSession, SystemParameter, Notification
from decimal import Decimal

# 自定义系统参数表单
class SystemParameterForm(ModelForm):
    class Meta:
        model = SystemParameter
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.param_type == 'json':
            # 为JSON类型的参数提供更友好的编辑界面
            self.fields['param_value'].widget = forms.Textarea(attrs={'rows': 10})
    
    def clean_param_value(self):
        value = self.cleaned_data['param_value']
        param_key = self.cleaned_data.get('param_key')
        param_type = self.cleaned_data.get('param_type')
        
        # 对四个核心参数进行验证
        if param_key in ['FastChargingPileNum', 'TrickleChargingPileNum', 'WaitingAreaSize', 'ChargingQueueLen']:
            try:
                int_value = int(value)
                if int_value <= 0:
                    raise ValidationError(f'{param_key} 必须是正整数')
            except ValueError:
                raise ValidationError(f'{param_key} 必须是有效的整数')
        
        # 对费率参数进行验证
        elif param_key in ['peak_rate', 'normal_rate', 'valley_rate', 'service_rate']:
            try:
                float_value = float(value)
                if float_value < 0:
                    raise ValidationError(f'{param_key} 不能为负数')
            except ValueError:
                raise ValidationError(f'{param_key} 必须是有效的数字')
        
        # 根据参数类型验证
        if param_type == 'int':
            try:
                int(value)
            except ValueError:
                raise ValidationError('整数类型参数值必须是有效的整数')
        elif param_type == 'float':
            try:
                float(value)
            except ValueError:
                raise ValidationError('浮点数类型参数值必须是有效的数字')
        elif param_type == 'boolean':
            if value.lower() not in ('true', 'false', '1', '0', 'yes', 'no'):
                raise ValidationError('布尔类型参数值必须是 true/false, 1/0, yes/no')
        elif param_type == 'json':
            try:
                import json
                json.loads(value)
            except json.JSONDecodeError:
                raise ValidationError('JSON类型参数值必须是有效的JSON格式')
        
        return value

@admin.register(SystemParameter)
class SystemParameterAdmin(admin.ModelAdmin):
    form = SystemParameterForm
    list_display = ['param_key', 'param_value', 'param_type', 'description', 'is_editable', 'updated_at']
    list_editable = ['param_value']  # 允许在列表页直接编辑
    list_filter = ['param_type', 'is_editable']
    search_fields = ['param_key', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_readonly_fields(self, request, obj=None):
        if obj and not obj.is_editable:
            return self.readonly_fields + ['param_key', 'param_value', 'param_type']
        return self.readonly_fields
    
    # 自定义字段显示
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # 为不同的参数添加帮助文本
        help_texts = {
            'FastChargingPileNum': '快充电桩数量，修改后会自动同步充电桩数据',
            'TrickleChargingPileNum': '慢充电桩数量，修改后会自动同步充电桩数据',
            'WaitingAreaSize': '等候区最大容量，超过此数量将无法加入排队',
            'ChargingQueueLen': '每个充电桩的最大排队长度',
            'peak_rate': '峰时电价(元/kWh)，时段：10:00-15:00, 18:00-21:00',
            'normal_rate': '平时电价(元/kWh)，时段：07:00-10:00, 15:00-18:00, 21:00-23:00',
            'valley_rate': '谷时电价(元/kWh)，时段：23:00-07:00',
            'service_rate': '服务费(元/kWh)',
        }
        
        if obj and obj.param_key in help_texts:
            form.base_fields['param_value'].help_text = help_texts[obj.param_key]
        
        return form
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        # 如果修改了充电桩数量，同步充电桩数据
        if obj.param_key in ['FastChargingPileNum', 'TrickleChargingPileNum']:
            self._sync_charging_piles()
    
    def _sync_charging_piles(self):
        """同步充电桩数据"""
        try:
            fast_count = SystemParameter.objects.get(param_key='FastChargingPileNum').get_value()
            slow_count = SystemParameter.objects.get(param_key='TrickleChargingPileNum').get_value()
            
            # 同步快充桩
            current_fast = ChargingPile.objects.filter(pile_type='fast').count()
            if fast_count > current_fast:
                # 需要增加快充桩
                for i in range(current_fast + 1, fast_count + 1):
                    ChargingPile.objects.create(
                        pile_id=f'FAST-{i:03d}',
                        pile_type='fast',
                        status='normal'
                    )
            elif fast_count < current_fast:
                # 需要减少快充桩（只删除未使用的）
                excess_piles = ChargingPile.objects.filter(
                    pile_type='fast',
                    is_working=False
                ).order_by('-pile_id')[:(current_fast - fast_count)]
                for pile in excess_piles:
                    pile.delete()
            
            # 同步慢充桩
            current_slow = ChargingPile.objects.filter(pile_type='slow').count()
            if slow_count > current_slow:
                # 需要增加慢充桩
                for i in range(current_slow + 1, slow_count + 1):
                    ChargingPile.objects.create(
                        pile_id=f'SLOW-{i:03d}',
                        pile_type='slow',
                        status='normal'
                    )
            elif slow_count < current_slow:
                # 需要减少慢充桩（只删除未使用的）
                excess_piles = ChargingPile.objects.filter(
                    pile_type='slow',
                    is_working=False
                ).order_by('-pile_id')[:(current_slow - slow_count)]
                for pile in excess_piles:
                    pile.delete()
                    
        except SystemParameter.DoesNotExist:
            pass  # 参数不存在时忽略

@admin.register(ChargingPile)
class ChargingPileAdmin(admin.ModelAdmin):
    list_display = ['pile_id', 'pile_type', 'status', 'is_working', 'total_sessions', 'total_revenue']
    list_filter = ['pile_type', 'status', 'is_working']
    search_fields = ['pile_id']
    readonly_fields = ['total_sessions', 'total_duration', 'total_energy', 'total_revenue', 'created_at', 'updated_at']
    
    # 按类型分组显示
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('pile_type', 'pile_id')

@admin.register(ChargingRequest)
class ChargingRequestAdmin(admin.ModelAdmin):
    list_display = ['queue_number', 'user', 'charging_mode', 'current_status', 'progress_display', 'queue_position', 'created_at']
    list_filter = ['charging_mode', 'current_status', 'created_at']
    search_fields = ['queue_number', 'user__username']
    readonly_fields = ['queue_number', 'queue_position', 'estimated_wait_time', 'created_at', 'updated_at']
    actions = ['update_progress_5kwh', 'update_progress_10kwh', 'set_progress_50percent', 'complete_charging_action']
    
    def progress_display(self, obj):
        """显示充电进度"""
        if obj.current_status == 'charging':
            percentage = (obj.current_amount / obj.requested_amount) * 100
            return format_html(
                '<div style="width: 100px; height: 20px; background-color: #f0f0f0; border-radius: 10px; position: relative;">'
                '<div style="width: {:.1f}%; height: 100%; background-color: #4CAF50; border-radius: 10px;"></div>'
                '<span style="position: absolute; top: 0; left: 0; right: 0; text-align: center; line-height: 20px; font-size: 12px;">{:.1f}%</span>'
                '</div>',
                percentage, percentage
            )
        elif obj.current_status == 'completed':
            return format_html('<span style="color: green;">✅ 已完成</span>')
        elif obj.current_status == 'waiting':
            return format_html('<span style="color: orange;">⏳ 等待中</span>')
        else:
            return format_html('<span style="color: gray;">➖ 已取消</span>')
    progress_display.short_description = '充电进度'
    
    def _update_progress(self, charging_request, amount_change):
        """更新充电进度"""
        new_amount = max(0, min(
            charging_request.current_amount + amount_change,
            charging_request.requested_amount
        ))
        charging_request.current_amount = new_amount
        charging_request.save()
        
        # 更新会话数据
        if hasattr(charging_request, 'session'):
            session = charging_request.session
            session.charging_amount = new_amount
            session.save()
        
        # 检查是否完成
        if new_amount >= charging_request.requested_amount:
            self._complete_charging(charging_request)
    
    def _complete_charging(self, charging_request):
        """完成充电"""
        from .services import BillingService, ChargingQueueService
        
        with transaction.atomic():
            # 更新请求状态
            charging_request.current_status = 'completed'
            charging_request.end_time = timezone.now()
            charging_request.current_amount = charging_request.requested_amount
            charging_request.save()
            
            # 更新会话
            if hasattr(charging_request, 'session'):
                session = charging_request.session
                session.end_time = timezone.now()
                session.charging_amount = charging_request.requested_amount
                
                # 计算费用
                billing_service = BillingService()
                billing_service.calculate_bill(session)
                session.save()
            
            # 释放充电桩
            if charging_request.charging_pile:
                pile = charging_request.charging_pile
                pile.is_working = False
                pile.save()
                
                # 处理下一个排队请求
                queue_service = ChargingQueueService()
                queue_service.process_next_in_queue(pile)
            
            # 创建完成通知
            Notification.objects.create(
                user=charging_request.user,
                type='charging_complete',
                message=f'您的充电请求 {charging_request.queue_number} 已完成'
            )
    
    # Admin Actions
    def update_progress_5kwh(self, request, queryset):
        """增加5kWh充电量"""
        count = 0
        for obj in queryset.filter(current_status='charging'):
            self._update_progress(obj, 5)
            count += 1
        self.message_user(request, f'已为 {count} 个充电请求增加 5kWh')
    update_progress_5kwh.short_description = "增加 5kWh 充电量"
    
    def update_progress_10kwh(self, request, queryset):
        """增加10kWh充电量"""
        count = 0
        for obj in queryset.filter(current_status='charging'):
            self._update_progress(obj, 10)
            count += 1
        self.message_user(request, f'已为 {count} 个充电请求增加 10kWh')
    update_progress_10kwh.short_description = "增加 10kWh 充电量"
    
    def set_progress_50percent(self, request, queryset):
        """设置进度到50%"""
        count = 0
        for obj in queryset.filter(current_status='charging'):
            target = obj.requested_amount * 0.5
            obj.current_amount = min(target, obj.requested_amount)
            obj.save()
            count += 1
        self.message_user(request, f'已为 {count} 个充电请求设置到 50%% 进度')
    set_progress_50percent.short_description = "设置进度到 50%%"
    
    def complete_charging_action(self, request, queryset):
        """完成充电"""
        count = 0
        for obj in queryset.filter(current_status='charging'):
            self._complete_charging(obj)
            count += 1
        self.message_user(request, f'已完成 {count} 个充电请求')
    complete_charging_action.short_description = "完成充电"
    
    # 按状态和创建时间排序
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('current_status', 'created_at')

@admin.register(ChargingSession)
class ChargingSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'pile', 'start_time', 'end_time', 'charging_amount', 'total_cost']
    list_filter = ['start_time', 'pile__pile_type']
    search_fields = ['user__username', 'pile__pile_id']
    readonly_fields = ['id', 'created_at']
    
    # 显示费用明细
    fieldsets = (
        ('基本信息', {
            'fields': ('id', 'request', 'pile', 'user', 'created_at')
        }),
        ('充电信息', {
            'fields': ('start_time', 'end_time', 'charging_amount', 'charging_duration')
        }),
        ('时段分布', {
            'fields': ('peak_hours', 'normal_hours', 'valley_hours')
        }),
        ('费用明细', {
            'fields': ('peak_cost', 'normal_cost', 'valley_cost', 'service_cost', 'total_cost')
        }),
    )

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'message_preview', 'read', 'created_at']
    list_filter = ['type', 'read', 'created_at']
    search_fields = ['user__username', 'message']
    readonly_fields = ['created_at']
    
    def message_preview(self, obj):
        """显示消息预览"""
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = '消息预览'
    
    # 按创建时间倒序
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-created_at')
