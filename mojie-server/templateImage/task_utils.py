import logging
import time
import uuid
from typing import Dict, List, Optional
from django.utils import timezone
from django.core.cache import cache
from concurrent.futures import ThreadPoolExecutor
import threading
import urllib.request
import json
import os
from django.db import transaction
from common.ErrorCode import ErrorCode
from common.volcengine_tos_utils import VolcengineTOSUtils
from exception.business_exception import BusinessException
from order.models import UserVIP
from templateImage.queue_service import QueueService
from templateImage.models import templateImage, ComfyUITask, ImageUploadRecord, ConversationList
from django.conf import settings
from datetime import timedelta

from templateImage.workflowUtils import ComfyUIHelper
from user.models import SysUser

# 导入单例模块中的queue_service实例
from templateImage.queue_service_singleton import queue_service

# 获取logger
logger = logging.getLogger(__name__)


class TaskUtils:
    # 常量定义
    PRIORITY_LOW = "low"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_HIGH = "high"

    # 优先级映射（用于排序，数字越小优先级越高）
    PRIORITY_MAP = {
        PRIORITY_HIGH: 0,
        PRIORITY_MEDIUM: 1,
        PRIORITY_LOW: 2
    }

    @staticmethod
    def create_async_task(task_type: str, task_data: Dict, user: Optional[SysUser] = None,
                          priority: str = "medium") -> Dict:
        """
        创建异步任务
        :param task_type: 任务类型
        :param task_data: 任务数据
        :param user: 用户对象
        :param priority: 任务优先级 (low, medium, high)
        :return: 任务信息
        """
        try:
            # 0. 如果有用户，先对该用户的所有处理中任务进行快速检查
            if user:
                # 检查最近30分钟的处理中任务，优先处理这些可能卡住的任务
                processing_tasks = ComfyUITask.objects.filter(
                    user=user,
                    status__in=['processing', 'processing_completed'],
                    updated_at__lt=timezone.now() - timedelta(minutes=1)  # 检查至少1分钟未更新的任务
                ).order_by('-updated_at')[:5]  # 最多处理5个最近的任务

                if processing_tasks.exists():
                    logger.info(f"用户 {user.id} 有 {processing_tasks.count()} 个可能卡住的任务，进行快速检查")
                    for task in processing_tasks:
                        try:
                            # 检查任务是否有结果
                            task_status = TaskUtils.get_task_status(task.task_id)
                            has_results = False

                            # 检查Redis数据
                            if task_status:
                                if 'image_urls' in task_status and task_status['image_urls']:
                                    has_results = True
                                    logger.info(f"任务 {task.task_id} 在Redis中有结果但状态为 {task_status.get('status')}")
                                elif 'output_data' in task_status and task_status['output_data']:
                                    output_data = task_status['output_data']
                                    if isinstance(output_data, dict) and 'image_urls' in output_data and output_data['image_urls']:
                                        has_results = True
                                        logger.info(f"任务 {task.task_id} 在Redis的output_data中有结果但状态为 {task_status.get('status')}")

                            # 检查MySQL数据
                            if not has_results and task.output_data:
                                if isinstance(task.output_data, dict) and 'image_urls' in task.output_data and task.output_data['image_urls']:
                                    has_results = True
                                    logger.info(f"任务 {task.task_id} 在MySQL中有结果但状态为 {task.status}")

                            # 如果任务有结果但状态不是completed，更新状态
                            if has_results:
                                logger.info(f"发现用户 {user.id} 的任务 {task.task_id} 有结果但状态为 {task.status}，立即修复")

                                # 准备output_data
                                output_data = None
                                if task.output_data and isinstance(task.output_data, dict) and 'image_urls' in task.output_data:
                                    output_data = task.output_data

                                # 更新任务状态
                                TaskUtils._update_task_status(
                                    task.task_id,
                                    'completed',
                                    force_redis_update=True,
                                    output_data=output_data,
                                    completed_at=timezone.now()
                                )
                            # 如果任务处理时间超过10分钟还没有结果，标记为失败
                            elif task.started_at and (timezone.now() - task.started_at).total_seconds() > 600:
                                logger.warning(f"任务 {task.task_id} 处理超过10分钟无结果，标记为失败")
                                TaskUtils._update_task_status(
                                    task.task_id,
                                    'failed',
                                    force_redis_update=True,
                                    error_message='任务处理超时，系统自动取消',
                                    completed_at=timezone.now()
                                )
                        except Exception as e:
                            logger.error(f"检查任务 {task.task_id} 时出错: {str(e)}")

            # 1. 检查用户并发限制（如果有用户）
            if user and not TaskUtils.check_user_concurrent_limit(user):
                raise BusinessException(
                    error_code=ErrorCode.SYSTEM_ERROR,
                    data=None,
                    errors="您在队列中的任务已满！"
                )

            # 2. 验证优先级
            if priority not in [TaskUtils.PRIORITY_LOW, TaskUtils.PRIORITY_MEDIUM, TaskUtils.PRIORITY_HIGH]:
                priority = TaskUtils.PRIORITY_MEDIUM

            # 3. 生成任务ID
            task_id = str(uuid.uuid4())

            # 获取自动保存设置
            auto_save_to_cloud = False

            if user:
                # 从缓存中获取用户的自动保存设置
                user_cache_key = f"comfyui_auto_save_default_{user.id}"
                user_auto_save = cache.get(user_cache_key, None)

                if user_auto_save is not None:
                    # 如果用户有设置，使用用户设置
                    auto_save_to_cloud = user_auto_save
                else:
                    # 否则使用全局设置
                    global_auto_save = cache.get("comfyui_auto_save_default_global", False)
                    auto_save_to_cloud = global_auto_save

            # 4. 创建任务记录
            task = ComfyUITask.objects.create(
                task_id=task_id,
                task_type=task_type,
                input_data=task_data,
                status='pending',
                user=user,
                priority=priority,
                auto_save_to_cloud=auto_save_to_cloud  # 应用自动保存设置
            )

            # 5. 保存任务数据
            task_data_obj = ComfyUITask.objects.filter(task_id=task_id).first()
            if task_data_obj:
                task_data_obj.input_data = task_data
                task_data_obj.save()

            # 6. 计算队列位置
            queue_position = TaskUtils._get_queue_position(task_id, priority)

            # 7. 将任务添加到队列
            queue_service.add_task(
                task_id=task_id,
                task_type=task_type,
                task_data=task_data
            )

            # 8. 启动异步处理
            threading.Thread(
                target=TaskUtils._process_task_async,
                args=(task_id, task_type, task_data),
                daemon=True
            ).start()

            # 9. 返回任务信息
            return {
                'task_id': task_id,
                'status': 'pending',
                'status_url': f"/api/image/tasks/{task_id}/status",
                'cancel_url': f"/api/image/tasks/{task_id}/cancel",
                'queue_position': queue_position,
                'priority': priority
            }
        except BusinessException as be:
            # 直接抛出业务异常
            raise be
        except Exception as e:
            logger.error(f"创建异步任务失败: {str(e)}")
            raise BusinessException(
                error_code=ErrorCode.SYSTEM_ERROR,
                data=None,
                errors=str(e)
            )

    @staticmethod
    def _get_queue_position(task_id: str, priority: str) -> int:
        """
        获取任务在队列中的位置
        :param task_id: 任务ID
        :param priority: 任务优先级
        :return: 队列位置 (从1开始)
        """
        try:
            # 获取所有待处理任务
            pending_tasks = ComfyUITask.objects.filter(status='pending')

            # 按优先级和创建时间排序
            sorted_tasks = sorted(
                pending_tasks,
                key=lambda t: (TaskUtils.PRIORITY_MAP.get(t.priority, 999), t.created_at)
            )

            # 查找当前任务位置
            for i, task in enumerate(sorted_tasks):
                if task.task_id == task_id:
                    return i + 1  # 返回1-based索引

            # 如果找不到任务，返回队列末尾
            return len(sorted_tasks)
        except Exception as e:
            logger.error(f"计算队列位置失败: {str(e)}")
            return 0  # 出错时返回0

    @staticmethod
    def _wait_for_higher_priority_tasks(task_id: str, priority: str):
        """
        等待当前正在处理的任务完成，并确保高优先级任务在队列前面
        :param task_id: 当前任务ID
        :param priority: 当前任务优先级
        """
        try:
            # 获取当前任务优先级值
            current_priority_value = TaskUtils.PRIORITY_MAP.get(priority, 999)
            logger.info(f"任务 {task_id} 正在检查其他任务状态，当前任务优先级: {priority}({current_priority_value})")

            # 循环检查是否有任务正在处理中
            wait_count = 0
            max_wait_attempts = 3600  # 最多等待30分钟 (1800次, 每次1秒)
            while wait_count < max_wait_attempts:
                # 获取所有处理中的任务，不包括当前任务
                processing_tasks = ComfyUITask.objects.filter(status='processing').exclude(task_id=task_id)

                # 如果有任务正在处理，检查它们是否真的在处理中
                if processing_tasks.exists():
                    processing_task_ids = [t.task_id for t in processing_tasks]
                    if wait_count % 10 == 0:  # 每10秒记录一次日志
                        logger.info(f"任务 {task_id} 等待中: 有 {processing_tasks.count()} 个任务正在处理中: {processing_task_ids}")

                    # 检查每个处理中的任务是否真的在处理中
                    for task in processing_tasks:
                        try:
                            # 获取任务的最新状态
                            task_status = TaskUtils.get_task_status(task.task_id)
                            
                            # 检查任务是否有结果
                            has_results = False
                            if task_status:
                                if 'image_urls' in task_status and task_status['image_urls']:
                                    has_results = True
                                elif 'output_data' in task_status and task_status['output_data']:
                                    output_data = task_status['output_data']
                                    if isinstance(output_data, dict) and 'image_urls' in output_data and output_data['image_urls']:
                                        has_results = True

                            # 如果任务有结果但状态不是completed，更新状态
                            if has_results:
                                logger.info(f"发现任务 {task.task_id} 有结果但状态为 {task.status}，立即修复")
                                TaskUtils._update_task_status(
                                    task.task_id,
                                    'completed',
                                    force_redis_update=True,
                                    output_data=task_status.get('output_data'),
                                    completed_at=timezone.now()
                                )
                                continue

                            # 如果任务处理时间超过10分钟还没有结果，标记为失败
                            if task.started_at and (timezone.now() - task.started_at).total_seconds() > 600:
                                logger.warning(f"任务 {task.task_id} 处理超过10分钟无结果，标记为失败")
                                TaskUtils._update_task_status(
                                    task.task_id,
                                    'failed',
                                    force_redis_update=True,
                                    error_message='任务处理超时，系统自动取消',
                                    completed_at=timezone.now()
                                )
                                continue

                        except Exception as e:
                            logger.error(f"检查任务 {task.task_id} 时出错: {str(e)}")

                    # 重新获取处理中的任务数量
                    processing_tasks = ComfyUITask.objects.filter(status='processing').exclude(task_id=task_id)
                    if processing_tasks.exists():
                        time.sleep(1)
                        wait_count += 1
                        continue

                # 如果没有正在处理的任务，检查队列中的任务优先级
                pending_tasks = ComfyUITask.objects.filter(status='pending').exclude(task_id=task_id).order_by(
                    'priority', 'created_at'
                )

                # 检查是否有更高优先级的任务在等待
                has_higher_priority = False
                for task in pending_tasks:
                    task_priority_value = TaskUtils.PRIORITY_MAP.get(task.priority, 999)
                    if task_priority_value < current_priority_value:
                        has_higher_priority = True
                        if wait_count % 10 == 0:  # 每10秒记录一次日志
                            logger.info(f"任务 {task_id} 等待中: 有优先级更高的任务 {task.task_id} (优先级: {task.priority}({task_priority_value}))")
                        break

                # 如果有更高优先级的任务，继续等待
                if has_higher_priority:
                    time.sleep(1)
                    wait_count += 1
                    continue

                # 如果没有正在处理的任务，也没有更高优先级的任务，可以开始处理当前任务
                logger.info(f"任务 {task_id} 检查完成: 没有正在处理的任务或更高优先级的任务，开始处理")
                break

            # 如果达到最大等待次数，记录警告但仍继续执行
            if wait_count >= max_wait_attempts:
                logger.warning(f"任务 {task_id} 等待超时，强制开始处理")

        except Exception as e:
            logger.error(f"等待其他任务完成时出错: {str(e)}")

    @staticmethod
    def _process_task_async(task_id: str, task_type: str, task_data: Dict):
        """
        异步处理任务
        :param task_id: 任务ID
        :param task_type: 任务类型
        :param task_data: 任务数据
        """
        try:
            # 1. 获取任务对象 - 添加重试机制，处理数据库同步延迟问题
            max_retries = 3
            retry_wait = 0.5  # 初始等待时间（秒）
            task = None
            
            for retry in range(max_retries):
                task = ComfyUITask.objects.filter(task_id=task_id).first()
                if task:
                    break
                
                if retry < max_retries - 1:
                    logger.warning(f"任务 {task_id} 在数据库中不存在，等待 {retry_wait} 秒后重试 ({retry+1}/{max_retries})")
                    time.sleep(retry_wait)
                    retry_wait *= 2  # 指数退避
            
            if not task:
                logger.error(f"经过 {max_retries} 次重试后，任务 {task_id} 在数据库中仍不存在")
                raise Exception(f"任务 {task_id} 不存在")

            # 确保状态为pending
            if task.status != 'pending':
                logger.warning(f"任务 {task_id} 状态为 {task.status}，而不是预期的pending状态，确保状态一致")
                task.status = 'pending'
                task.save(update_fields=['status'])

            # 更新任务状态为等待中
            TaskUtils._update_task_status(
                task_id,
                'pending',
                queue_position=TaskUtils._get_queue_position(task_id, task.priority)
            )
            logger.info(f"任务 {task_id} 已更新状态为等待中，正在等待其他任务完成")

            # 2. 等待其他任务完成
            TaskUtils._wait_for_higher_priority_tasks(task_id, task.priority)

            # 3. 再次检查任务状态，确保任务仍然存在且未被取消
            task = ComfyUITask.objects.filter(task_id=task_id).first()
            if not task:
                logger.info(f"任务 {task_id} 不存在")
                return

            # 检查任务是否已被取消
            cache_key = f"task:{task_id}:cancelled"
            if cache.get(cache_key) == "true":
                logger.info(f"任务 {task_id} 已被取消，停止处理")
                return

            if task.status != 'pending':
                logger.info(f"任务 {task_id} 状态已改变为 {task.status}，停止处理")
                return

            # 在更新状态为处理中之前，添加一个额外的检查点
            def ensure_single_processing_task():
                # 获取所有处理中的任务
                processing_tasks = ComfyUITask.objects.filter(status='processing')
                
                # 如果当前任务已经在处理中，直接返回
                if task.status == 'processing':
                    return True
                    
                # 如果有其他任务正在处理
                if processing_tasks.exists():
                    for other_task in processing_tasks:
                        if other_task.task_id != task_id:
                            try:
                                # 获取任务的最新状态
                                task_status = TaskUtils.get_task_status(other_task.task_id)
                                
                                # 检查任务是否真的在处理中
                                if task_status and task_status.get('status') == 'processing':
                                    # 检查任务是否有结果
                                    has_results = False
                                    if 'image_urls' in task_status and task_status['image_urls']:
                                        has_results = True
                                    elif 'output_data' in task_status and task_status['output_data']:
                                        output_data = task_status['output_data']
                                        if isinstance(output_data, dict) and 'image_urls' in output_data and output_data['image_urls']:
                                            has_results = True
                                
                                    # 如果任务有结果，更新状态为completed
                                    if has_results:
                                        logger.info(f"发现任务 {other_task.task_id} 有结果但状态为processing，立即修复")
                                        TaskUtils._update_task_status(
                                            other_task.task_id,
                                            'completed',
                                            force_redis_update=True,
                                            output_data=task_status.get('output_data'),
                                            completed_at=timezone.now()
                                        )
                                        continue
                                
                                    # 如果任务处理时间超过10分钟，标记为失败
                                    if other_task.started_at and (timezone.now() - other_task.started_at).total_seconds() > 600:
                                        logger.warning(f"任务 {other_task.task_id} 处理超过10分钟，标记为失败")
                                        TaskUtils._update_task_status(
                                            other_task.task_id,
                                            'failed',
                                            force_redis_update=True,
                                            error_message='任务处理超时，系统自动取消',
                                            completed_at=timezone.now()
                                        )
                                        continue
                                
                                    # 如果任务确实在处理中，返回False
                                    return False
                            except Exception as e:
                                logger.error(f"检查任务 {other_task.task_id} 时出错: {str(e)}")
                                continue
                return True

            # 在更新状态为处理中之前，确保没有其他任务在处理中
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                if ensure_single_processing_task():
                    break
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"等待其他任务完成，重试 {retry_count}/{max_retries}")
                    time.sleep(2)  # 等待2秒后重试
            
            if retry_count >= max_retries:
                logger.warning(f"任务 {task_id} 等待其他任务完成超时，强制开始处理")

            # 再次检查任务是否已被取消
            if cache.get(cache_key) == "true":
                logger.info(f"任务 {task_id} 已被取消，停止处理")
                return

            # 4. 更新任务状态为处理中 
            task.status = 'processing'
            task.started_at = timezone.now()
            task.save()

            TaskUtils._update_task_status(
                task_id,
                'processing',
                started_at=timezone.now()
            )
            logger.info(f"任务 {task_id} 已更新状态为处理中")

            # 5. 执行任务处理
            try:
                # 获取消费者并处理任务
                consumer = queue_service.get_consumer()
                if not consumer:
                    raise Exception("图像处理服务未初始化")

                # 创建停止事件
                stop_event = threading.Event()

                # 添加停止事件到任务数据中
                task_data['stop_event'] = stop_event

                # 添加优先级到任务数据中
                task_data['priority'] = task.priority

                # 执行任务
                result = consumer.process_task(
                    {'task_id': task_id, 'data': task_data},
                    stop_event
                )

                # 检查任务是否已被取消
                if cache.get(cache_key) == "true":
                    logger.info(f"任务 {task_id} 已被取消，停止处理")
                    return

                # 处理结果
                if result.get('status') == 'success':
                    logger.info(f"任务 {task_id} 处理成功，等待保存结果")
                    # 注意：不在这里更新状态为completed
                    # 状态将在consumer的_save_task_result完成后更新为completed
                elif result.get('status') == 'failed':
                    # 检查任务是否已被取消
                    if cache.get(cache_key) == "true":
                        logger.info(f"任务 {task_id} 已被取消，不标记为失败")
                        return

                    logger.error(f"任务 {task_id} 处理失败: {result.get('error')}")
                    task.status = 'failed'
                    task.error_message = result.get('error', '未知错误')
                    task.completed_at = timezone.now()
                    task.save()

                    TaskUtils._update_task_status(
                        task_id,
                        'failed',
                        error_message=result.get('error', '未知错误'),
                        completed_at=timezone.now()
                    )
                elif result.get('status') == 'cancelled':
                    logger.info(f"任务 {task_id} 已被取消")
                    task.status = 'cancelled'
                    task.error_message = "任务已被用户取消"
                    task.completed_at = timezone.now()
                    task.save()

                    TaskUtils._update_task_status(
                        task_id,
                        'cancelled',
                        error_message="任务已被用户取消",
                        completed_at=timezone.now()
                    )
                else:
                    logger.warning(f"任务 {task_id} 返回未知状态: {result.get('status')}")

            except Exception as e:
                # 检查任务是否已被取消
                if cache.get(cache_key) == "true":
                    logger.info(f"任务 {task_id} 已被取消，不标记为失败")
                    return

                # 更新任务状态为失败
                task.status = 'failed'
                task.error_message = str(e)
                task.completed_at = timezone.now()
                task.save()

                TaskUtils._update_task_status(
                    task_id,
                    'failed',
                    error_message=str(e),
                    completed_at=timezone.now()
                )
                raise

        except Exception as e:
            # 检查任务是否已被取消
            cache_key = f"task:{task_id}:cancelled"
            if cache.get(cache_key) == "true":
                logger.info(f"任务 {task_id} 已被取消，不标记为失败")
                return

            logger.error(f"处理任务 {task_id} 失败: {str(e)}")
            task = ComfyUITask.objects.filter(task_id=task_id).first()
            if task:
                task.status = 'failed'
                task.error_message = str(e)
                task.completed_at = timezone.now()
                task.save()

            TaskUtils._update_task_status(
                task_id,
                'failed',
                error_message=str(e),
                completed_at=timezone.now()
            )
            # 任务失败后，重新计算其他任务的队列位置
            TaskUtils._recalculate_queue_positions()
            raise BusinessException(
                error_code=ErrorCode.SYSTEM_ERROR,
                data=None,
                errors=str(e)
            )

    @staticmethod
    def _recalculate_queue_positions():
        """重新计算所有待处理任务的队列位置，考虑任务等待时间因素"""
        try:
            # 获取所有待处理任务
            pending_tasks = ComfyUITask.objects.filter(status='pending')
            
            if not pending_tasks.exists():
                return

            # 计算等待时间 - 当前时间减去创建时间
            now = timezone.now()
            
            # 找出等待时间最长的任务
            max_waiting_time = 0
            for task in pending_tasks:
                if task.created_at:
                    waiting_time = (now - task.created_at).total_seconds()
                    max_waiting_time = max(max_waiting_time, waiting_time)
            
            # 设置等待时间阈值（10分钟）- 超过这个时间的任务开始获得优先级提升
            waiting_threshold = 10 * 60  # 10分钟，单位为秒
            
            # 计算每个任务的有效优先级
            tasks_with_priority = []
            for task in pending_tasks:
                # 原始优先级值（数字越小优先级越高）
                base_priority = TaskUtils.PRIORITY_MAP.get(task.priority, 999)
                
                # 计算等待时间
                waiting_time = 0
                if task.created_at:
                    waiting_time = (now - task.created_at).total_seconds()
                
                # 计算等待因子 - 任务等待时间超过阈值后，根据等待时间提升优先级
                waiting_factor = 0
                if waiting_time > waiting_threshold:
                    # 计算等待时间与最长等待时间的比例，最大提升到最高优先级
                    if max_waiting_time > waiting_threshold:
                        waiting_factor = min(3, (waiting_time - waiting_threshold) / 
                                           (max_waiting_time - waiting_threshold) * 3)
                    else:
                        waiting_factor = 1  # 至少提供一些优先级提升
                
                # 综合优先级 - 原始优先级减去等待因子（数值越小优先级越高）
                effective_priority = base_priority - waiting_factor
                
                tasks_with_priority.append({
                    'task': task,
                    'base_priority': base_priority,
                    'waiting_time': waiting_time,
                    'waiting_factor': waiting_factor,
                    'effective_priority': effective_priority
                })
            
            # 按有效优先级和创建时间排序
            sorted_tasks = sorted(
                tasks_with_priority,
                key=lambda t: (t['effective_priority'], t['task'].created_at)
            )

            # 记录任务优先级变化并更新队列位置
            for i, task_info in enumerate(sorted_tasks):
                task = task_info['task']
                queue_position = i + 1
                
                # 更新队列位置
                TaskUtils._update_task_queue_position(task.task_id, queue_position)
                
                # 如果有优先级提升，记录日志
                if task_info['waiting_factor'] > 0:
                    waiting_minutes = task_info['waiting_time'] / 60
                    logger.info(f"任务 {task.task_id} 等待时间 {waiting_minutes:.1f} 分钟，"
                                f"原始优先级: {task.priority}({task_info['base_priority']}), "
                                f"等待因子: {task_info['waiting_factor']:.2f}, "
                                f"有效优先级: {task_info['effective_priority']:.2f}, "
                                f"新队列位置: {queue_position}")

            # 设置处理中任务的队列位置为0
            processing_tasks = ComfyUITask.objects.filter(status='processing')
            for task in processing_tasks:
                TaskUtils._update_task_queue_position(task.task_id, 0)

        except Exception as e:
            logger.error(f"重新计算队列位置失败: {str(e)}", exc_info=True)

    @staticmethod
    def _update_task_queue_position(task_id: str, position: int):
        """
        更新任务的队列位置
        :param task_id: 任务ID
        :param position: 队列位置
        """
        try:
            task = ComfyUITask.objects.get(task_id=task_id)
            task.queue_position = position
            task.save()
        except ComfyUITask.DoesNotExist:
            logger.error(f"更新队列位置失败: 任务 {task_id} 不存在")
        except Exception as e:
            logger.error(f"更新队列位置失败: {str(e)}")

    @staticmethod
    def _update_task_status(task_id: str, status: str, force_redis_update=True, **kwargs):
        """
        更新任务状态 - 使用队列服务确保Redis优先且异步更新MySQL
        :param task_id: 任务ID
        :param status: 新状态
        :param force_redis_update: 是否强制更新Redis，默认为True
        :param kwargs: 其他需要更新的字段
        """
        try:
            # 获取当前任务状态
            task = ComfyUITask.objects.filter(task_id=task_id).first()
            if not task:
                logger.error(f"更新任务状态失败: 任务 {task_id} 不存在")
                return

            # 如果任务已经是completed状态，不允许更改为其他状态
            if task.status == 'completed' and status != 'completed':
                logger.warning(f"任务 {task_id} 已完成，不允许更改为 {status} 状态")
                return

            # 调用队列服务的方法来更新状态
            if 'queue_service' in globals() and hasattr(queue_service, '_update_task_status'):
                # 使用全局队列服务实例来更新状态
                queue_service._update_task_status(task_id, status, force_redis_update=force_redis_update, **kwargs)
            else:
                # 如果队列服务不可用，直接更新数据库
                logger.warning(f"队列服务不可用，直接更新数据库状态: {task_id}")
                # 1. 获取任务对象
                task = ComfyUITask.objects.get(task_id=task_id)

                # 2. 更新状态
                task.status = status

                # 处理临时状态'processing_completed'
                if status == 'processing_completed':
                    task.status = 'processing'  # 在数据库中仍然保持processing状态

                # 3. 更新其他字段
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)

                # 4. 保存更新
                task.save()
                logger.info(f"任务 {task_id} 状态已直接更新为: {status}")

            # 重新计算队列位置
            if status in ['completed', 'failed', 'cancelled']:
                TaskUtils._recalculate_queue_positions()

            # 如果任务完成或失败，同步更新相关记录
            if status in ['completed', 'failed', 'cancelled']:
                # 调用sync_record_status同步记录状态
                try:
                    sync_result = TaskUtils.sync_record_status(task_id, force=True)
                    if sync_result['success'] and sync_result['updated_count'] > 0:
                        logger.info(f"_update_task_status: 已同步 {sync_result['updated_count']} 条记录状态为 {status}")
                    elif not sync_result['success']:
                        logger.error(f"_update_task_status: 同步记录状态失败: {sync_result.get('message', '未知错误')}")
                except Exception as e:
                    logger.error(f"_update_task_status: 同步记录状态异常: {str(e)}")

        except ComfyUITask.DoesNotExist:
            logger.error(f"更新任务状态失败: 任务 {task_id} 不存在")
        except Exception as e:
            logger.error(f"更新任务状态失败: {str(e)}")

    @staticmethod
    def get_task_status(task_id: str) -> Dict:
        """
        获取任务状态 - 优先从Redis获取最新数据，补充MySQL数据
        :param task_id: 任务ID
        :return: 任务状态信息
        """
        try:
            # 1. 首先尝试从Redis获取最新任务状态
            redis_status = None
            if 'queue_service' in globals() and hasattr(queue_service, 'get_task_status'):
                redis_status = queue_service.get_task_status(task_id)
                if redis_status:
                    # 添加状态来源标记，用于调试
                    redis_status['from_source'] = 'redis'
                    logger.info(f"从Redis获取到任务 {task_id} 的状态: {redis_status.get('status')}")
                    
                    # 如果Redis中有数据，触发异步MySQL更新
                    if redis_status.get('status') != 'processing_completed':
                        # 异步更新MySQL状态
                        try:
                            task = ComfyUITask.objects.get(task_id=task_id)
                            if task.status != redis_status.get('status'):
                                task.status = redis_status.get('status')
                                if redis_status.get('status') == 'processing':
                                    task.started_at = timezone.now()
                                elif redis_status.get('status') in ['completed', 'failed', 'cancelled']:
                                    task.completed_at = timezone.now()
                                task.save()
                                logger.info(f"已同步Redis状态到MySQL: {task_id} -> {redis_status.get('status')}")
                        except Exception as e:
                            logger.error(f"同步Redis状态到MySQL失败: {str(e)}")
                    
                    # 从MySQL补充缺失的字段，但保留Redis中的新数据
                    try:
                        task = ComfyUITask.objects.get(task_id=task_id)
                        # 补充缺失的字段，但只在Redis中没有该字段时才补充
                        if 'priority' not in redis_status:
                            redis_status['priority'] = task.priority
                        if 'created_at' not in redis_status and task.created_at:
                            redis_status['created_at'] = task.created_at.isoformat()
                        if 'updated_at' not in redis_status and task.updated_at:
                            redis_status['updated_at'] = task.updated_at.isoformat()
                        if 'queue_position' not in redis_status and task.queue_position is not None:
                            redis_status['queue_position'] = task.queue_position
                        if 'progress' not in redis_status and task.progress is not None:
                            redis_status['progress'] = task.progress
                        if 'processing_time' not in redis_status and task.processing_time is not None:
                            redis_status['processing_time'] = task.processing_time
                        if 'error_message' not in redis_status and task.error_message:
                            redis_status['error_message'] = task.error_message
                        
                        # 处理output_data和image_urls，确保不覆盖Redis中的新数据
                        redis_output_data = redis_status.get('output_data')
                        redis_image_urls = redis_status.get('image_urls')
                        
                        # 如果Redis中没有output_data但MySQL中有，同步到Redis
                        if not redis_output_data and task.output_data:
                            redis_status['output_data'] = task.output_data
                            # 更新Redis中的output_data
                            if 'queue_service' in globals() and hasattr(queue_service, '_update_task_status'):
                                queue_service._update_task_status(
                                    task_id,
                                    redis_status.get('status'),
                                    force_redis_update=True,
                                    output_data=task.output_data
                                )
                                logger.info(f"已同步MySQL的output_data到Redis: {task_id}")
                        
                        # 如果Redis中没有image_urls但MySQL中有，同步到Redis
                        if not redis_image_urls and task.output_data:
                            if isinstance(task.output_data, dict) and 'image_urls' in task.output_data:
                                redis_status['image_urls'] = task.output_data['image_urls']
                                # 更新Redis中的image_urls
                                if 'queue_service' in globals() and hasattr(queue_service, '_update_task_status'):
                                    queue_service._update_task_status(
                                        task_id,
                                        redis_status.get('status'),
                                        force_redis_update=True,
                                        image_urls=task.output_data['image_urls']
                                    )
                                    logger.info(f"已同步MySQL的image_urls到Redis: {task_id}")
                        
                        # 检查Redis中的时间戳是否比MySQL中的更新
                        redis_timestamp = redis_status.get('timestamp')
                        if redis_timestamp and task.updated_at:
                            redis_time = float(redis_timestamp)
                            mysql_time = task.updated_at.timestamp()
                            if redis_time > mysql_time:
                                logger.info(f"Redis数据比MySQL更新，保留Redis数据: {task_id}")
                                return redis_status
                        
                        return redis_status
                    except Exception as e:
                        logger.error(f"从MySQL补充字段失败: {str(e)}")
                        return redis_status

            # 2. 如果Redis中没有数据或状态获取失败，尝试从MySQL获取
            task = ComfyUITask.objects.get(task_id=task_id)
            
            # 3. 构建基本状态信息
            status_info = {
                'task_id': task_id,
                'status': task.status,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'updated_at': task.updated_at.isoformat() if task.updated_at else None,
                'priority': task.priority,
                'from_source': 'mysql',  # 标明数据来源
                'input_data': task.input_data,  # 始终包含input_data
                'timestamp': time.time()  # 添加时间戳
            }

            # 4. 处理特殊状态
            if task.status == 'processing_completed':
                # 检查是否有输出数据
                has_results = False
                if task.output_data and isinstance(task.output_data, dict):
                    if 'image_urls' in task.output_data and task.output_data['image_urls']:
                        has_results = True
                
                # 如果有结果，自动转为completed
                if has_results:
                    logger.info(f"MySQL中任务 {task_id} 状态为processing_completed但已有结果，自动转为completed")
                    task.status = 'completed'
                    if not task.completed_at:
                        task.completed_at = timezone.now()
                    task.save(update_fields=['status', 'completed_at'])
                    status_info['status'] = 'completed'

            # 5. 添加其他字段
            if task.queue_position is not None:
                status_info['queue_position'] = task.queue_position
            if task.progress is not None:
                status_info['progress'] = task.progress
            if task.processing_time is not None:
                status_info['processing_time'] = task.processing_time
            if task.error_message:
                status_info['error_message'] = task.error_message
            if task.output_data:
                status_info['output_data'] = task.output_data
                if isinstance(task.output_data, dict) and 'image_urls' in task.output_data:
                    status_info['image_urls'] = task.output_data['image_urls']

            # 6. 将MySQL数据同步到Redis，但检查Redis中是否有更新的数据
            if 'queue_service' in globals() and hasattr(queue_service, '_update_task_status'):
                try:
                    # 再次检查Redis中是否有更新的数据
                    latest_redis_status = queue_service.get_task_status(task_id)
                    if latest_redis_status:
                        redis_timestamp = latest_redis_status.get('timestamp')
                        if redis_timestamp and float(redis_timestamp) > status_info['timestamp']:
                            logger.info(f"Redis中有更新的数据，不覆盖: {task_id}")
                            return latest_redis_status

                    # 如果没有更新的数据，同步到Redis
                    queue_service._update_task_status(
                        task_id,
                        status_info['status'],
                        force_redis_update=True,
                        **{k: v for k, v in status_info.items() if k not in ['task_id', 'status', 'from_source']}
                    )
                    logger.info(f"已同步MySQL数据到Redis: {task_id}")
                except Exception as e:
                    logger.error(f"同步MySQL数据到Redis失败: {str(e)}")

            return status_info

        except ComfyUITask.DoesNotExist:
            logger.error(f"任务 {task_id} 不存在")
            return {
                'task_id': task_id,
                'status': 'not_found',
                'error': 'Task not found'
            }
        except Exception as e:
            logger.error(f"获取任务状态失败: {str(e)}")
            return {
                'task_id': task_id,
                'status': 'error',
                'error': str(e)
            }

    @staticmethod
    def cancel_task(task_id: str) -> Dict:
        """
        取消任务
        对于队列中的任务直接标记为取消并从队列中移除
        对于运行中的任务需要通知消费者取消并断开连接
        """
        try:
            # 获取任务状态
            task_status = TaskUtils.get_task_status(task_id)
            if not task_status:
                raise BusinessException(error_code=ErrorCode.RESOURCE_NOT_FOUND, data='', errors="任务不存在")

            # 获取任务对象
            task = ComfyUITask.objects.filter(task_id=task_id).first()
            if not task:
                raise BusinessException(error_code=ErrorCode.RESOURCE_NOT_FOUND, data='', errors="任务不存在")

            # 检查任务状态
            current_status = task_status.get('status')
            if current_status == 'cancelled':
                return {'status': 'cancelled', 'message': '任务已经是取消状态'}
            if current_status == 'completed':
                raise BusinessException(error_code=ErrorCode.OPERATION_DENIED, data='', errors="已完成的任务不能取消")

            # 根据任务状态处理取消
            if current_status == 'pending':
                # 队列中的任务直接标记为取消并从队列中移除
                try:
                    # 从队列中移除任务
                    if 'queue_service' in globals() and hasattr(queue_service, 'remove_task'):
                        queue_service.remove_task(task_id)
                        logger.info(f"已从队列中移除任务 {task_id}")
                    
                    # 更新任务状态为取消
                    TaskUtils._update_task_status(task_id, 'cancelled', force_redis_update=True)
                    task.status = 'cancelled'
                    task.save()
                    
                    # 同步更新关联记录状态为取消
                    try:
                        records = ImageUploadRecord.objects.filter(comfyUI_task=task)
                        for record in records:
                            record.status = 'cancelled'
                            record.save()
                        logger.info(f"已更新 {records.count()} 条关联记录状态为取消")
                    except Exception as e:
                        logger.error(f"更新关联记录状态失败: {str(e)}")
                    
                    logger.info(f"队列中的任务 {task_id} 已直接标记为取消并从队列中移除")
                except Exception as e:
                    logger.error(f"取消队列中的任务失败: {str(e)}")
                    raise BusinessException(error_code=ErrorCode.OPERATION_FAILED, data='', errors=f"取消队列中的任务失败: {str(e)}")
            else:
                # 运行中的任务需要通知消费者取消并断开连接
                try:
                    # 更新Redis中的取消标志
                    cache_key = f"task:{task_id}:cancelled"
                    cache.set(cache_key, "true", timeout=3600)  # 设置1小时过期
                    
                    # 直接更新为取消状态
                    TaskUtils._update_task_status(task_id, 'cancelled', force_redis_update=True)
                    task.status = 'cancelled'
                    task.save()
                    
                    # 同步更新关联记录状态为取消
                    try:
                        records = ImageUploadRecord.objects.filter(comfyUI_task=task)
                        for record in records:
                            record.status = 'cancelled'
                            record.save()
                        logger.info(f"已更新 {records.count()} 条关联记录状态为取消")
                    except Exception as e:
                        logger.error(f"更新关联记录状态失败: {str(e)}")

                    # 通知消费者取消任务并断开连接
                    if 'queue_service' in globals() and hasattr(queue_service, 'disconnect_task'):
                        try:
                            queue_service.disconnect_task(task_id)
                            logger.info(f"已断开任务 {task_id} 的消费者连接")
                        except Exception as e:
                            logger.error(f"断开消费者连接失败: {str(e)}")
                    
                    logger.info(f"已发送取消信号给任务 {task_id} 的消费者")
                except Exception as e:
                    logger.error(f"发送取消信号失败: {str(e)}")
                    raise BusinessException(error_code=ErrorCode.OPERATION_FAILED, data='', errors=f"发送取消信号失败: {str(e)}")

            return {
                'task_id': task_id,
                'status': 'cancelled',
                'message': '任务已取消'
            }

        except BusinessException as e:
            raise e
        except Exception as e:
            logger.error(f"取消任务失败: {str(e)}")
            raise BusinessException(error_code=ErrorCode.OPERATION_FAILED, data='', errors=f"取消任务失败: {str(e)}")

    @staticmethod
    def _save_task_result(task_id: str, task_type: str, image_urls: List[str],
                          description: str, user, metadata: Dict) -> List[str]:
        """保存任务结果到数据库"""
        if not image_urls:
            raise ValueError("未生成有效图片")

        # 根据任务类型确定存储方式
        image_method = {
            'text_to_image': 'ai_text',
            'image_to_image': 'ai_image',
            'product_replace': 'ai_product',
            'white_background': 'white',
            'product_clue': 'clue',
            'clue_product': 'clue_image',
            'multi_image_to_image': 'multi_image',
            'fine_detail': 'fine_detail',
            'wide_picture': 'wide_picture',
            'internal_supplementation': 'internal_supplementation',
            'internal_supplementation_and_removal': 'internal_supplementation_and_removal',
            'complete_redrawing': 'complete_redrawing',
        }.get(task_type, 'ai_custom')

        # 预处理数据 - 提前处理image_urls避免重复处理
        actual_image_urls = []
        if isinstance(image_urls, dict):
            if 'image_urls' in image_urls:
                actual_image_urls = image_urls['image_urls']
            else:
                # 尝试直接获取值
                actual_image_urls = list(image_urls.values())
        elif isinstance(image_urls, list):
            for item in image_urls:
                if isinstance(item, str):
                    actual_image_urls.append(item)
                elif isinstance(item, dict) and 'url' in item:
                    actual_image_urls.append(item['url'])
        else:
            logger.warning(f"无法解析image_urls: {image_urls}")
            # 如果无法解析，使用空列表
            actual_image_urls = []

        # 检查图片URL是否为空列表
        if not actual_image_urls:
            logger.warning(f"解析后的image_urls为空，使用原始数据: {image_urls}")
            if isinstance(image_urls, list):
                actual_image_urls = image_urls
            else:
                actual_image_urls = [str(image_urls)]

        # 查找任务记录或会话
        task = None
        is_retry = False
        try:
            task = ComfyUITask.objects.get(task_id=task_id)

            # 检查是否是重试的任务
            if task.status in ['failed', 'cancelled']:
                is_retry = True
                logger.info(f"检测到任务 {task_id} 是失败或取消状态的重试")
        except ComfyUITask.DoesNotExist:
            logger.warning(f"任务 {task_id} 不存在")

        try:
            # 使用事务包裹所有数据库操作
            with transaction.atomic():
                # 如果找到了任务，更新任务状态
                if task:
                    # 在事务内更新任务
                    task = ComfyUITask.objects.select_for_update().get(pk=task.pk)

                    # 直接更新为completed状态
                    task.status = 'completed'
                    task.completed_at = timezone.now()
                    task.output_data = {'image_urls': actual_image_urls}
                    if is_retry:
                        task.output_data['is_retry'] = True

                    # 清除错误信息和队列位置
                    task.error_message = ''
                    task.queue_position = None

                    # 单次保存减少数据库操作
                    task.save(
                        update_fields=['status', 'completed_at', 'output_data', 'error_message', 'queue_position'])
                    logger.info(f"找到任务对象: {task_id}, 状态已更新为: {task.status}, 是否重试: {is_retry}")

                    # 强制更新Redis中的状态为completed（解决状态不同步问题）
                    if 'queue_service' in globals() and hasattr(queue_service, '_update_task_status'):
                        try:
                            # 直接强制更新Redis中的状态
                            queue_service._update_task_status(
                                task_id,
                                'completed',
                                completed_at=timezone.now(),
                                output_data={'image_urls': actual_image_urls},
                                force_redis_update=True  # 添加标志，确保Redis和MySQL都同步更新
                            )
                            logger.info(f"已强制更新Redis中任务 {task_id} 的状态为completed")
                        except Exception as e:
                            logger.error(f"更新Redis状态失败: {str(e)}")

                    # 确保同步记录状态 - 强制从MySQL更新到关联记录
                    try:
                        sync_result = TaskUtils.sync_record_status(task_id, force=True)
                        if sync_result['success']:
                            logger.info(f"同步更新了 {sync_result['updated_count']} 条关联记录")
                        else:
                            logger.warning(f"同步记录状态失败: {sync_result.get('message')}")
                    except Exception as e:
                        logger.error(f"同步记录状态时出错: {str(e)}")

                # 获取或创建用户对话
                conversation = None
                try:
                    # 检查是否存在关联记录
                    existing_records = ImageUploadRecord.objects.filter(
                        comfyUI_task=task
                    )

                    if existing_records.exists():
                        logger.info(f"任务 {task_id} 已有关联记录，将更新这些记录")
                        # 批量更新这些记录
                        for record in existing_records:
                            # 仅在状态不是completed或需要强制更新时才更新
                            if record.status != 'completed' or is_retry:
                                # 更新状态和图片URL
                                record.status = 'completed'
                                if actual_image_urls and len(actual_image_urls) > 0:
                                    # 如果记录索引超出范围，使用第一个URL
                                    idx = existing_records.index(record)
                                    if idx < len(actual_image_urls):
                                        record.image_url = actual_image_urls[idx]
                                    else:
                                        record.image_url = actual_image_urls[0]
                                record.save()
                                logger.info(f"已更新记录状态: {record.id}")
                        return actual_image_urls
                except Exception as e:
                    logger.error(f"获取或创建用户对话失败: {str(e)}")
                    return []

        except Exception as e:
            logger.error(f"保存任务结果过程中发生错误: {str(e)}")
            # 降级处理
            return TaskUtils._save_to_template_image(task_id, task_type, actual_image_urls, description, user, metadata)

    @staticmethod
    def _save_to_template_image(task_id: str, task_type: str, image_urls: List[str],
                                description: str, user, metadata: Dict) -> List[str]:
        """降级保存方法，使用原始templateImage模型保存"""
        # 根据任务类型确定存储方式
        image_method = {
            'text_to_image': 'ai_text',
            'image_to_image': 'ai_image',
            'product_replace': 'ai_product',
            'white_background': 'white',
            'product_clue': 'clue',
            'clue_product': 'clue_image',
        }.get(task_type, 'ai_custom')

        # 保存所有图片
        saved_urls = []
        for index, image_url in enumerate(image_urls):
            # 为每张图片生成唯一名称
            if len(image_urls) > 1:
                image_name = f"{task_id}_{index + 1}.png"
            else:
                image_name = f"{task_id}.png"

            # 保存图片记录
            image = templateImage.objects.create(
                image_name=image_name,
                image_address=image_url,
                description=description or f"AI生成-{task_id}" + (f"-{index + 1}" if len(image_urls) > 1 else ""),
                image_method=image_method,
                userImage=user,
                isDelete=0,
                metadata=metadata
            )
            saved_urls.append(image_url)
            logger.info(f"已降级保存图片 {index + 1}/{len(image_urls)} 到templateImage: {image_name}")

        return saved_urls

    @staticmethod
    def _update_task_progress(task_id: str, progress: float):
        """
        更新任务进度
        :param task_id: 任务ID
        :param progress: 进度值 (0-100)
        """
        try:
            task = ComfyUITask.objects.get(task_id=task_id)
            task.progress = progress
            task.save()

            # 同时更新任务状态
            TaskUtils._update_task_status(
                task_id,
                task.status,
                progress=progress
            )
        except ComfyUITask.DoesNotExist:
            logger.error(f"更新任务进度失败: 任务 {task_id} 不存在")
        except Exception as e:
            logger.error(f"更新任务进度失败: {str(e)}")

    @staticmethod
    def _save_failed_task_data(task_id: str, task_type: str, description: str, user, metadata: Dict) -> None:
        """
        保存失败任务的数据到数据库
        :param task_id: 任务ID
        :param task_type: 任务类型
        :param description: 任务描述
        :param user: 用户对象
        :param metadata: 元数据，包含错误信息
        """
        try:
            # 根据任务类型确定存储方式
            image_method = {
                'text_to_image': 'ai_text',
                'image_to_image': 'ai_image',
                'product_replace': 'ai_product',
                'white_background': 'white',
                'product_clue': 'clue',
                'clue_product': 'clue_image',
                'multi_image_to_image': 'multi_image',
                'fine_detail': 'fine_detail',
                'wide_picture': 'wide_picture',
                'internal_supplementation': 'internal_supplementation',
                'internal_supplementation_and_removal': 'internal_supplementation_and_removal',
                'complete_redrawing': 'complete_redrawing',
            }.get(task_type, 'ai_custom')

            # 获取任务对象
            task = ComfyUITask.objects.filter(task_id=task_id).first()
            input_data = {}
            is_retry = False
            if task:
                # 检查是否是重试任务
                if task.output_data and isinstance(task.output_data, dict) and task.output_data.get('is_retry'):
                    is_retry = True
                    logger.info(f"检测到重试失败任务: {task_id}")

                # 确保任务状态为失败
                if task.status != 'failed':
                    task.status = 'failed'
                    task.error_message = metadata.get('error_message', '未知错误')
                    task.completed_at = timezone.now()

                    # 如果是重试任务，保留重试标记和历史记录
                    if is_retry and isinstance(task.output_data, dict):
                        task.output_data['is_retry'] = True
                        task.output_data['retry_failed_at'] = timezone.now().isoformat()
                        task.output_data['retry_error'] = metadata.get('error_message', '未知错误')

                    task.save()
                input_data = task.input_data or {}
                logger.info(f"失败任务保存: 找到任务对象: {task_id}, 是否重试: {is_retry}")
            else:
                logger.warning(f"失败任务保存: 未找到任务对象: {task_id}")

            # 尝试从任务数据中提取输入图片URL
            input_image_urls = []
            if input_data:
                # 直接从metadata提取
                if 'url' in input_data:
                    input_image_urls.append(input_data['url'])

                # 从prompt_updates提取
                prompt_updates = input_data.get('prompt_updates', {})
                for node_id, update in prompt_updates.items():
                    if 'inputs' in update and 'url' in update['inputs'] and update['inputs']['url']:
                        input_image_urls.append(update['inputs']['url'])

                # 特殊字段
                for url_field in ['white_background_product_url', 'template_url', 'mask_url', 'white_mask_url']:
                    if url_field in input_data and input_data[url_field]:
                        input_image_urls.append(input_data[url_field])

            # 首先检查是否已有与该任务关联的记录
            existing_records = ImageUploadRecord.objects.filter(comfyUI_task=task)
            if existing_records.exists():
                # 如果已有关联记录，直接更新这些记录
                logger.info(f"失败任务保存: 找到 {existing_records.count()} 个与任务 {task_id} 关联的记录，将更新它们")

                # 获取错误信息
                error_message = metadata.get('error_message', '未知错误')

                # 更新所有关联记录
                for record in existing_records:
                    record.status = 'failed'
                    # 如果是重试任务，更新描述
                    if is_retry:
                        record.prompt = f"{record.prompt} (重试失败: {error_message})"
                    else:
                        record.prompt = f"{record.prompt} (失败: {error_message})"
                    record.save()
                    logger.info(f"失败任务保存: 已更新记录状态为失败: ID: {record.id}")

                return

            # 如果没有找到关联记录，创建一个新会话
            try:
                # 任务类型英文到中文的映射
                task_type_names = {
                    'text_to_image': '文生图',
                    'image_to_image': '图生图',
                    'product_replace': '产品替换',
                    'white_background': '白底图',
                    'product_clue': '产品线索',
                    'clue_product': '线索产品',
                    'fine_detail': '细节精修',
                    'wide_picture': '扩图',
                    'internal_supplementation': '内补',
                    'internal_supplementation_and_removal': '内补去除',
                    'complete_redrawing': '重绘精修',
                    'multi_image_to_image': '多图生图'
                }

                # 获取中文任务类型名称，如果没有对应的则使用原始任务类型
                conversation_name = task_type_names.get(task_type, task_type) + "(失败)"
                if is_retry:
                    conversation_name += "(重试)"

                # 创建新会话
                conversation = ConversationList.objects.create(
                    name=conversation_name,
                    user=user
                )
                logger.info(
                    f"失败任务保存: 为用户 {user.id} 创建新会话: {conversation.id}，会话名称: {conversation_name}")
            except Exception as e:
                logger.error(f"失败任务保存: 创建会话失败: {str(e)}")
                return

            # 准备图片来源列表字符串
            image_list = ""
            if input_image_urls:
                # 只取第一个输入URL
                image_list = input_image_urls[0]
                logger.info(f"失败任务保存: 使用第一个输入图片URL作为image_list")

            # 生成唯一图片名称
            image_name = f"{task_id}_failed.png"

            # 使用第一个输入图片URL作为图片URL（如果有）
            image_url = input_image_urls[0] if input_image_urls else ""

            # 添加错误信息到描述
            error_message = metadata.get('error_message', '未知错误')
            if is_retry:
                full_description = f"{description} (重试失败: {error_message})"
            else:
                full_description = f"{description} (失败: {error_message})"

            # 保存图片记录到ImageUploadRecord
            try:
                logger.info(f"失败任务保存: 尝试创建ImageUploadRecord，任务ID: {task_id}")
                record = ImageUploadRecord.objects.create(
                    user=user,
                    conversation=conversation,
                    image_url=image_url,
                    image_name=image_name,
                    prompt=full_description or f"AI生成失败-{task_id}",
                    image_list=image_list,
                    model_used=image_method,
                    comfyUI_task=task,  # 显式传递task对象
                    seed_used=str(metadata.get('seed', '')),
                    status='failed'
                )
                logger.info(f"失败任务保存: 已保存失败任务数据到ImageUploadRecord: ID: {record.id}")
            except Exception as e:
                logger.error(f"失败任务保存: 保存到ImageUploadRecord失败: {str(e)}")

        except Exception as e:
            logger.error(f"保存失败任务数据失败: {str(e)}")

    @staticmethod
    def retry_task(task_id: str) -> Dict:
        """
        重新运行任务（支持失败、完成和卡住的任务）
        :param task_id: 任务ID
        :return: 任务信息
        """
        try:
            # 1. 检查任务是否存在
            task = ComfyUITask.objects.filter(task_id=task_id).first()
            if not task:
                raise ValueError("任务不存在")

            # 2. 检查任务状态是否允许重试
            if task.status not in ['failed', 'completed', 'stuck_timeout', 'cancelled']:
                raise ValueError(f"当前状态 '{task.status}' 不支持重新运行，仅支持失败、已完成、超时或已取消的任务")

            # 3. 获取原始任务数据
            task_type = task.task_type
            task_data = task.input_data
            user = task.user
            original_priority = task.priority
            original_status = task.status
            
            # 如果是卡住或失败的任务，提高其优先级确保更快处理
            priority = original_priority
            # 如果原始优先级已经是high，不再提升
            # 否则，根据原始优先级提升一级
            if original_status in ['stuck_timeout', 'failed']:
                if original_priority == TaskUtils.PRIORITY_LOW:
                    priority = TaskUtils.PRIORITY_MEDIUM
                    logger.info(f"将卡住/失败任务 {task_id} 优先级从 {original_priority} 提升到 {priority}")
                elif original_priority == TaskUtils.PRIORITY_MEDIUM:
                    priority = TaskUtils.PRIORITY_HIGH
                    logger.info(f"将卡住/失败任务 {task_id} 优先级从 {original_priority} 提升到 {priority}")

            # 保存原始输出数据（如果有）
            original_output = None
            if task.output_data:
                original_output = task.output_data
                logger.info(f"保存原始输出数据，原始状态: {original_status}")
            
            # 4. 重置任务状态
            task.status = 'pending'
            task.error_message = None
            task.progress = 0.0
            task.queue_position = None
            task.started_at = None
            task.completed_at = None
            task.processing_time = None
            # 设置任务优先级
            task.priority = priority
            
            # 5. 在任务数据中添加重试标记
            if task.output_data:
                if isinstance(task.output_data, dict):
                    task.output_data['is_retry'] = True
                    task.output_data['retry_timestamp'] = timezone.now().isoformat()
                    task.output_data['original_status'] = original_status
                    
                    # 添加重试历史记录
                    if 'retry_history' not in task.output_data:
                        task.output_data['retry_history'] = []
                    
                    # 创建重试记录
                    retry_record = {
                        'timestamp': timezone.now().isoformat(),
                        'original_status': original_status,
                        'original_priority': original_priority,
                        'new_priority': priority
                    }
                    
                    # 如果有图片URL，保存到重试记录
                    if 'image_urls' in task.output_data:
                        retry_record['image_urls'] = task.output_data.get('image_urls')
                    
                    # 如果有错误信息，保存到重试记录
                    if task.error_message:
                        retry_record['error_message'] = task.error_message
                    
                    # 添加重试记录到历史中
                    task.output_data['retry_history'].append(retry_record)
                else:
                    # 如果output_data不是字典，创建一个新的字典
                    task.output_data = {
                        'is_retry': True,
                        'retry_timestamp': timezone.now().isoformat(),
                        'original_status': original_status,
                        'previous_output': task.output_data,
                        'retry_history': [
                            {
                                'timestamp': timezone.now().isoformat(),
                                'original_status': original_status,
                                'original_priority': original_priority,
                                'new_priority': priority
                            }
                        ]
                    }
            else:
                # 如果之前没有输出数据，创建基本的重试信息
                task.output_data = {
                    'is_retry': True,
                    'retry_timestamp': timezone.now().isoformat(),
                    'original_status': original_status,
                    'retry_history': [
                        {
                            'timestamp': timezone.now().isoformat(),
                            'original_status': original_status,
                            'original_priority': original_priority,
                            'new_priority': priority
                        }
                    ]
                }
                
            # 保存任务更新
            task.save()

            # 6. 重新计算队列位置
            queue_position = TaskUtils._get_queue_position(task_id, priority)

            # 7. 将任务添加到队列
            queue_service.add_task(
                task_id=task_id,
                task_type=task_type,
                task_data=task_data
            )

            # 8. 启动异步处理
            threading.Thread(
                target=TaskUtils._process_task_async,
                args=(task_id, task_type, task_data),
                daemon=True
            ).start()

            # 9. 更新关联记录状态为pending
            try:
                records = ImageUploadRecord.objects.filter(comfyUI_task=task)
                if records.exists():
                    for record in records:
                        record.status = 'pending'
                        record.save(update_fields=['status'])
                    logger.info(f"已将 {records.count()} 条关联记录状态更新为pending")
            except Exception as e:
                logger.error(f"更新关联记录状态失败: {str(e)}")

            # 10. 更新Redis状态
            if 'queue_service' in globals() and hasattr(queue_service, '_update_task_status'):
                try:
                    queue_service._update_task_status(
                        task_id,
                        'pending',
                        force_redis_update=True,
                        queue_position=queue_position,
                        is_retry=True,
                        original_status=original_status,
                        retry_timestamp=timezone.now().isoformat()
                    )
                except Exception as e:
                    logger.error(f"更新Redis状态失败: {str(e)}")

            # 11. 记录重试信息
            logger.info(f"重新运行任务 {task_id}，原始状态: {original_status}，新优先级: {priority}")

            # 12. 返回任务信息
            return {
                'task_id': task_id,
                'status': 'pending',
                'status_url': f"/api/image/tasks/{task_id}/status",
                'cancel_url': f"/api/image/tasks/{task_id}/cancel",
                'queue_position': queue_position,
                'priority': priority,
                'is_retry': True,
                'original_status': original_status,
                'original_priority': original_priority,
                'retry_timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f"重新运行任务失败: {str(e)}")
            raise BusinessException(
                error_code=ErrorCode.SYSTEM_ERROR,
                data=None,
                errors=str(e)
            )

    @staticmethod
    def check_user_concurrent_limit(user) -> bool:
        """
        检查用户是否超出任务并发限制
        :param user: 用户对象
        :return: 是否允许创建新任务
        """
        try:
            # 判断用户是否为VIP (使用userRole字段判断)
            user_vip = UserVIP.objects.filter(user=user, is_active=True).first()
            is_vip = False
            if user_vip:
                is_vip = True
            
            # 设置并发限制
            if is_vip:
                # VIP用户最多5个并发任务
                max_concurrent_tasks = 5
            else:
                # 非VIP用户最多1个并发任务
                max_concurrent_tasks = 1
            
            # 获取用户当前活跃任务（等待中和处理中）
            active_tasks = ComfyUITask.objects.filter(
                user=user,
                status__in=['pending', 'processing', 'processing_completed']
            )
            
            # 首先直接检查活跃任务数量
            active_tasks_count = active_tasks.count()
            
            # 如果未超过限制，直接返回允许创建新任务
            if active_tasks_count < max_concurrent_tasks:
                logger.info(f"用户 {user.id} 当前有 {active_tasks_count} 个活跃任务，未超过限制 {max_concurrent_tasks}")
                return True
            
            # 如果看起来已超过限制，检查是否有任务已经实际完成但状态未更新
            # 这种情况下需要执行额外的检查，防止任务状态延迟更新导致错误限制用户
            processing_tasks = active_tasks.filter(status__in=['processing', 'processing_completed'])
            
            # 如果没有处理中的任务，说明都是等待中的任务，不需要额外检查
            if not processing_tasks.exists():
                logger.info(f"用户 {user.id} 有 {active_tasks_count} 个等待中的任务，超过限制 {max_concurrent_tasks}")
                return False
            
            # 对每个处理中的任务进行检查，看是否实际已完成
            updated_task_count = 0
            for task in processing_tasks:
                try:
                    # 只检查更新时间超过30秒的任务，避免刚开始处理的任务被误判
                    if task.updated_at and (timezone.now() - task.updated_at).total_seconds() > 30:
                        # 检查任务是否有结果
                        has_results = False
                        
                        # 从数据库检查
                        if task.output_data and isinstance(task.output_data, dict) and 'image_urls' in task.output_data:
                            if task.output_data['image_urls']:
                                has_results = True
                        
                        # 从Redis检查
                        if not has_results and 'queue_service' in globals() and hasattr(queue_service, 'get_task_status'):
                            task_status = queue_service.get_task_status(task.task_id)
                            if task_status:
                                if 'image_urls' in task_status and task_status['image_urls']:
                                    has_results = True
                                    logger.info(f"任务 {task.task_id} 在Redis中有结果但状态为 {task_status.get('status')}")
                                elif 'output_data' in task_status and task_status['output_data']:
                                    output_data = task_status['output_data']
                                    if isinstance(output_data, dict) and 'image_urls' in output_data and output_data['image_urls']:
                                        has_results = True
                                        logger.info(f"任务 {task.task_id} 在Redis的output_data中有结果但状态为 {task_status.get('status')}")
                        
                        # 如果任务实际已完成，立即修复状态
                        if has_results:
                            # 立即强制更新状态为已完成
                            logger.info(f"发现用户 {user.id} 的任务 {task.task_id} 已有结果，立即修复状态")
                            
                            # 准备output_data
                            output_data = None
                            if task.output_data and isinstance(task.output_data, dict) and 'image_urls' in task.output_data:
                                output_data = task.output_data
                            
                            # 更新状态
                            TaskUtils._update_task_status(
                                task.task_id,
                                'completed',
                                force_redis_update=True,
                                output_data=output_data,
                                completed_at=timezone.now()
                            )
                            
                            # 更新计数
                            updated_task_count += 1
                except Exception as e:
                    logger.error(f"检查任务 {task.task_id} 状态时出错: {str(e)}")
            
            # 如果有任务状态被修复，重新计算活跃任务数
            if updated_task_count > 0:
                # 重新获取活跃任务数
                active_tasks_count = ComfyUITask.objects.filter(
                    user=user,
                    status__in=['pending', 'processing', 'processing_completed']
                ).count()
                
                logger.info(f"用户 {user.id} 修复了 {updated_task_count} 个任务状态，当前实际有 {active_tasks_count} 个活跃任务")
            
            # 最终检查是否符合限制
            return active_tasks_count < max_concurrent_tasks

        except Exception as e:
            logger.error(f"检查用户并发限制失败: {str(e)}", exc_info=True)
            return False  # 出错时默认不允许创建新任务

    @staticmethod
    def sync_record_status(task_id: str, force: bool = False) -> Dict:
        """
        同步任务状态到记录
        如果任务状态为取消，保持取消状态
        如果任务状态为失败且没有结果，检查是否为取消状态
        """
        try:
            # 获取任务状态
            task_status = TaskUtils.get_task_status(task_id)
            if not task_status:
                return {'success': False, 'message': '任务不存在', 'updated_count': 0}

            # 获取任务对象
            task = ComfyUITask.objects.filter(task_id=task_id).first()
            if not task:
                return {'success': False, 'message': '任务不存在', 'updated_count': 0}

            # 获取关联的记录
            records = ImageUploadRecord.objects.filter(comfyUI_task=task)
            if not records.exists():
                return {'success': False, 'message': '未找到关联记录', 'updated_count': 0}

            # 获取当前状态
            current_status = task_status.get('status')
            
            # 如果任务已完成，不允许更改为其他状态
            if task.status == 'completed' and current_status != 'completed':
                logger.warning(f"任务 {task_id} 已完成，不允许更改为 {current_status} 状态")
                return {'success': False, 'message': '任务已完成，不允许更改状态', 'updated_count': 0}
            
            # 如果是取消状态，直接同步为取消
            if current_status == 'cancelled':
                # 如果任务已完成，不允许更改为取消状态
                if task.status == 'completed':
                    logger.warning(f"任务 {task_id} 已完成，不允许更改为取消状态")
                    return {'success': False, 'message': '任务已完成，不允许更改为取消状态', 'updated_count': 0}
                    
                updated_count = 0
                for record in records:
                    if record.status != 'cancelled':
                        record.status = 'cancelled'
                        record.save()
                        updated_count += 1
                return {'success': True, 'message': '已同步取消状态', 'updated_count': updated_count}

            # 如果是失败状态，检查是否为取消
            if current_status == 'failed':
                # 检查缓存中是否有取消标志
                cache_key = f"task:{task_id}:cancelled"
                is_cancelled = cache.get(cache_key)
                
                if is_cancelled == "true":
                    # 如果任务已完成，不允许更改为取消状态
                    if task.status == 'completed':
                        logger.warning(f"任务 {task_id} 已完成，不允许更改为取消状态")
                        return {'success': False, 'message': '任务已完成，不允许更改为取消状态', 'updated_count': 0}
                        
                    # 如果是取消状态，更新为取消
                    updated_count = 0
                    for record in records:
                        if record.status != 'cancelled':
                            record.status = 'cancelled'
                            record.save()
                            updated_count += 1
                        return {'success': True, 'message': '已同步取消状态', 'updated_count': updated_count}

            # 获取图片URL
            image_urls = TaskUtils._extract_image_urls(task_status, task)
            
            # 更新记录状态和图片URL
            updated_count = 0
            for record in records:
                needs_update = False
                
                # 检查状态是否需要更新
                if record.status != current_status:
                    # 如果记录状态为completed，不允许更改为其他状态
                    if record.status == 'completed' and current_status != 'completed':
                        logger.warning(f"记录 {record.id} 已完成，不允许更改为 {current_status} 状态")
                        continue
                        
                    record.status = current_status
                    needs_update = True
                
                # 如果有图片URL且记录中没有，更新图片URL
                if image_urls and not record.image_url:
                    record.image_url = image_urls[0] if len(image_urls) == 1 else ','.join(image_urls)
                    needs_update = True
                
                if needs_update:
                    record.save()
                    updated_count += 1
            
            return {
                'success': True,
                'message': f'已同步 {updated_count} 条记录',
                'updated_count': updated_count
            }

        except Exception as e:
            logger.error(f"同步记录状态失败: {str(e)}")
            return {'success': False, 'message': str(e), 'updated_count': 0}

    @staticmethod
    def _extract_image_urls(redis_task_status, task):
        """
        从Redis或MySQL中提取图片URL
        :param redis_task_status: Redis中的任务状态
        :param task: MySQL中的任务对象
        :return: 图片URL列表或None
        """
        task_image_urls = []

        # 1. 首先从Redis尝试获取图片URL（最新）
        if redis_task_status:
            # 检查不同可能的字段
            if 'image_urls' in redis_task_status:
                task_image_urls = redis_task_status['image_urls']
                logger.info(f"从Redis.image_urls获取到 {len(task_image_urls)} 张图片URL")
            elif 'output_data' in redis_task_status and redis_task_status['output_data']:
                output_data = redis_task_status['output_data']
                # 处理不同的格式
                if isinstance(output_data, dict) and 'image_urls' in output_data:
                    task_image_urls = output_data['image_urls']
                    logger.info(f"从Redis.output_data.image_urls获取到 {len(task_image_urls)} 张图片URL")
                elif isinstance(output_data, str):
                    try:
                        output_dict = json.loads(output_data)
                        if isinstance(output_dict, dict) and 'image_urls' in output_dict:
                            task_image_urls = output_dict['image_urls']
                            logger.info(f"从Redis.output_data(JSON字符串)获取到 {len(task_image_urls)} 张图片URL")
                    except:
                        logger.warning(f"Redis中的output_data不是有效的JSON: {output_data}")

        # 2. 如果Redis没有图片URL，尝试从MySQL获取
        if not task_image_urls and task.output_data:
            if isinstance(task.output_data, dict) and 'image_urls' in task.output_data:
                task_image_urls = task.output_data['image_urls']
                logger.info(f"从MySQL.output_data获取到 {len(task_image_urls)} 张图片URL")
            elif isinstance(task.output_data, str):
                try:
                    output_dict = json.loads(task.output_data)
                    if isinstance(output_dict, dict) and 'image_urls' in output_dict:
                        task_image_urls = output_dict['image_urls']
                        logger.info(f"从MySQL.output_data(JSON字符串)获取到 {len(task_image_urls)} 张图片URL")
                except:
                    logger.warning(f"MySQL中的output_data不是有效的JSON: {task.output_data}")

        return task_image_urls

    @staticmethod
    def check_and_update_stuck_tasks():
        """
        检查任务状态可能卡住的任务，修复状态
        查找那些有结果但状态不正确的任务并更新它们
        """
        try:
            logger.info("开始检查卡住的任务...")
            # 查找处理中状态可能卡住的任务
            processing_tasks = ComfyUITask.objects.filter(
                status__in=['processing', 'processing_completed'],
                updated_at__lt=timezone.now() - timedelta(minutes=2)  # 至少卡住2分钟
            )
            
            fixed_count = 0
            # 对每个可能卡住的任务
            for task in processing_tasks:
                try:
                    # 获取包含结果的完整任务状态
                    task_status = TaskUtils.get_task_status(task.task_id)
                    
                    # 检查任务是否有结果
                    has_results = False
                    
                    # 检查output_data中是否有image_urls
                    if task.output_data and isinstance(task.output_data, dict) and 'image_urls' in task.output_data:
                        if task.output_data['image_urls']:
                            has_results = True
                            logger.info(f"任务 {task.task_id} 在MySQL中有结果但状态为 {task.status}")
                    
                    # 同时检查Redis数据
                    if not has_results and task_status:
                        if 'image_urls' in task_status and task_status['image_urls']:
                            has_results = True
                            logger.info(f"任务 {task.task_id} 在Redis中有image_urls但状态为 {task_status.get('status')}")
                        elif 'output_data' in task_status and task_status['output_data']:
                            output_data = task_status['output_data']
                            if isinstance(output_data, dict) and 'image_urls' in output_data and output_data['image_urls']:
                                has_results = True
                                logger.info(f"任务 {task.task_id} 在Redis的output_data中有结果但状态为 {task_status.get('status')}")
                    
                    # 如果任务有结果，更新状态为completed
                    if has_results:
                        logger.info(f"检测到任务 {task.task_id} 有结果但状态为 {task.status}，正在修复...")
                        
                        # 准备output_data
                        output_data = None
                        if task.output_data and isinstance(task.output_data, dict) and 'image_urls' in task.output_data:
                            output_data = task.output_data
                        
                        # 更新状态
                        TaskUtils._update_task_status(
                            task.task_id,
                            'completed',
                            force_redis_update=True,
                            output_data=output_data,
                            completed_at=timezone.now()
                        )
                        
                        # 同步记录状态
                        sync_result = TaskUtils.sync_record_status(task.task_id, force=True)
                        if sync_result['success']:
                            logger.info(f"已同步 {sync_result['updated_count']} 条关联记录")
                        else:
                            logger.warning(f"同步记录状态失败: {sync_result.get('message')}")
                        
                        fixed_count += 1
                except Exception as e:
                    logger.error(f"检查任务 {task.task_id} 时出错: {str(e)}")
            
            if fixed_count > 0:
                logger.info(f"共修复了 {fixed_count} 个卡住的任务")
            else:
                logger.info("未发现需要修复的卡住任务")
        
        except Exception as e:
            logger.error(f"check_and_update_stuck_tasks执行出错: {str(e)}")
