from django.core.management.base import BaseCommand
from charging.models import SystemParameter, ChargingPile
from django.db import transaction

class Command(BaseCommand):
    help = '清理旧参数并设置统一命名风格的系统参数'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='确认执行操作',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING('⚠️  这将清除所有现有系统参数并重新设置。')
            )
            self.stdout.write(
                self.style.WARNING('请使用 --confirm 参数确认执行。')
            )
            return

        self.stdout.write(self.style.SUCCESS('🔄 开始重置系统参数...'))
        
        with transaction.atomic():
            self.clear_old_parameters()
            self.set_new_parameters()
            self.update_charging_pile_settings()
        
        self.stdout.write(self.style.SUCCESS('✅ 系统参数重置完成！'))
        self.show_final_status()

    def clear_old_parameters(self):
        """清除所有旧参数"""
        old_count = SystemParameter.objects.count()
        SystemParameter.objects.all().delete()
        self.stdout.write(f'🗑️  已清除 {old_count} 个旧参数')

    def set_new_parameters(self):
        """设置新的统一命名风格的参数"""
        self.stdout.write('📝 设置新的系统参数...')
        
        # 定义新参数（使用下划线命名风格）
        new_parameters = [
            # 充电桩配置
            {
                'param_key': 'fast_charging_pile_num',
                'param_value': '2',
                'param_type': 'int',
                'description': '快充桩数量',
                'is_editable': True
            },
            {
                'param_key': 'slow_charging_pile_num',
                'param_value': '5',
                'param_type': 'int',
                'description': '慢充桩数量',
                'is_editable': True
            },
            {
                'param_key': 'fast_charging_power',
                'param_value': '120.0',
                'param_type': 'float',
                'description': '快充桩充电功率(kW)',
                'is_editable': True
            },
            {
                'param_key': 'slow_charging_power',
                'param_value': '7.0',
                'param_type': 'float',
                'description': '慢充桩充电功率(kW)',
                'is_editable': True
            },
            
            # 队列管理配置
            {
                'param_key': 'external_waiting_area_size',
                'param_value': '50',
                'param_type': 'int',
                'description': '外部等候区最大容量',
                'is_editable': True
            },
            {
                'param_key': 'fast_pile_max_queue_size',
                'param_value': '3',
                'param_type': 'int',
                'description': '快充桩队列最大容量',
                'is_editable': True
            },
            {
                'param_key': 'slow_pile_max_queue_size',
                'param_value': '5',
                'param_type': 'int',
                'description': '慢充桩队列最大容量',
                'is_editable': True
            },
            {
                'param_key': 'queue_position_update_interval',
                'param_value': '30',
                'param_type': 'int',
                'description': '队列位置更新间隔(秒)',
                'is_editable': True
            },
            
            # 电价配置
            {
                'param_key': 'peak_rate',
                'param_value': '1.2',
                'param_type': 'float',
                'description': '峰时电价(元/kWh)',
                'is_editable': True
            },
            {
                'param_key': 'normal_rate',
                'param_value': '0.8',
                'param_type': 'float',
                'description': '平时电价(元/kWh)',
                'is_editable': True
            },
            {
                'param_key': 'valley_rate',
                'param_value': '0.4',
                'param_type': 'float',
                'description': '谷时电价(元/kWh)',
                'is_editable': True
            },
            {
                'param_key': 'service_rate',
                'param_value': '0.3',
                'param_type': 'float',
                'description': '服务费率(元/kWh)',
                'is_editable': True
            },
            
            # 时间段配置
            {
                'param_key': 'peak_hours_start',
                'param_value': '8:00',
                'param_type': 'string',
                'description': '峰时开始时间',
                'is_editable': True
            },
            {
                'param_key': 'peak_hours_end',
                'param_value': '11:00',
                'param_type': 'string',
                'description': '峰时结束时间',
                'is_editable': True
            },
            {
                'param_key': 'valley_hours_start',
                'param_value': '23:00',
                'param_type': 'string',
                'description': '谷时开始时间',
                'is_editable': True
            },
            {
                'param_key': 'valley_hours_end',
                'param_value': '7:00',
                'param_type': 'string',
                'description': '谷时结束时间',
                'is_editable': True
            },
            
            # 系统配置
            {
                'param_key': 'max_charging_time_per_session',
                'param_value': '480',
                'param_type': 'int',
                'description': '单次充电最大时长(分钟)',
                'is_editable': True
            },
            {
                'param_key': 'notification_enabled',
                'param_value': 'true',
                'param_type': 'boolean',
                'description': '是否启用通知功能',
                'is_editable': True
            },
            {
                'param_key': 'auto_queue_management',
                'param_value': 'true',
                'param_type': 'boolean',
                'description': '是否启用自动队列管理',
                'is_editable': True
            },
            {
                'param_key': 'shortest_wait_time_threshold',
                'param_value': '10',
                'param_type': 'int',
                'description': '最短等待时间调度阈值(分钟)',
                'is_editable': True
            },
            
            # 故障处理配置
            {
                'param_key': 'fault_dispatch_strategy',
                'param_value': 'priority',
                'param_type': 'string',
                'description': '故障调度策略(priority/time_order)',
                'is_editable': True
            },
            {
                'param_key': 'fault_detection_enabled',
                'param_value': 'true',
                'param_type': 'boolean',
                'description': '是否启用充电桩故障检测',
                'is_editable': True
            },
            {
                'param_key': 'auto_recovery_enabled',
                'param_value': 'true',
                'param_type': 'boolean',
                'description': '是否启用故障自动恢复处理',
                'is_editable': True
            },
            {
                'param_key': 'fault_notification_delay',
                'param_value': '0',
                'param_type': 'int',
                'description': '故障通知延迟时间(秒)',
                'is_editable': True
            },
            {
                'param_key': 'recovery_reschedule_enabled',
                'param_value': 'true',
                'param_type': 'boolean',
                'description': '恢复时是否重新调度队列',
                'is_editable': True
            },
            
            # 维护配置
            {
                'param_key': 'maintenance_check_interval',
                'param_value': '24',
                'param_type': 'int',
                'description': '维护检查间隔(小时)',
                'is_editable': False
            },
            {
                'param_key': 'system_version',
                'param_value': '2.0.0',
                'param_type': 'string',
                'description': '系统版本',
                'is_editable': False
            }
        ]
        
        # 批量创建参数
        created_count = 0
        for param_data in new_parameters:
            param, created = SystemParameter.objects.get_or_create(
                param_key=param_data['param_key'],
                defaults=param_data
            )
            if created:
                created_count += 1
                self.stdout.write(f'   ✓ 创建参数: {param_data["param_key"]} = {param_data["param_value"]}')
        
        self.stdout.write(f'📊 共创建 {created_count} 个新参数')

    def update_charging_pile_settings(self):
        """根据新参数更新充电桩设置"""
        self.stdout.write('🔧 更新充电桩设置...')
        
        try:
            # 获取参数值
            fast_power = float(SystemParameter.objects.get(param_key='fast_charging_power').param_value)
            slow_power = float(SystemParameter.objects.get(param_key='slow_charging_power').param_value)
            fast_queue_size = int(SystemParameter.objects.get(param_key='fast_pile_max_queue_size').param_value)
            slow_queue_size = int(SystemParameter.objects.get(param_key='slow_pile_max_queue_size').param_value)
            
            # 更新快充桩
            fast_piles_updated = ChargingPile.objects.filter(pile_type='fast').update(
                charging_power=fast_power,
                max_queue_size=fast_queue_size
            )
            
            # 更新慢充桩
            slow_piles_updated = ChargingPile.objects.filter(pile_type='slow').update(
                charging_power=slow_power,
                max_queue_size=slow_queue_size
            )
            
            self.stdout.write(f'   ✓ 更新 {fast_piles_updated} 个快充桩设置')
            self.stdout.write(f'   ✓ 更新 {slow_piles_updated} 个慢充桩设置')
            
        except SystemParameter.DoesNotExist as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 参数不存在: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 更新充电桩设置失败: {e}')
            )

    def show_final_status(self):
        """显示最终状态"""
        self.stdout.write('\n📋 === 参数设置完成状态 ===')
        
        # 按类别显示参数
        categories = {
            '充电桩配置': [
                'fast_charging_pile_num', 'slow_charging_pile_num',
                'fast_charging_power', 'slow_charging_power'
            ],
            '队列管理': [
                'external_waiting_area_size', 'fast_pile_max_queue_size',
                'slow_pile_max_queue_size', 'queue_position_update_interval'
            ],
            '电价配置': [
                'peak_rate', 'normal_rate', 'valley_rate', 'service_rate'
            ],
            '时间段配置': [
                'peak_hours_start', 'peak_hours_end',
                'valley_hours_start', 'valley_hours_end'
            ],
            '系统配置': [
                'max_charging_time_per_session', 'notification_enabled',
                'auto_queue_management', 'shortest_wait_time_threshold'
            ]
        }
        
        for category, param_keys in categories.items():
            self.stdout.write(f'\n🏷️  {category}:')
            for key in param_keys:
                try:
                    param = SystemParameter.objects.get(param_key=key)
                    unit = self.get_param_unit(key)
                    self.stdout.write(
                        f'   {key}: {param.param_value}{unit} ({param.param_type})'
                    )
                except SystemParameter.DoesNotExist:
                    self.stdout.write(f'   {key}: ❌ 未找到')

    def get_param_unit(self, param_key):
        """获取参数单位"""
        units = {
            'fast_charging_pile_num': '个',
            'slow_charging_pile_num': '个',
            'external_waiting_area_size': '人',
            'fast_pile_max_queue_size': '人',
            'slow_pile_max_queue_size': '人',
            'queue_position_update_interval': '秒',
            'fast_charging_power': 'kW',
            'slow_charging_power': 'kW',
            'peak_rate': '元/kWh',
            'normal_rate': '元/kWh',
            'valley_rate': '元/kWh',
            'service_rate': '元/kWh',
            'max_charging_time_per_session': '分钟',
            'shortest_wait_time_threshold': '分钟',
            'maintenance_check_interval': '小时'
        }
        return units.get(param_key, '') 