from charging.utils.config_manager import get_config
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from .models import ChargingRequest, ChargingPile, SystemParameter, Notification
import logging

logger = logging.getLogger(__name__)

class ChargingQueueService:
    """充电排队服务"""
    
    def can_join_queue(self):
        """检查是否可以加入排队"""
        try:
            waiting_area_size = SystemParameter.objects.get(
                param_key='WaitingAreaSize'
            ).get_value()
            current_waiting = ChargingRequest.objects.filter(
                current_status='waiting'
            ).count()
            return current_waiting < waiting_area_size
        except SystemParameter.DoesNotExist:
            return True  # 如果没有配置，默认允许
    
    def add_to_queue(self, charging_request):
        """添加到排队"""
        # 计算排队位置
        same_mode_waiting = ChargingRequest.objects.filter(
            charging_mode=charging_request.charging_mode,
            current_status='waiting'
        ).count()
        
        charging_request.queue_position = same_mode_waiting + 1
        charging_request.estimated_wait_time = self._calculate_wait_time(charging_request)
        charging_request.save()
        
        # 尝试立即分配充电桩
        self._try_assign_pile(charging_request)
    
    def _calculate_wait_time(self, charging_request):
        """计算预计等待时间"""
        # 简化计算：每个前面的请求预计30分钟
        ahead_count = charging_request.queue_position - 1
        return ahead_count * 30
    
    def _try_assign_pile(self, charging_request):
        """尝试分配充电桩"""
        available_pile = ChargingPile.objects.filter(
            pile_type=charging_request.charging_mode,
            status='normal',
            is_working=False
        ).first()
        
        if available_pile:
            self._start_charging(charging_request, available_pile)
    
    def _start_charging(self, charging_request, pile):
        """开始充电"""
        with transaction.atomic():
            charging_request.charging_pile = pile
            charging_request.current_status = 'charging'
            charging_request.start_time = timezone.now()
            charging_request.save()
            
            pile.is_working = True
            pile.save()
            
            # 创建充电会话
            from .models import ChargingSession
            ChargingSession.objects.create(
                request=charging_request,
                pile=pile,
                user=charging_request.user,
                start_time=timezone.now()
            )
            
            # 发送通知
            Notification.objects.create(
                user=charging_request.user,
                type='charging_start',
                message=f'您的充电请求 {charging_request.queue_number} 已开始充电，充电桩：{pile.pile_id}'
            )
    
    def process_next_in_queue(self, pile):
        """处理下一个排队请求"""
        next_request = ChargingRequest.objects.filter(
            charging_mode=pile.pile_type,
            current_status='waiting'
        ).order_by('queue_position').first()
        
        if next_request:
            self._start_charging(next_request, pile)

class BillingService:
    """计费服务"""
    
    def calculate_bill(self, session):
        """计算账单"""
        if not session.end_time:
            session.end_time = timezone.now()
        
        # 计算充电时长
        duration = session.end_time - session.start_time
        session.charging_duration = duration.total_seconds() / 3600  # 转换为小时
        
        # 模拟充电量（实际应该从充电桩获取）
        session.charging_amount = session.request.requested_amount
        
        # 计算分时段费用
        self._calculate_time_based_cost(session)
        
        # 计算服务费
        service_rate = self._get_parameter('service_rate', '0.8')
        session.service_cost = Decimal(str(session.charging_amount)) * Decimal(service_rate)
        
        # 计算总费用
        session.total_cost = (session.peak_cost + session.normal_cost + 
                            session.valley_cost + session.service_cost)
    
    def _calculate_time_based_cost(self, session):
        """计算分时段费用"""
        # 简化实现：根据开始时间判断时段
        start_hour = session.start_time.hour
        
        # 获取费率
        peak_rate = Decimal(self._get_parameter('peak_rate', '1.2'))
        normal_rate = Decimal(self._get_parameter('normal_rate', '0.8'))
        valley_rate = Decimal(self._get_parameter('valley_rate', '0.4'))
        
        # 简化：整个充电时段使用同一费率
        if 10 <= start_hour < 15 or 18 <= start_hour < 21:
            # 峰时
            session.peak_hours = session.charging_duration
            session.peak_cost = Decimal(str(session.charging_amount)) * peak_rate
        elif 23 <= start_hour or start_hour < 7:
            # 谷时
            session.valley_hours = session.charging_duration
            session.valley_cost = Decimal(str(session.charging_amount)) * valley_rate
        else:
            # 平时
            session.normal_hours = session.charging_duration
            session.normal_cost = Decimal(str(session.charging_amount)) * normal_rate
    
    def _get_parameter(self, key, default):
        """获取系统参数"""
        try:
            return SystemParameter.objects.get(param_key=key).get_value()
        except SystemParameter.DoesNotExist:
            return default
