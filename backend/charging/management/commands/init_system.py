# backend/charging/management/commands/init_system_params.py
from django.core.management.base import BaseCommand
from charging.models import SystemParameter, ChargingPile

class Command(BaseCommand):
    help = '初始化系统参数和充电桩'
    
    def handle(self, *args, **options):
        # 初始化系统参数
        default_params = [
            ('FastChargingPileNum', '2', 'int', '快充电桩数量'),
            ('TrickleChargingPileNum', '3', 'int', '慢充电桩数量'),
            ('WaitingAreaSize', '10', 'int', '等候区容量'),
            ('ChargingQueueLen', '5', 'int', '每桩排队队列长度'),
            ('peak_rate', '1.2', 'float', '峰时电价(元/kWh)'),
            ('normal_rate', '0.8', 'float', '平时电价(元/kWh)'),
            ('valley_rate', '0.4', 'float', '谷时电价(元/kWh)'),
            ('service_rate', '0.8', 'float', '服务费(元/kWh)'),
        ]
        
        for param_key, param_value, param_type, description in default_params:
            obj, created = SystemParameter.objects.get_or_create(
                param_key=param_key,
                defaults={
                    'param_value': param_value,
                    'param_type': param_type,
                    'description': description,
                    'is_editable': True
                }
            )
            if created:
                self.stdout.write(f'✅ 创建参数: {param_key} = {param_value}')
            else:
                self.stdout.write(f'ℹ️  参数已存在: {param_key} = {obj.param_value}')
        
        # 初始化充电桩
        try:
            fast_count = SystemParameter.objects.get(param_key='FastChargingPileNum').get_value()
            slow_count = SystemParameter.objects.get(param_key='TrickleChargingPileNum').get_value()
            
            # 创建快充桩
            for i in range(1, fast_count + 1):
                pile_id = f'FAST-{i:03d}'
                pile, created = ChargingPile.objects.get_or_create(
                    pile_id=pile_id,
                    defaults={'pile_type': 'fast', 'status': 'normal'}
                )
                if created:
                    self.stdout.write(f'✅ 创建快充桩: {pile_id}')
            
            # 创建慢充桩
            for i in range(1, slow_count + 1):
                pile_id = f'SLOW-{i:03d}'
                pile, created = ChargingPile.objects.get_or_create(
                    pile_id=pile_id,
                    defaults={'pile_type': 'slow', 'status': 'normal'}
                )
                if created:
                    self.stdout.write(f'✅ 创建慢充桩: {pile_id}')
            
            self.stdout.write(self.style.SUCCESS('🎉 系统参数和充电桩初始化完成！'))
            
        except SystemParameter.DoesNotExist:
            self.stdout.write(self.style.ERROR('❌ 系统参数不存在，请先运行参数初始化'))