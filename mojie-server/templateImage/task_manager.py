"""
任务类型管理模块 - 提供任务类型的注册、获取和处理功能
"""
import logging
import importlib
import inspect
from typing import Dict, List, Optional, Any, Callable
from django.core.cache import cache

from templateImage.models import TaskType, ComfyUITask

logger = logging.getLogger(__name__)

# 缓存键
TASK_TYPES_CACHE_KEY = "comfyui_task_types"
TASK_HANDLERS_CACHE_KEY = "comfyui_task_handlers"

# 任务处理器字典
_task_handlers = {}


def initialize_task_managers():
    """
    初始化任务管理器，加载所有任务类型
    """
    load_task_types()
    logger.info("任务类型管理器已初始化")


def load_task_types():
    """
    从数据库加载所有任务类型到缓存
    """
    try:
        # 获取所有活跃的任务类型
        task_types = TaskType.objects.filter(is_active=True).order_by('priority_order')
        
        # 构建任务类型字典
        task_types_dict = {task_type.name: {
            'id': task_type.id,
            'name': task_type.name,
            'display_name': task_type.display_name,
            'description': task_type.description,
            'handler_name': task_type.handler_name,
            'config': task_type.config or {},
        } for task_type in task_types}
        
        # 存入缓存
        cache.set(TASK_TYPES_CACHE_KEY, task_types_dict, timeout=None)  # 无超时
        logger.info(f"已加载 {len(task_types_dict)} 个任务类型到缓存")
        
        return task_types_dict
    except Exception as e:
        logger.error(f"加载任务类型失败: {str(e)}")
        return {}


def get_task_types() -> Dict[str, Dict]:
    """
    获取所有任务类型
    
    返回格式:
    {
        'task_type_name': {
            'id': 1,
            'name': 'task_type_name',
            'display_name': '显示名称',
            'description': '描述',
            'handler_name': '处理器名称',
            'config': {}
        }
    }
    """
    # 尝试从缓存获取
    task_types = cache.get(TASK_TYPES_CACHE_KEY)
    
    # 如果缓存中没有，从数据库加载
    if task_types is None:
        task_types = load_task_types()
    
    return task_types


def get_task_type(task_type_name: str) -> Optional[Dict]:
    """
    根据任务类型名称获取任务类型信息
    """
    task_types = get_task_types()
    return task_types.get(task_type_name)


def register_task_handler(task_type_name: str, handler_func: Callable):
    """
    注册任务处理器函数
    
    :param task_type_name: 任务类型名称
    :param handler_func: 处理器函数
    """
    _task_handlers[task_type_name] = handler_func
    logger.info(f"已注册任务处理器: {task_type_name}")


def get_task_handler(task_type_name: str) -> Optional[Callable]:
    """
    获取任务处理器函数
    
    :param task_type_name: 任务类型名称
    :return: 处理器函数或None
    """
    # 1. 尝试从已注册的处理器中获取
    if task_type_name in _task_handlers:
        return _task_handlers[task_type_name]
    
    # 2. 尝试从任务类型配置中获取
    task_type = get_task_type(task_type_name)
    if not task_type:
        logger.error(f"未找到任务类型: {task_type_name}")
        return None
    
    handler_name = task_type.get('handler_name')
    if not handler_name:
        logger.error(f"任务类型 {task_type_name} 未配置处理器")
        return None
    
    # 3. 处理特殊情况: 'generic' 表示使用通用处理器
    if handler_name == 'generic':
        # 使用通用处理方法
        from templateImage.task_utils import TaskUtils
        
        def generic_handler(task_id, task_data):
            """通用任务处理器"""
            logger.info(f"使用通用处理器处理任务 [{task_type_name}]: {task_id}")
            from templateImage.task_utils import queue_service
            consumer = queue_service.get_consumer()
            if not consumer:
                raise Exception("图像处理服务未初始化")
            import threading
            stop_event = threading.Event()
            return consumer.process_task(
                {'task_id': task_id, 'type': task_type_name, 'data': task_data},
                stop_event
            )
        
        # 注册通用处理器
        register_task_handler(task_type_name, generic_handler)
        return generic_handler
    
    # 4. 处理特定任务处理器
    try:
        # 尝试从TaskUtils中获取处理器
        from templateImage.task_utils import TaskUtils
        handler = getattr(TaskUtils, handler_name, None)
        if handler:
            # 注册到处理器字典
            register_task_handler(task_type_name, handler)
            return handler
    except Exception as e:
        logger.error(f"获取任务处理器失败 [{task_type_name}]: {str(e)}")
    
    return None


