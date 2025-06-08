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
from django.http import JsonResponse
from django.utils.safestring import mark_safe

# 自定义系统参数表单
# class SystemParameterForm(ModelForm):
#     class Meta:
#         model = SystemParameter
#         fields = '__all__'
    
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         if self.instance and self.instance.param_type == 'json':
#             # 为JSON类型的参数提供更友好的编辑界面
#             self.fields['param_value'].widget = forms.Textarea(attrs={'rows': 10})
    
#     def clean_param_value(self):
#         value = self.cleaned_data['param_value']
#         param_key = self.cleaned_data.get('param_key')
#         param_type = self.cleaned_data.get('param_type')
        
#         # 对四个核心参数进行验证
#         if param_key in ['FastChargingPileNum', 'TrickleChargingPileNum', 'WaitingAreaSize', 'ChargingQueueLen']:
#             try:
#                 int_value = int(value)
#                 if int_value <= 0:
#                     raise ValidationError(f'{param_key} 必须是正整数')
#             except ValueError:
#                 raise ValidationError(f'{param_key} 必须是有效的整数')
        
#         # 对费率参数进行验证
#         elif param_key in ['peak_rate', 'normal_rate', 'valley_rate', 'service_rate']:
#             try:
#                 float_value = float(value)
#                 if float_value < 0:
#                     raise ValidationError(f'{param_key} 不能为负数')
#             except ValueError:
#                 raise ValidationError(f'{param_key} 必须是有效的数字')
        
#         # 根据参数类型验证
#         if param_type == 'int':
#             try:
#                 int(value)
#             except ValueError:
#                 raise ValidationError('整数类型参数值必须是有效的整数')
#         elif param_type == 'float':
#             try:
#                 float(value)
#             except ValueError:
#                 raise ValidationError('浮点数类型参数值必须是有效的数字')
#         elif param_type == 'boolean':
#             if value.lower() not in ('true', 'false', '1', '0', 'yes', 'no'):
#                 raise ValidationError('布尔类型参数值必须是 true/false, 1/0, yes/no')
#         elif param_type == 'json':
#             try:
#                 import json
#                 json.loads(value)
#             except json.JSONDecodeError:
#                 raise ValidationError('JSON类型参数值必须是有效的JSON格式')
        
#         return value

# @admin.register(SystemParameter)
# class SystemParameterAdmin(admin.ModelAdmin):
#     form = SystemParameterForm
#     list_display = ['param_key', 'param_value', 'param_type', 'description', 'is_editable', 'updated_at']
#     list_editable = ['param_value']  # 允许在列表页直接编辑
#     list_filter = ['param_type', 'is_editable']
#     search_fields = ['param_key', 'description']
#     readonly_fields = ['created_at', 'updated_at']
    
#     def get_readonly_fields(self, request, obj=None):
#         if obj and not obj.is_editable:
#             return self.readonly_fields + ['param_key', 'param_value', 'param_type']
#         return self.readonly_fields
    
#     # 自定义字段显示
#     def get_form(self, request, obj=None, **kwargs):
#         form = super().get_form(request, obj, **kwargs)
        
#         # 为不同的参数添加帮助文本
#         help_texts = {
#             'FastChargingPileNum': '快充电桩数量，修改后会自动同步充电桩数据',
#             'TrickleChargingPileNum': '慢充电桩数量，修改后会自动同步充电桩数据',
#             'WaitingAreaSize': '等候区最大容量，超过此数量将无法加入排队',
#             'ChargingQueueLen': '每个充电桩的最大排队长度',
#             'peak_rate': '峰时电价(元/kWh)，时段：10:00-15:00, 18:00-21:00',
#             'normal_rate': '平时电价(元/kWh)，时段：07:00-10:00, 15:00-18:00, 21:00-23:00',
#             'valley_rate': '谷时电价(元/kWh)，时段：23:00-07:00',
#             'service_rate': '服务费(元/kWh)',
#         }
        
#         if obj and obj.param_key in help_texts:
#             form.base_fields['param_value'].help_text = help_texts[obj.param_key]
        
#         return form
    
#     def save_model(self, request, obj, form, change):
#         super().save_model(request, obj, form, change)
        
#         # 如果修改了充电桩数量，同步充电桩数据
#         if obj.param_key in ['FastChargingPileNum', 'TrickleChargingPileNum']:
#             self._sync_charging_piles()
    
#     def _sync_charging_piles(self):
#         """同步充电桩数据"""
#         try:
#             fast_count = SystemParameter.objects.get(param_key='FastChargingPileNum').get_value()
#             slow_count = SystemParameter.objects.get(param_key='TrickleChargingPileNum').get_value()
            
