"""
队列服务单例模块
提供全局访问的queue_service实例，避免循环导入问题
"""
import logging
from django.conf import settings
from templateImage.queue_service import QueueService

# 设置logger
logger = logging.getLogger(__name__)

# 创建全局 QueueService 实例
queue_service = QueueService(
    redis_host=settings.REDIS_HOST,
    redis_port=settings.REDIS_PORT
)

# 初始化标记
_initialized = False

def initialize_queue_service():
    """初始化队列服务"""
    global _initialized
    if not _initialized:
        try:
            # 检查consumer是否已设置
            if not queue_service.get_consumer():
                logger.error("Consumer未设置，无法初始化队列服务")
                return False

            # 设置消费者（由应用初始化过程中调用）
            if hasattr(queue_service, 'initialize_recovery'):
                try:
                    queue_service.initialize_recovery()
                    logger.info("队列服务恢复功能已初始化")
                except Exception as e:
                    logger.warning(f"初始化队列服务恢复功能失败: {str(e)}")
                    logger.warning("将继续使用内存模式运行")
            
            # 启动消费者线程
            if hasattr(queue_service, 'start_consumer'):
                try:
                    queue_service.start_consumer()
                    logger.info("队列服务消费者线程已启动")
                except Exception as e:
                    logger.error(f"启动队列服务消费者线程失败: {str(e)}")
                    return False
            
            # 启动任务监控线程
            try:
                from templateImage.task_status_monitor import start_monitoring_thread
                start_monitoring_thread()
                logger.info("任务监控线程已启动")
            except Exception as e:
                logger.warning(f"启动任务监控线程失败: {str(e)}")
                logger.warning("将继续使用基本模式运行")
            
            _initialized = True
            logger.info("队列服务已完全初始化")
            return True
        except Exception as e:
            logger.error(f"初始化队列服务失败: {str(e)}")
            return False
    return True

# 导出实例和函数
__all__ = ['queue_service', 'initialize_queue_service'] 