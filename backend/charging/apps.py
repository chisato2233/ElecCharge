from django.apps import AppConfig


class ChargingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'charging'

    def ready(self):
        # 导入配置管理器并初始化默认配置
        from charging.utils.config_manager import ConfigManager
        try:
            ConfigManager.initialize_default_config()
        except Exception as e:
            # 在迁移期间可能会出错，忽略
            pass