#             # 同步快充桩
#             current_fast = ChargingPile.objects.filter(pile_type='fast').count()
#             if fast_count > current_fast:
#                 # 需要增加快充桩
#                 for i in range(current_fast + 1, fast_count + 1):
#                     ChargingPile.objects.create(
#                         pile_id=f'FAST-{i:03d}',
#                         pile_type='fast',
#                         status='normal'
#                     )
#             elif fast_count < current_fast:
#                 # 需要减少快充桩（只删除未使用的）
#                 excess_piles = ChargingPile.objects.filter(
#                     pile_type='fast',
#                     is_working=False
#                 ).order_by('-pile_id')[:(current_fast - fast_count)]
#                 for pile in excess_piles:
#                     pile.delete()
            
#             # 同步慢充桩
#             current_slow = ChargingPile.objects.filter(pile_type='slow').count()
#             if slow_count > current_slow:
#                 # 需要增加慢充桩
#                 for i in range(current_slow + 1, slow_count + 1):
#                     ChargingPile.objects.create(
#                         pile_id=f'SLOW-{i:03d}',
#                         pile_type='slow',
#                         status='normal'
#                     )
#             elif slow_count < current_slow:
#                 # 需要减少慢充桩（只删除未使用的）
#                 excess_piles = ChargingPile.objects.filter(
#                     pile_type='slow',
#                     is_working=False
#                 ).order_by('-pile_id')[:(current_slow - slow_count)]
#                 for pile in excess_piles:
#                     pile.delete()
                    
#         except SystemParameter.DoesNotExist:
#             pass  # 参数不存在时忽略

@admin.register(ChargingPile)
class ChargingPileAdmin(admin.ModelAdmin):
    list_display = ['pile_id', 'pile_type', 'status', 'is_working', 'charging_power', 'max_queue_size', 'queue_status_display', 'estimated_remaining_time', 'total_sessions', 'total_revenue']
    list_filter = ['pile_type', 'status', 'is_working']
    search_fields = ['pile_id']
    readonly_fields = ['estimated_remaining_time', 'total_sessions', 'total_duration', 'total_energy', 'total_revenue', 'current_charging_display', 'queue_detail_display', 'created_at', 'updated_at']
    list_editable = ['charging_power', 'max_queue_size']
    
    def queue_status_display(self, obj):
        """显示队列状态摘要"""
        queue_count = obj.get_queue_count()
        current_charging = ChargingRequest.objects.filter(
            charging_pile=obj,
            current_status='charging'
        ).first()
        
        status_parts = []
        if current_charging:
            progress = (current_charging.current_amount / current_charging.requested_amount) * 100
            status_parts.append(f'充电中({progress:.1f}%)')
        else:
            status_parts.append('空闲' if obj.status == 'normal' else obj.get_status_display())
            
        if queue_count > 0:
            status_parts.append(f'队列{queue_count}人')
        
        return ' | '.join(status_parts)
    queue_status_display.short_description = '队列状态'
    
    def current_charging_display(self, obj):
        """显示当前充电详情"""
        current_charging = ChargingRequest.objects.filter(
            charging_pile=obj,
            current_status='charging'
        ).first()
        
        if current_charging:
            progress = (current_charging.current_amount / current_charging.requested_amount) * 100
            return format_html(
                '<div style="padding: 10px; background: #f8f9fa; border-radius: 5px;">'
                '<strong>正在充电：</strong> {}<br>'
                '<strong>用户：</strong> {}<br>'
                '<strong>进度：</strong> {:.1f} / {:.1f} kWh ({:.1f}%)<br>'
                '<strong>开始时间：</strong> {}<br>'
                '<strong>预计剩余：</strong> {}分钟'
                '</div>',
                current_charging.queue_number,
                current_charging.user.username,
                current_charging.current_amount,
                current_charging.requested_amount,
                progress,
                current_charging.start_time.strftime('%Y-%m-%d %H:%M:%S') if current_charging.start_time else 'N/A',
                obj.estimated_remaining_time
            )
        else:
            return format_html('<span style="color: #6c757d;">无充电任务</span>')
    current_charging_display.short_description = '当前充电'
    
    def queue_detail_display(self, obj):
        """显示详细队列信息"""
        queue_requests = ChargingRequest.objects.filter(
            charging_pile=obj,
            queue_level='pile_queue'
        ).order_by('pile_queue_position')[:5]  # 显示前5个
        
        if not queue_requests.exists():
            return format_html('<span style="color: #6c757d;">队列为空</span>')
        
        html_parts = ['<div style="padding: 10px; background: #fff3cd; border-radius: 5px;">']
        html_parts.append(f'<strong>队列容量：</strong> {queue_requests.count()}/{obj.max_queue_size}<br>')
        html_parts.append('<strong>队列详情：</strong><br>')
        
        for req in queue_requests:
            wait_time = req.estimated_wait_time
            html_parts.append(
                f'<span style="margin-left: 10px;">'
                f'{req.pile_queue_position}. {req.queue_number} '
                f'({req.user.username}) - '
                f'{req.requested_amount}kWh, '
                f'等待{wait_time}分钟'
                f'</span><br>'
            )
        
        if queue_requests.count() >= 5:
            html_parts.append('<span style="color: #6c757d; margin-left: 10px;">...</span>')
        
        html_parts.append('</div>')
        return format_html(''.join(html_parts))
    queue_detail_display.short_description = '队列详情'
    
    # 按类型分组显示
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('pile_type', 'pile_id')

