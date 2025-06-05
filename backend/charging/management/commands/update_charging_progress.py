from django.core.management.base import BaseCommand
from django.utils import timezone
from charging.models import ChargingRequest, ChargingSession, Notification
from decimal import Decimal
import random
import time
import signal
import sys

class Command(BaseCommand):
    help = '更新充电进度'
    
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
    
    def __init__(self):
        super().__init__()
        self.running = True
        
    def handle_signal(self, signum, frame):
        """处理停止信号"""
        self.stdout.write('\n⏹️ 接收到停止信号，正在安全退出...')
        self.running = False
    
    def handle(self, *args, **options):
        # 注册信号处理器
        signal.signal(signal.SIGTERM, self.handle_signal)
        signal.signal(signal.SIGINT, self.handle_signal)
        
        interval = options['interval']
        
        if options['once']:
            # 只运行一次
            self.update_single_progress()
        elif options['daemon']:
            # 守护进程模式
            self.run_daemon(interval)
        else:
            # 默认运行一次
            self.update_single_progress()
    
    def run_daemon(self, interval):
        """守护进程模式，持续运行"""
        self.stdout.write(f'🚀 充电进度守护进程启动，更新间隔: {interval}秒')
        self.stdout.write('💡 按 Ctrl+C 或发送 SIGTERM 信号停止')
        
        try:
            while self.running:
                start_time = time.time()
                
                # 执行更新
                self.update_single_progress()
                
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
    
    def update_single_progress(self):
        """单次更新所有正在充电的请求进度"""
        charging_requests = ChargingRequest.objects.filter(current_status='charging')
        
        if not charging_requests.exists():
            self.stdout.write(f'⏰ {timezone.now().strftime("%H:%M:%S")} - 没有正在充电的请求')
            return
        
        updated_count = 0
        completed_count = 0
        
        for request in charging_requests:
            old_status = request.current_status
            self.update_request_progress(request)
            
            updated_count += 1
            if request.current_status == 'completed' and old_status == 'charging':
                completed_count += 1
        
        status_msg = f'✅ {timezone.now().strftime("%H:%M:%S")} - 更新了 {updated_count} 个充电请求'
        if completed_count > 0:
            status_msg += f', 完成了 {completed_count} 个'
        
        self.stdout.write(self.style.SUCCESS(status_msg))
    
    def update_request_progress(self, request):
        """更新单个请求的充电进度"""
        if not request.start_time:
            return
        
        # 计算充电时长（小时）
        now = timezone.now()
        charging_duration = (now - request.start_time).total_seconds() / 3600
        
        # 计算充电功率（kW）
        if request.charging_mode == 'fast':
            power = 120  # 快充功率约120kW
        else:
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
        from charging.services import BillingService
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
            
            # 释放充电桩
            pile = request.charging_pile
            pile.is_working = False
            pile.save()
            
            # 创建完成通知
            Notification.objects.create(
                user=request.user,
                type='charging_complete',
                message=f'您的充电请求 {request.queue_number} 已完成，共充电 {request.current_amount} kWh，总费用 {session.total_cost} 元'
            )
            
            # 处理下一个排队请求
            from charging.services import ChargingQueueService
            queue_service = ChargingQueueService()
            queue_service.process_next_in_queue(pile)
        
        self.stdout.write(
            self.style.SUCCESS(f'🎉 {request.queue_number} ({request.user.username}) 充电完成！费用: {session.total_cost} 元')
        ) 