from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

# Create your models here.

class SystemParameter(models.Model):
    PARAM_TYPE_CHOICES = [
        ('int', '整数'),
        ('float', '浮点数'),
        ('string', '字符串'),
        ('boolean', '布尔值'),
        ('json', 'JSON'),
    ]
    
    param_key = models.CharField(max_length=100, unique=True, verbose_name='参数键')
    param_value = models.TextField(verbose_name='参数值')
    param_type = models.CharField(max_length=20, choices=PARAM_TYPE_CHOICES, default='string', verbose_name='参数类型')
    description = models.CharField(max_length=255, blank=True, verbose_name='参数描述')
    is_editable = models.BooleanField(default=True, verbose_name='是否可编辑')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'system_parameters'
        verbose_name = '系统参数'
        verbose_name_plural = '系统参数'
    
    def get_value(self):
        """根据类型返回正确的值"""
        if self.param_type == 'int':
            return int(self.param_value)
        elif self.param_type == 'float':
            return float(self.param_value)
        elif self.param_type == 'boolean':
            return self.param_value.lower() in ('true', '1', 'yes')
        elif self.param_type == 'json':
            import json
            return json.loads(self.param_value)
        return self.param_value
    
    def set_value(self, value):
        """设置值并自动转换为字符串"""
        if self.param_type == 'json':
            import json
            self.param_value = json.dumps(value)
        else:
            self.param_value = str(value)






User = get_user_model()

class ChargingPile(models.Model):
    """充电桩模型"""
    PILE_TYPES = [
        ('fast', '快充'),
        ('slow', '慢充'),
    ]
    
    STATUS_CHOICES = [
        ('normal', '正常'),
        ('fault', '故障'),
        ('offline', '离线'),
    ]
    
    pile_id = models.CharField(max_length=20, unique=True, primary_key=True)
    pile_type = models.CharField(max_length=10, choices=PILE_TYPES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='normal')
    is_working = models.BooleanField(default=False)  # 是否正在工作
    
    # 多级队列系统新增字段
    max_queue_size = models.IntegerField(default=3, verbose_name='桩队列最大容量')
    charging_power = models.FloatField(default=120.0, verbose_name='充电功率(kW)', help_text='快充通常120kW，慢充7kW')
    estimated_remaining_time = models.IntegerField(default=0, verbose_name='预计剩余时间(分钟)')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # 统计信息
    total_sessions = models.IntegerField(default=0)
    total_duration = models.FloatField(default=0.0)  # 小时
    total_energy = models.FloatField(default=0.0)    # kWh
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    class Meta:
        db_table = 'charging_pile'
        verbose_name = '充电桩'
        verbose_name_plural = '充电桩'
    
    def __str__(self):
        return f"{self.pile_id} ({self.get_pile_type_display()})"
    
    def get_queue_count(self):
        """获取当前桩队列中的请求数量"""
        return ChargingRequest.objects.filter(
            charging_pile=self,
            queue_level='pile_queue'
        ).count()
    
    def is_queue_full(self):
        """检查桩队列是否已满"""
        return self.get_queue_count() >= self.max_queue_size
    
    def calculate_remaining_time(self):
        """计算该桩的预计剩余时间"""
        # 获取当前正在充电的请求
        current_charging = ChargingRequest.objects.filter(
            charging_pile=self,
            current_status='charging'
        ).first()
        
        # 获取桩队列中的所有请求
        pile_queue = ChargingRequest.objects.filter(
            charging_pile=self,
            queue_level='pile_queue'
        ).order_by('pile_queue_position')
        
        total_time = 0
        
        # 计算当前充电请求的剩余时间
        if current_charging:
            remaining_amount = current_charging.requested_amount - current_charging.current_amount
            current_remaining = (remaining_amount / self.charging_power) * 60  # 转换为分钟
            total_time += current_remaining
        
        # 计算队列中所有请求的时间
        for request in pile_queue:
            charging_time = (request.requested_amount / self.charging_power) * 60
            total_time += charging_time
        
        self.estimated_remaining_time = int(total_time)
        self.save(update_fields=['estimated_remaining_time'])
        return self.estimated_remaining_time

