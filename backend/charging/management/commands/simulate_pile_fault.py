from django.core.management.base import BaseCommand
from charging.models import ChargingPile, ChargingRequest
from charging.services import AdvancedChargingQueueService
from django.utils import timezone

class Command(BaseCommand):
    help = '模拟充电桩故障和恢复（用于测试故障处理功能）'

    def add_arguments(self, parser):
        parser.add_argument(
            'pile_id',
            type=str,
            help='充电桩ID'
        )
        parser.add_argument(
            '--action',
            type=str,
            choices=['fault', 'recover', 'offline', 'online'],
            default='fault',
            help='操作类型：fault(故障), recover(恢复), offline(离线), online(上线)'
        )
        parser.add_argument(
            '--auto-recover',
            type=int,
            help='自动恢复时间（秒），设置后将在指定时间后自动恢复'
        )

    def handle(self, *args, **options):
        pile_id = options['pile_id']
        action = options['action']
        auto_recover = options['auto_recover']

        try:
            pile = ChargingPile.objects.get(pile_id=pile_id)
        except ChargingPile.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ 充电桩 {pile_id} 不存在')
            )
            return

        self.stdout.write(f'🔧 开始处理充电桩 {pile_id}...')
        
        # 显示当前状态
        self.show_pile_status(pile)
        
        # 执行操作
        if action == 'fault':
            self.simulate_fault(pile)
        elif action == 'recover':
            self.simulate_recovery(pile)
        elif action == 'offline':
            self.simulate_offline(pile)
        elif action == 'online':
            self.simulate_online(pile)

        # 显示操作后状态
        pile.refresh_from_db()
        self.show_pile_status(pile)
        
        # 自动恢复
        if auto_recover and action in ['fault', 'offline']:
            import time
            self.stdout.write(f'⏰ 将在 {auto_recover} 秒后自动恢复...')
            time.sleep(auto_recover)
            
            if action == 'fault':
                self.simulate_recovery(pile)
            elif action == 'offline':
                self.simulate_online(pile)
                
            pile.refresh_from_db()
            self.stdout.write('✅ 自动恢复完成')
            self.show_pile_status(pile)

    def show_pile_status(self, pile):
        """显示充电桩当前状态"""
        self.stdout.write('\n📊 === 充电桩状态 ===')
        self.stdout.write(f'桩ID: {pile.pile_id}')
        self.stdout.write(f'类型: {pile.get_pile_type_display()}')
        self.stdout.write(f'状态: {pile.get_status_display()}')
        self.stdout.write(f'工作中: {"是" if pile.is_working else "否"}')
        
        # 显示当前充电用户
        if pile.is_working:
            current_request = ChargingRequest.objects.filter(
                charging_pile=pile,
                current_status='charging'
            ).first()
            if current_request:
                progress = (current_request.current_amount / current_request.requested_amount) * 100
                self.stdout.write(f'当前用户: {current_request.user.username} ({current_request.queue_number})')
                self.stdout.write(f'充电进度: {progress:.1f}% ({current_request.current_amount:.2f}/{current_request.requested_amount:.2f} kWh)')

        # 显示队列情况
        queue_requests = ChargingRequest.objects.filter(
            charging_pile=pile,
            queue_level='pile_queue'
        ).order_by('pile_queue_position')
        
        if queue_requests.exists():
            self.stdout.write(f'队列等待: {queue_requests.count()} 人')
            for req in queue_requests[:3]:  # 显示前3个
                self.stdout.write(f'  #{req.pile_queue_position}: {req.user.username} ({req.queue_number})')
            if queue_requests.count() > 3:
                self.stdout.write(f'  ...还有 {queue_requests.count() - 3} 人')
        else:
            self.stdout.write('队列等待: 无')
        
        self.stdout.write('=' * 30)

    def simulate_fault(self, pile):
        """模拟充电桩故障"""
        if pile.status == 'fault':
            self.stdout.write(
                self.style.WARNING(f'⚠️ 充电桩 {pile.pile_id} 已经处于故障状态')
            )
            return

        self.stdout.write(
            self.style.WARNING(f'🚨 模拟充电桩 {pile.pile_id} 发生故障...')
        )
        
        # 更新状态
        pile.status = 'fault'
        pile.save()
        
        # 手动调用故障处理（正常情况下由守护进程检测）
        queue_service = AdvancedChargingQueueService()
        queue_service.handle_pile_fault(pile)
        
        self.stdout.write(
            self.style.SUCCESS('✅ 故障模拟和处理完成')
        )

    def simulate_recovery(self, pile):
        """模拟充电桩故障恢复"""
        if pile.status == 'normal':
            self.stdout.write(
                self.style.WARNING(f'⚠️ 充电桩 {pile.pile_id} 已经处于正常状态')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'✅ 模拟充电桩 {pile.pile_id} 故障恢复...')
        )
        
        # 更新状态
        pile.status = 'normal'
        pile.save()
        
        # 手动调用恢复处理
        queue_service = AdvancedChargingQueueService()
        queue_service.handle_pile_recovery(pile)
        
        self.stdout.write(
            self.style.SUCCESS('✅ 恢复模拟和处理完成')
        )

    def simulate_offline(self, pile):
        """模拟充电桩离线"""
        if pile.status == 'offline':
            self.stdout.write(
                self.style.WARNING(f'⚠️ 充电桩 {pile.pile_id} 已经处于离线状态')
            )
            return

        self.stdout.write(
            self.style.WARNING(f'📴 模拟充电桩 {pile.pile_id} 离线...')
        )
        
        # 更新状态
        pile.status = 'offline'
        pile.save()
        
        # 离线按故障处理
        queue_service = AdvancedChargingQueueService()
        queue_service.handle_pile_fault(pile)
        
        self.stdout.write(
            self.style.SUCCESS('✅ 离线模拟和处理完成')
        )

    def simulate_online(self, pile):
        """模拟充电桩上线"""
        if pile.status == 'normal':
            self.stdout.write(
                self.style.WARNING(f'⚠️ 充电桩 {pile.pile_id} 已经处于正常状态')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'🔌 模拟充电桩 {pile.pile_id} 重新上线...')
        )
        
        # 更新状态
        pile.status = 'normal'
        pile.save()
        
        # 上线按恢复处理
        queue_service = AdvancedChargingQueueService()
        queue_service.handle_pile_recovery(pile)
        
        self.stdout.write(
            self.style.SUCCESS('✅ 上线模拟和处理完成')
        ) 