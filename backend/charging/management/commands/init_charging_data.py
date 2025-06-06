from django.core.management.base import BaseCommand
from charging.models import ChargingPile, SystemParameter
from decimal import Decimal

class Command(BaseCommand):
    help = '初始化充电站数据'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('开始初始化充电站数据...'))
        
        # 初始化系统参数
        self.create_system_parameters()
        
        # 获取充电桩数量参数
        try:
            fast_count = int(SystemParameter.objects.get(param_key='FastChargingPileNum').get_value())
            slow_count = int(SystemParameter.objects.get(param_key='TrickleChargingPileNum').get_value())
        except SystemParameter.DoesNotExist:
            fast_count = 5
            slow_count = 10
        
        # 创建充电桩
        self.create_charging_piles(fast_count, slow_count)
        
        self.stdout.write(self.style.SUCCESS('充电站数据初始化完成！'))

    def create_system_parameters(self):
        """创建系统参数"""
        self.stdout.write('创建系统参数...')
        
        parameters = [
            # 充电桩数量
            ('FastChargingPileNum', '5', 'int', '快充桩数量'),
            ('TrickleChargingPileNum', '10', 'int', '慢充桩数量'),
            ('WaitingAreaSize', '20', 'int', '外部等候区容量'),
            
            # 充电费率
            ('peak_rate', '1.2', 'float', '峰时电价(元/kWh)'),
            ('normal_rate', '0.8', 'float', '平时电价(元/kWh)'),
            ('valley_rate', '0.4', 'float', '谷时电价(元/kWh)'),
            ('service_rate', '0.8', 'float', '服务费率(元/kWh)'),
            
            # 多级队列系统参数
            ('fast_pile_max_queue', '3', 'int', '快充桩最大队列长度'),
            ('slow_pile_max_queue', '5', 'int', '慢充桩最大队列长度'),
            ('fast_charging_power', '120', 'float', '快充桩充电功率(kW)'),
            ('slow_charging_power', '7', 'float', '慢充桩充电功率(kW)'),
        ]
        
        for param_key, param_value, param_type, description in parameters:
            param, created = SystemParameter.objects.get_or_create(
                param_key=param_key,
                defaults={
                    'param_value': param_value,
                    'param_type': param_type,
                    'description': description,
                    'is_editable': True
                }
            )
            if created:
                self.stdout.write(f'  创建参数: {param_key} = {param_value}')
            else:
                self.stdout.write(f'  参数已存在: {param_key} = {param.param_value}')

    def create_charging_piles(self, fast_count, slow_count):
        """创建充电桩"""
        self.stdout.write(f'创建充电桩: 快充桩 {fast_count} 个, 慢充桩 {slow_count} 个')
        
        # 创建快充桩
        for i in range(1, fast_count + 1):
            pile, created = ChargingPile.objects.get_or_create(
                pile_id=f'FC{i:03d}',
                defaults={
                    'pile_type': 'fast',
                    'status': 'normal',
                    'is_working': False,
                    'max_queue_size': 3,  # 桩队列最大容量
                    'charging_power': 120.0,  # 快充功率120kW
                    'estimated_remaining_time': 0
                }
            )
            if created:
                self.stdout.write(f'  创建快充桩: {pile.pile_id}')
            else:
                # 更新现有桩的新字段
                if not hasattr(pile, 'charging_power') or pile.charging_power == 0:
                    pile.max_queue_size = 3
                    pile.charging_power = 120.0
                    pile.estimated_remaining_time = 0
                    pile.save()
                    self.stdout.write(f'  更新快充桩: {pile.pile_id}')
        
        # 创建慢充桩
        for i in range(1, slow_count + 1):
            pile, created = ChargingPile.objects.get_or_create(
                pile_id=f'SC{i:03d}',
                defaults={
                    'pile_type': 'slow',
                    'status': 'normal',
                    'is_working': False,
                    'max_queue_size': 5,  # 慢充桩队列容量可以大一些
                    'charging_power': 7.0,  # 慢充功率7kW
                    'estimated_remaining_time': 0
                }
            )
            if created:
                self.stdout.write(f'  创建慢充桩: {pile.pile_id}')
            else:
                # 更新现有桩的新字段
                if not hasattr(pile, 'charging_power') or pile.charging_power == 0:
                    pile.max_queue_size = 5
                    pile.charging_power = 7.0
                    pile.estimated_remaining_time = 0
                    pile.save()
                    self.stdout.write(f'  更新慢充桩: {pile.pile_id}') 