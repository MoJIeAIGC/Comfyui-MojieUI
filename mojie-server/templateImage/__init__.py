import logging
import os

logger = logging.getLogger(__name__)

# 应用启动时执行的代码
logger.info("初始化 TemplateImage 模块...")

try:
    # 确保comfyui目录存在
    comfyui_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "comfyui")
    if not os.path.exists(comfyui_dir):
        os.makedirs(comfyui_dir, exist_ok=True)
        logger.info(f"创建comfyui目录: {comfyui_dir}")
    logger.info(f"comfyui目录: {comfyui_dir}")
    
    # 延迟导入初始化模块
    def initialize_workflows():
        try:
            from . import init_workflows
            logger.info("工作流初始化完成")
        except Exception as e:
            logger.error(f"工作流初始化失败: {str(e)}")
    
    # 导入任务管理器并初始化
    def initialize_task_manager():
        """
        延迟初始化任务管理器，确保Django已完全加载
        """
        try:
            from . import task_manager
            task_manager.initialize_task_managers()
            logger.info("任务类型管理器初始化完成")
        except Exception as e:
            logger.error(f"初始化任务类型管理器失败: {str(e)}")
    
    # 注册应用就绪事件
    from django.apps import AppConfig
    
    class TemplateImageConfig(AppConfig):
        name = 'templateImage'
        
        def ready(self):
            # 延迟导入以避免循环引用
            import threading
            # 延迟2秒执行初始化
            threading.Timer(2, initialize_workflows).start()
            threading.Timer(2, initialize_task_manager).start()
            logger.info("任务类型管理器和工作流初始化已安排")
    
    logger.info("TemplateImage 服务初始化完成")
except Exception as e:
    logger.error(f"初始化 TemplateImage 服务失败: {str(e)}")
