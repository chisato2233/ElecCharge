from django.core.management.base import BaseCommand
from django.utils import timezone
from charging.models import ChargingRequest, ChargingSession, Notification, ChargingPile
from decimal import Decimal
import random
import time
import signal
import sys

class Command(BaseCommand):
    help = '更新充电进度'
    
    def __init__(self):
        super().__init__()
        self.running = True
        # 用于跟踪充电桩状态变化
        self.pile_status_cache = {}
        
    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=30,
            help='更新间隔（秒），默认30秒'
        )
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='作为守护进程持续运行'
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='只运行一次'
        )
        parser.add_argument(
            '--enable-fault-detection',
            action='store_true',
            default=True,
            help='启用充电桩故障检测（默认启用）'
        )
        parser.add_argument(
            '--check-faults',
            action='store_true',
            help='手动检查并处理所有故障桩（调试用）'
        )
    
    def handle_signal(self, signum, frame):
        """处理停止信号"""
        self.stdout.write('\n⏹️ 接收到停止信号，正在安全退出...')
        self.running = False
    
    def handle(self, *args, **options):
        # 注册信号处理器
        signal.signal(signal.SIGTERM, self.handle_signal)
        signal.signal(signal.SIGINT, self.handle_signal)
        
        interval = options['interval']
        enable_fault_detection = options['enable_fault_detection']
        check_faults = options['check_faults']
        
        # 手动故障检查模式
        if check_faults:
            self.manual_fault_check()
            return
        
        # 初始化充电桩状态缓存
        if enable_fault_detection:
            self.initialize_pile_status_cache()
        
        if options['once']:
            # 只运行一次
            self.update_single_cycle(enable_fault_detection)
        elif options['daemon']:
            # 守护进程模式
            self.run_daemon(interval, enable_fault_detection)
        else:
            # 默认运行一次
            self.update_single_cycle(enable_fault_detection)
    
    def initialize_pile_status_cache(self):
        """初始化充电桩状态缓存"""
        piles = ChargingPile.objects.all()
        for pile in piles:
            self.pile_status_cache[pile.pile_id] = pile.status
        self.stdout.write(f'📝 初始化充电桩状态缓存，监控 {len(self.pile_status_cache)} 个充电桩')
    
    def run_daemon(self, interval, enable_fault_detection):
        """守护进程模式，持续运行"""
        self.stdout.write(f'🚀 充电进度守护进程启动，更新间隔: {interval}秒')
        if enable_fault_detection:
            self.stdout.write('🔍 故障检测已启用')
        self.stdout.write('💡 按 Ctrl+C 或发送 SIGTERM 信号停止')
        
        try:
            while self.running:
                start_time = time.time()
                
                # 执行更新
                self.update_single_cycle(enable_fault_detection)
                
                # 计算下次更新时间
                elapsed = time.time() - start_time
                sleep_time = max(0, interval - elapsed)
                
                if self.running and sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            self.stdout.write('\n⏹️ 接收到键盘中断')
        except Exception as e:
            self.stdout.write(f'\n❌ 守护进程异常: {e}')
        finally:
            self.stdout.write('🔚 充电进度守护进程已停止')
    
    def update_single_cycle(self, enable_fault_detection=True):
        """单次更新周期"""
        # 1. 检测充电桩故障（如果启用）
        if enable_fault_detection:
            self.detect_and_handle_pile_faults()
        
        # 2. 更新充电进度
        self.update_charging_progress()
    
    def detect_and_handle_pile_faults(self):
        """检测并处理充电桩故障"""
        from charging.services import AdvancedChargingQueueService
        
        try:
            # 获取当前所有充电桩状态
            current_piles = ChargingPile.objects.all()
            queue_service = AdvancedChargingQueueService()
            
            fault_detected = False
            recovery_detected = False
            existing_fault_handled = False
            
            for pile in current_piles:
                cached_status = self.pile_status_cache.get(pile.pile_id)
                current_status = pile.status
                
                # 检测状态变化
                if cached_status != current_status:
                    self.stdout.write(
                        f'📊 检测到充电桩 {pile.pile_id} 状态变化: {cached_status} -> {current_status}'
                    )
                    
                    # 检测故障
                    if cached_status == 'normal' and current_status == 'fault':
                        self.stdout.write(
                            self.style.WARNING(f'🚨 检测到充电桩 {pile.pile_id} 发生故障')
                        )
                        # 调用故障处理
                        queue_service.handle_pile_fault(pile)
                        fault_detected = True
                    
                    # 检测恢复
                    elif cached_status == 'fault' and current_status == 'normal':
                        self.stdout.write(
                            self.style.SUCCESS(f'✅ 检测到充电桩 {pile.pile_id} 故障恢复')
                        )
                        # 调用恢复处理
                        queue_service.handle_pile_recovery(pile)
                        recovery_detected = True
                    
                    # 检测离线/上线
                    elif cached_status == 'offline' and current_status == 'normal':
                        self.stdout.write(
                            self.style.SUCCESS(f'🔌 检测到充电桩 {pile.pile_id} 重新上线')
                        )
                        # 离线恢复也需要重新调度
                        queue_service.handle_pile_recovery(pile)
                        recovery_detected = True
                    
                    elif cached_status == 'normal' and current_status == 'offline':
                        self.stdout.write(
                            self.style.WARNING(f'📴 检测到充电桩 {pile.pile_id} 离线')
                        )
                        # 离线按故障处理
                        queue_service.handle_pile_fault(pile)
                        fault_detected = True
                    
                    # 更新缓存
                    self.pile_status_cache[pile.pile_id] = current_status
                
                # 检查已存在的故障状态（特别是在守护进程启动时）
                elif current_status in ['fault', 'offline'] and cached_status is None:
                    # 这是初始化时发现的故障桩
                    self.stdout.write(
                        self.style.WARNING(f'🔍 初始化时发现故障桩 {pile.pile_id} (状态: {current_status})')
                    )
                    
                    # 检查是否有活跃的充电或队列请求
                    has_active_requests = ChargingRequest.objects.filter(
                        charging_pile=pile,
                        current_status__in=['charging', 'waiting']
                    ).exists()
                    
                    if has_active_requests:
                        self.stdout.write(
                            self.style.WARNING(f'🚨 故障桩 {pile.pile_id} 上有活跃请求，触发故障处理')
                        )
                        queue_service.handle_pile_fault(pile)
                        existing_fault_handled = True
                    
                    # 更新缓存
                    self.pile_status_cache[pile.pile_id] = current_status
            
            # 输出检测结果摘要
            if fault_detected or recovery_detected or existing_fault_handled:
                status_summary = []
                if fault_detected:
                    status_summary.append('发现故障')
                if recovery_detected:
                    status_summary.append('发现恢复')
                if existing_fault_handled:
                    status_summary.append('处理既有故障')
                self.stdout.write(
                    f'🔄 故障检测周期完成 - {", ".join(status_summary)}'
                )
            else:
                # 只在详细模式下输出
                if hasattr(self, 'verbosity') and self.verbosity >= 2:
                    self.stdout.write('🔍 故障检测周期完成 - 无状态变化')
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 故障检测过程发生错误: {e}')
            )
    
    def update_charging_progress(self):
        """更新充电进度"""
        charging_requests = ChargingRequest.objects.filter(current_status='charging')
        
        if not charging_requests.exists():
            # 只在详细模式下输出
            if hasattr(self, 'verbosity') and self.verbosity >= 2:
                self.stdout.write(f'⏰ {timezone.now().strftime("%H:%M:%S")} - 没有正在充电的请求')
            return
        
        updated_count = 0
        completed_count = 0
        fault_requests_found = []  # 收集在故障桩上的充电请求
        
        for request in charging_requests:
            # 检查桩是否仍然正常（防止在故障检测和进度更新之间的状态变化）
            if request.charging_pile and request.charging_pile.status != 'normal':
                self.stdout.write(
                    f'⚠️ 跳过故障桩 {request.charging_pile.pile_id} 上的充电进度更新'
                )
                # 收集故障桩上的充电请求，稍后处理
                fault_requests_found.append(request)
                continue
                
            old_status = request.current_status
            self.update_request_progress(request)
            
            updated_count += 1
            if request.current_status == 'completed' and old_status == 'charging':
                completed_count += 1
        
        # 处理在故障桩上发现的充电请求
        if fault_requests_found:
            self._handle_fault_charging_requests(fault_requests_found)
        
        status_msg = f'✅ {timezone.now().strftime("%H:%M:%S")} - 更新了 {updated_count} 个充电请求'
        if completed_count > 0:
            status_msg += f', 完成了 {completed_count} 个'
        if fault_requests_found:
            status_msg += f', 处理了 {len(fault_requests_found)} 个故障桩请求'
        
        self.stdout.write(self.style.SUCCESS(status_msg))
    
    def _handle_fault_charging_requests(self, fault_requests):
        """处理在故障桩上发现的充电请求"""
        from charging.services import AdvancedChargingQueueService
        
        processed_piles = set()  # 避免重复处理同一个桩
        
        for request in fault_requests:
            pile = request.charging_pile
            if not pile or pile.pile_id in processed_piles:
                continue
                
            if pile.status != 'normal':
                self.stdout.write(
                    self.style.WARNING(f'🚨 发现故障桩 {pile.pile_id} 上有活跃充电，触发故障处理')
                )
                
                try:
                    # 调用故障处理逻辑
                    queue_service = AdvancedChargingQueueService()
                    queue_service.handle_pile_fault(pile)
                    processed_piles.add(pile.pile_id)
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ 已处理故障桩 {pile.pile_id} 的充电和队列调度')
                    )
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'❌ 处理故障桩 {pile.pile_id} 时发生错误: {e}')
                    )
    
    def update_request_progress(self, request):
        """更新单个请求的充电进度"""
        if not request.start_time:
            return
        
        # 计算充电时长（小时）
        now = timezone.now()
        charging_duration = (now - request.start_time).total_seconds() / 3600
        
        # 获取充电桩的实际功率
        power = 120  # 默认快充功率
        if request.charging_pile:
            power = request.charging_pile.charging_power
        elif request.charging_mode == 'slow':
            power = 7   # 慢充功率约7kW
        
        # 计算已充电量
        charged_amount = min(
            charging_duration * power,
            request.requested_amount
        )
        
        # 添加一些随机性模拟真实情况
        if charged_amount < request.requested_amount:
            # 充电效率在80%-100%之间变动
            efficiency = random.uniform(0.8, 1.0)
            charged_amount = min(charged_amount * efficiency, request.requested_amount)
        
        # 更新请求进度
        old_amount = request.current_amount
        request.current_amount = round(charged_amount, 2)
        request.save()
        
        # 更新会话数据
        if hasattr(request, 'session'):
            session = request.session
            session.charging_amount = request.current_amount
            session.charging_duration = charging_duration
            session.save()
        
        # 检查是否完成充电
        if request.current_amount >= request.requested_amount:
            self.complete_charging(request)
        
        # 只在有显著变化时输出详细信息
        if abs(request.current_amount - old_amount) > 0.1:
            progress_pct = (request.current_amount / request.requested_amount * 100)
            self.stdout.write(
                f'📊 {request.queue_number} ({request.user.username}): '
                f'{old_amount:.2f} -> {request.current_amount:.2f} kWh ({progress_pct:.1f}%)'
            )
    
    def complete_charging(self, request):
        """自动完成充电"""
        from charging.services import BillingService, AdvancedChargingQueueService
        from django.db import transaction
        
        with transaction.atomic():
            # 更新请求状态
            request.current_status = 'completed'
            request.end_time = timezone.now()
            request.save()
            
            # 更新会话
            session = request.session
            session.end_time = timezone.now()
            
            # 计算费用
            billing_service = BillingService()
            billing_service.calculate_bill(session)
            session.save()
            
            # 使用新的队列服务完成充电
            queue_service = AdvancedChargingQueueService()
            queue_service.complete_charging(request)
            
            # 创建完成通知
            Notification.objects.create(
                user=request.user,
                type='charging_complete',
                message=f'您的充电请求 {request.queue_number} 已完成，共充电 {request.current_amount} kWh，总费用 {session.total_cost} 元'
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'🎉 {request.queue_number} ({request.user.username}) 充电完成！费用: {session.total_cost} 元')
        )
    
    def manual_fault_check(self):
        """手动检查并处理所有故障桩"""
        from charging.services import AdvancedChargingQueueService
        
        self.stdout.write('🔧 手动故障检查模式启动...')
        
        # 查找所有故障桩
        fault_piles = ChargingPile.objects.filter(status__in=['fault', 'offline'])
        
        if not fault_piles.exists():
            self.stdout.write(self.style.SUCCESS('✅ 未发现故障桩'))
            return
        
        self.stdout.write(f'🔍 发现 {fault_piles.count()} 个故障桩:')
        
        queue_service = AdvancedChargingQueueService()
        processed_count = 0
        
        for pile in fault_piles:
            self.stdout.write(f'   - {pile.pile_id}: {pile.get_status_display()}')
            
            # 检查是否有活跃请求
            active_requests = ChargingRequest.objects.filter(
                charging_pile=pile,
                current_status__in=['charging', 'waiting']
            )
            
            if active_requests.exists():
                self.stdout.write(
                    f'     ⚠️ 发现 {active_requests.count()} 个活跃请求，执行故障处理...'
                )
                
                try:
                    queue_service.handle_pile_fault(pile)
                    processed_count += 1
                    self.stdout.write(f'     ✅ 故障处理完成')
                except Exception as e:
                    self.stdout.write(f'     ❌ 故障处理失败: {e}')
            else:
                self.stdout.write(f'     📝 无活跃请求，跳过')
        
        self.stdout.write(
            self.style.SUCCESS(f'🔧 手动故障检查完成，处理了 {processed_count} 个故障桩')
        ) 