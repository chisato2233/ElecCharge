from django.core.management.base import BaseCommand
from charging.models import ChargingPile, ChargingRequest
from charging.services import AdvancedChargingQueueService

class Command(BaseCommand):
    help = '模拟充电桩故障和恢复处理'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['fault', 'recover'], help='故障操作类型')
        parser.add_argument('pile_id', type=str, help='充电桩ID')

    def handle(self, *args, **options):
        action = options['action']
        pile_id = options['pile_id']
        
        try:
            pile = ChargingPile.objects.get(pile_id=pile_id)
        except ChargingPile.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'充电桩 {pile_id} 不存在'))
            return
        
        service = AdvancedChargingQueueService()
        
        if action == 'fault':
            self.simulate_fault(pile, service)
        elif action == 'recover':
            self.simulate_recovery(pile, service)

    def simulate_fault(self, pile, service):
        """模拟充电桩故障"""
        self.stdout.write(f"=== 模拟充电桩 {pile.pile_id} 故障 ===")
        
        # 检查当前状态
        current_charging = ChargingRequest.objects.filter(
            charging_pile=pile,
            current_status='charging'
        ).first()
        
        queue_requests = ChargingRequest.objects.filter(
            charging_pile=pile,
            queue_level='pile_queue'
        ).order_by('pile_queue_position')
        
        self.stdout.write(f"故障前状态:")
        if current_charging:
            self.stdout.write(f"  正在充电: {current_charging.queue_number} (用户: {current_charging.user.username})")
        self.stdout.write(f"  队列等待: {queue_requests.count()} 人")
        for req in queue_requests:
            self.stdout.write(f"    - {req.queue_number} (位置: {req.pile_queue_position})")
        
        # 设置充电桩为故障状态
        pile.status = 'fault'
        pile.save()
        
        # 执行故障处理
        service.handle_pile_fault(pile)
        
        self.stdout.write(self.style.SUCCESS(f"✅ 充电桩 {pile.pile_id} 故障处理完成"))
        
        # 显示故障后状态
        self.show_queue_status_after_fault(pile)

    def simulate_recovery(self, pile, service):
        """模拟充电桩恢复"""
        self.stdout.write(f"=== 模拟充电桩 {pile.pile_id} 恢复 ===")
        
        if pile.status != 'fault':
            self.stdout.write(self.style.WARNING(f"充电桩 {pile.pile_id} 当前状态不是故障"))
            return
        
        # 设置充电桩为正常状态
        pile.status = 'normal'
        pile.save()
        
        # 执行恢复处理
        service.handle_pile_recovery(pile)
        
        self.stdout.write(self.style.SUCCESS(f"✅ 充电桩 {pile.pile_id} 恢复处理完成"))
        
        # 显示恢复后状态
        self.show_system_status_after_recovery()

    def show_queue_status_after_fault(self, pile):
        """显示故障后的队列状态"""
        self.stdout.write(f"\n故障后状态:")
        
        # 显示外部等候区状态
        external_requests = ChargingRequest.objects.filter(
            charging_mode=pile.pile_type,
            queue_level='external_waiting'
        ).order_by('external_queue_position')
        
        self.stdout.write(f"外部等候区 ({pile.pile_type}):")
        for req in external_requests:
            self.stdout.write(f"  - {req.queue_number} (位置: {req.external_queue_position}, 用户: {req.user.username})")
        
        # 检查是否暂停叫号
        service = AdvancedChargingQueueService()
        is_paused = service.is_external_queue_paused(pile.pile_type)
        if is_paused:
            self.stdout.write(self.style.WARNING(f"⚠️  {pile.pile_type} 外部等候区叫号已暂停"))

    def show_system_status_after_recovery(self):
        """显示恢复后的系统状态"""
        self.stdout.write(f"\n系统状态:")
        
        service = AdvancedChargingQueueService()
        queue_status = service.get_enhanced_queue_status()
        
        # 显示外部等候区
        external = queue_status.get('external_queue', {})
        self.stdout.write(f"外部等候区: 总计 {external.get('total_count', 0)} 人")
        self.stdout.write(f"  快充: {external.get('fast_count', 0)} 人")
        self.stdout.write(f"  慢充: {external.get('slow_count', 0)} 人")
        
        # 显示桩队列
        pile_queues = queue_status.get('pile_queues', {})
        for mode in ['fast', 'slow']:
            mode_data = pile_queues.get(mode, {})
            self.stdout.write(f"{mode.upper()}充桩队列: 总计 {mode_data.get('total_count', 0)} 人")
            self.stdout.write(f"  等待: {mode_data.get('waiting_count', 0)} 人")
            self.stdout.write(f"  充电: {mode_data.get('charging_count', 0)} 人") 