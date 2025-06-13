import logging
import time
import json
from datetime import timedelta
import redis
from threading import Thread
from django.utils import timezone
from celery import shared_task
from django.conf import settings

from templateImage.models import ComfyUITask
from templateImage.task_utils import TaskUtils
from templateImage.queue_service_singleton import queue_service

logger = logging.getLogger(__name__)

@shared_task
def monitor_processing_tasks():
    """定期检查并处理长时间处于processing状态的任务"""
    logger.info("开始检查长时间处于processing状态的任务...")
    
    # 找出所有处于processing状态超过10分钟的任务
    time_threshold = timezone.now() - timedelta(minutes=10)
    stuck_tasks = ComfyUITask.objects.filter(
        status='processing',
        started_at__lt=time_threshold
    )
    
    fixed_count = 0
    for task in stuck_tasks:
        try:
            # 检查任务是否在队列服务的活跃任务列表中
            is_task_active = False
            if queue_service:
                with queue_service.lock:
                    is_task_active = task.task_id in queue_service.active_tasks
            
            # 如果任务不在活跃任务列表中，但状态为processing，说明任务已卡住
            if not is_task_active:
                logger.warning(f"检测到卡住的任务 {task.task_id}，状态为processing但不在活跃任务列表中")
                TaskUtils._update_task_status(
                    task.task_id,
                    'pending',  # 重置为等待状态，允许重新处理
                    error_message='任务处理超时，系统自动重置',
                    force_redis_update=True
                )
                fixed_count += 1
                logger.info(f"已重置超时任务 {task.task_id} 状态为pending")
        except Exception as e:
            logger.error(f"重置任务 {task.task_id} 状态失败: {str(e)}", exc_info=True)
    
    logger.info(f"任务监控完成，已处理 {fixed_count} 个卡住的任务")
    return f"已处理 {fixed_count} 个卡住的任务"

@shared_task
def full_task_status_sync():
    """全量扫描所有任务，确保状态一致性"""
    logger.info("开始全量扫描任务状态...")
    
    try:
        redis_client = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
        
        # 获取所有未完成的任务
        pending_and_processing_tasks = ComfyUITask.objects.filter(
            status__in=['pending', 'processing']
        ).order_by('created_at')
        
        processed_count = 0
        inconsistent_count = 0
        
        for task in pending_and_processing_tasks:
            # 检查任务创建时间，如果太久远（例如超过24小时），标记为失败
            if (timezone.now() - task.created_at).total_seconds() > 86400:  # 24小时
                logger.warning(f"任务 {task.task_id} 创建时间超过24小时，自动标记为失败")
                TaskUtils._update_task_status(
                    task.task_id,
                    'failed',
                    error_message='任务处理超时，系统自动取消',
                    completed_at=timezone.now(),
                    force_redis_update=True
                )
                processed_count += 1
                continue
                
            # 检查Redis与数据库的状态一致性
            try:
                redis_status_data = redis_client.hget('comfyui_task_status', task.task_id)
                if redis_status_data:
                    redis_status = json.loads(redis_status_data)
                    db_status = task.status
                    
                    # 如果状态不一致，进行同步
                    if redis_status.get('status') != db_status:
                        logger.warning(f"任务 {task.task_id} 状态不一致: Redis={redis_status.get('status')}, DB={db_status}")
                        inconsistent_count += 1
                        # 优先以Redis中的终态为准
                        if redis_status.get('status') in ['completed', 'failed', 'cancelled']:
                            TaskUtils._update_task_status(
                                task.task_id,
                                redis_status.get('status'),
                                output_data=redis_status.get('output_data'),
                                error_message=redis_status.get('error_message'),
                                completed_at=timezone.now() if not task.completed_at else task.completed_at,
                                force_redis_update=False  # 不更新Redis
                            )
                        else:
                            # 如果Redis不是终态，以数据库为准
                            status_data = {
                                'task_id': task.task_id,
                                'status': task.status,
                                'timestamp': time.time(),
                                'from_source': 'full_sync'
                            }
                            redis_client.hset('comfyui_task_status', task.task_id, json.dumps(status_data))
            except Exception as e:
                logger.error(f"检查任务 {task.task_id} 状态一致性失败: {str(e)}", exc_info=True)
        
        logger.info(f"全量扫描任务状态完成，已处理 {processed_count} 个超时任务，修复 {inconsistent_count} 个状态不一致任务")
        return f"已处理 {processed_count} 个超时任务，修复 {inconsistent_count} 个状态不一致任务"
    except Exception as e:
        logger.error(f"全量扫描任务状态失败: {str(e)}", exc_info=True)
        return f"全量扫描任务状态失败: {str(e)}"

def start_monitoring_thread():
    """启动一个后台线程，定期检查活跃任务状态"""
    def _check_active_tasks_loop():
        while True:
            try:
                # 检查队列服务中所有活跃任务的状态
                if queue_service:
                    _check_active_tasks_status()
                # 每60秒检查一次
                time.sleep(60)
            except Exception as e:
                logger.error(f"检查活跃任务状态失败: {str(e)}", exc_info=True)
                time.sleep(10)  # 出错后稍等一会再继续
    
    monitor_thread = Thread(target=_check_active_tasks_loop, daemon=True)
    monitor_thread.start()
    logger.info("活跃任务监控线程已启动")

def _check_active_tasks_status():
    """检查所有活跃任务的状态，处理可能卡住的任务"""
    if not queue_service:
        logger.warning("队列服务未初始化，无法检查活跃任务状态")
        return
    
    current_time = time.time()
    tasks_to_reset = []
    
    with queue_service.lock:
        # 检查每个活跃任务的执行时间
        for task_id, stop_event in list(queue_service.active_tasks.items()):
            # 获取任务详情
            try:
                task = ComfyUITask.objects.get(task_id=task_id)
                if task.started_at:
                    # 检查任务处理时间是否超过阈值（例如5分钟）
                    processing_time = (timezone.now() - task.started_at).total_seconds()
                    if processing_time > 300:  # 5分钟
                        logger.warning(f"任务 {task_id} 处理时间过长 ({processing_time:.0f}秒)，可能已卡住，准备重置")
                        tasks_to_reset.append(task_id)
            except ComfyUITask.DoesNotExist:
                logger.warning(f"活跃任务 {task_id} 在数据库中不存在")
                tasks_to_reset.append(task_id)
            except Exception as e:
                logger.error(f"检查任务 {task_id} 时出错: {str(e)}", exc_info=True)
    
    # 重置卡住的任务
    for task_id in tasks_to_reset:
        try:
            # 从活跃任务列表中移除
            with queue_service.lock:
                if task_id in queue_service.active_tasks:
                    # 发送中断信号
                    queue_service.active_tasks[task_id].set()
                    del queue_service.active_tasks[task_id]
                    
            # 更新任务状态为pending，允许重新处理
            TaskUtils._update_task_status(
                task_id,
                'pending',
                error_message='任务处理超时，系统自动重置',
                force_redis_update=True
            )
            
            logger.info(f"已重置卡住的任务 {task_id}")
        except Exception as e:
            logger.error(f"重置任务 {task_id} 失败: {str(e)}", exc_info=True) 