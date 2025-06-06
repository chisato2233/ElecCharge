"""
系统参数管理工具

提供统一的参数获取和设置接口，确保参数命名的一致性
"""

from charging.models import SystemParameter
from django.core.cache import cache
from typing import Union, Any, Optional


class ParameterManager:
    """系统参数管理器"""
    
    # 缓存前缀
    CACHE_PREFIX = 'sys_param:'
    # 缓存超时时间（秒）
    CACHE_TIMEOUT = 300  # 5分钟
    
    @classmethod
    def get_parameter(cls, key: str, default: Any = None, param_type: str = 'auto') -> Any:
        """
        获取系统参数值
        
        Args:
            key: 参数键名
            default: 默认值（如果参数不存在）
            param_type: 参数类型，'auto'表示自动检测
        
        Returns:
            参数值（已转换为对应类型）
        """
        # 尝试从缓存获取
        cache_key = f"{cls.CACHE_PREFIX}{key}"
        cached_value = cache.get(cache_key)
        
        if cached_value is not None:
            return cached_value
        
        try:
            param = SystemParameter.objects.get(param_key=key)
            value = cls._convert_value(param.param_value, param.param_type)
            
            # 存入缓存
            cache.set(cache_key, value, cls.CACHE_TIMEOUT)
            return value
            
        except SystemParameter.DoesNotExist:
            return default
    
    @classmethod
    def set_parameter(cls, key: str, value: Any, param_type: str = 'auto', description: str = '') -> bool:
        """
        设置系统参数值
        
        Args:
            key: 参数键名
            value: 参数值
            param_type: 参数类型，'auto'表示自动检测
            description: 参数描述
        
        Returns:
            是否设置成功
        """
        try:
            # 自动检测类型
            if param_type == 'auto':
                param_type = cls._detect_type(value)
            
            # 更新或创建参数
            param, created = SystemParameter.objects.update_or_create(
                param_key=key,
                defaults={
                    'param_value': str(value),
                    'param_type': param_type,
                    'description': description
                }
            )
            
            # 清除缓存
            cache_key = f"{cls.CACHE_PREFIX}{key}"
            cache.delete(cache_key)
            
            return True
            
        except Exception:
            return False
    
    @classmethod
    def _convert_value(cls, value: str, param_type: str) -> Any:
        """将字符串值转换为对应类型"""
        if param_type == 'int':
            return int(value)
        elif param_type == 'float':
            return float(value)
        elif param_type == 'boolean':
            return value.lower() in ('true', '1', 'yes', 'on')
        elif param_type == 'json':
            import json
            return json.loads(value)
        else:  # string
            return value
    
    @classmethod
    def _detect_type(cls, value: Any) -> str:
        """自动检测值的类型"""
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'int'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, (dict, list)):
            return 'json'
        else:
            return 'string'
    
    @classmethod
    def clear_cache(cls, key: Optional[str] = None):
        """清除参数缓存"""
        if key:
            cache_key = f"{cls.CACHE_PREFIX}{key}"
            cache.delete(cache_key)
        else:
            # 清除所有参数缓存
            cache.delete_many([
                f"{cls.CACHE_PREFIX}{param.param_key}" 
                for param in SystemParameter.objects.all()
            ])


# 常用参数获取函数（简化接口）
def get_charging_pile_config():
    """获取充电桩配置"""
    return {
        'fast_pile_num': ParameterManager.get_parameter('fast_charging_pile_num', 2, 'int'),
        'slow_pile_num': ParameterManager.get_parameter('slow_charging_pile_num', 5, 'int'),
        'fast_power': ParameterManager.get_parameter('fast_charging_power', 120.0, 'float'),
        'slow_power': ParameterManager.get_parameter('slow_charging_power', 7.0, 'float'),
    }


def get_queue_config():
    """获取队列管理配置"""
    return {
        'external_waiting_area_size': ParameterManager.get_parameter('external_waiting_area_size', 50, 'int'),
        'fast_pile_max_queue_size': ParameterManager.get_parameter('fast_pile_max_queue_size', 3, 'int'),
        'slow_pile_max_queue_size': ParameterManager.get_parameter('slow_pile_max_queue_size', 5, 'int'),
        'queue_update_interval': ParameterManager.get_parameter('queue_position_update_interval', 30, 'int'),
        'shortest_wait_threshold': ParameterManager.get_parameter('shortest_wait_time_threshold', 10, 'int'),
    }


def get_pricing_config():
    """获取电价配置"""
    return {
        'peak_rate': ParameterManager.get_parameter('peak_rate', 1.2, 'float'),
        'normal_rate': ParameterManager.get_parameter('normal_rate', 0.8, 'float'),
        'valley_rate': ParameterManager.get_parameter('valley_rate', 0.4, 'float'),
        'service_rate': ParameterManager.get_parameter('service_rate', 0.3, 'float'),
    }


def get_time_period_config():
    """获取时间段配置"""
    return {
        'peak_start': ParameterManager.get_parameter('peak_hours_start', '8:00'),
        'peak_end': ParameterManager.get_parameter('peak_hours_end', '11:00'),
        'valley_start': ParameterManager.get_parameter('valley_hours_start', '23:00'),
        'valley_end': ParameterManager.get_parameter('valley_hours_end', '7:00'),
    }


def get_system_config():
    """获取系统配置"""
    return {
        'max_charging_time': ParameterManager.get_parameter('max_charging_time_per_session', 480, 'int'),
        'notification_enabled': ParameterManager.get_parameter('notification_enabled', True, 'boolean'),
        'auto_queue_management': ParameterManager.get_parameter('auto_queue_management', True, 'boolean'),
    } 