def process_task(task_id: str, task_type: str, task_data: Dict) -> Dict:
    """
    处理任务的统一入口
    
    :param task_id: 任务ID
    :param task_type: 任务类型
    :param task_data: 任务数据
    :return: 处理结果
    """
    try:
        # 1. 检查任务类型是否存在
        task_type_info = get_task_type(task_type)
        if not task_type_info:
            raise ValueError(f"不支持的任务类型: {task_type}")
        
        # 2. 获取任务处理器
        handler = get_task_handler(task_type)
        if not handler:
            raise ValueError(f"未找到任务处理器: {task_type}")
        
        # 3. 执行任务处理
        logger.info(f"开始处理任务 [{task_type}]: {task_id}")
        result = handler(task_id, task_data)
        
        return result
    
    except Exception as e:
        logger.error(f"处理任务失败 [{task_type}]: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e)
        }


def create_task_type(name: str, display_name: str, description: str = None, 
                    handler_name: str = 'generic', config: Dict = None,
                    is_active: bool = True, priority_order: int = 0) -> TaskType:
    """
    创建新的任务类型
    
    :param name: 任务类型名称代码
    :param display_name: 显示名称
    :param description: 描述
    :param handler_name: 处理器名称
    :param config: 配置信息
    :param is_active: 是否激活
    :param priority_order: 排序优先级
    :return: 创建的任务类型对象
    """
    try:
        # 创建新任务类型
        task_type = TaskType.objects.create(
            name=name,
            display_name=display_name,
            description=description,
            handler_name=handler_name,
            config=config or {},
            is_active=is_active,
            priority_order=priority_order
        )
        
        # 刷新缓存
        load_task_types()
        
        return task_type
    except Exception as e:
        logger.error(f"创建任务类型失败: {str(e)}")
        raise


def update_task_type(name: str, **kwargs) -> Optional[TaskType]:
    """
    更新任务类型
    
    :param name: 任务类型名称
    :param kwargs: 要更新的字段
    :return: 更新后的任务类型对象
    """
    try:
        # 获取任务类型
        task_type = TaskType.objects.filter(name=name).first()
        if not task_type:
            logger.error(f"未找到任务类型: {name}")
            return None
        
        # 更新字段
        for key, value in kwargs.items():
            if hasattr(task_type, key):
                setattr(task_type, key, value)
        
        # 保存
        task_type.save()
        
        # 刷新缓存
        load_task_types()
        
        return task_type
    except Exception as e:
        logger.error(f"更新任务类型失败 [{name}]: {str(e)}")
        return None


def delete_task_type(name: str) -> bool:
    """
    删除任务类型
    
    :param name: 任务类型名称
    :return: 是否成功删除
    """
    try:
        # 检查是否有依赖此任务类型的任务
        if ComfyUITask.objects.filter(task_type=name).exists():
            logger.warning(f"任务类型 {name} 有关联任务，无法删除")
            return False
        
        # 获取任务类型
        task_type = TaskType.objects.filter(name=name).first()
        if not task_type:
            logger.error(f"未找到任务类型: {name}")
            return False
        
        # 删除
        task_type.delete()
        
        # 刷新缓存
        load_task_types()
        
        return True
    except Exception as e:
        logger.error(f"删除任务类型失败 [{name}]: {str(e)}")
        return False


def get_active_task_types_choices() -> List[tuple]:
    """
    获取所有活跃的任务类型选项，用于表单
    
    :return: [(value, label), ...]
    """
    task_types = get_task_types()
    return [(name, data['display_name']) for name, data in task_types.items()] 