import queue
import threading
import time
import redis
import json
import uuid
import logging
from threading import Thread, Event
from queue import Queue
from typing import Dict, Optional, Callable, List, Any
from datetime import datetime

from django.db import transaction
from django.db.backends.signals import connection_created
from django.dispatch import receiver
from django.utils import timezone

from templateImage.models import ComfyUITask

logger = logging.getLogger(__name__)


class QueueService:
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379):
        """
        增强版队列服务，支持任务中断和状态跟踪
        """
        self.redis = redis.StrictRedis(host=redis_host, port=redis_port, db=0)
        self.local_queue = Queue()  # 本地内存队列作为备份
        self.is_redis_available = True
        self.task_callbacks = {}  # 存储任务回调函数
        self.running = True
        self.active_tasks = {}  # 存储当前活跃任务及其停止事件
        self.lock = threading.Lock()  # 线程锁
        self.consumer = None
        self._recovery_initialized = False
        self.consumer_thread = None  # 初始化时不启动线程

        # 检查 Redis 连接
        self._check_redis_connection()

    def get_consumer(self):
        """获取当前设置的消费者"""
        return self.consumer

    def get_queue_size(self) -> int:
        """获取队列中等待的任务数量"""
        try:
            if self.is_redis_available:
                return self.redis.llen('comfyui_queue')
            else:
                return self.local_queue.qsize()
        except Exception as e:
            logger.error(f"获取队列大小失败: {str(e)}")
            return 0

    def initialize_recovery(self):
        """初始化任务恢复（在应用完全初始化后调用）"""
        if not self._recovery_initialized:
            logger.info("开始初始化恢复功能")
            
            # 清理队列，避免重复处理已完成或失败的任务
            self._clear_queue()
            
            # 将数据库访问移到单独的线程中
            def _recover_tasks_async():
                try:
                    # 首先检查并同步所有已完成任务的状态
                    _sync_completed_tasks_status()
                    
                    # 彻底扫描所有状态不一致的任务
                    _scan_for_inconsistent_statuses()
                    
                    # 恢复pending和processing状态的任务
                    tasks_to_recover = ComfyUITask.objects.filter(
                        status__in=['pending', 'processing']
                    ).order_by('created_at')

                    if tasks_to_recover:
                        logger.info(f"发现 {len(tasks_to_recover)} 个需要恢复的任务")
                        recovered_task_ids = []  # 跟踪已恢复的任务ID

                        for task in tasks_to_recover:
                            try:
                                # 增强：双重检查Redis中任务状态，避免重复处理已完成任务
                                skip_task = False
                                redis_status = None
                                if self.is_redis_available:
                                    redis_status_data = self.redis.hget('comfyui_task_status', task.task_id)
                                    if redis_status_data:
                                        try:
                                            redis_status = json.loads(redis_status_data)
                                            if 'status' in redis_status and redis_status['status'] in ['completed', 'failed', 'cancelled']:
                                                logger.warning(f"Redis中任务 {task.task_id} 状态为 {redis_status['status']}，不再恢复")
                                                
                                                # 如果数据库状态与Redis不一致，更新数据库状态
                                                if task.status != redis_status['status']:
                                                    logger.info(f"【状态同步】更新数据库中任务 {task.task_id} 状态为 {redis_status['status']} (原状态: {task.status})")
                                                    task.status = redis_status['status']
                                                    if 'completed_at' in redis_status and redis_status['completed_at']:
                                                        try:
                                                            task.completed_at = datetime.fromisoformat(redis_status['completed_at'])
                                                        except:
                                                            task.completed_at = timezone.now()
                                                    elif redis_status['status'] in ['completed', 'failed', 'cancelled']:
                                                        task.completed_at = timezone.now()
                                                    
                                                    if 'output_data' in redis_status and redis_status['output_data']:
                                                        task.output_data = redis_status['output_data']
                                                    
                                                    task.save()
                                                    logger.info(f"已成功更新数据库中任务 {task.task_id} 状态")
                                                skip_task = True
                                        except json.JSONDecodeError:
                                            logger.warning(f"Redis中任务状态数据无效: {redis_status_data}")

                                if skip_task:
                                    continue

                                # 再次检查数据库中的任务状态（可能已被其他线程更新）
                                task.refresh_from_db()
                                if task.status in ['completed', 'failed', 'cancelled']:
                                    logger.info(f"数据库中任务 {task.task_id} 状态为 {task.status}，不再恢复")
                                    
                                    # 确保Redis状态一致
                                    if self.is_redis_available and (not redis_status or redis_status.get('status') != task.status):
                                        status_data = {
                                            'task_id': task.task_id,
                                            'status': task.status,
                                            'timestamp': time.time(),
                                            'from_source': 'mysql_sync',
                                            'completed_at': task.completed_at.isoformat() if task.completed_at else timezone.now().isoformat(),
                                            'output_data': task.output_data
                                        }
                                        self.redis.hset('comfyui_task_status', task.task_id, json.dumps(status_data))
                                        logger.info(f"已同步数据库状态到Redis: 任务 {task.task_id} 状态 {task.status}")
                                    continue

                                # 重置processing状态的任务为pending
                                if task.status == 'processing':
                                    task.status = 'pending'
                                    task.started_at = None
                                    task.save(update_fields=['status', 'started_at'])
                                    logger.info(f"已将任务 {task.task_id} 状态从processing重置为pending")

                                # 重新加入队列
                                task_item = {
                                    'task_id': task.task_id,  # 使用task_id而不是id
                                    'type': task.task_type,
                                    'data': task.input_data,
                                    'status': 'pending'
                                }

                                # 最终检查确保任务状态
                                final_check = True
                                
                                # 1. 最后一次刷新检查数据库状态
                                try:
                                    task.refresh_from_db()  # 刷新任务对象
                                    if task.status in ['completed', 'failed', 'cancelled']:
                                        logger.warning(f"任务 {task.task_id} 在最终检查时数据库状态为 {task.status}，取消恢复")
                                        final_check = False
                                except Exception as e:
                                    logger.error(f"最终检查任务状态失败: {str(e)}")
                                
                                # 2. 最后一次检查Redis状态
                                if final_check and self.is_redis_available:
                                    try:
                                        redis_status_data = self.redis.hget('comfyui_task_status', task.task_id)
                                        if redis_status_data:
                                            redis_status = json.loads(redis_status_data)
                                            if 'status' in redis_status and redis_status['status'] in ['completed', 'failed', 'cancelled']:
                                                logger.warning(f"Redis中任务 {task.task_id} 在最终检查时状态为 {redis_status['status']}，取消恢复")
                                                
                                                # 同步到MySQL
                                                if task.status != redis_status['status']:
                                                    task.status = redis_status['status']
                                                    if 'completed_at' in redis_status and redis_status['completed_at']:
                                                        try:
                                                            task.completed_at = datetime.fromisoformat(redis_status['completed_at'])
                                                        except:
                                                            task.completed_at = timezone.now()
                                                    task.save()
                                                final_check = False
                                    except Exception as e:
                                        logger.error(f"最终检查Redis状态失败: {str(e)}")
                                
                                if not final_check:
                                    logger.info(f"任务 {task.task_id} 基于最终检查结果不再恢复")
                                    continue

                                # 通过所有检查后，将任务加入队列
                                if self.is_redis_available:
                                    self.redis.rpush('comfyui_queue', json.dumps(task_item))
                                    # 同时更新Redis状态
                                    status_data = {
                                        'task_id': task.task_id,
                                        'status': 'pending',
                                        'timestamp': time.time(),
                                        'from_source': 'recovery'
                                    }
                                    self.redis.hset('comfyui_task_status', task.task_id, json.dumps(status_data))
                                else:
                                    self.local_queue.put(task_item)

                                logger.info(f"已恢复任务 {task.task_id} (原状态: {task.status})")
                                recovered_task_ids.append(task.task_id)
                                
                                # 如果这是第一个恢复的任务，且当前无活跃任务，考虑直接处理
                                if len(recovered_task_ids) == 1:
                                    with self.lock:
                                        active_tasks = list(self.active_tasks.keys())
                                        if not active_tasks and self.consumer:
                                            logger.info(f"这是第一个恢复的任务且当前无活跃任务，尝试直接处理: {task.task_id}")
                                            # 先从队列中移除刚刚添加的任务
                                            if self.is_redis_available:
                                                try:
                                                    removed = self.redis.lrem('comfyui_queue', 1, json.dumps(task_item))
                                                    logger.info(f"已从Redis队列移除任务: {removed} 个")
                                                except Exception as e:
                                                    logger.error(f"从Redis队列移除任务失败: {str(e)}")
                                            
                                            # 确保任务数据完整
                                            try:
                                                if not task_item.get('data'):
                                                    task_item['data'] = task.input_data
                                                if not task_item.get('type'):
                                                    task_item['type'] = task.task_type
                                            except Exception as e:
                                                logger.error(f"补充任务数据失败: {str(e)}")
                                                
                                            # 使用专门的方法直接处理恢复的任务
                                            logger.info(f"调用_direct_process_recovered_task处理任务 {task.task_id}")
                                            self._direct_process_recovered_task(task_item)
                                            # 不要在这里返回，继续处理其他恢复的任务

                            except Exception as e:
                                logger.error(f"恢复任务 {task.task_id} 失败: {str(e)}")
                    else:
                        logger.info("没有发现需要恢复的任务")
                        
                    # 所有恢复任务添加到队列后，检查是否有活跃任务
                    # 如果没有活跃任务，就主动触发任务处理机制
                    with self.lock:
                        active_tasks = list(self.active_tasks.keys())
                        if not active_tasks and self.consumer:
                            logger.info("恢复完成后队列中没有活跃任务，尝试强制触发处理机制")
                            # 主动触发任务处理
                            self._trigger_task_processing()
                            
                            # 额外检查：如果触发后仍没有活跃任务，直接取出一个任务处理
                            # 这确保恢复的任务能尽快开始处理
                            with self.lock:
                                if not self.active_tasks and recovered_task_ids and self.is_redis_available:
                                    logger.info("触发后仍无活跃任务，尝试直接处理第一个恢复的任务")
                                    try:
                                        # 检查队列中是否有任务
                                        queue_size = self.redis.llen('comfyui_queue')
                                        if queue_size > 0:
                                            # 获取第一个任务但不从队列移除，先检查是否是恢复的任务
                                            task_data = self.redis.lindex('comfyui_queue', 0)
                                            if task_data:
                                                task = json.loads(task_data)
                                                task_id = task.get('task_id', '未知')
                                                # 确认是恢复的任务才处理
                                                if task_id in recovered_task_ids:
                                                    # 从队列中移除
                                                    self.redis.lpop('comfyui_queue')
                                                    logger.info(f"直接处理恢复的任务: {task_id}")
                                                    # 立即处理这个任务
                                                    self._direct_process_recovered_task(task)
                                    except Exception as e:
                                        logger.error(f"尝试直接处理恢复任务失败: {str(e)}")

                except Exception as e:
                    logger.error(f"恢复任务时发生错误: {str(e)}")

            def _sync_completed_tasks_status():
                """同步所有已完成任务的状态"""
                try:
                    # 获取已完成、失败或取消的任务
                    completed_tasks = ComfyUITask.objects.filter(
                        status__in=['completed', 'failed', 'cancelled']
                    ).order_by('-updated_at')[:1000]  # 限制数量，避免过多数据库操作
                    
                    if self.is_redis_available and completed_tasks:
                        logger.info(f"同步 {len(completed_tasks)} 个已完成任务的状态到Redis")
                        
                        for task in completed_tasks:
                            # 检查Redis中的任务状态
                            redis_status_data = self.redis.hget('comfyui_task_status', task.task_id)
                            if redis_status_data:
                                try:
                                    redis_status = json.loads(redis_status_data)
                                    # 如果Redis中的状态与数据库不一致，优先使用数据库的状态
                                    if redis_status.get('status') != task.status:
                                        logger.warning(f"Redis中任务 {task.task_id} 状态 {redis_status.get('status')} 与数据库中 {task.status} 不一致，优先使用数据库的状态")
                                        # 更新Redis中的状态
                                        status_data = {
                                            'task_id': task.task_id,
                                            'status': task.status,
                                            'timestamp': time.time(),
                                            'from_source': 'mysql_sync',
                                            'completed_at': task.completed_at.isoformat() if task.completed_at else timezone.now().isoformat(),
                                            'output_data': task.output_data
                                        }
                                        self.redis.hset('comfyui_task_status', task.task_id, json.dumps(status_data))
                                except Exception as e:
                                    logger.error(f"解析或更新Redis中任务状态失败 {task.task_id}: {str(e)}")
                            else:
                                # Redis中没有这个任务的状态，添加它
                                try:
                                    status_data = {
                                        'task_id': task.task_id,
                                        'status': task.status,
                                        'timestamp': time.time(),
                                        'from_source': 'mysql_sync',
                                        'completed_at': task.completed_at.isoformat() if task.completed_at else timezone.now().isoformat(),
                                        'output_data': task.output_data
                                    }
                                    self.redis.hset('comfyui_task_status', task.task_id, json.dumps(status_data))
                                    logger.info(f"将任务 {task.task_id} 状态 {task.status} 添加到Redis")
                                except Exception as e:
                                    logger.error(f"将任务状态添加到Redis失败 {task.task_id}: {str(e)}")
                except Exception as e:
                    logger.error(f"同步已完成任务状态失败: {str(e)}")
                    
            def _scan_for_inconsistent_statuses():
                """扫描所有状态不一致的任务"""
                if not self.is_redis_available:
                    return
                    
                try:
                    # 从Redis获取所有任务状态
                    all_redis_tasks = self.redis.hgetall('comfyui_task_status')
                    if not all_redis_tasks:
                        logger.info("Redis中没有任务状态记录，跳过不一致状态扫描")
                        return
                        
                    logger.info(f"扫描 {len(all_redis_tasks)} 个Redis任务状态的一致性")
                    inconsistent_count = 0
                    
                    for task_id_bytes, status_data_bytes in all_redis_tasks.items():
                        try:
                            task_id = task_id_bytes.decode('utf-8')
                            redis_status = json.loads(status_data_bytes.decode('utf-8'))
                            
                            # 只关注终态任务
                            if redis_status.get('status') not in ['completed', 'failed', 'cancelled']:
                                continue
                                
                            # 检查数据库状态
                            db_task = ComfyUITask.objects.filter(task_id=task_id).first()
                            if not db_task:
                                logger.warning(f"Redis中任务 {task_id} 在数据库中不存在")
                                continue
                                
                            # 如果状态不一致，记录并根据配置同步
                            if db_task.status != redis_status.get('status'):
                                inconsistent_count += 1
                                logger.warning(f"状态不一致: 任务 {task_id} - Redis: {redis_status.get('status')}, MySQL: {db_task.status}")
                                
                                # 根据实际需求决定是更新MySQL还是Redis
                                # 此处我们选择更新MySQL以匹配Redis（Redis为主要状态源）
                                db_task.status = redis_status.get('status')
                                if 'completed_at' in redis_status and redis_status['completed_at']:
                                    try:
                                        db_task.completed_at = datetime.fromisoformat(redis_status['completed_at'])
                                    except:
                                        db_task.completed_at = timezone.now()
                                elif redis_status.get('status') in ['completed', 'failed', 'cancelled'] and not db_task.completed_at:
                                    db_task.completed_at = timezone.now()
                                    
                                if 'output_data' in redis_status and redis_status['output_data']:
                                    db_task.output_data = redis_status['output_data']
                                    
                                db_task.save()
                                logger.info(f"已同步Redis状态到MySQL: 任务 {task_id} -> {redis_status.get('status')}")
                                
                        except Exception as e:
                            logger.error(f"处理任务状态一致性检查失败 {task_id if 'task_id' in locals() else '未知'}: {str(e)}")
                            
                    if inconsistent_count > 0:
                        logger.warning(f"发现并处理了 {inconsistent_count} 个状态不一致的任务")
                    else:
                        logger.info("所有任务状态一致，无需同步")
                        
                except Exception as e:
                    logger.error(f"扫描不一致状态任务失败: {str(e)}")

            # 启动异步恢复线程
            recovery_thread = Thread(target=_recover_tasks_async, daemon=True)
            recovery_thread.start()
            
            self._recovery_initialized = True
            logger.info("恢复功能初始化完成")

    def _clear_queue(self):
        """清理队列，避免重复处理已完成或失败的任务"""
        try:
            if self.is_redis_available:
                queue_len = self.redis.llen('comfyui_queue')
                if queue_len > 0:
                    logger.warning(f"清理 Redis 中的 {queue_len} 个待处理任务")
                    self.redis.delete('comfyui_queue')
            self.local_queue = Queue()  # 清理本地队列
            logger.info("队列清理完成")
        except Exception as e:
            logger.error(f"清理队列失败: {str(e)}")

    def set_consumer(self, consumer):
        """设置任务消费者"""
        if not consumer:
            raise ValueError("Consumer不能为空")
        self.consumer = consumer
        logger.info("Consumer已设置")

    def _check_redis_connection(self):
        """检查 Redis 连接是否可用"""
        try:
            self.redis.ping()
            self.is_redis_available = True
        except redis.ConnectionError:
            logger.warning("Redis 连接不可用，将使用本地内存队列")
            self.is_redis_available = False

    def add_task(self, task_id: str, task_type: str, task_data: Dict) -> str:
        """
        添加任务到队列
        :param task_id: 任务ID
        :param task_type: 任务类型
        :param task_data: 任务数据
        :return: 任务ID
        """
        try:
            # 1. 首先检查Redis中任务的状态（优先，因为更快）
            redis_status = None
            if self.is_redis_available:
                try:
                    redis_status_data = self.redis.hget('comfyui_task_status', task_id)
                    if redis_status_data:
                        redis_status = json.loads(redis_status_data)
                        redis_task_status = redis_status.get('status')
                        
                        # 处理特殊状态 - 如果是processing_completed，自动转为completed
                        if redis_task_status == 'processing_completed':
                            logger.info(f"Redis中任务 {task_id} 状态为processing_completed，自动转为completed")
                            redis_task_status = 'completed'
                            # 马上更新Redis和MySQL状态
                            self._update_task_status(
                                task_id, 
                                'completed',
                                completed_at=timezone.now() if 'completed_at' not in redis_status else redis_status['completed_at'],
                                output_data=redis_status.get('output_data'),
                                force_mysql_update=True
                            )
                        
                        if redis_task_status in ['completed', 'failed', 'cancelled']:
                            logger.warning(f"Redis中任务 {task_id} 状态为 {redis_task_status}，不再添加到队列")
                            return task_id
                except Exception as e:
                    logger.error(f"检查Redis任务状态失败: {str(e)}")
            
            # 2. 检查数据库中任务的状态
            db_task = None
            try:
                db_task = ComfyUITask.objects.filter(task_id=task_id).first()
                if db_task and db_task.status in ['completed', 'failed', 'cancelled']:
                    logger.warning(f"数据库中任务 {task_id} 状态为 {db_task.status}，不再添加到队列")
                    return task_id
            except Exception as e:
                logger.error(f"检查数据库任务状态失败: {str(e)}")
            
            # 3. 同步状态，优先使用Redis中的终态
            if redis_status and redis_status.get('status') in ['completed', 'failed', 'cancelled'] and db_task.status != redis_status.get('status'):
                logger.warning(f"同步Redis终态状态 {redis_status.get('status')} 到MySQL (任务 {task_id}，原状态: {db_task.status})")
                db_task.status = redis_status.get('status')
                if 'completed_at' in redis_status and redis_status['completed_at']:
                    try:
                        db_task.completed_at = datetime.fromisoformat(redis_status['completed_at'])
                    except:
                        db_task.completed_at = timezone.now()
                elif not db_task.completed_at and redis_status.get('status') in ['completed', 'failed', 'cancelled']:
                    db_task.completed_at = timezone.now()
                
                if 'output_data' in redis_status and redis_status['output_data']:
                    db_task.output_data = redis_status['output_data']
                    
                db_task.save()
                return task_id
            
            # 4. 检查任务是否已在队列中
            if self._is_task_in_queue(task_id):
                logger.warning(f"任务 {task_id} 已存在于队列中，不再添加")
                return task_id

            # 5. 如果数据库中有任务，但状态不是终态，更新为pending
            if db_task and db_task.status not in ['completed', 'failed', 'cancelled']:
                if db_task.status != 'pending':
                    logger.info(f"重置任务 {task_id} 状态为pending (原状态: {db_task.status})")
                    db_task.status = 'pending'
                    db_task.save(update_fields=['status'])
                    
                    # 同步到Redis
                    if self.is_redis_available:
                        status_data = {
                            'task_id': task_id,
                            'status': 'pending',
                            'timestamp': time.time(),
                            'from_source': 'mysql_sync'
                        }
                        self.redis.hset('comfyui_task_status', task_id, json.dumps(status_data))

            # 6. 创建任务对象并添加到队列
            task = {
                'task_id': task_id,
                'type': task_type,
                'data': task_data
            }

            # 使用事务，确保先完成数据库提交再添加到队列
            def add_to_queue():
                # 添加到队列
                if self.is_redis_available:
                    self.redis.rpush('comfyui_queue', json.dumps(task))
                    # 更新任务状态
                    status_data = {
                        'task_id': task_id,
                        'status': 'pending',
                        'timestamp': time.time(),
                        'from_source': 'add_task'
                    }
                    self.redis.hset('comfyui_task_status', task_id, json.dumps(status_data))
                else:
                    self.local_queue.put(task)
                logger.info(f"任务 {task_id} 已加入队列")
            
            # 检查是否在事务中，如果是则使用on_commit，否则直接添加
            if transaction.get_connection().in_atomic_block:
                transaction.on_commit(add_to_queue)
                logger.info(f"任务 {task_id} 将在事务提交后加入队列")
            else:
                add_to_queue()

            return task_id

        except Exception as e:
            logger.error(f"添加任务到队列失败: {str(e)}")
            raise

    def _is_task_in_queue(self, task_id: str) -> bool:
        """检查任务是否已在队列中"""
        try:
            if self.is_redis_available:
                # 检查Redis队列
                queue_len = self.redis.llen('comfyui_queue')
                if queue_len > 0:
                    for i in range(queue_len):
                        queue_item = self.redis.lindex('comfyui_queue', i)
                        if queue_item:
                            try:
                                queue_task = json.loads(queue_item)
                                if queue_task.get('task_id') == task_id:
                                    return True
                            except:
                                pass
            else:
                # 检查本地队列
                for queue_task in list(self.local_queue.queue):
                    if queue_task.get('task_id') == task_id:
                        return True
            return False
        except Exception as e:
            logger.error(f"检查任务是否在队列中失败: {str(e)}")
            return False

    def _consume_tasks(self):
        """消费者线程，处理队列中的任务"""
        logger.info("消费者线程已启动，开始监听队列...")
        idle_count = 0
        while self.running:
            task = None  # 关键修复：预定义变量
            task_id = "未知"  # 默认任务ID
            try:
                # 检查活跃任务数量
                with self.lock:
                    active_tasks_count = len(self.active_tasks)
                
                if active_tasks_count > 0:
                    # 如果有任务正在处理，适度降低轮询频率
                    wait_timeout = 1
                    if idle_count > 0:
                        idle_count = 0  # 重置空闲计数
                else:
                    # 没有任务处理时，使用较短的轮询间隔以提高响应速度
                    wait_timeout = 0.1
                    idle_count += 1
                    # 每隔30次空闲轮询（约3秒）记录一次日志
                    if idle_count % 30 == 0:
                        queue_size = self.get_queue_size()
                        logger.info(f"消费者线程空闲中 ({idle_count} 轮询), 队列大小: {queue_size}")
                
                if self.is_redis_available:
                    # 从 Redis 获取任务，使用动态超时时间
                    if idle_count % 30 == 0:
                        logger.info(f"准备从Redis队列获取任务，超时时间: {int(wait_timeout)}秒")
                    task_data = self.redis.blpop('comfyui_queue', timeout=int(wait_timeout))
                    if task_data:
                        logger.info(f"成功从Redis队列获取到任务数据: {task_data[1][:100]}...")
                        task = json.loads(task_data[1])
                    else:
                        if idle_count % 30 == 0:
                            logger.info("Redis队列中没有任务，继续等待...")
                else:
                    try:
                        if idle_count % 30 == 0:
                            logger.info(f"准备从本地队列获取任务，超时时间: {wait_timeout}秒")
                        task = self.local_queue.get(timeout=wait_timeout)
                        logger.info(f"成功从本地队列获取到任务")
                    except queue.Empty:
                        if idle_count % 30 == 0:
                            logger.info("本地队列中没有任务，继续等待...")
                        task = None

                if not task:
                    # 没有任务时，不要过度占用CPU
                    if active_tasks_count == 0:
                        # 如果没有活跃任务，使用更短的睡眠时间提高响应速度
                        time.sleep(0.05)
                        
                        # 定期检查队列大小，如果队列中有任务但没有活跃任务处理，尝试主动触发
                        if idle_count % 10 == 0:  # 大约每0.5秒检查一次
                            queue_size = self.get_queue_size()
                            if queue_size > 0:
                                logger.info(f"发现队列中有 {queue_size} 个任务等待但无活跃任务处理，尝试主动触发")
                                self._trigger_task_processing()
                    else:
                        time.sleep(0.1)
                    continue
                    
                task_id = task.get('task_id', '未知')
                logger.info(f"从队列中获取到任务: {task_id}")

                if 'task_id' not in task:
                    raise ValueError("任务缺少task_id字段")

                self._process_task(task)

            except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
                logger.warning("Redis异常，切换本地队列模式")
                self.is_redis_available = False
            except json.JSONDecodeError as e:
                logger.error(f"无效的任务数据: {str(e)}")
            except Exception as e:
                logger.error(f"处理任务异常（ID: {task_id}）: {str(e)}", exc_info=True)
                time.sleep(1)

    def _process_task(self, task: Dict):
        """处理单个任务"""
        task_id = task.get('task_id')
        if not task_id:
            logger.error("任务缺少task_id字段")
            return
            
        # 添加任务进入处理流程的时间戳，如果没有的话
        if 'enter_queue_time' not in task:
            task['enter_queue_time'] = time.time()
            
        # 检查任务是否在队列中等待过长时间（例如超过15分钟）
        current_time = time.time()
        wait_time = current_time - task.get('enter_queue_time', current_time)
        force_process = False
        
        if wait_time > 1800:  # 15分钟
            logger.warning(f"任务 {task_id} 在队列中等待超过15分钟 ({wait_time:.0f}秒)，尝试强制处理")
            force_process = True

        logger.info(f"开始处理任务 {task_id}，检查consumer...")
        
        try:
            # 1. 检查Redis中的任务状态
            if self.is_redis_available:
                try:
                    redis_status_data = self.redis.hget('comfyui_task_status', task_id)
                    if redis_status_data:
                        redis_status = json.loads(redis_status_data)
                        if redis_status.get('status') in ['completed', 'failed', 'cancelled']:
                            logger.warning(f"Redis中任务 {task_id} 状态为 {redis_status.get('status')}，跳过处理")
                            return
                except Exception as e:
                    logger.error(f"检查Redis任务状态失败 {task_id}: {str(e)}")
                    
            # 2. 然后再检查数据库中的状态（可能更新了但没同步到Redis）
            db_task = None
            max_retries = 3
            retry_wait = 0.2
            
            for retry in range(max_retries):
                try:
                    db_task = ComfyUITask.objects.filter(task_id=task_id).first()
                    if db_task:
                        if db_task.status in ['completed', 'failed', 'cancelled']:
                            logger.warning(f"数据库中任务 {task_id} 状态为 {db_task.status}，跳过处理")
                            return
                        break
                    elif retry < max_retries - 1:
                        # 如果没找到且不是最后一次重试，等待后再试
                        logger.warning(f"数据库中未找到任务 {task_id}，等待 {retry_wait} 秒后重试 ({retry+1}/{max_retries})")
                        time.sleep(retry_wait)
                        retry_wait *= 2  # 指数退避
                except Exception as e:
                    logger.error(f"检查数据库任务状态失败 {task_id}: {str(e)}")
                    if retry < max_retries - 1:
                        time.sleep(retry_wait)
                        retry_wait *= 2
            
            # 如果经过重试后仍未找到任务，但我们仍有任务数据
            if not db_task:
                # 记录详细日志，但继续处理，因为任务异步处理将自行处理这种情况
                logger.warning(f"经过 {max_retries} 次重试后，数据库中仍未找到任务 {task_id}，继续下一步处理")

            # 检查consumer是否已设置
            if not self.consumer:
                logger.error("Consumer未设置，无法处理任务，请检查应用初始化过程")
                self._update_task_status(
                    task_id,
                    'failed',
                    error_message="Consumer未设置，无法处理任务",
                    completed_at=timezone.now()
                )
                return
            
            logger.info(f"Consumer已设置: {type(self.consumer).__name__}")

            # 检查是否已有任务在处理中
            with self.lock:
                active_tasks = list(self.active_tasks.keys())
                if task_id in active_tasks:
                    logger.warning(f"任务 {task_id} 已经在处理中，跳过重复处理")
                    return
                    
                if active_tasks and not force_process:
                    logger.warning(f"已有 {len(active_tasks)} 个任务在处理中: {active_tasks}，任务 {task_id} 将等待")
                    
                    # 检查该任务是否已在队列中
                    already_in_queue = False
                    if self.is_redis_available:
                        # 检查队列中是否已经有该任务
                        queue_size = self.redis.llen('comfyui_queue')
                        for i in range(queue_size):
                            queue_item = self.redis.lindex('comfyui_queue', i)
                            if queue_item:
                                queue_task = json.loads(queue_item)
                                if queue_task.get('task_id') == task_id:
                                    already_in_queue = True
                                    logger.info(f"任务 {task_id} 已在队列中，无需重新加入")
                                    break
                    
                    # 如果任务不在队列中，将其放回队列
                    if not already_in_queue:
                        task_item = {
                            'task_id': task_id,
                            'type': task.get('type'),
                            'data': task.get('data'),
                            'status': 'pending',
                            'enter_queue_time': task.get('enter_queue_time', time.time())  # 保留原始进入队列时间
                        }
                        if self.is_redis_available:
                            # 对于长时间等待的任务，放到队列头部，优先处理
                            if wait_time > 600:  # 10分钟以上
                                self.redis.lpush('comfyui_queue', json.dumps(task_item))  # 放到队列头部
                                logger.info(f"已将长时间等待的任务 {task_id} 放入队列头部，等待优先处理")
                            else:
                                self.redis.rpush('comfyui_queue', json.dumps(task_item))  # 放到队列尾部
                                logger.info(f"已将任务 {task_id} 放入队列尾部，等待后续处理")
                        else:
                            self.local_queue.put(task_item)
                    return
                
                # 如果是强制处理，发出警告日志
                if force_process and active_tasks:
                    logger.warning(f"任务 {task_id} 等待时间过长 ({wait_time:.0f}秒)，强制处理，当前活跃任务: {active_tasks}")
                else:
                    logger.info(f"队列状态检查完成，没有其他任务在处理中，开始处理任务 {task_id}")

                # 创建停止事件
                stop_event = Event()
                self.active_tasks[task_id] = stop_event

                # 更新任务状态为处理中
                self._update_task_status(
                    task_id, 
                    'processing',
                    started_at=timezone.now()
                )
                logger.info(f"任务 {task_id} 已进入处理阶段")

                # 立即处理任务
                try:
                    # 确保任务数据完整
                    if not task.get('data'):
                        if db_task and db_task.input_data:
                            task['data'] = db_task.input_data
                        else:
                            logger.warning(f"任务 {task_id} 缺少数据，且数据库中也没有对应数据")
                            
                    if not task.get('type'):
                        if db_task and db_task.task_type:
                            task['type'] = db_task.task_type
                        else:
                            logger.warning(f"任务 {task_id} 缺少类型，且数据库中也没有对应数据")
                        
                    logger.info(f"开始执行任务 {task_id} 的处理逻辑，准备调用consumer.process_task")
                    
                    # 打印consumer信息和任务数据摘要，帮助诊断
                    consumer_info = f"Consumer类型: {type(self.consumer).__name__}"
                    task_info = f"任务类型: {task.get('type')}, 数据大小: {len(str(task.get('data'))) if task.get('data') else 'None'}"
                    logger.info(f"处理任务 {task_id} - {consumer_info} - {task_info}")
                    
                    # 实际调用consumer处理任务
                    result = self.consumer.process_task(task, stop_event)
                    if result:
                        logger.info(f"任务 {task_id} 处理完成: {result.get('status')}")
                except Exception as e:
                    logger.error(f"处理任务 {task_id} 时发生错误: {str(e)}", exc_info=True)
                    self._update_task_status(
                        task_id,
                        'failed',
                        error_message=f"处理任务时发生错误: {str(e)}",
                        completed_at=timezone.now()
                    )
                finally:
                    # 清理任务状态
                    with self.lock:
                        if task_id in self.active_tasks:
                            del self.active_tasks[task_id]
                    logger.info(f"任务 {task_id} 处理完成，已从活跃任务列表中移除")

        except Exception as e:
            logger.error(f"处理任务 {task_id} 时发生错误: {str(e)}", exc_info=True)

    def cancel_task(self, task_id: str) -> bool:
        """取消正在执行的任务"""
        with self.lock:
            if task_id in self.active_tasks:
                self.active_tasks[task_id].set()
                logger.info(f"已发送中断信号给任务 {task_id}")
                return True
            return False

    def _update_task_status(self, task_id: str, status: str, force_redis_update=True, **kwargs):
        """
        更新任务状态 - 优先更新Redis，异步更新MySQL
        :param task_id: 任务ID
        :param status: 新状态
        :param force_redis_update: 是否强制更新Redis，默认为True
        :param kwargs: 其他需要更新的字段
        """
        try:
            # 1. 获取任务对象
            task = ComfyUITask.objects.get(task_id=task_id)
            
            # 2. 更新Redis中的任务状态
            if force_redis_update:
                # 构建Redis状态数据
                redis_data = {
                    'task_id': task_id,
                    'status': status,
                    'timestamp': time.time(),
                    'from_source': 'redis',
                    'input_data': task.input_data,  # 添加input_data
                }
                
                # 如果任务完成或失败，确保更新processing_time
                if status in ['completed', 'processing_completed', 'failed']:
                    # 优先使用传入的processing_time
                    if 'processing_time' in kwargs:
                        redis_data['processing_time'] = float(kwargs['processing_time'])
                        # 同时更新数据库中的processing_time
                        task.processing_time = float(kwargs['processing_time'])
                        task.save(update_fields=['processing_time'])
                    elif task.processing_time:
                        redis_data['processing_time'] = float(task.processing_time)
                
                # 添加其他字段，处理datetime对象
                for key, value in kwargs.items():
                    if key not in ['force_redis_update', 'force_mysql_update']:
                        if isinstance(value, datetime):
                            redis_data[key] = value.isoformat()
                        else:
                            redis_data[key] = value
                
                # 保存到Redis - 使用统一的key格式
                self.redis.hset('comfyui_task_status', task_id, json.dumps(redis_data))
                logger.info(f"已更新Redis中任务 {task_id} 的状态为: {status}")
            
            # 3. 更新MySQL中的任务状态
            if not force_redis_update:
                try:
                    # 构建MySQL状态数据
                    mysql_data = {
                        'status': status,
                        'input_data': task.input_data,  # 添加input_data
                    }
                    
                    # 如果任务完成或失败，确保更新processing_time
                    if status in ['completed', 'processing_completed', 'failed']:
                        # 优先使用传入的processing_time
                        if 'processing_time' in kwargs:
                            mysql_data['processing_time'] = float(kwargs['processing_time'])
                        elif task.processing_time:
                            mysql_data['processing_time'] = float(task.processing_time)
                    
                    # 添加其他字段
                    for key, value in kwargs.items():
                        if key not in ['force_redis_update', 'force_mysql_update']:
                            mysql_data[key] = value
                    
                    # 更新MySQL中的任务状态
                    ComfyUITask.objects.filter(task_id=task_id).update(**mysql_data)
                    logger.info(f"已更新MySQL中任务 {task_id} 的状态为: {status}")
                except Exception as e:
                    logger.error(f"更新MySQL状态失败: {str(e)}")
                    
        except Exception as e:
            logger.error(f"更新任务状态失败: {str(e)}")
            return False

    def _trigger_task_processing(self):
        """
        触发任务处理机制
        当队列中有任务但没有活跃任务时，主动触发处理
        """
        try:
            if not self.consumer:
                logger.warning("Consumer未设置，无法触发任务处理")
                return

            with self.lock:
                active_tasks = list(self.active_tasks.keys())
                if active_tasks:
                    logger.info(f"当前已有 {len(active_tasks)} 个活跃任务，无需触发处理")
                    return

                # 检查队列中是否有任务
                queue_size = self.get_queue_size()
                if queue_size > 0:
                    logger.info(f"队列中有 {queue_size} 个任务等待处理，开始触发处理机制")
                    
                    # 如果消费者线程未启动，启动它
                    if not self.consumer_thread or not self.consumer_thread.is_alive():
                        self.consumer_thread = Thread(target=self._consume_tasks, daemon=True)
                        self.consumer_thread.start()
                        logger.info("已启动消费者线程")
                    else:
                        logger.info("消费者线程已在运行中")
                        
                    # 尝试直接从队列中获取并处理一个任务，而不是等待消费者线程
                    try:
                        if self.is_redis_available:
                            # 直接获取一个任务
                            task_data = self.redis.lpop('comfyui_queue')
                            if task_data:
                                task = json.loads(task_data)
                                task_id = task.get('task_id', '未知')
                                logger.info(f"_trigger_task_processing 直接处理队列中的任务: {task_id}")
                                # 启动一个新线程来处理任务，避免阻塞当前方法
                                Thread(
                                    target=self._process_task,
                                    args=(task,),
                                    daemon=True
                                ).start()
                    except Exception as e:
                        logger.error(f"尝试直接处理队列中的任务失败: {str(e)}")
                        # 如果失败，不影响正常的消费者线程处理
                else:
                    logger.info("队列为空，无需触发处理")
        except Exception as e:
            logger.error(f"触发任务处理机制失败: {str(e)}")

    def _direct_process_by_id(self, task_id: str):
        """
        直接处理指定ID的任务
        :param task_id: 任务ID
        """
        try:
            # 首先检查任务是否已经在处理中
            with self.lock:
                if task_id in self.active_tasks:
                    logger.warning(f"任务 {task_id} 已经在处理中，跳过重复处理")
                    return

            # 从Redis获取任务数据
            if self.is_redis_available:
                # 遍历队列找到对应任务
                queue_len = self.redis.llen('comfyui_queue')
                for i in range(queue_len):
                    task_data = self.redis.lindex('comfyui_queue', i)
                    if task_data:
                        task = json.loads(task_data)
                        if task.get('task_id') == task_id:
                            # 找到任务后，从队列中移除
                            self.redis.lrem('comfyui_queue', 0, task_data)
                            # 直接处理任务
                            self._process_task(task)
                            return
            else:
                # 从本地队列中查找任务
                for _ in range(self.local_queue.qsize()):
                    task = self.local_queue.get()
                    if task.get('task_id') == task_id:
                        # 直接处理任务
                        self._process_task(task)
                        return
                    else:
                        # 不是目标任务，放回队列
                        self.local_queue.put(task)
            
            logger.warning(f"未找到任务 {task_id} 的数据")
        except Exception as e:
            logger.error(f"直接处理任务 {task_id} 失败: {str(e)}")
            # 如果处理失败，确保任务状态被正确更新
            self._update_task_status(
                task_id,
                'failed',
                error_message=f"直接处理任务失败: {str(e)}",
                completed_at=timezone.now()
            )

    def start_consumer(self):
        """启动消费者线程（在应用完全初始化后调用）"""
        try:
            if self.consumer_thread is None or not self.consumer_thread.is_alive():
                logger.info("启动消费者线程")
                self.consumer_thread = Thread(target=self._consume_tasks, daemon=True)
                self.consumer_thread.start()
                logger.info("消费者线程已启动")
                
                # 额外检查：启动后确认线程是否真的在运行
                time.sleep(0.2)  # 等待一小段时间让线程启动
                if not self.consumer_thread.is_alive():
                    logger.error("消费者线程启动失败！")
                    # 尝试再次启动
                    self.consumer_thread = Thread(target=self._consume_tasks, daemon=True)
                    self.consumer_thread.start()
                    logger.info("已重新尝试启动消费者线程")
            else:
                logger.info("消费者线程已在运行中")
                
            # 检查consumer是否设置
            if self.consumer is None:
                logger.error("警告：consumer未设置，虽然消费者线程已启动，但无法处理任务")
            else:
                logger.info(f"消费者类型: {type(self.consumer).__name__}")
                
            # 额外触发一次任务处理
            self._trigger_task_processing()
            
            return True
        except Exception as e:
            logger.error(f"启动消费者线程失败: {str(e)}", exc_info=True)
            return False

    def _direct_process_recovered_task(self, task_item: Dict):
        """
        直接处理恢复的任务，不经过队列
        :param task_item: 任务数据
        """
        task_id = task_item.get('task_id')
        if not task_id:
            logger.error("恢复的任务缺少task_id字段")
            return False
            
        logger.info(f"正在直接处理恢复的任务: {task_id}")
        
        try:
            # 检查consumer是否已设置
            if not self.consumer:
                logger.error(f"Consumer未设置，无法处理恢复的任务 {task_id}")
                self._update_task_status(
                    task_id,
                    'failed',
                    error_message="Consumer未设置，无法处理任务",
                    completed_at=timezone.now()
                )
                return False
                
            consumer_name = type(self.consumer).__name__    
            logger.info(f"Consumer已设置: {consumer_name}，开始执行直接处理流程")
            
            # 检查和补充任务数据
            try:
                db_task = ComfyUITask.objects.get(task_id=task_id)
                # 如果需要，从数据库补充任务数据
                if not task_item.get('data'):
                    task_item['data'] = db_task.input_data
                if not task_item.get('type'):
                    task_item['type'] = db_task.task_type
                logger.info(f"已补充任务数据，类型: {task_item.get('type')}")
            except Exception as e:
                logger.error(f"补充任务数据失败: {str(e)}")
            
            logger.info(f"开始处理恢复的任务 {task_id}")
            
            # 创建停止事件
            stop_event = Event()
            
            # 将任务添加到活跃任务列表
            with self.lock:
                self.active_tasks[task_id] = stop_event
                logger.info(f"已将任务 {task_id} 添加到活跃任务列表，当前活跃任务: {list(self.active_tasks.keys())}")
            
            # 更新任务状态为处理中
            self._update_task_status(
                task_id, 
                'processing',
                started_at=timezone.now()
            )
            logger.info(f"已更新任务 {task_id} 状态为processing，准备调用consumer处理")
            
            # 直接调用consumer处理任务 - 关键改进：不在锁内调用，避免长时间阻塞
            logger.info(f"开始调用{consumer_name}.process_task({task_id})...")
            
            try:
                # 直接调用处理逻辑
                result = self.consumer.process_task(task_item, stop_event)
                logger.info(f"处理完成，结果: {result}")
                
                # 更新任务状态标记为处理完成 - 这个逻辑正常应该在consumer中处理
                # 但为确保状态更新，这里再次调用
                if result and result.get('status') == 'success':
                    self._update_task_status(
                        task_id,
                        'completed',
                        completed_at=timezone.now()
                    )
                    logger.info(f"恢复的任务 {task_id} 已成功处理并标记为完成")
                return True
            except Exception as e:
                logger.error(f"处理恢复的任务 {task_id} 时发生错误: {str(e)}", exc_info=True)
                self._update_task_status(
                    task_id,
                    'failed',
                    error_message=f"处理任务时发生错误: {str(e)}",
                    completed_at=timezone.now()
                )
                return False
            finally:
                # 清理活跃任务状态
                with self.lock:
                    if task_id in self.active_tasks:
                        del self.active_tasks[task_id]
                    logger.info(f"已从活跃任务列表中移除任务 {task_id}")
        
        except Exception as e:
            logger.error(f"直接处理恢复的任务 {task_id} 失败: {str(e)}", exc_info=True)
            
            # 确保任务状态被更新
            try:
                self._update_task_status(
                    task_id,
                    'failed',
                    error_message=f"处理恢复的任务时出错: {str(e)}",
                    completed_at=timezone.now()
                )
            except Exception as update_error:
                logger.error(f"更新任务状态失败: {str(update_error)}")
                
            # 清理活跃任务状态
            with self.lock:
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
            
            return False

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        从Redis获取任务状态
        :param task_id: 任务ID
        :return: 任务状态信息字典，如果不存在则返回None
        """
        try:
            if not self.is_redis_available:
                logger.warning(f"Redis不可用，无法获取任务 {task_id} 的状态")
                return None

            # 从Redis获取任务状态
            status_key = f"task_status:{task_id}"
            status_data = self.redis.get(status_key)
            
            if not status_data:
                logger.info(f"Redis中不存在任务 {task_id} 的状态")
                return None

            # 解析状态数据
            try:
                status_info = json.loads(status_data)
                logger.info(f"从Redis获取到任务 {task_id} 的状态: {status_info.get('status')}")
                return status_info
            except json.JSONDecodeError as e:
                logger.error(f"解析任务 {task_id} 的状态数据失败: {str(e)}")
                return None

        except Exception as e:
            logger.error(f"获取任务 {task_id} 状态失败: {str(e)}")
            return None