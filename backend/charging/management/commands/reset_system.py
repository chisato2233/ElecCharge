from django.core.management.base import BaseCommand
from django.db import transaction
from charging.models import ChargingPile, SystemParameter, ChargingRequest
from decimal import Decimal

class Command(BaseCommand):
    help = '重置系统参数和充电桩配置'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重置，删除所有现有数据'
        )
        parser.add_argument(
            '--fast-piles',
            type=int,
            default=2,
            help='快充桩数量 (默认: 2)'
        )
        parser.add_argument(
            '--slow-piles',
            type=int,
            default=5,
            help='慢充桩数量 (默认: 5)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔄 开始系统重置...'))
        
        force = options['force']
        fast_count = options['fast_piles']
        slow_count = options['slow_piles']
        
        # 检查是否有活跃的充电请求
        active_requests = ChargingRequest.objects.filter(
            current_status__in=['waiting', 'charging']
        ).count()
        
        if active_requests > 0 and not force:
            self.stdout.write(
                self.style.ERROR(
                    f'❌ 发现 {active_requests} 个活跃的充电请求，无法重置。\n'
                    '请等待所有充电完成，或使用 --force 参数强制重置。'
                )
            )
            return
        
        with transaction.atomic():
            # 1. 重置系统参数
            self.reset_system_parameters(fast_count, slow_count)
            
            # 2. 重置充电桩
            self.reset_charging_piles(fast_count, slow_count, force)
            
            # 3. 如果强制重置，清理充电请求
            if force and active_requests > 0:
                self.cleanup_requests()
        
        self.stdout.write(self.style.SUCCESS('✅ 系统重置完成！'))
        self.show_system_status()

    def reset_system_parameters(self, fast_count, slow_count):
        """重置系统参数"""
        self.stdout.write('🔧 重置系统参数...')
        
        parameters = [
            # 充电桩数量
            ('FastChargingPileNum', str(fast_count), 'int', '快充桩数量'),
            ('TrickleChargingPileNum', str(slow_count), 'int', '慢充桩数量'),
            ('WaitingAreaSize', '20', 'int', '外部等候区容量'),
            
            # 多级队列系统参数
            ('fast_pile_max_queue', '3', 'int', '快充桩最大队列长度'),
            ('slow_pile_max_queue', '5', 'int', '慢充桩最大队列长度'),
            ('fast_charging_power', '120', 'float', '快充桩充电功率(kW)'),
            ('slow_charging_power', '7', 'float', '慢充桩充电功率(kW)'),
            
            # 充电费率
            ('peak_rate', '1.2', 'float', '峰时电价(元/kWh)'),
            ('normal_rate', '0.8', 'float', '平时电价(元/kWh)'),
            ('valley_rate', '0.4', 'float', '谷时电价(元/kWh)'),
            ('service_rate', '0.8', 'float', '服务费率(元/kWh)'),
        ]
        
        for param_key, param_value, param_type, description in parameters:
            param, created = SystemParameter.objects.update_or_create(
                param_key=param_key,
                defaults={
                    'param_value': param_value,
                    'param_type': param_type,
                    'description': description,
                    'is_editable': True
                }
            )
            action = '创建' if created else '更新'
            self.stdout.write(f'  {action} 参数: {param_key} = {param_value}')

    def reset_charging_piles(self, fast_count, slow_count, force):
        """重置充电桩"""
        self.stdout.write('⚡ 重置充电桩...')
        
        # 如果强制重置，删除所有现有充电桩
        if force:
            deleted_count = ChargingPile.objects.count()
            ChargingPile.objects.all().delete()
            self.stdout.write(f'  删除了 {deleted_count} 个现有充电桩')
        else:
            # 只删除未使用的充电桩
            unused_piles = ChargingPile.objects.filter(is_working=False)
            deleted_count = unused_piles.count()
            unused_piles.delete()
            self.stdout.write(f'  删除了 {deleted_count} 个未使用的充电桩')
        
        # 创建快充桩
        for i in range(1, fast_count + 1):
            pile, created = ChargingPile.objects.update_or_create(
                pile_id=f'FC{i:03d}',
                defaults={
                    'pile_type': 'fast',
                    'status': 'normal',
                    'is_working': False,
                    'max_queue_size': 3,
                    'charging_power': 120.0,
                    'estimated_remaining_time': 0,
                    'total_sessions': 0,
                    'total_duration': 0.0,
                    'total_energy': 0.0,
                    'total_revenue': Decimal('0.00')
                }
            )
            action = '创建' if created else '更新'
            self.stdout.write(f'  {action} 快充桩: {pile.pile_id}')
        
        # 创建慢充桩
        for i in range(1, slow_count + 1):
            pile, created = ChargingPile.objects.update_or_create(
                pile_id=f'SC{i:03d}',
                defaults={
                    'pile_type': 'slow',
                    'status': 'normal',
                    'is_working': False,
                    'max_queue_size': 5,
                    'charging_power': 7.0,
                    'estimated_remaining_time': 0,
                    'total_sessions': 0,
                    'total_duration': 0.0,
                    'total_energy': 0.0,
                    'total_revenue': Decimal('0.00')
                }
            )
            action = '创建' if created else '更新'
            self.stdout.write(f'  {action} 慢充桩: {pile.pile_id}')

    def cleanup_requests(self):
        """清理充电请求"""
        self.stdout.write('🧹 清理活跃充电请求...')
        
        # 将所有活跃请求标记为已取消
        updated = ChargingRequest.objects.filter(
            current_status__in=['waiting', 'charging']
        ).update(
            current_status='cancelled',
            queue_level='completed'
        )
        
        self.stdout.write(f'  取消了 {updated} 个活跃充电请求')

    def show_system_status(self):
        """显示系统状态"""
        self.stdout.write('\n📊 当前系统状态:')
        
        # 系统参数
        self.stdout.write('\n=== 系统参数 ===')
        key_params = [
            'FastChargingPileNum', 'TrickleChargingPileNum', 'WaitingAreaSize',
            'fast_charging_power', 'slow_charging_power'
        ]
        
        for key in key_params:
            try:
                param = SystemParameter.objects.get(param_key=key)
                self.stdout.write(f'  {key}: {param.param_value}')
            except SystemParameter.DoesNotExist:
                self.stdout.write(f'  {key}: 未设置')
        
        # 充电桩统计
        self.stdout.write('\n=== 充电桩统计 ===')
        fast_count = ChargingPile.objects.filter(pile_type='fast').count()
        slow_count = ChargingPile.objects.filter(pile_type='slow').count()
        
        self.stdout.write(f'  快充桩: {fast_count} 个')
        self.stdout.write(f'  慢充桩: {slow_count} 个')
        self.stdout.write(f'  总计: {fast_count + slow_count} 个')
        
        # 充电桩详情
        self.stdout.write('\n=== 充电桩详情 ===')
        for pile in ChargingPile.objects.all().order_by('pile_type', 'pile_id'):
            status = '工作中' if pile.is_working else '空闲'
            self.stdout.write(
                f'  {pile.pile_id}: {pile.get_pile_type_display()}, '
                f'功率: {pile.charging_power}kW, '
                f'队列容量: {pile.max_queue_size}, '
                f'状态: {status}'
            )
        
        # 活跃请求
        active_count = ChargingRequest.objects.filter(
            current_status__in=['waiting', 'charging']
        ).count()
        self.stdout.write(f'\n  活跃充电请求: {active_count} 个') 