class ChargingRequest(models.Model):
    """充电请求模型"""
    MODE_CHOICES = [
        ('fast', '快充'),
        ('slow', '慢充'),
    ]
    
    STATUS_CHOICES = [
        ('waiting', '等待中'),
        ('charging', '充电中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]
    
    # 多级队列层级选择
    QUEUE_LEVEL_CHOICES = [
        ('external_waiting', '外部等候区'),
        ('pile_queue', '充电桩队列'),
        ('charging', '正在充电'),
        ('completed', '已完成'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charging_requests')
    vehicle = models.ForeignKey('accounts.Vehicle', on_delete=models.CASCADE, related_name='charging_requests', verbose_name='车辆', null=True, blank=True)
    queue_number = models.CharField(max_length=20, unique=True)
    charging_mode = models.CharField(max_length=10, choices=MODE_CHOICES)
    requested_amount = models.FloatField()  # 请求充电量 kWh
    battery_capacity = models.FloatField()  # 电池容量 kWh
    current_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='waiting')
    
    # 多级队列系统字段
    queue_level = models.CharField(max_length=20, choices=QUEUE_LEVEL_CHOICES, default='external_waiting', verbose_name='队列层级')
    external_queue_position = models.IntegerField(default=0, verbose_name='外部等候区位置')
    pile_queue_position = models.IntegerField(default=0, verbose_name='桩队列位置')
    estimated_wait_time = models.IntegerField(default=0, verbose_name='预计等待时间(分钟)')
    
    # 充电信息
    charging_pile = models.ForeignKey(ChargingPile, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='分配的充电桩')
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    current_amount = models.FloatField(default=0.0)  # 当前已充电量
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'charging_request'
        verbose_name = '充电请求'
        verbose_name_plural = '充电请求'
        ordering = ['created_at']
        # 约束：同一车辆不能有多个活跃请求
        constraints = [
            models.UniqueConstraint(
                fields=['vehicle'],
                condition=models.Q(current_status__in=['waiting', 'charging']),
                name='unique_active_request_per_vehicle'
            )
        ]
    
    def __str__(self):
        vehicle_plate = self.vehicle.license_plate if self.vehicle else "未关联车辆"
        return f"{self.queue_number} - {self.user.username} - {vehicle_plate}"
    
    def save(self, *args, **kwargs):
        if not self.queue_number:
            # 生成队列号
            prefix = 'F' if self.charging_mode == 'fast' else 'S'
            timestamp = timezone.now().strftime('%m%d%H%M')
            count = ChargingRequest.objects.filter(
                charging_mode=self.charging_mode,
                created_at__date=timezone.now().date()
            ).count() + 1
            self.queue_number = f"{prefix}{timestamp}{count:03d}"
        super().save(*args, **kwargs)
    
    def get_estimated_charging_time(self):
        """计算预计充电时间(分钟)"""
        if self.charging_pile:
            return (self.requested_amount / self.charging_pile.charging_power) * 60
        # 如果还没分配桩，使用默认功率
        default_power = 120 if self.charging_mode == 'fast' else 7
        return (self.requested_amount / default_power) * 60
    
    def get_queue_status_display(self):
        """获取队列状态的友好显示"""
        if self.queue_level == 'external_waiting':
            return f'外部等候区第{self.external_queue_position}位'
        elif self.queue_level == 'pile_queue':
            return f'桩{self.charging_pile.pile_id}队列第{self.pile_queue_position}位'
        elif self.queue_level == 'charging':
            return f'正在桩{self.charging_pile.pile_id}充电'
        else:
            return self.get_queue_level_display()

class ChargingSession(models.Model):
    """充电会话模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.OneToOneField(ChargingRequest, on_delete=models.CASCADE, related_name='session')
    pile = models.ForeignKey(ChargingPile, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    vehicle = models.ForeignKey('accounts.Vehicle', on_delete=models.CASCADE, related_name='charging_sessions', verbose_name='车辆', null=True, blank=True)
    
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    charging_amount = models.FloatField(default=0.0)  # 实际充电量
    charging_duration = models.FloatField(default=0.0)  # 充电时长(小时)
    
    # 费用计算
    peak_hours = models.FloatField(default=0.0)
    normal_hours = models.FloatField(default=0.0)
    valley_hours = models.FloatField(default=0.0)
    
    peak_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    normal_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    valley_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    service_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'charging_session'
        verbose_name = '充电会话'
        verbose_name_plural = '充电会话'
    
    def __str__(self):
        vehicle_plate = self.vehicle.license_plate if self.vehicle else "未关联车辆"
        return f"{self.user.username} - {vehicle_plate} - {self.pile.pile_id}"



class Notification(models.Model):
    """通知模型"""
    TYPE_CHOICES = [
        ('queue_update', '排队更新'),
        ('charging_start', '开始充电'),
        ('charging_complete', '充电完成'),
        ('pile_fault', '充电桩故障'),
        ('queue_transfer', '转入桩队列'),
        ('charging_mode_change', '充电类型变更'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notification'
        verbose_name = '通知'
        verbose_name_plural = '通知'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_type_display()}"