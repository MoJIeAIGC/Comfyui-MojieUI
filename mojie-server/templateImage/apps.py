import os
import logging
import time
from typing import Type, Any
from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from threading import Thread
from django.core.cache import cache
import traceback

logger = logging.getLogger(__name__)

class TemplateImageConfig(AppConfig):
    """
    模板图片应用配置，负责初始化后台服务

    特性：
    1. 开发模式下避免重复初始化
    2. 完善的配置检查
    3. 优雅的服务关闭
    4. 服务健康检查
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'templateImage'

    def __init__(self, app_name, app_module):
        super().__init__(app_name, app_module)
        self.queue_service = None
        self.comfyui_consumer = None

    def ready(self):
        """
        在应用启动时执行的初始化代码
        用于设置默认值和初始化配置
        """
        # 导入信号处理器
        import templateImage.signals
        
        # 注册数据库迁移后的信号处理
        from django.db.models.signals import post_migrate
        post_migrate.connect(self._handle_post_migrate, sender=self)

        if self._should_start_services():
            try:
                # 使用线程延迟初始化服务
                import threading
                threading.Timer(2, self._initialize_services).start()
                logger.info("服务初始化已安排在后台线程中")
            except Exception as e:
                logger.error(f"安排服务初始化失败: {str(e)}")
                logger.error(traceback.format_exc())

    def _initialize_services(self):
        """在后台线程中初始化服务"""
        try:
            from .comfyUI_consumer import ComfyUIConsumer
            from .queue_service_singleton import queue_service, initialize_queue_service
            from .ImageService import ImageService
            
            # 初始化 ComfyUI 消费者
            comfyui_url = getattr(settings, 'COMFYUI_SERVER_ADDRESS', '127.0.0.1:8188')
            workflow_file = getattr(settings, 'COMFYUI_WORKFLOW_FILE', 'comfyui/text_image.json')
            output_dir = getattr(settings, 'COMFYUI_OUTPUT_DIR', 'output')

            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)

            # 创建消费者实例
            consumer = ComfyUIConsumer(
                comfyui_url=comfyui_url,
                workflow_file=workflow_file,
                output_dir=output_dir
            )

            # 将队列服务实例赋值给 ImageService
            ImageService.queue_service = queue_service

            # 初始化队列服务（包括启动消费者线程）
            initialize_queue_service()

            # 设置ComfyUI任务自动保存到云空间的默认值
            cache.set("comfyui_auto_save_default_global", False, timeout=None)

            logger.info("应用初始化完成")
        except Exception as e:
            logger.error(f"应用初始化失败: {str(e)}")
            logger.error(traceback.format_exc())

    def _handle_post_migrate(self, sender, **kwargs):
        """在数据库迁移完成后处理任务恢复"""
        if self.queue_service:
            self.queue_service.initialize_recovery()

    def _should_start_services(self) -> bool:
        """判断是否需要启动后台服务"""
        # 生产环境总是启动
        if not settings.DEBUG:
            return True

        # 开发模式下确保只启动一次（避免Django的自动重载导致重复初始化）
        return os.environ.get('RUN_MAIN') == 'true'

    def start_services(self, consumer_class: Type[Any], queue_class: Type[Any]):
        """初始化并启动所有后台服务"""
        logger.info("正在启动后台服务...")

        # 初始化队列服务
        self.queue_service = self._init_queue_service(queue_class)

        # 初始化ComfyUI消费者
        self.comfyui_consumer = self._init_comfyui_consumer(consumer_class)

        # 将消费者注入队列服务
        self.queue_service.set_consumer(self.comfyui_consumer)

        logger.info("后台服务启动完成")

    def _init_queue_service(self, queue_class: Type[Any]):
        """初始化队列服务"""
        required_settings = ['REDIS_HOST', 'REDIS_PORT']
        self._check_settings(required_settings)

        logger.info(f"初始化队列服务 (Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT})")
        return queue_class(
            redis_host=settings.REDIS_HOST,
            redis_port=settings.REDIS_PORT
        )

    def _init_comfyui_consumer(self, consumer_class):
        """初始化ComfyUI消费者"""
        try:
            # 获取配置
            comfyui_url = getattr(settings, 'COMFYUI_SERVER_ADDRESS', '127.0.0.1:8188')
            workflow_file = getattr(settings, 'COMFYUI_WORKFLOW_FILE', 'workflow_api.json')
            output_dir = getattr(settings, 'COMFYUI_OUTPUT_DIR', 'output')

            # 创建消费者实例
            return consumer_class(
                comfyui_url=comfyui_url,
                workflow_file=workflow_file,
                output_dir=output_dir
            )
        except Exception as e:
            logger.error(f"初始化ComfyUI消费者失败: {str(e)}")
            raise

    def _check_settings(self, required_settings: list):
        """检查必需的配置项"""
        for setting in required_settings:
            if not hasattr(settings, setting):
                raise ImproperlyConfigured(
                    f"缺少必要配置: {setting}. 请在settings.py中配置此参数"
                )

    def _check_services_health(self):
        """检查服务健康状态"""
        if not self.queue_service.is_redis_available:
            logger.warning("Redis连接不可用，将使用本地内存队列")

        # 可以添加更多的健康检查逻辑
        logger.info("服务健康检查通过")

    def shutdown_services(self):
        """优雅关闭后台服务"""
        if self.queue_service:
            logger.info("正在关闭队列服务...")
            self.queue_service.shutdown()

        # 可以添加其他服务的关闭逻辑
        logger.info("后台服务已关闭")