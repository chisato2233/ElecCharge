from django.core.management.base import BaseCommand
from charging.models import ChargingRequest, ChargingPile
from charging.services import AdvancedChargingQueueService

class Command(BaseCommand):
    help = '检查和修复队列位置数据一致性问题'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='自动修复发现的问题',
        )
        parser.add_argument(
            '--mode',
            type=str,
            choices=['fast', 'slow', 'all'],
            default='all',
            help='检查的充电模式',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== 队列位置数据检查工具 ===\n'))
        
        modes = ['fast', 'slow'] if options['mode'] == 'all' else [options['mode']]
        
        issues_found = False
        
        for mode in modes:
            self.stdout.write(f'🔍 检查 {mode} 充电队列...')
            
            # 检查外部等候区
            external_issues = self.check_external_queue(mode)
            
            # 检查桩队列
            pile_issues = self.check_pile_queues(mode)
            
            if external_issues or pile_issues:
                issues_found = True
                
                if options['fix']:
                    self.fix_issues(mode)
                    self.stdout.write(self.style.SUCCESS(f'✅ 已修复 {mode} 充电队列问题\n'))
                else:
                    self.stdout.write(self.style.WARNING(f'⚠️  发现 {mode} 充电队列问题，使用 --fix 参数进行修复\n'))
            else:
                self.stdout.write(self.style.SUCCESS(f'✅ {mode} 充电队列位置正常\n'))
        
        if not issues_found:
            self.stdout.write(self.style.SUCCESS('🎉 所有队列位置都正常！'))
        elif not options['fix']:
            self.stdout.write(self.style.WARNING('\n💡 使用 --fix 参数自动修复问题'))

    def check_external_queue(self, mode):
        """检查外部等候区位置是否连续"""
        external_requests = ChargingRequest.objects.filter(
            charging_mode=mode,
            queue_level='external_waiting'
        ).order_by('external_queue_position')
        
        total_count = external_requests.count()
        if total_count == 0:
            return False
        
        positions = [req.external_queue_position for req in external_requests]
        expected_positions = list(range(1, total_count + 1))
        
        self.stdout.write(f'   外部等候区: {total_count} 人')
        self.stdout.write(f'   实际位置: {positions}')
        self.stdout.write(f'   期望位置: {expected_positions}')
        
        issues = []
        
        # 检查是否从1开始
        if positions and positions[0] != 1:
            issues.append(f"队列不是从第1位开始，而是从第{positions[0]}位开始")
        
        # 检查是否连续
        if positions != expected_positions:
            issues.append("位置不连续")
        
        # 检查是否有重复
        if len(set(positions)) != len(positions):
            issues.append("存在重复位置")
        
        if issues:
            self.stdout.write(self.style.ERROR(f'   ❌ 外部等候区问题:'))
            for issue in issues:
                self.stdout.write(f'      - {issue}')
            
            # 显示详细信息
            for req in external_requests:
                self.stdout.write(f'      位置 {req.external_queue_position}: {req.queue_number} '
                                f'(用户: {req.user.username})')
            return True
        
        return False

    def check_pile_queues(self, mode):
        """检查桩队列位置是否连续"""
        piles = ChargingPile.objects.filter(pile_type=mode, status='normal')
        has_issues = False
        
        for pile in piles:
            pile_requests = ChargingRequest.objects.filter(
                charging_pile=pile,
                queue_level='pile_queue'
            ).order_by('pile_queue_position')
            
            total_count = pile_requests.count()
            if total_count == 0:
                continue
            
            positions = [req.pile_queue_position for req in pile_requests]
            expected_positions = list(range(1, total_count + 1))
            
            if positions != expected_positions:
                has_issues = True
                self.stdout.write(self.style.ERROR(f'   ❌ 桩 {pile.pile_id} 队列问题:'))
                self.stdout.write(f'      实际位置: {positions}')
                self.stdout.write(f'      期望位置: {expected_positions}')
                
                for req in pile_requests:
                    self.stdout.write(f'      位置 {req.pile_queue_position}: {req.queue_number} '
                                    f'(用户: {req.user.username})')
        
        return has_issues

    def fix_issues(self, mode):
        """修复队列位置问题"""
        queue_service = AdvancedChargingQueueService()
        
        # 修复外部等候区
        queue_service._normalize_external_queue_positions(mode)
        
        # 修复桩队列
        piles = ChargingPile.objects.filter(pile_type=mode, status='normal')
        for pile in piles:
            pile_requests = ChargingRequest.objects.filter(
                charging_pile=pile,
                queue_level='pile_queue'
            ).order_by('created_at')  # 按创建时间排序
            
            for i, request in enumerate(pile_requests, 1):
                if request.pile_queue_position != i:
                    request.pile_queue_position = i
                    request.estimated_wait_time = pile.calculate_remaining_time()
                    request.save()
        
        self.stdout.write(f'   🔧 修复完成 {mode} 充电队列位置') 