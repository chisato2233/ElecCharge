from charging.utils.parameter_manager import ParameterManager, get_queue_config
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from .models import ChargingRequest, ChargingPile, SystemParameter, Notification
import logging

logger = logging.getLogger(__name__)

class AdvancedChargingQueueService:
    """高级充电排队服务 - 多级队列系统"""
    
    def __init__(self):
        # 使用新的参数管理器获取配置
        queue_config = get_queue_config()
        self.external_waiting_limit = queue_config['external_waiting_area_size']
        
    def can_join_external_queue(self):
        """检查是否可以加入外部等候区"""
        try:
            current_external_waiting = ChargingRequest.objects.filter(
                queue_level='external_waiting'
            ).count()
            return current_external_waiting < self.external_waiting_limit
        except Exception as e:
            logger.error(f"检查外部等候区容量失败: {e}")
            return True
    
    def add_to_external_queue(self, charging_request):
        """添加到外部等候区"""
        with transaction.atomic():
            # 计算外部等候区位置
            same_mode_external = ChargingRequest.objects.filter(
                charging_mode=charging_request.charging_mode,
                queue_level='external_waiting'
            ).count()
            
            charging_request.queue_level = 'external_waiting'
            charging_request.external_queue_position = same_mode_external + 1
            charging_request.pile_queue_position = 0
            charging_request.current_status = 'waiting'
            
            # 计算预计等待时间
            charging_request.estimated_wait_time = self._calculate_external_wait_time(charging_request)
            charging_request.save()
            
            # 立即尝试转移到桩队列
            self._try_transfer_to_pile_queue(charging_request)
            
            logger.info(f"用户 {charging_request.user.username} 加入外部等候区，位置: {charging_request.external_queue_position}")
    
    def _calculate_external_wait_time(self, charging_request):
        """计算外部等候区的预计等待时间"""
        # 获取所有同模式的可用桩
        available_piles = ChargingPile.objects.filter(
            pile_type=charging_request.charging_mode,
            status='normal'
        )
        
        if not available_piles.exists():
            return 999  # 没有可用桩
        
        # 计算最短等待时间
        min_wait_time = float('inf')
        for pile in available_piles:
            pile_wait_time = pile.calculate_remaining_time()
            if not pile.is_queue_full():
                # 桩队列未满，可以直接加入
                min_wait_time = min(min_wait_time, pile_wait_time)
            else:
                # 桩队列已满，需要等待队列中的最后一个完成
                min_wait_time = min(min_wait_time, pile_wait_time + charging_request.get_estimated_charging_time())
        
        # 考虑前面等待的人数
        ahead_count = charging_request.external_queue_position - 1
        base_wait_time = min_wait_time if min_wait_time != float('inf') else 30
        
        return int(base_wait_time + ahead_count * 10)  # 每个前面的人额外等待10分钟
    
    def _try_transfer_to_pile_queue(self, charging_request):
        """尝试将请求从外部等候区转移到桩队列"""
        if charging_request.queue_level != 'external_waiting':
            return False
        
        # 查找最优桩（剩余时间最短且队列未满）
        best_pile = self._find_best_available_pile(charging_request.charging_mode)
        
        if best_pile:
            with transaction.atomic():
                # 转移到桩队列
                self._transfer_to_pile_queue(charging_request, best_pile)
                
                # 更新外部等候区位置
                self._update_external_queue_positions(charging_request.charging_mode, 
                                                   charging_request.external_queue_position)
                
                # 尝试开始充电
                self._try_start_charging(charging_request)
                
                return True
        
        return False
    
    def _find_best_available_pile(self, charging_mode):
        """找到最优的可用充电桩（剩余时间最短且队列未满）"""
        available_piles = ChargingPile.objects.filter(
            pile_type=charging_mode,
            status='normal'
        )
        
        best_pile = None
        min_wait_time = float('inf')
        
        for pile in available_piles:
            if not pile.is_queue_full():
                # 更新桩的剩余时间
                remaining_time = pile.calculate_remaining_time()
                
                if remaining_time < min_wait_time:
                    min_wait_time = remaining_time
                    best_pile = pile
        
        return best_pile
    
    def _transfer_to_pile_queue(self, charging_request, pile):
        """将请求转移到指定桩的队列"""
        # 计算在该桩队列中的位置
        pile_queue_count = pile.get_queue_count()
        
        charging_request.queue_level = 'pile_queue'
        charging_request.charging_pile = pile
        charging_request.pile_queue_position = pile_queue_count + 1
        charging_request.estimated_wait_time = pile.calculate_remaining_time()
        charging_request.save()
        
        # 发送通知
        Notification.objects.create(
            user=charging_request.user,
            type='queue_transfer',
            message=f'您的充电请求 {charging_request.queue_number} 已转入充电桩 {pile.pile_id} 的队列，位置：第{charging_request.pile_queue_position}位'
        )
        
        logger.info(f"请求 {charging_request.queue_number} 转移到桩 {pile.pile_id} 队列，位置: {charging_request.pile_queue_position}")
    
    def _update_external_queue_positions(self, charging_mode, removed_position):
        """更新外部等候区中后续请求的位置"""
        subsequent_requests = ChargingRequest.objects.filter(
            charging_mode=charging_mode,
            queue_level='external_waiting',
            external_queue_position__gt=removed_position
        )
        
        for request in subsequent_requests:
            request.external_queue_position -= 1
            request.estimated_wait_time = self._calculate_external_wait_time(request)
            request.save()
    
    def _try_start_charging(self, charging_request):
        """尝试开始充电"""
        pile = charging_request.charging_pile
        
        # 检查是否是队列中的第一个且桩空闲
        if (charging_request.pile_queue_position == 1 and 
            not pile.is_working):
            
            self._start_charging(charging_request, pile)
    
    def _start_charging(self, charging_request, pile):
        """开始充电"""
        with transaction.atomic():
            charging_request.queue_level = 'charging'
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
                vehicle=charging_request.vehicle,
                start_time=timezone.now()
            )
            
            # 更新桩队列位置
            self._update_pile_queue_positions(pile, charging_request.pile_queue_position)
            
            # 发送通知
            Notification.objects.create(
                user=charging_request.user,
                type='charging_start',
                message=f'您的充电请求 {charging_request.queue_number} 已开始充电，充电桩：{pile.pile_id}'
            )
            
            logger.info(f"请求 {charging_request.queue_number} 开始在桩 {pile.pile_id} 充电")
    
    def _update_pile_queue_positions(self, pile, removed_position):
        """更新桩队列中后续请求的位置"""
        subsequent_requests = ChargingRequest.objects.filter(
            charging_pile=pile,
            queue_level='pile_queue',
            pile_queue_position__gt=removed_position
        )
        
        for request in subsequent_requests:
            request.pile_queue_position -= 1
            request.estimated_wait_time = pile.calculate_remaining_time()
            request.save()
    
    def complete_charging(self, charging_request):
        """完成充电"""
        with transaction.atomic():
            pile = charging_request.charging_pile
            
            # 更新请求状态
            charging_request.queue_level = 'completed'
            charging_request.current_status = 'completed'
            charging_request.end_time = timezone.now()
            charging_request.save()
            
            # 释放充电桩
            pile.is_working = False
            pile.save()
            
            # 处理桩队列中的下一个请求
            self._process_next_in_pile_queue(pile)
            
            # 更新所有桩的剩余时间（因为一个桩空闲了，可能影响外部等候区的计算）
            self._update_all_pile_remaining_times(charging_request.charging_mode)
            
            # 尝试从外部等候区转移更多请求
            self._process_external_queue_transfers(charging_request.charging_mode)
    
    def _process_next_in_pile_queue(self, pile):
        """处理桩队列中的下一个请求"""
        next_request = ChargingRequest.objects.filter(
            charging_pile=pile,
            queue_level='pile_queue'
        ).order_by('pile_queue_position').first()
        
        if next_request:
            self._start_charging(next_request, pile)
    
    def _update_all_pile_remaining_times(self, charging_mode):
        """更新所有同模式桩的剩余时间"""
        piles = ChargingPile.objects.filter(
            pile_type=charging_mode,
            status='normal'
        )
        
        for pile in piles:
            pile.calculate_remaining_time()
    
    def _process_external_queue_transfers(self, charging_mode):
        """处理外部等候区的转移请求"""
        external_requests = ChargingRequest.objects.filter(
            charging_mode=charging_mode,
            queue_level='external_waiting'
        ).order_by('external_queue_position')
        
        for request in external_requests:
            if self._try_transfer_to_pile_queue(request):
                # 成功转移一个后，继续尝试下一个
                continue
            else:
                # 没有可用桩了，停止尝试
                break
    
    def cancel_charging_request(self, charging_request):
        """取消充电请求"""
        with transaction.atomic():
            if charging_request.queue_level == 'external_waiting':
                # 更新外部等候区位置
                self._update_external_queue_positions(
                    charging_request.charging_mode, 
                    charging_request.external_queue_position
                )
            elif charging_request.queue_level == 'pile_queue':
                # 更新桩队列位置
                self._update_pile_queue_positions(
                    charging_request.charging_pile, 
                    charging_request.pile_queue_position
                )
                # 尝试从外部等候区转移请求补充
                self._process_external_queue_transfers(charging_request.charging_mode)
            
            charging_request.current_status = 'cancelled'
            charging_request.queue_level = 'completed'
            charging_request.save()
    
    def get_queue_status(self, charging_mode=None):
        """获取队列状态"""
        if charging_mode:
            modes = [charging_mode]
        else:
            modes = ['fast', 'slow']
        
        result = {}
        
        for mode in modes:
            # 外部等候区状态
            external_queue = ChargingRequest.objects.filter(
                charging_mode=mode,
                queue_level='external_waiting'
            ).order_by('external_queue_position')
            
            # 获取所有桩的状态
            piles = ChargingPile.objects.filter(
                pile_type=mode,
                status='normal'
            )
            
            pile_status = []
            for pile in piles:
                pile_queue = ChargingRequest.objects.filter(
                    charging_pile=pile,
                    queue_level='pile_queue'
                ).order_by('pile_queue_position')
                
                current_charging = ChargingRequest.objects.filter(
                    charging_pile=pile,
                    current_status='charging'
                ).first()
                
                pile_status.append({
                    'pile_id': pile.pile_id,
                    'is_working': pile.is_working,
                    'current_charging': {
                        'queue_number': current_charging.queue_number if current_charging else None,
                        'progress': (current_charging.current_amount / current_charging.requested_amount * 100) if current_charging else 0
                    },
                    'queue_count': pile_queue.count(),
                    'max_queue_size': pile.max_queue_size,
                    'estimated_remaining_time': pile.estimated_remaining_time,
                    'queue_list': [
                        {
                            'queue_number': req.queue_number,
                            'position': req.pile_queue_position,
                            'estimated_wait_time': req.estimated_wait_time
                        }
                        for req in pile_queue[:3]  # 显示前3个
                    ]
                })
            
            result[mode] = {
                'external_waiting': {
                    'count': external_queue.count(),
                    'queue_list': [
                        {
                            'queue_number': req.queue_number,
                            'position': req.external_queue_position,
                            'estimated_wait_time': req.estimated_wait_time
                        }
                        for req in external_queue[:5]  # 显示前5个
                    ]
                },
                'piles': pile_status,
                'total_waiting': external_queue.count() + sum(pile.get_queue_count() for pile in piles)
            }
        
        return result

# 保持向后兼容的别名
class ChargingQueueService(AdvancedChargingQueueService):
    """保持向后兼容的类别名"""
    pass

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
