from django.core.management.base import BaseCommand
from charging.models import SystemParameter
from charging.services import AdvancedChargingQueueService, BillingService


class Command(BaseCommand):
    help = '检查系统参数完整性和一致性'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='自动修复发现的问题'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='显示详细检查信息'
        )

    def handle(self, *args, **options):
        self.fix_mode = options['fix']
        self.verbose = options['verbose']
        
        self.stdout.write('🔍 开始检查系统参数完整性...')
        
        # 定义所有应该存在的参数
        self.required_parameters = self.get_required_parameters()
        
        # 执行检查
        issues_found = 0
        issues_found += self.check_missing_parameters()
        issues_found += self.check_parameter_types()
        issues_found += self.check_services_parameter_usage()
        issues_found += self.check_dynamic_parameters()
        
        if issues_found == 0:
            self.stdout.write(self.style.SUCCESS('✅ 系统参数检查通过，没有发现问题'))
        else:
            if self.fix_mode:
                self.stdout.write(
                    self.style.WARNING(f'⚠️ 发现 {issues_found} 个问题，已尝试自动修复')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ 发现 {issues_found} 个问题，使用 --fix 参数自动修复')
                )

    def get_required_parameters(self):
        """定义所有必需的系统参数"""
        return {
            # 充电桩配置
            'fast_charging_pile_num': {'type': 'int', 'default': '2', 'description': '快充桩数量'},
            'slow_charging_pile_num': {'type': 'int', 'default': '5', 'description': '慢充桩数量'},
            'fast_charging_power': {'type': 'float', 'default': '120.0', 'description': '快充桩充电功率(kW)'},
            'slow_charging_power': {'type': 'float', 'default': '7.0', 'description': '慢充桩充电功率(kW)'},
            
            # 队列管理配置
            'external_waiting_area_size': {'type': 'int', 'default': '50', 'description': '外部等候区最大容量'},
            'fast_pile_max_queue_size': {'type': 'int', 'default': '3', 'description': '快充桩队列最大容量'},
            'slow_pile_max_queue_size': {'type': 'int', 'default': '5', 'description': '慢充桩队列最大容量'},
            'queue_position_update_interval': {'type': 'int', 'default': '30', 'description': '队列位置更新间隔(秒)'},
            
            # 电价配置（services.py 中使用）
            'peak_rate': {'type': 'float', 'default': '1.2', 'description': '峰时电价(元/kWh)'},
            'normal_rate': {'type': 'float', 'default': '0.8', 'description': '平时电价(元/kWh)'},
            'valley_rate': {'type': 'float', 'default': '0.4', 'description': '谷时电价(元/kWh)'},
            'service_rate': {'type': 'float', 'default': '0.3', 'description': '服务费率(元/kWh)'},
            
            # 时间段配置
            'peak_hours_start': {'type': 'string', 'default': '8:00', 'description': '峰时开始时间'},
            'peak_hours_end': {'type': 'string', 'default': '11:00', 'description': '峰时结束时间'},
            'valley_hours_start': {'type': 'string', 'default': '23:00', 'description': '谷时开始时间'},
            'valley_hours_end': {'type': 'string', 'default': '7:00', 'description': '谷时结束时间'},
            
            # 系统配置
            'max_charging_time_per_session': {'type': 'int', 'default': '480', 'description': '单次充电最大时长(分钟)'},
            'notification_enabled': {'type': 'boolean', 'default': 'true', 'description': '是否启用通知功能'},
            'auto_queue_management': {'type': 'boolean', 'default': 'true', 'description': '是否启用自动队列管理'},
            'shortest_wait_time_threshold': {'type': 'int', 'default': '10', 'description': '最短等待时间调度阈值(分钟)'},
            
            # 故障处理配置（services.py 中使用）
            'fault_dispatch_strategy': {'type': 'string', 'default': 'priority', 'description': '故障调度策略(priority/time_order)'},
            'fault_detection_enabled': {'type': 'boolean', 'default': 'true', 'description': '是否启用充电桩故障检测'},
            'auto_recovery_enabled': {'type': 'boolean', 'default': 'true', 'description': '是否启用故障自动恢复处理'},
            'fault_notification_delay': {'type': 'int', 'default': '0', 'description': '故障通知延迟时间(秒)'},
            'recovery_reschedule_enabled': {'type': 'boolean', 'default': 'true', 'description': '恢复时是否重新调度队列'},
            
            # 维护配置
            'maintenance_check_interval': {'type': 'int', 'default': '24', 'description': '维护检查间隔(小时)'},
            'system_version': {'type': 'string', 'default': '2.0.0', 'description': '系统版本'},
        }

    def check_missing_parameters(self):
        """检查缺失的参数"""
        if self.verbose:
            self.stdout.write('\n📋 检查缺失参数...')
        
        existing_params = set(SystemParameter.objects.values_list('param_key', flat=True))
        required_params = set(self.required_parameters.keys())
        missing_params = required_params - existing_params
        
        issues_count = len(missing_params)
        
        if missing_params:
            self.stdout.write(
                self.style.WARNING(f'⚠️ 发现 {len(missing_params)} 个缺失参数:')
            )
            
            for param_key in missing_params:
                param_def = self.required_parameters[param_key]
                self.stdout.write(f'   - {param_key}: {param_def["description"]}')
                
                if self.fix_mode:
                    # 创建缺失的参数
                    SystemParameter.objects.create(
                        param_key=param_key,
                        param_value=param_def['default'],
                        param_type=param_def['type'],
                        description=param_def['description'],
                        is_editable=True
                    )
                    self.stdout.write(f'     ✓ 已创建')
        elif self.verbose:
            self.stdout.write('   ✅ 所有必需参数都存在')
        
        return issues_count

    def check_parameter_types(self):
        """检查参数类型是否正确"""
        if self.verbose:
            self.stdout.write('\n🔍 检查参数类型...')
        
        issues_count = 0
        
        for param in SystemParameter.objects.filter(param_key__in=self.required_parameters.keys()):
            required_type = self.required_parameters[param.param_key]['type']
            
            if param.param_type != required_type:
                issues_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️ 参数 {param.param_key} 类型不匹配: 期望 {required_type}, 实际 {param.param_type}'
                    )
                )
                
                if self.fix_mode:
                    param.param_type = required_type
                    param.save()
                    self.stdout.write(f'     ✓ 已修复类型为 {required_type}')
        
        if issues_count == 0 and self.verbose:
            self.stdout.write('   ✅ 所有参数类型正确')
        
        return issues_count

    def check_services_parameter_usage(self):
        """检查 services.py 中使用的参数是否可以正常访问"""
        if self.verbose:
            self.stdout.write('\n🔧 检查服务类参数访问...')
        
        issues_count = 0
        
        # 测试参数使用
        test_cases = [
            ('fault_dispatch_strategy', 'priority', '故障调度策略'),
            ('service_rate', '0.3', '服务费率'),
            ('peak_rate', '1.2', '峰时电价'),
            ('normal_rate', '0.8', '平时电价'),
            ('valley_rate', '0.4', '谷时电价'),
        ]
        
        # 创建服务实例进行测试
        try:
            billing_service = BillingService()
            
            for param_key, expected_default, description in test_cases:
                try:
                    value = billing_service._get_parameter(param_key, expected_default)
                    if self.verbose:
                        self.stdout.write(f'   ✓ {param_key}: {value} ({description})')
                except Exception as e:
                    issues_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'❌ 参数 {param_key} 访问失败: {e}')
                    )
                    
                    if self.fix_mode and param_key in self.required_parameters:
                        # 创建缺失的参数
                        param_def = self.required_parameters[param_key]
                        SystemParameter.objects.get_or_create(
                            param_key=param_key,
                            defaults={
                                'param_value': param_def['default'],
                                'param_type': param_def['type'],
                                'description': param_def['description'],
                                'is_editable': True
                            }
                        )
                        self.stdout.write(f'     ✓ 已创建参数 {param_key}')
                        
        except Exception as e:
            issues_count += 1
            self.stdout.write(
                self.style.ERROR(f'❌ 服务类初始化失败: {e}')
            )
        
        return issues_count

    def check_dynamic_parameters(self):
        """检查动态创建的参数（如故障状态参数）"""
        if self.verbose:
            self.stdout.write('\n🔄 检查动态参数状态...')
        
        issues_count = 0
        
        # 检查外部队列暂停参数
        dynamic_params = [
            'fast_external_queue_paused',
            'slow_external_queue_paused'
        ]
        
        for param_key in dynamic_params:
            try:
                param = SystemParameter.objects.get(param_key=param_key)
                value = param.get_value()
                
                if value not in [True, False]:
                    issues_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'⚠️ 动态参数 {param_key} 值无效: {value}')
                    )
                    
                    if self.fix_mode:
                        param.param_value = 'false'
                        param.save()
                        self.stdout.write(f'     ✓ 已重置为 false')
                elif self.verbose:
                    self.stdout.write(f'   ✓ {param_key}: {value}')
                    
            except SystemParameter.DoesNotExist:
                if self.verbose:
                    self.stdout.write(f'   📝 动态参数 {param_key} 未创建（正常，按需创建）')
        
        return issues_count 