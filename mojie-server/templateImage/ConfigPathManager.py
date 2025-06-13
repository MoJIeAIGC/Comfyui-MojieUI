import os
import logging
from pathlib import Path
from common.ConfigUtils import ConfigUtils

logger = logging.getLogger(__name__)

class ConfigPathManager:
    """
    配置和路径管理器
    用于管理工作流文件路径和配置路径，确保工作流文件可以被正确找到
    """
    
    @staticmethod
    def get_project_root():
        """获取项目根目录"""
        # 尝试从环境变量获取项目根目录
        env_root = os.environ.get('PROJECT_ROOT')
        if env_root and os.path.isdir(env_root):
            logger.info(f"从环境变量获取项目根目录: {env_root}")
            return env_root
        
        # 尝试多种可能的位置
        possible_roots = [
            os.getcwd(),  # 当前工作目录
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # 相对于当前文件的上两级目录
        ]
        
        # 检查哪个路径存在 comfyui 目录，或者可以创建 comfyui 目录
        for root in possible_roots:
            comfyui_dir = os.path.join(root, "comfyui")
            if os.path.isdir(comfyui_dir):
                logger.info(f"找到项目根目录: {root}")
                return root
            elif os.access(root, os.W_OK):
                # 如果目录可写，我们可以后续创建 comfyui 目录
                logger.info(f"使用可写目录作为项目根目录: {root}")
                return root
        
        # 如果没有找到，返回当前工作目录
        logger.warning(f"未找到合适的项目根目录，使用当前工作目录: {os.getcwd()}")
        return os.getcwd()
    
    @staticmethod
    def get_comfyui_dir():
        """获取comfyui目录"""
        # 尝试从环境变量获取comfyui目录路径
        env_comfyui = os.environ.get('COMFYUI_DIR')
        if env_comfyui:
            if os.path.exists(env_comfyui):
                logger.info(f"从环境变量获取comfyui目录: {env_comfyui}")
                return env_comfyui
            elif os.access(os.path.dirname(env_comfyui), os.W_OK):
                # 如果父目录可写，则创建目录
                os.makedirs(env_comfyui, exist_ok=True)
                logger.info(f"创建环境变量指定的comfyui目录: {env_comfyui}")
                return env_comfyui
        
        # 使用项目根目录
        root = ConfigPathManager.get_project_root()
        comfyui_dir = os.path.join(root, "comfyui")
        
        # 如果目录不存在，创建它
        if not os.path.exists(comfyui_dir):
            try:
                logger.info(f"创建comfyui目录: {comfyui_dir}")
                os.makedirs(comfyui_dir, exist_ok=True)
            except Exception as e:
                logger.error(f"创建comfyui目录失败: {str(e)}")
                # 如果创建失败，尝试使用系统临时目录
                import tempfile
                comfyui_dir = os.path.join(tempfile.gettempdir(), "comfyui")
                logger.info(f"尝试使用临时目录: {comfyui_dir}")
                os.makedirs(comfyui_dir, exist_ok=True)
        
        logger.info(f"使用comfyui目录: {comfyui_dir}")
        return comfyui_dir
    
    @staticmethod
    def get_workflow_file_path(workflow_key: str):
        """
        获取工作流文件的正确路径
        :param workflow_key: 配置项的键名，如 'comfyuiTextImage'
        :return: 工作流文件的完整路径
        """
        try:
            import os
            
            # 1. 优先从环境变量获取工作流文件路径
            env_var_name = f"WORKFLOW_{workflow_key.upper()}"
            env_path = os.environ.get(env_var_name)
            if env_path and os.path.exists(env_path):
                logger.info(f"从环境变量 {env_var_name} 获取工作流文件路径: {env_path}")
                return env_path
            
            # 2. 从配置获取相对路径
            relative_path = ConfigUtils.get_path(workflow_key, "workflow_file")
            logger.info(f"从配置获取的工作流文件路径: {relative_path}")
            
            # 标准化路径分隔符，确保跨平台兼容
            if relative_path:
                relative_path = os.path.normpath(relative_path)
            
            # 3. 尝试解析路径
            # 3.1 如果是绝对路径，直接返回
            if os.path.isabs(relative_path) and os.path.exists(relative_path):
                logger.info(f"使用绝对路径: {relative_path}")
                return relative_path
            
            # 3.2 尝试解析为相对于comfyui目录的路径
            filename = os.path.basename(relative_path)
            comfyui_path = os.path.join(ConfigPathManager.get_comfyui_dir(), filename)
            if os.path.exists(comfyui_path):
                logger.info(f"使用comfyui目录下的文件: {comfyui_path}")
                return comfyui_path
            
            # 3.3 尝试解析为相对于项目根目录的路径
            root_path = os.path.join(ConfigPathManager.get_project_root(), relative_path)
            if os.path.exists(root_path):
                logger.info(f"使用项目根目录下的文件: {root_path}")
                return root_path
            
            # 3.4 返回预期的comfyui文件路径（即使它可能不存在，后续可能会创建）
            logger.warning(f"未找到工作流文件，返回预期路径: {comfyui_path}")
            return comfyui_path
            
        except Exception as e:
            logger.error(f"获取工作流文件路径失败: {str(e)}")
            # 返回基于当前目录的路径
            return os.path.join(ConfigPathManager.get_comfyui_dir(), f"{workflow_key}_workflow.json")
    
    @staticmethod
    def ensure_workflow_file(workflow_key: str, default_content=None):
        """
        确保工作流文件存在，如果不存在则报错
        :param workflow_key: 配置项的键名
        :param default_content: 忽略此参数，保留是为了兼容旧代码
        :return: 工作流文件路径
        :raises: FileNotFoundError 当工作流文件不存在时
        """
        import os
        
        path = ConfigPathManager.get_workflow_file_path(workflow_key)
        
        # 检查文件是否存在，不存在则抛出错误
        if not os.path.exists(path):
            error_msg = f"工作流文件不存在: {path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        logger.info(f"工作流文件已验证存在: {path}")
        return path 