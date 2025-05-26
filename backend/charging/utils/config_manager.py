from django.core.cache import cache
from charging.models import SystemParameter
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """系统配置管理器"""
    
    # 缓存键前缀
    CACHE_PREFIX = 'system_param_'
    CACHE_TIMEOUT = 300  # 5分钟缓存
    
    # 默认配置值
    DEFAULT_CONFIG = {
        'FastChargingPileNum': {'value': 2, 'type': 'int', 'description': '快充电桩数量'},
        'TrickleChargingPileNum': {'value': 3, 'type': 'int', 'description': '慢充电桩数量'},
        'WaitingAreaSize': {'value': 6, 'type': 'int', 'description': '等候区容量'},
        'ChargingQueueLen': {'value': 2, 'type': 'int', 'description': '每桩排队队列长度'},
    }
    
    @classmethod
    def get_parameter(cls, key, default=None):
        """获取系统参数"""
        # 先从缓存获取
        cache_key = f"{cls.CACHE_PREFIX}{key}"
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            return cached_value
        
        try:
            # 从数据库获取
            param = SystemParameter.objects.get(param_key=key)
            value = param.get_value()
            
            # 存入缓存
            cache.set(cache_key, value, cls.CACHE_TIMEOUT)
            return value
            
        except SystemParameter.DoesNotExist:
            # 如果参数不存在，使用默认值并创建
            if key in cls.DEFAULT_CONFIG:
                default_config = cls.DEFAULT_CONFIG[key]
                cls.set_parameter(
                    key, 
                    default_config['value'], 
                    default_config['type'],
                    default_config['description']
                )
                return default_config['value']
            
            logger.warning(f"系统参数 {key} 不存在，使用默认值: {default}")
            return default
    
    @classmethod
    def set_parameter(cls, key, value, param_type='string', description=''):
        """设置系统参数"""
        try:
            param, created = SystemParameter.objects.get_or_create(
                param_key=key,
                defaults={
                    'param_type': param_type,
                    'description': description,
                    'is_editable': True
                }
            )
            param.set_value(value)
            param.save()
            
            # 清除缓存
            cache_key = f"{cls.CACHE_PREFIX}{key}"
            cache.delete(cache_key)
            
            logger.info(f"系统参数 {key} 已更新为: {value}")
            return True
            
        except Exception as e:
            logger.error(f"设置系统参数 {key} 失败: {str(e)}")
            return False
    
    @classmethod
    def get_all_parameters(cls):
        """获取所有系统参数"""
        params = {}
        for param in SystemParameter.objects.all():
            params[param.param_key] = param.get_value()
        return params
    
    @classmethod
    def initialize_default_config(cls):
        """初始化默认配置"""
        for key, config in cls.DEFAULT_CONFIG.items():
            if not SystemParameter.objects.filter(param_key=key).exists():
                cls.set_parameter(
                    key, 
                    config['value'], 
                    config['type'], 
                    config['description']
                )

# 便捷访问函数
def get_config(key, default=None):
    return ConfigManager.get_parameter(key, default)

def set_config(key, value, param_type='string', description=''):
    return ConfigManager.set_parameter(key, value, param_type, description)
