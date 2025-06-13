import os
import json
import logging
import shutil
from pathlib import Path
from .ConfigPathManager import ConfigPathManager

logger = logging.getLogger(__name__)

# 默认的工作流内容
DEFAULT_WORKFLOW = {
    "last_node_id": 100,
    "last_link_id": 100,
    "nodes": {},
    "links": {},
    "groups": [],
    "config": {},
    "extra": {},
    "version": 0.4
}

def create_empty_workflow(path):
    """创建一个空的工作流文件"""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_WORKFLOW, f, indent=2)
        logger.info(f"成功创建空工作流文件: {path}")
        return path
    except Exception as e:
        logger.error(f"创建空工作流文件失败 {path}: {str(e)}")
        # 最后的备选方案：尝试在临时目录创建
        import tempfile
        import uuid
        temp_path = os.path.join(tempfile.gettempdir(), f"workflow_{uuid.uuid4()}.json")
        logger.info(f"尝试在临时目录创建工作流文件: {temp_path}")
        
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_WORKFLOW, f, indent=2)
            return temp_path
        except Exception as e2:
            logger.error(f"在临时目录创建工作流文件也失败了: {str(e2)}")
            raise RuntimeError(f"无法创建工作流文件: {str(e)} | {str(e2)}")

def create_initial_workflow_file(workflow_key, source_path=None):
    """
    在初始化阶段创建工作流文件，如果不存在的话
    :param workflow_key: 工作流配置键名
    :param source_path: 源工作流文件路径
    :return: 创建的工作流文件路径
    """
    try:
        target_path = ConfigPathManager.get_workflow_file_path(workflow_key)
        
        # 如果目标文件已存在，不覆盖
        if os.path.exists(target_path):
            logger.info(f"工作流文件已存在: {target_path}")
            return target_path
        
        # 确保目标目录存在
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        # 如果提供了源文件并且源文件存在，则复制
        if source_path and os.path.exists(source_path):
            try:
                shutil.copy2(source_path, target_path)
                logger.info(f"从 {source_path} 复制工作流文件到 {target_path}")
                return target_path
            except Exception as e:
                logger.error(f"复制工作流文件失败: {str(e)}")
                # 如果复制失败，回退到创建空文件
                logger.info(f"尝试创建空的默认工作流文件: {target_path}")
        
        # 创建空的默认工作流
        logger.info(f"创建初始化工作流文件: {target_path}")
        return create_empty_workflow(target_path)
    except Exception as e:
        logger.error(f"处理初始化工作流文件 {workflow_key} 失败: {str(e)}")
        # 如果所有尝试都失败，记录错误但不使用临时文件
        raise RuntimeError(f"无法创建初始化工作流文件 {workflow_key}: {str(e)}")

def copy_sample_workflow(target_key, source_path=None):
    """
    复制样例工作流到目标位置，初始化时使用
    :param target_key: 目标工作流配置键名
    :param source_path: 源工作流文件路径，如果为None则创建空工作流
    """
    return create_initial_workflow_file(target_key, source_path)

def ensure_comfyui_dir():
    """确保comfyui目录存在"""
    comfyui_dir = ConfigPathManager.get_comfyui_dir()
    if not os.path.exists(comfyui_dir):
        os.makedirs(comfyui_dir, exist_ok=True)
        logger.info(f"创建comfyui目录: {comfyui_dir}")
    return comfyui_dir

def init_workflow_files():
    """初始化所有工作流文件"""
    # 确保comfyui目录存在
    try:
        comfyui_dir = ensure_comfyui_dir()
        logger.info(f"工作流文件目录: {comfyui_dir}")
        
        # 创建所有需要的工作流文件
        workflow_keys = [
            "comfyuiTextImage",
            "comfyuiTextToGenerateImages",
            "comfyuiImageImages",
            "comfyuiProductTextImage",
            "comfyuiWhiteImage",
            "comfyuiImagesImageClue",
            "comfyuiImagesClueImage",
            "comfyuiProductImageInTemplateReplace",
            "comfyuiFineDetailWorkflow",
            "comfyuiWidePictureWorkflow",
            "comfyuiInternalSupplementationWorkflow",
            "comfyuiInternalSupplementationAndRemovalWorkflow",
            "comfyuiCompleteRedrawingAndRefinementOfTheEntireImageWorkflow"
        ]
        
        # 尝试从环境变量获取额外的工作流键
        env_keys = os.environ.get('ADDITIONAL_WORKFLOW_KEYS')
        if env_keys:
            extra_keys = [k.strip() for k in env_keys.split(',')]
            workflow_keys.extend(extra_keys)
            logger.info(f"从环境变量添加工作流键: {extra_keys}")
        
        # 统计初始化结果
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        # 确保每个工作流文件存在
        for key in workflow_keys:
            try:
                # 检查文件是否已存在
                try:
                    path = ConfigPathManager.get_workflow_file_path(key)
                    if os.path.exists(path):
                        logger.info(f"工作流 {key} 已存在: {path}")
                        skipped_count += 1
                        continue
                except Exception:
                    # 如果获取路径失败，继续尝试创建
                    pass
                
                # 创建工作流文件
                workflow_path = create_initial_workflow_file(key)
                logger.info(f"工作流 {key} 已初始化: {workflow_path}")
                success_count += 1
            except Exception as e:
                logger.error(f"初始化工作流 {key} 失败: {str(e)}")
                failed_count += 1
        
        logger.info(f"工作流文件初始化完成: 成功 {success_count}, 跳过 {skipped_count}, 失败 {failed_count}")
        
        if failed_count > 0:
            logger.warning("有些工作流文件初始化失败，应用可能无法正常工作")
        
    except Exception as e:
        logger.error(f"初始化工作流文件失败: {str(e)}", exc_info=True)
        raise

# 在模块导入时自动初始化
if __name__ != "__main__":
    try:
        init_workflow_files()
    except Exception as e:
        logger.error(f"初始化工作流文件失败: {str(e)}") 