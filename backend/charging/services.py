from django.db import transaction
from django.utils import timezone
from django.db.models import F
from .models import ChargingRequest, ChargingPile, Notification, SystemParameter
from decimal import Decimal
from charging.utils.parameter_manager import ParameterManager, get_queue_config, get_fault_handling_config
import logging

logger = logging.getLogger(__name__)

class AdvancedChargingQueueService:
    """高级充电排队服务 - 多级队列系统"""
    
    def __init__(self):
        # 使用新的参数管理器获取配置
        queue_config = get_queue_config()
        self.external_waiting_limit = queue_config['external_waiting_area_size']
        self.SystemParameter = SystemParameter
        
    def _get_parameter(self, key, default):
        """获取系统参数（优化版，使用参数管理器）"""
        return ParameterManager.get_parameter(key, default)
        
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
            
            # 在尝试转移前，先标准化队列位置（防止数据不一致）
            self._normalize_external_queue_positions(charging_request.charging_mode)
            
            # 立即尝试转移到桩队列
            transferred = self._try_transfer_to_pile_queue(charging_request)
            
            # 如果转移成功，再次确保位置连续
            if transferred:
                self._normalize_external_queue_positions(charging_request.charging_mode)
            
            logger.info(f"用户 {charging_request.user.username} 加入外部等候区，位置: {charging_request.external_queue_position}, 已转移: {transferred}")
    
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
        """尝试将请求从外部等候区转移到桩队列（修改版，考虑暂停状态）"""
        if charging_request.queue_level != 'external_waiting':
            return False
        
        # 检查是否暂停了叫号
        if self.is_external_queue_paused(charging_request.charging_mode):
            logger.debug(f"外部等候区叫号已暂停，跳过转移请求 {charging_request.queue_number}")
            return False
        
        # 查找最优桩（剩余时间最短且队列未满）
        best_pile = self._find_best_available_pile(charging_request.charging_mode)
        
        if best_pile:
            with transaction.atomic():
                # 记录原来的位置
                original_position = charging_request.external_queue_position
                
                # 转移到桩队列
                self._transfer_to_pile_queue(charging_request, best_pile)
                
                # 更新外部等候区位置
                self._update_external_queue_positions(charging_request.charging_mode, original_position)
                
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
    
    def _normalize_external_queue_positions(self, charging_mode):
        """标准化外部等候区的队列位置，确保从1开始连续排列"""
        external_requests = ChargingRequest.objects.filter(
            charging_mode=charging_mode,
            queue_level='external_waiting'
        ).order_by('created_at')  # 按创建时间排序，保持公平
        
        for i, request in enumerate(external_requests, 1):
            if request.external_queue_position != i:
                request.external_queue_position = i
                request.estimated_wait_time = self._calculate_external_wait_time(request)
                request.save()
        
        logger.info(f"标准化 {charging_mode} 充电外部等候区位置，共 {external_requests.count()} 个请求")
    
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
                # 确保位置连续
                self._normalize_external_queue_positions(charging_request.charging_mode)
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
    
    def change_charging_mode(self, charging_request, new_charging_mode):
        """修改充电类型（仅限外部等候区的请求）"""
        if charging_request.queue_level != 'external_waiting':
            raise ValueError("只有外部等候区的充电请求可以修改充电类型")
        
        if charging_request.charging_mode == new_charging_mode:
            raise ValueError("新的充电类型与当前相同")
        
        if new_charging_mode not in ['fast', 'slow']:
            raise ValueError("充电类型必须是 'fast' 或 'slow'")
        
        with transaction.atomic():
            old_mode = charging_request.charging_mode
            old_position = charging_request.external_queue_position
            
            # 记录原始信息用于通知
            original_queue_number = charging_request.queue_number
            
            # 从原队列中移除
            self._update_external_queue_positions(old_mode, old_position)
            self._normalize_external_queue_positions(old_mode)
            
            # 修改充电类型
            charging_request.charging_mode = new_charging_mode
            
            # 重新生成排队号
            prefix = 'F' if new_charging_mode == 'fast' else 'S'
            timestamp = timezone.now().strftime('%m%d%H%M')
            count = ChargingRequest.objects.filter(
                charging_mode=new_charging_mode,
                created_at__date=timezone.now().date()
            ).count() + 1
            charging_request.queue_number = f"{prefix}{timestamp}{count:03d}"
            
            # 重新加入外部等候区（排队到末尾）
            same_mode_external = ChargingRequest.objects.filter(
                charging_mode=new_charging_mode,
                queue_level='external_waiting'
            ).count()
            
            charging_request.external_queue_position = same_mode_external + 1
            charging_request.estimated_wait_time = self._calculate_external_wait_time(charging_request)
            charging_request.save()
            
            # 立即尝试转移到桩队列
            transferred = self._try_transfer_to_pile_queue(charging_request)
            
            # 如果转移成功，再次确保位置连续
            if transferred:
                self._normalize_external_queue_positions(new_charging_mode)
            
            # 发送通知
            from .models import Notification
            mode_display = "快充" if new_charging_mode == 'fast' else "慢充"
            old_mode_display = "快充" if old_mode == 'fast' else "慢充"
            
            Notification.objects.create(
                user=charging_request.user,
                type='charging_mode_change',
                message=f'您的充电请求已从{old_mode_display}（{original_queue_number}）改为{mode_display}（{charging_request.queue_number}），'
                       f'当前位置：{charging_request.get_queue_status_display()}'
            )
            
            logger.info(f"用户 {charging_request.user.username} 修改充电类型：{old_mode} -> {new_charging_mode}，"
                       f"新排队号：{charging_request.queue_number}，位置：{charging_request.external_queue_position}")
            
            return charging_request
    
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

    def get_enhanced_queue_status(self):
        """获取增强的队列状态（适配前端dashboard）"""
        # 获取原始队列状态
        queue_status = self.get_queue_status()
        
        # 外部等候区数据
        external_fast_count = queue_status.get('fast', {}).get('external_waiting', {}).get('count', 0)
        external_slow_count = queue_status.get('slow', {}).get('external_waiting', {}).get('count', 0)
        
        # 合并外部等候区请求
        external_requests = []
        for mode in ['fast', 'slow']:
            mode_data = queue_status.get(mode, {})
            mode_requests = mode_data.get('external_waiting', {}).get('queue_list', [])
            for req in mode_requests:
                req['charging_mode'] = mode
                external_requests.append(req)
        
        # 按位置排序
        external_requests.sort(key=lambda x: x['position'])
        
        # 桩队列数据
        def get_pile_queue_data(mode):
            mode_data = queue_status.get(mode, {})
            piles = mode_data.get('piles', [])
            
            waiting_count = sum(pile['queue_count'] for pile in piles)
            charging_count = sum(1 for pile in piles if pile['is_working'])
            
            # 合并所有桩的队列请求
            requests = []
            for pile in piles:
                pile_id = pile['pile_id']
                # 添加正在充电的请求
                if pile['current_charging']['queue_number']:
                    requests.append({
                        'queue_number': pile['current_charging']['queue_number'],
                        'queue_position': 0,  # 正在充电的位置为0
                        'status': 'charging',
                        'pile_id': pile_id,
                        'estimated_wait_time': 0
                    })
                
                # 添加排队请求
                for req in pile['queue_list']:
                    requests.append({
                        'queue_number': req['queue_number'],
                        'queue_position': req['position'],
                        'status': 'waiting',
                        'pile_id': pile_id,
                        'estimated_wait_time': req['estimated_wait_time']
                    })
            
            # 按位置排序（充电中的在前）
            requests.sort(key=lambda x: (1 if x['status'] == 'waiting' else 0, x['queue_position']))
            
            return {
                'total_count': waiting_count + charging_count,
                'waiting_count': waiting_count,
                'charging_count': charging_count,
                'requests': requests
            }
        
        # 构建增强格式的响应
        enhanced_data = {
            'external_queue': {
                'total_count': external_fast_count + external_slow_count,
                'fast_count': external_fast_count,
                'slow_count': external_slow_count,
                'requests': external_requests
            },
            'pile_queues': {
                'fast': get_pile_queue_data('fast'),
                'slow': get_pile_queue_data('slow')
            }
        }
        
        return enhanced_data

    def handle_pile_fault(self, pile):
        """处理充电桩故障"""
        from django.db import transaction
        
        logger.warning(f"检测到充电桩 {pile.pile_id} 故障，开始故障处理流程")
        
        with transaction.atomic():
            # 1. 立即停止当前充电（如果有）
            current_charging = self._stop_current_charging_due_to_fault(pile)
            
            # 2. 获取故障桩队列中的所有请求
            fault_queue_requests = self._get_fault_queue_requests(pile)
            
            # 3. 根据系统参数选择调度策略（使用新的参数管理器）
            fault_config = get_fault_handling_config()
            dispatch_strategy = fault_config['dispatch_strategy']
            
            if dispatch_strategy == 'priority':
                # 优先级调度：暂停等候区叫号，优先处理故障队列
                self._handle_fault_priority_dispatch(pile, fault_queue_requests)
            elif dispatch_strategy == 'time_order':
                # 时间顺序调度：与同类车辆合并排序
                self._handle_fault_time_order_dispatch(pile, fault_queue_requests)
            else:
                # 默认使用优先级调度
                self._handle_fault_priority_dispatch(pile, fault_queue_requests)
            
            # 4. 发送故障通知（考虑延迟）
            notification_delay = fault_config['notification_delay']
            if notification_delay > 0:
                # 这里可以实现延迟通知逻辑
                pass
            self._send_fault_notifications(pile, current_charging, fault_queue_requests)
            
            logger.info(f"充电桩 {pile.pile_id} 故障处理完成，影响用户数: {len(fault_queue_requests) + (1 if current_charging else 0)}")

    def _stop_current_charging_due_to_fault(self, pile):
        """停止故障桩上的当前充电"""
        from .models import ChargingRequest, ChargingSession, Notification
        from django.utils import timezone
        
        current_charging = ChargingRequest.objects.filter(
            charging_pile=pile,
            current_status='charging'
        ).first()
        
        if not current_charging:
            return None
            
        logger.info(f"停止用户 {current_charging.user.username} 在故障桩 {pile.pile_id} 的充电")
        
        # 更新请求状态
        current_charging.current_status = 'completed'
        current_charging.end_time = timezone.now()
        current_charging.queue_level = 'completed'
        current_charging.save()
        
        # 释放充电桩
        pile.is_working = False
        pile.save()
        
        # 结束充电会话并计费
        session = current_charging.session
        session.end_time = timezone.now()
        
        # 计算充电时长
        duration = session.end_time - session.start_time
        session.charging_duration = duration.total_seconds() / 3600
        session.charging_amount = current_charging.current_amount
        
        # 计算费用（故障导致的提前结束）
        billing_service = BillingService()
        billing_service.calculate_bill(session)
        session.save()
        
        # 创建故障通知
        Notification.objects.create(
            user=current_charging.user,
            type='pile_fault',
            message=f'充电桩 {pile.pile_id} 发生故障，您的充电已提前结束。实际充电 {current_charging.current_amount:.2f} kWh，费用 {session.total_cost} 元。'
        )
        
        return current_charging

    def _get_fault_queue_requests(self, pile):
        """获取故障桩队列中的所有请求"""
        from .models import ChargingRequest
        
        return list(ChargingRequest.objects.filter(
            charging_pile=pile,
            queue_level='pile_queue'
        ).order_by('pile_queue_position'))

    def _handle_fault_priority_dispatch(self, fault_pile, fault_queue_requests):
        """优先级调度：暂停等候区叫号，优先处理故障队列"""
        logger.info(f"采用优先级调度策略处理故障桩 {fault_pile.pile_id} 的 {len(fault_queue_requests)} 个请求")
        
        # 1. 暂停等候区叫号（通过设置系统参数）
        self._pause_external_queue_calling(fault_pile.pile_type)
        
        # 2. 优先重新分配故障队列中的请求
        for request in fault_queue_requests:
            self._reassign_request_priority(request)
        
        # 3. 在所有故障请求处理完毕后恢复等候区叫号
        self._schedule_resume_external_queue_calling(fault_pile.pile_type)

    def _handle_fault_time_order_dispatch(self, fault_pile, fault_queue_requests):
        """时间顺序调度：故障车辆与其它同类未充电车辆合并排序调度"""
        logger.info(f"采用时间顺序调度策略处理故障桩 {fault_pile.pile_id} 的 {len(fault_queue_requests)} 个请求")
        
        # 1. 将故障请求重新加入外部等候区，按时间顺序排序
        for request in fault_queue_requests:
            self._reassign_request_time_order(request)

    def _pause_external_queue_calling(self, pile_type):
        """暂停指定类型的外部等候区叫号"""
        param_key = f'{pile_type}_external_queue_paused'
        
        # 设置暂停标志
        from .models import SystemParameter
        param, created = SystemParameter.objects.get_or_create(
            param_key=param_key,
            defaults={
                'param_value': 'true',
                'param_type': 'boolean',
                'description': f'{pile_type}充电外部等候区暂停叫号（故障处理中）'
            }
        )
        if not created:
            param.param_value = 'true'
            param.save()
            
        logger.info(f"已暂停 {pile_type} 外部等候区叫号")

    def _reassign_request_priority(self, request):
        """优先级模式重新分配请求"""
        from .models import Notification
        
        # 清除原桩分配
        original_pile = request.charging_pile
        request.charging_pile = None
        request.queue_level = 'external_waiting'
        request.pile_queue_position = 0
        
        # 先保存到数据库（临时位置）
        request.external_queue_position = 999  # 临时位置，避免冲突
        request.save()
        
        # 更新其他外部等候区请求的位置（为故障请求让出第1位）
        ChargingRequest.objects.filter(
            charging_mode=request.charging_mode,
            queue_level='external_waiting'
        ).exclude(id=request.id).update(
            external_queue_position=F('external_queue_position') + 1
        )
        
        # 设置故障请求为第1位
        request.external_queue_position = 1  # 优先级最高，插入队首
        request.estimated_wait_time = self._calculate_external_wait_time(request)
        request.save()
        
        # 立即尝试转移到可用桩
        transferred = self._try_transfer_to_pile_queue(request)
        
        # 如果转移成功，需要重新整理外部等候区位置
        if transferred:
            self._normalize_external_queue_positions(request.charging_mode)
        
        # 发送重新调度通知
        Notification.objects.create(
            user=request.user,
            type='queue_transfer',
            message=f'由于充电桩 {original_pile.pile_id} 故障，您的请求 {request.queue_number} 已重新调度，当前位置：{request.get_queue_status_display()}'
        )

    def _reassign_request_time_order(self, request):
        """时间顺序模式重新分配请求"""
        from .models import Notification
        from django.db.models import F
        
        # 清除原桩分配
        original_pile = request.charging_pile
        request.charging_pile = None
        request.queue_level = 'external_waiting'
        request.pile_queue_position = 0
        
        # 先临时保存
        request.external_queue_position = 999  # 临时位置
        request.save()
        
        # 重新标准化所有外部等候区位置（按时间顺序）
        self._normalize_external_queue_positions(request.charging_mode)
        
        # 尝试转移到可用桩
        transferred = self._try_transfer_to_pile_queue(request)
        
        # 如果转移成功，需要重新整理外部等候区位置
        if transferred:
            self._normalize_external_queue_positions(request.charging_mode)
        
        # 发送重新调度通知
        Notification.objects.create(
            user=request.user,
            type='queue_transfer',
            message=f'由于充电桩 {original_pile.pile_id} 故障，您的请求 {request.queue_number} 已按时间顺序重新排队，当前位置：{request.get_queue_status_display()}'
        )

    def _schedule_resume_external_queue_calling(self, pile_type):
        """安排恢复外部等候区叫号（在所有故障请求处理完毕后）"""
        # 这里可以设置一个延迟任务或者在下次处理时检查
        # 暂时直接恢复，实际可以根据业务需求调整
        self._resume_external_queue_calling(pile_type)

    def _resume_external_queue_calling(self, pile_type):
        """恢复指定类型的外部等候区叫号"""
        param_key = f'{pile_type}_external_queue_paused'
        
        from .models import SystemParameter
        try:
            param = SystemParameter.objects.get(param_key=param_key)
            param.param_value = 'false'
            param.save()
            logger.info(f"已恢复 {pile_type} 外部等候区叫号")
        except SystemParameter.DoesNotExist:
            pass  # 参数不存在说明没有暂停过

    def _send_fault_notifications(self, pile, current_charging, fault_queue_requests):
        """发送故障相关通知"""
        from .models import Notification
        
        # 给队列中的用户发送通知
        for request in fault_queue_requests:
            Notification.objects.create(
                user=request.user,
                type='pile_fault',
                message=f'充电桩 {pile.pile_id} 发生故障，您的充电请求 {request.queue_number} 已重新调度。'
            )

    def handle_pile_recovery(self, pile):
        """处理充电桩故障恢复"""
        from django.db import transaction
        
        logger.info(f"检测到充电桩 {pile.pile_id} 故障恢复，开始恢复处理流程")
        
        with transaction.atomic():
            # 1. 检查是否还有其他同类桩仍有排队车辆
            same_type_piles = ChargingPile.objects.filter(
                pile_type=pile.pile_type,
                status='normal'
            ).exclude(pile_id=pile.pile_id)
            
            has_queue = any(
                ChargingRequest.objects.filter(
                    charging_pile=p,
                    queue_level='pile_queue'
                ).exists() for p in same_type_piles
            )
            
            if has_queue:
                # 2. 如果有排队车辆，统一重新调度
                logger.info(f"检测到其他 {pile.pile_type} 桩仍有排队，执行统一重新调度")
                self._unified_reschedule_after_recovery(pile.pile_type)
            
            # 3. 恢复叫号服务
            self._resume_external_queue_calling(pile.pile_type)
            
            # 4. 尝试处理外部等候区转移
            self._process_external_queue_transfers(pile.pile_type)
            
            logger.info(f"充电桩 {pile.pile_id} 恢复处理完成")

    def _unified_reschedule_after_recovery(self, pile_type):
        """故障恢复后的统一重新调度"""
        from .models import ChargingRequest
        
        # 获取所有同类型的正常桩队列中的请求
        all_pile_requests = ChargingRequest.objects.filter(
            charging_mode=pile_type,
            queue_level='pile_queue'
        ).order_by('created_at')  # 按时间顺序
        
        # 临时将所有请求移回外部等候区
        for request in all_pile_requests:
            request.queue_level = 'external_waiting'
            request.charging_pile = None
            request.pile_queue_position = 0
            request.save()
        
        # 重新计算外部等候区位置
        for i, request in enumerate(all_pile_requests, 1):
            request.external_queue_position = i
            request.estimated_wait_time = self._calculate_external_wait_time(request)
            request.save()
        
        # 重新执行转移到桩队列的逻辑
        self._process_external_queue_transfers(pile_type)
        
        logger.info(f"完成 {pile_type} 类型桩的统一重新调度，处理请求数: {len(all_pile_requests)}")

    def is_external_queue_paused(self, pile_type):
        """检查外部等候区是否暂停叫号"""
        param_key = f'{pile_type}_external_queue_paused'
        try:
            from .models import SystemParameter
            param = SystemParameter.objects.get(param_key=param_key)
            return param.get_value() is True
        except:
            return False

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
