from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from .models import ChargingPile, ChargingRequest, ChargingSession, SystemParameter, Notification

# 自定义系统参数表单
class SystemParameterForm(ModelForm):
    class Meta:
        model = SystemParameter
        fields = '__all__'
    
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
    list_display = ['queue_number', 'user', 'charging_mode', 'current_status', 'queue_position', 'created_at']
    list_filter = ['charging_mode', 'current_status', 'created_at']
    search_fields = ['queue_number', 'user__username']
    readonly_fields = ['queue_number', 'queue_position', 'estimated_wait_time', 'created_at', 'updated_at']
    
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