@admin.register(ChargingRequest)
class ChargingRequestAdmin(admin.ModelAdmin):
    list_display = ['queue_number', 'user', 'vehicle', 'charging_mode', 'current_status', 'queue_level', 'queue_position_display', 'progress_display', 'queue_status_display', 'created_at']
    list_filter = ['charging_mode', 'current_status', 'queue_level', 'created_at']
    search_fields = ['queue_number', 'user__username', 'vehicle__license_plate']
    readonly_fields = ['queue_number', 'queue_level', 'external_queue_position', 'pile_queue_position', 'estimated_wait_time', 'queue_detail_display', 'created_at', 'updated_at']
    actions = ['update_progress_5kwh', 'update_progress_10kwh', 'set_progress_50percent', 'complete_charging_action']
    
    def queue_position_display(self, obj):
        """显示队列位置"""
        if obj.queue_level == 'external_waiting':
            return format_html(
                '<span style="background: #d1ecf1; padding: 2px 6px; border-radius: 3px; color: #0c5460;">'
                '外部等候区 #{}'
                '</span>',
                obj.external_queue_position
            )
        elif obj.queue_level == 'pile_queue':
            return format_html(
                '<span style="background: #fff3cd; padding: 2px 6px; border-radius: 3px; color: #856404;">'
                '桩{} #{}'
                '</span>',
                obj.charging_pile.pile_id if obj.charging_pile else 'N/A',
                obj.pile_queue_position
            )
        elif obj.queue_level == 'charging':
            return format_html(
                '<span style="background: #d4edda; padding: 2px 6px; border-radius: 3px; color: #155724;">'
                '充电中@{}'
                '</span>',
                obj.charging_pile.pile_id if obj.charging_pile else 'N/A'
            )
        else:
            return format_html(
                '<span style="background: #f8d7da; padding: 2px 6px; border-radius: 3px; color: #721c24;">'
                '{}'
                '</span>',
                obj.get_queue_level_display()
            )
    queue_position_display.short_description = '队列位置'
    
    def queue_detail_display(self, obj):
        """显示详细队列信息"""
        html_parts = ['<div style="padding: 10px; background: #f8f9fa; border-radius: 5px;">']
        
        # 基本信息
        html_parts.append(f'<strong>队列编号：</strong> {obj.queue_number}<br>')
        html_parts.append(f'<strong>队列层级：</strong> {obj.get_queue_level_display()}<br>')
        
        # 根据不同层级显示不同信息
        if obj.queue_level == 'external_waiting':
            html_parts.append(f'<strong>外部等候区位置：</strong> 第{obj.external_queue_position}位<br>')
            
            # 显示同模式的外部等候区情况
            same_mode_count = ChargingRequest.objects.filter(
                charging_mode=obj.charging_mode,
                queue_level='external_waiting'
            ).count()
            html_parts.append(f'<strong>同模式等待：</strong> 共{same_mode_count}人<br>')
            
        elif obj.queue_level == 'pile_queue':
            html_parts.append(f'<strong>分配充电桩：</strong> {obj.charging_pile.pile_id}<br>')
            html_parts.append(f'<strong>桩队列位置：</strong> 第{obj.pile_queue_position}位<br>')
            
            # 显示桩的状态
            if obj.charging_pile:
                pile_status = "正在使用" if obj.charging_pile.is_working else "空闲"
                html_parts.append(f'<strong>桩状态：</strong> {pile_status}<br>')
                html_parts.append(f'<strong>桩队列容量：</strong> {obj.charging_pile.get_queue_count()}/{obj.charging_pile.max_queue_size}<br>')
            
        elif obj.queue_level == 'charging':
            html_parts.append(f'<strong>充电桩：</strong> {obj.charging_pile.pile_id}<br>')
            if obj.start_time:
                from django.utils import timezone
                duration = timezone.now() - obj.start_time
                html_parts.append(f'<strong>充电时长：</strong> {duration.total_seconds() // 60:.0f}分钟<br>')
        
        html_parts.append(f'<strong>预计等待时间：</strong> {obj.estimated_wait_time}分钟<br>')
        html_parts.append(f'<strong>请求充电量：</strong> {obj.requested_amount} kWh<br>')
        html_parts.append(f'<strong>当前充电量：</strong> {obj.current_amount} kWh<br>')
        
        html_parts.append('</div>')
        return format_html(''.join(html_parts))
    queue_detail_display.short_description = '队列详情'
    
    def queue_status_display(self, obj):
        """显示队列状态"""
        return obj.get_queue_status_display()
    queue_status_display.short_description = '队列状态'
    
    def progress_display(self, obj):
        """显示充电进度"""
        if obj.current_status == 'charging':
            percentage = (obj.current_amount / obj.requested_amount) * 100
            return format_html(
                '<div style="width: 100px; height: 20px; background-color: #f0f0f0; border-radius: 10px; position: relative;">'
                '<div style="width: {}%; height: 100%; background-color: #4CAF50; border-radius: 10px;"></div>'
                '<span style="position: absolute; top: 0; left: 0; right: 0; text-align: center; line-height: 20px; font-size: 12px;">{}%</span>'
                '</div>',
                '{:.1f}'.format(percentage), '{:.1f}'.format(percentage)
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
        from .services import BillingService, AdvancedChargingQueueService
        
        with transaction.atomic():
            # 使用新的队列服务完成充电
            queue_service = AdvancedChargingQueueService()
            queue_service.complete_charging(charging_request)
            
            # 计算费用
            if hasattr(charging_request, 'session'):
                session = charging_request.session
                billing_service = BillingService()
                billing_service.calculate_bill(session)
                session.save()
    
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

# 添加队列状态管理视图
class QueueStatusView:
    """队列状态管理视图"""
    
    def changelist_view(self, request, extra_context=None):
        """队列状态总览页面"""
        from .services import AdvancedChargingQueueService
        from .models import ChargingPile, ChargingRequest
        
        # 获取队列服务
        queue_service = AdvancedChargingQueueService()
        
        # 获取快充和慢充的队列状态
        fast_status = queue_service.get_queue_status('fast')
        slow_status = queue_service.get_queue_status('slow')
        
        # 系统统计
        stats = {
            'total_piles': ChargingPile.objects.count(),
            'working_piles': ChargingPile.objects.filter(is_working=True).count(),
            'fault_piles': ChargingPile.objects.filter(status='fault').count(),
            'offline_piles': ChargingPile.objects.filter(status='offline').count(),
            'total_waiting': ChargingRequest.objects.filter(current_status='waiting').count(),
            'total_charging': ChargingRequest.objects.filter(current_status='charging').count(),
            'external_waiting': ChargingRequest.objects.filter(queue_level='external_waiting').count(),
            'pile_queue_waiting': ChargingRequest.objects.filter(queue_level='pile_queue').count(),
        }
        
        extra_context = extra_context or {}
        extra_context.update({
            'title': '充电队列状态总览',
            'fast_status': fast_status,
            'slow_status': slow_status,
            'stats': stats,
            'has_permission': True,
        })
        
        return render(request, 'admin/charging/queue_status.html', extra_context)
    
    def refresh_view(self, request):
        """刷新队列状态的AJAX接口"""
        from .services import AdvancedChargingQueueService
        
        queue_service = AdvancedChargingQueueService()
        fast_status = queue_service.get_queue_status('fast')
        slow_status = queue_service.get_queue_status('slow')
        
        return JsonResponse({
            'fast_status': fast_status,
            'slow_status': slow_status,
        })

# 扩展admin site，添加队列状态视图
from django.contrib.admin import AdminSite

class ChargingAdminSite(AdminSite):
    """自定义admin site，添加队列状态功能"""
    
    def get_urls(self):
        urls = super().get_urls()
        queue_view = QueueStatusView()
        
        custom_urls = [
            path('charging/queue-status/', queue_view.changelist_view, name='charging_queue_status'),
            path('charging/queue-status/refresh/', queue_view.refresh_view, name='charging_queue_refresh'),
        ]
        return custom_urls + urls
    
    def index(self, request, extra_context=None):
        """自定义admin首页，添加队列状态链接"""
        extra_context = extra_context or {}
        extra_context['queue_status_url'] = '/admin/charging/queue-status/'
        return super().index(request, extra_context)

# 直接扩展默认admin site的URLs
def get_urls_with_queue_status():
    """为默认admin site添加队列状态URLs"""
    urls = original_get_urls()
    queue_view = QueueStatusView()
    
    custom_urls = [
        path('charging/queue-status/', queue_view.changelist_view, name='charging_queue_status'),
        path('charging/queue-status/refresh/', queue_view.refresh_view, name='charging_queue_refresh'),
    ]
    return custom_urls + urls

# 替换admin site的get_urls方法
original_get_urls = admin.site.get_urls
admin.site.get_urls = get_urls_with_queue_status
