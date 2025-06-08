from django.apps import AppConfig
import os


class ChargingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'charging'

    def ready(self):
        # 不再使用弃用的ConfigManager，系统参数通过reset_system_parameters命令管理
        # 在系统启动时自动同步充电桩状态（仅在正常运行时）
        self._auto_sync_charging_piles()

    def _auto_sync_charging_piles(self):
        """自动同步充电桩状态"""
        # 检查是否应该跳过同步（在迁移、测试、命令行等情况下）
        import sys
        
        # 跳过条件：
        # 1. 正在运行迁移
        # 2. 正在运行测试
        # 3. 正在收集静态文件
        # 4. 环境变量明确禁用
        skip_conditions = [
            'migrate' in sys.argv,
            'makemigrations' in sys.argv,
            'test' in sys.argv,
            'collectstatic' in sys.argv,
            'check' in sys.argv,
            os.environ.get('SKIP_PILE_SYNC', '').lower() in ['true', '1', 'yes'],
            # 检查是否在Django shell中
            'shell' in sys.argv,
            'shell_plus' in sys.argv,
        ]
        
        if any(skip_conditions):
            return
            
        # 延迟导入避免在应用初始化时出现循环导入
        from django.core.management import call_command
        from django.db import connection
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # 检查数据库连接是否可用
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            # 检查必要的表是否存在
            if not self._check_tables_exist():
                logger.info("充电桩相关表尚未创建，跳过同步")
                return
            
            # 异步执行同步，避免阻塞启动过程
            import threading
            sync_thread = threading.Thread(
                target=self._perform_sync,
                daemon=True  # 守护线程，主程序退出时自动结束
            )
            sync_thread.start()
            
        except Exception as e:
            # 数据库不可用或其他错误，静默跳过
            logger.debug(f"跳过充电桩同步: {e}")
    
    def _check_tables_exist(self):
        """检查必要的数据库表是否存在"""
        from django.db import connection
        
        try:
            with connection.cursor() as cursor:
                # 检查关键表是否存在
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_name IN ('charging_pile', 'system_parameters')
                """)
                result = cursor.fetchone()
                return result[0] >= 2  # 至少有这两个表
        except Exception:
            return False
    
    def _perform_sync(self):
        """执行实际的同步操作"""
        import time
        import logging
        from django.core.management import call_command
        
        logger = logging.getLogger(__name__)
        
        # 等待一小段时间确保应用完全启动
        time.sleep(2)
        
        try:
            logger.info("🚀 系统启动 - 开始自动同步充电桩状态...")
            
            # 调用同步命令，使用安静模式
            call_command(
                'sync_charging_piles',
                verbosity=0,  # 安静模式
            )
            
            logger.info("✅ 充电桩状态同步完成")
            
        except Exception as e:
            logger.error(f"❌ 充电桩自动同步失败: {e}")
            # 不抛出异常，避免影响应用启动
