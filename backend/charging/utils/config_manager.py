"""
弃用的配置管理器 - 仅保留向后兼容接口
实际实现已迁移到 parameter_manager.py
"""

from .parameter_manager import ParameterManager
import logging

logger = logging.getLogger(__name__)

# 仅保留向后兼容的接口

class ConfigManager:
    """
    弃用的配置管理器类
    
    此类已弃用，请使用 charging.utils.parameter_manager.ParameterManager
    保留此类仅为向后兼容，所有调用都会委托给新的参数管理器
    """
    
    @classmethod
    def get_parameter(cls, key, default=None):
        """获取系统参数 - 委托给新的参数管理器"""
        logger.warning(f"ConfigManager.get_parameter 已弃用，请使用 ParameterManager.get_parameter")
        return ParameterManager.get_parameter(key, default)
    
    @classmethod
    def set_parameter(cls, key, value, param_type='string', description=''):
        """设置系统参数 - 委托给新的参数管理器"""
        logger.warning(f"ConfigManager.set_parameter 已弃用，请使用 ParameterManager.set_parameter")
        return ParameterManager.set_parameter(key, value, param_type, description)
    
    @classmethod
    def initialize_default_config(cls):
        """
        初始化默认配置 - 已弃用
        
        请使用 reset_system_parameters 命令来初始化系统参数
        """
        logger.warning("ConfigManager.initialize_default_config 已弃用")
        logger.info("请使用 'python manage.py reset_system_parameters --confirm' 来初始化系统参数")
        # 空实现，不执行任何操作

# 向后兼容的便捷函数
def get_config(key, default=None):
    """弃用的便捷函数，委托给新的参数管理器"""
    logger.warning("get_config 函数已弃用，请使用 ParameterManager.get_parameter")
    return ParameterManager.get_parameter(key, default)

def set_config(key, value, param_type='string', description=''):
    """弃用的便捷函数，委托给新的参数管理器"""
    logger.warning("set_config 函数已弃用，请使用 ParameterManager.set_parameter")
    return ParameterManager.set_parameter(key, value, param_type, description)
