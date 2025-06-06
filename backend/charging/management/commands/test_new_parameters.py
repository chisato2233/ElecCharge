from django.core.management.base import BaseCommand
from charging.utils.parameter_manager import (
    ParameterManager, 
    get_charging_pile_config,
    get_queue_config,
    get_pricing_config,
    get_time_period_config,
    get_system_config
)

class Command(BaseCommand):
    help = '测试新的参数管理系统'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🧪 测试新的参数管理系统'))
        self.stdout.write('=' * 50)
        
        self.test_parameter_manager()
        self.test_config_functions()
        self.test_cache_functionality()
        self.test_parameter_types()

    def test_parameter_manager(self):
        """测试ParameterManager基本功能"""
        self.stdout.write('\n🔧 === 测试ParameterManager基本功能 ===')
        
        # 测试获取存在的参数
        fast_power = ParameterManager.get_parameter('fast_charging_power', 100.0)
        self.stdout.write(f'✓ 快充功率: {fast_power}kW (类型: {type(fast_power).__name__})')
        
        # 测试获取不存在的参数（使用默认值）
        unknown_param = ParameterManager.get_parameter('unknown_param', 'default_value')
        self.stdout.write(f'✓ 未知参数: {unknown_param} (默认值)')
        
        # 测试布尔值参数
        auto_queue = ParameterManager.get_parameter('auto_queue_management', False)
        self.stdout.write(f'✓ 自动队列管理: {auto_queue} (类型: {type(auto_queue).__name__})')

    def test_config_functions(self):
        """测试配置获取函数"""
        self.stdout.write('\n📋 === 测试配置获取函数 ===')
        
        # 测试充电桩配置
        pile_config = get_charging_pile_config()
        self.stdout.write(f'🔌 充电桩配置:')
        for key, value in pile_config.items():
            self.stdout.write(f'   {key}: {value}')
        
        # 测试队列配置
        queue_config = get_queue_config()
        self.stdout.write(f'\n👥 队列配置:')
        for key, value in queue_config.items():
            self.stdout.write(f'   {key}: {value}')
        
        # 测试电价配置
        pricing_config = get_pricing_config()
        self.stdout.write(f'\n💰 电价配置:')
        for key, value in pricing_config.items():
            self.stdout.write(f'   {key}: {value} 元/kWh')
        
        # 测试时间段配置
        time_config = get_time_period_config()
        self.stdout.write(f'\n⏰ 时间段配置:')
        for key, value in time_config.items():
            self.stdout.write(f'   {key}: {value}')
        
        # 测试系统配置
        system_config = get_system_config()
        self.stdout.write(f'\n⚙️  系统配置:')
        for key, value in system_config.items():
            self.stdout.write(f'   {key}: {value}')

    def test_cache_functionality(self):
        """测试缓存功能"""
        self.stdout.write('\n🗂️  === 测试缓存功能 ===')
        
        import time
        
        # 第一次获取（应该从数据库读取）
        start_time = time.time()
        value1 = ParameterManager.get_parameter('fast_charging_power')
        time1 = time.time() - start_time
        
        # 第二次获取（应该从缓存读取）
        start_time = time.time()
        value2 = ParameterManager.get_parameter('fast_charging_power')
        time2 = time.time() - start_time
        
        self.stdout.write(f'✓ 第一次获取: {value1} (耗时: {time1:.4f}s)')
        self.stdout.write(f'✓ 第二次获取: {value2} (耗时: {time2:.4f}s)')
        self.stdout.write(f'✓ 缓存效果: {"生效" if time2 < time1 else "未生效"}')
        
        # 清除缓存测试
        ParameterManager.clear_cache('fast_charging_power')
        self.stdout.write('✓ 缓存已清除')

    def test_parameter_types(self):
        """测试参数类型转换"""
        self.stdout.write('\n🔄 === 测试参数类型转换 ===')
        
        # 测试整数类型
        int_param = ParameterManager.get_parameter('fast_charging_pile_num')
        self.stdout.write(f'✓ 整数参数: {int_param} (类型: {type(int_param).__name__})')
        assert isinstance(int_param, int), "整数参数类型转换失败"
        
        # 测试浮点数类型
        float_param = ParameterManager.get_parameter('fast_charging_power')
        self.stdout.write(f'✓ 浮点数参数: {float_param} (类型: {type(float_param).__name__})')
        assert isinstance(float_param, float), "浮点数参数类型转换失败"
        
        # 测试布尔类型
        bool_param = ParameterManager.get_parameter('auto_queue_management')
        self.stdout.write(f'✓ 布尔参数: {bool_param} (类型: {type(bool_param).__name__})')
        assert isinstance(bool_param, bool), "布尔参数类型转换失败"
        
        # 测试字符串类型
        str_param = ParameterManager.get_parameter('peak_hours_start')
        self.stdout.write(f'✓ 字符串参数: {str_param} (类型: {type(str_param).__name__})')
        assert isinstance(str_param, str), "字符串参数类型转换失败"
        
        self.stdout.write('✅ 所有类型转换测试通过')

    def test_set_parameter(self):
        """测试参数设置功能"""
        self.stdout.write('\n✏️  === 测试参数设置功能 ===')
        
        # 设置一个测试参数
        test_key = 'test_parameter'
        test_value = 'test_value'
        
        success = ParameterManager.set_parameter(
            test_key, 
            test_value, 
            description='测试参数'
        )
        
        if success:
            # 验证设置是否成功
            retrieved_value = ParameterManager.get_parameter(test_key)
            if retrieved_value == test_value:
                self.stdout.write(f'✓ 参数设置成功: {test_key} = {retrieved_value}')
            else:
                self.stdout.write(f'❌ 参数设置失败: 期望 {test_value}, 实际 {retrieved_value}')
        else:
            self.stdout.write(f'❌ 参数设置操作失败')

        self.stdout.write(f'\n🎉 新参数管理系统测试完成！') 