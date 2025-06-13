import logging
import os
import json
import time
import uuid
import threading
import requests
import traceback
from io import BytesIO
from typing import Dict, List
from threading import Event, Thread
from datetime import datetime
import urllib.parse
import redis

from django.conf import settings
from django.utils import timezone

from common.volcengine_tos_utils import VolcengineTOSUtils
from templateImage.models import ComfyUITask, SysUser, ImageUploadRecord
from templateImage.workflowUtils import ComfyUIHelper
from templateImage.task_utils import TaskUtils, queue_service


class ComfyUIConsumer:
    def __init__(self, comfyui_url: str, workflow_file: str, output_dir: str):
        """
        初始化ComfyUI消费者
        :param comfyui_url: ComfyUI服务器地址（默认值，可被任务特定值覆盖）
        :param workflow_file: 工作流文件路径
        :param output_dir: 输出目录
        """
        # 设置日志记录器
        self.logger = logging.getLogger('ComfyUIConsumer')
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

        self.default_comfyui_url = comfyui_url
        self.workflow_file = workflow_file
        self.output_dir = output_dir
        self.helper = None  # 初始化为None，将在处理任务时创建
        self.helper_cache = {}  # 工作流帮助类缓存
        self.active_helpers = {}  # 当前活跃的helper实例
        self.processing_tasks = set()  # 当前正在处理的任务ID集合
        self.task_heartbeat_intervals = {}  # 存储每个任务的心跳间隔
        self.last_response_time = time.time()  # 添加最后响应时间

        # 初始化Redis客户端
        try:
            # 获取Redis配置，使用默认值
            redis_host = getattr(settings, 'REDIS_HOST', 'localhost')
            redis_port = getattr(settings, 'REDIS_PORT', 6379)
            redis_db = getattr(settings, 'REDIS_DB', 0)
            redis_password = getattr(settings, 'REDIS_PASSWORD', None)

            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True
            )
            # 测试连接
            self.redis_client.ping()
            self.logger.info(f"Redis客户端初始化成功 (host={redis_host}, port={redis_port}, db={redis_db})")
        except Exception as e:
            self.logger.error(f"Redis客户端初始化失败: {str(e)}")
            self.logger.warning("将使用内存缓存模式运行，任务状态可能无法持久化")
            self.redis_client = None

        # 确保默认工作流文件存在
        self._ensure_default_workflow_file()
        
        # 初始化TOS工具
        self.tos_utils = VolcengineTOSUtils()
        
        # 最后设置consumer
        queue_service.set_consumer(self)
        self.logger.info("ComfyUIConsumer初始化完成")

    def _ensure_default_workflow_file(self):
        """确保默认工作流文件存在，如果不存在则创建"""
        try:
            workflow_file_path = self.workflow_file
            if not os.path.isabs(workflow_file_path):
                # 如果是相对路径，相对于项目根目录解析
                workflow_file_path = os.path.join(settings.BASE_DIR, workflow_file_path)
                
            # 确保目录存在
            workflow_dir = os.path.dirname(workflow_file_path)
            os.makedirs(workflow_dir, exist_ok=True)
            
            if not os.path.exists(workflow_file_path):
                self.logger.warning(f"默认工作流文件不存在，正在创建: {workflow_file_path}")
                
                # 创建一个简单的默认工作流
                default_workflow = {
                    "3": {
                        "inputs": {
                            "width": 512,
                            "height": 512,
                            "batch_size": 1
                        },
                        "class_type": "EmptyLatentImage"
                    },
                    "4": {
                        "inputs": {
                            "text": "a photo of a cat",
                            "clip": ["5", 0]
                        },
                        "class_type": "CLIPTextEncode"
                    },
                    "5": {
                        "inputs": {
                            "stop_at_clip_layer": -1,
                            "clip_name": "clip_vit_b_32"
                        },
                        "class_type": "CLIPLoader"
                    },
                    "6": {
                        "inputs": {
                            "model_name": "v1-5-pruned-emaonly.safetensors",
                            "subfolder": "sd/v1"
                        },
                        "class_type": "CheckpointLoader"
                    },
                    "7": {
                        "inputs": {
                            "seed": 123456789,
                            "steps": 20,
                            "cfg": 7.5,
                            "sampler_name": "euler",
                            "scheduler": "normal",
                            "denoise": 1.0,
                            "model": ["6", 0],
                            "positive": ["4", 0],
                            "negative": ["8", 0],
                            "latent_image": ["3", 0]
                        },
                        "class_type": "KSampler"
                    },
                    "8": {
                        "inputs": {
                            "text": "text, watermark",
                            "clip": ["5", 0]
                        },
                        "class_type": "CLIPTextEncode"
                    },
                    "9": {
                        "inputs": {
                            "samples": ["7", 0],
                            "vae": ["6", 2]
                        },
                        "class_type": "VAEDecode"
                    },
                    "10": {
                        "inputs": {
                            "filename_prefix": "ComfyUI",
                            "images": ["9", 0]
                        },
                        "class_type": "SaveImage"
                    }
                }
                
                # 写入文件
                with open(workflow_file_path, 'w') as f:
                    json.dump(default_workflow, f, indent=4)
                
                self.logger.info(f"已创建默认工作流文件: {workflow_file_path}")
            else:
                self.logger.info(f"默认工作流文件已存在: {workflow_file_path}")
                
        except Exception as e:
            self.logger.error(f"确保默认工作流文件存在时出错: {str(e)}")
            self.logger.error(traceback.format_exc())

    def _get_helper(self, task_data: Dict) -> ComfyUIHelper:
        """获取或创建 ComfyUIHelper 实例，使用任务特定的服务器信息"""
        # 从任务数据中获取服务器信息
        server_address = task_data.get('server_address', self.default_comfyui_url)
        username = task_data.get('username')
        password = task_data.get('password')
        workflow_file = task_data.get('workflow_file', self.workflow_file)

        self.logger.info(f"[DEBUG] _get_helper: server_address={server_address}, workflow_file={workflow_file}")
        self.logger.info(f"[DEBUG] 任务数据包含的键: {list(task_data.keys())}")
        
        # 创建缓存键
        cache_key = f"{server_address}:{workflow_file}"

        if cache_key not in self.helper_cache:
            self.logger.info(f"[DEBUG] 未找到缓存的helper (cache_key={cache_key})，创建新实例")
            try:
                helper = ComfyUIHelper(
                    server_address=server_address,
                    workflow_file=workflow_file,
                    username=username,
                    password=password
                )
                self.helper_cache[cache_key] = helper
                self.logger.info(f"[DEBUG] ComfyUIHelper实例创建成功: {helper}")
                return helper
            except Exception as e:
                self.logger.error(f"[DEBUG] 创建ComfyUIHelper实例失败: {str(e)}")
                self.logger.error(f"[DEBUG] 异常详情: {traceback.format_exc()}")
                raise
        else:
            self.logger.info(f"[DEBUG] 使用缓存的helper实例 (cache_key={cache_key})")
            return self.helper_cache[cache_key]

    def _upload_to_oss(self, image_data: bytes) -> str:
        """上传图片到OSS并返回URL"""
        if not isinstance(image_data, bytes):
            self.logger.error(f"上传失败：数据类型错误，期望bytes，实际是{type(image_data)}")
            raise ValueError("上传数据必须是bytes类型")
            
        img_name = f"{uuid.uuid4()}.png"
        try:
            img_size_kb = len(image_data) // 1024
            self.logger.info(f"开始上传图片到OSS: {img_name}, 大小: {img_size_kb}KB")
            img_url = self.tos_utils.upload_image(
                object_name=img_name,
                file_data=image_data
            )
            self.logger.info(f"图片 {img_name} 上传成功，URL: {img_url}")
            return img_url
        except Exception as e:
            self.logger.error(f"图片 {img_name} 上传失败: {str(e)}")
            raise

    def _cleanup_task_resources(self, task_id: str):
        """清理任务相关的所有资源"""
        try:
            # 从活动任务列表中移除
            if task_id in self.active_helpers:
                del self.active_helpers[task_id]
                self.logger.info(f"已从活动任务列表中移除任务 {task_id}")
            
            # 从心跳间隔映射中移除
            if task_id in self.task_heartbeat_intervals:
                del self.task_heartbeat_intervals[task_id]
                self.logger.info(f"已从心跳间隔映射中移除任务 {task_id}")
            
            # 从处理中任务集合中移除
            if task_id in self.processing_tasks:
                self.processing_tasks.remove(task_id)
                self.logger.info(f"已从处理中任务集合中移除任务 {task_id}")
            
            # 确保任务状态为completed
            if self.redis_client:
                # 先检查任务是否已经完成
                current_status = self.redis_client.get(f"task:{task_id}:status")
                if current_status != "completed":
                    self.redis_client.set(f"task:{task_id}:status", "completed")
                    self.logger.info(f"已更新Redis中任务 {task_id} 的状态为: completed")
            else:
                self.logger.error("Redis客户端未初始化，无法更新任务状态")
            
            self.logger.info(f"任务 {task_id} 的所有资源已清理")
        except Exception as e:
            self.logger.error(f"清理任务资源时出错: {str(e)}")

    def _update_task_status(self, task_id: str, status: str, image_urls: List[str] = None, error_message: str = None, processing_time: float = None):
        """更新任务状态到Redis和MySQL"""
        try:
            # 1. 更新Redis状态
            if self.redis_client:
                try:
                    status_data = {
                        'task_id': task_id,
                        'status': status,
                        'timestamp': time.time(),
                        'from_source': 'consumer'
                    }
                    
                    if image_urls:
                        status_data['image_urls'] = image_urls
                    if error_message:
                        status_data['error_message'] = error_message
                    if processing_time is not None:
                        status_data['processing_time'] = processing_time
                        
                    self.redis_client.hset('comfyui_task_status', task_id, json.dumps(status_data))
                    self.logger.info(f"已更新Redis中任务 {task_id} 的状态为: {status}")
                except Exception as e:
                    self.logger.error(f"更新Redis状态失败: {str(e)}")

            # 2. 同步更新MySQL状态
            try:
                task_obj = ComfyUITask.objects.filter(task_id=task_id).first()
                if task_obj:
                    # 更新ComfyUITask表
                    task_obj.status = status
                    
                    # 更新输出结果
                    if image_urls:
                        output_data = {
                            "image_urls": image_urls
                        }
                        task_obj.output_data = output_data
                        self.logger.info(f"已更新MySQL中任务 {task_id} 的输出结果: {output_data}")
                    
                    # 更新错误信息
                    if error_message:
                        task_obj.error_message = error_message
                        self.logger.info(f"已更新MySQL中任务 {task_id} 的错误信息: {error_message}")
                    
                    # 更新完成时间
                    if status in ['completed', 'failed', 'cancelled']:
                        task_obj.completed_at = timezone.now()
                    
                    # 更新处理时间
                    if processing_time is not None:
                        task_obj.processing_time = processing_time
                        self.logger.info(f"已更新MySQL中任务 {task_id} 的处理时间: {processing_time:.2f}秒")
                    
                    # 保存ComfyUITask更改
                    update_fields = ['status', 'output_data', 'error_message', 'completed_at']
                    if processing_time is not None:
                        update_fields.append('processing_time')
                    task_obj.save(update_fields=update_fields)
                    self.logger.info(f"已更新MySQL中任务 {task_id} 的状态为: {status}")

                    # 更新ImageUploadRecord表
                    try:
                        # 查找关联的ImageUploadRecord记录
                        upload_record = ImageUploadRecord.objects.filter(comfyUI_task=task_obj).first()
                        if upload_record:
                            # 更新状态
                            upload_record.status = status
                            
                            # 更新图片URL
                            if image_urls:
                                # 存储结果图片URL到image_url字段
                                upload_record.image_url = image_urls[0] if image_urls else ''
                                
                                # 获取输入图片列表（从task_obj的input_data中）
                                input_images = []
                                if task_obj.input_data and 'images' in task_obj.input_data:
                                    input_images = task_obj.input_data['images']
                                elif task_obj.input_data and 'image_urls' in task_obj.input_data:
                                    input_images = task_obj.input_data['image_urls']
                                
                                # 将输入图片URL列表转换为逗号分隔的字符串
                                if input_images:
                                    upload_record.image_list = ','.join(input_images)
                                
                                self.logger.info(f"已更新ImageUploadRecord中任务 {task_id} 的图片URL")
                                self.logger.info(f"输入图片列表: {upload_record.image_list}")
                                self.logger.info(f"结果图片URL: {upload_record.image_url}")
                            
                            # 保存更改
                            upload_record.save(update_fields=['status', 'image_url', 'image_list'])
                    except Exception as e:
                        self.logger.error(f"更新ImageUploadRecord失败: {str(e)}")
            except Exception as e:
                self.logger.error(f"更新MySQL状态失败: {str(e)}")
                raise
        except Exception as e:
            self.logger.error(f"更新任务状态失败: {str(e)}")
            raise

    def _sync_task_status(self, task_id: str) -> bool:
        """同步任务状态"""
        try:
            if not self.redis_client:
                self.logger.error("Redis客户端未初始化，无法同步任务状态")
                return False

            task_obj = ComfyUITask.objects.filter(task_id=task_id).first()
            if not task_obj:
                self.logger.warning(f"任务 {task_id} 在MySQL中不存在")
                return False

            # 获取Redis中的当前状态和输出
            redis_status = self.redis_client.get(f"task:{task_id}:status")
            redis_output = self.redis_client.get(f"task:{task_id}:output")
            
            # 如果MySQL中的状态是终态（completed/failed/cancelled）
            if task_obj.status in ['completed', 'failed', 'cancelled']:
                # 确保Redis中的状态与MySQL一致
                if redis_status != task_obj.status:
                    self.redis_client.set(f"task:{task_id}:status", task_obj.status)
                    self.logger.info(f"已同步MySQL状态到Redis: {task_obj.status}")
                
                # 同步输出结果
                if task_obj.output_data and not redis_output:
                    self.redis_client.set(f"task:{task_id}:output", task_obj.output_data)
                    self.logger.info(f"已同步MySQL输出到Redis: {task_obj.output_data}")
                
                self._cleanup_task_resources(task_id)
                return True
            # 如果Redis中的状态是终态，但MySQL中不是
            elif redis_status in ['completed', 'failed', 'cancelled']:
                # 更新MySQL中的状态和输出
                task_obj.status = redis_status
                if redis_output:
                    task_obj.output_data = redis_output
                task_obj.completed_at = timezone.now()
                task_obj.save()
                self.logger.info(f"已同步Redis状态和输出到MySQL: {redis_status}")
                self._cleanup_task_resources(task_id)
                return True
            return False
        except Exception as e:
            self.logger.error(f"同步任务 {task_id} 状态时出错: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False

    def update_task_heartbeat_interval(self, task_id: str, interval: int):
        """更新任务的心跳间隔"""
        try:
            self.task_heartbeat_intervals[task_id] = interval
            # 同时更新helper的心跳间隔
            if task_id in self.active_helpers:
                helper = self.active_helpers[task_id]
                if helper:
                    helper.heartbeat_interval = interval
            self.logger.info(f"任务 {task_id} 的心跳间隔已更新为 {interval} 秒")
        except Exception as e:
            self.logger.error(f"更新任务 {task_id} 心跳间隔时出错: {str(e)}")

    def process_task(self, task: Dict, stop_event: Event = None) -> Dict:
        """
        处理任务并返回结果
        :param task: 任务数据
        :param stop_event: 停止事件
        :return: 处理结果
        """
        task_id = task.get('task_id')
        if not task_id:
            self.logger.error("任务缺少task_id字段")
            raise ValueError("任务缺少task_id字段")
            
        # 设置任务处理超时（10分钟）
        MAX_PROCESSING_TIME = 600  
        
        # 初始化任务的心跳间隔
        self.task_heartbeat_intervals[task_id] = 60  # 默认60秒
        
        # 调试信息
        self.logger.info(f"[DEBUG] ComfyUIConsumer开始处理任务 {task_id}")
        self.logger.info(f"[DEBUG] 任务数据: type={task.get('type')}, data_keys={list(task.get('data', {}).keys())}")
        self.logger.info(f"[DEBUG] 任务是否有stop_event: {stop_event is not None}")
        
        # 启动一个监控线程，用于检查任务是否超时
        timeout_monitor_thread = None
        if stop_event:
            timeout_monitor_thread = Thread(target=self._monitor_task, args=(task_id, stop_event), daemon=True)
            timeout_monitor_thread.start()
            self.logger.info(f"已启动任务 {task_id} 超时监控线程")
            
        # 检查任务是否已在处理中
        if task_id in self.processing_tasks:
            self.logger.warning(f"任务 {task_id} 已在处理中，跳过重复处理")
            return {
                'status': 'duplicate',
                'task_id': task_id,
                'error': "任务已在处理中，跳过重复处理"
            }
        
        # 将任务ID添加到处理中集合
        self.processing_tasks.add(task_id)
        self.logger.info(f"[DEBUG] 已将任务 {task_id} 添加到processing_tasks集合，当前大小: {len(self.processing_tasks)}")
        self.logger.info(f"[DEBUG] 当前处理中的任务: {self.processing_tasks}")

        try:
            start_time = time.time()
            self.logger.info(f"开始处理任务 {task_id}")

            # 获取任务数据
            task_data = task.get('data', {})
            
            # 获取或创建helper
            try:
                self.logger.info(f"[DEBUG] 准备创建ComfyUIHelper连接...")
                helper = self._get_helper(task_data)
                # 注册当前任务
                self.active_helpers[task_id] = helper
                self.logger.info(f"[DEBUG] 已成功创建ComfyUIHelper连接并注册到active_helpers")
                self.logger.info(f"[DEBUG] 当前活跃的helpers: {list(self.active_helpers.keys())}")
            except Exception as e:
                error_message = f"创建ComfyUIHelper失败: {str(e)}"
                self.logger.error(f"[DEBUG] {error_message}")
                self.logger.error(f"[DEBUG] 异常详情: {traceback.format_exc()}")
                
                # 更新任务状态
                self._update_task_status(
                    task_id,
                    'failed',
                    error_message=error_message
                )
                
                return {
                    'status': 'failed',
                    'task_id': task_id,
                    'error': error_message
                }

            # 防止错误尝试获取必需的任务参数
            try:
                # 获取需要更新的参数
                prompt_updates = {}
                if task_data:
                    prompt_updates = task_data.get('prompt_updates', {})
                    if not prompt_updates and 'prompt' in task_data:
                        # 向后兼容：如果有prompt但没有prompt_updates，使用prompt作为文本提示
                        self.logger.info(f"[DEBUG] 使用旧格式prompt: {task_data.get('prompt')[:100]}...")
                        prompt_updates = {'text': task_data.get('prompt')}
                        
                # 获取目标节点（如果有）  
                target_node_id = task_data.get('target_node_id')
                
                self.logger.info(f"[DEBUG] prompt_updates: {prompt_updates}")
                self.logger.info(f"[DEBUG] target_node_id: {target_node_id}")
                
                # 执行工作流并获取结果图片
                image_urls = self._execute_workflow(helper, prompt_updates, target_node_id, stop_event, task_id)
                self.logger.info(f"工作流执行完成，获取到 {len(image_urls) if image_urls else 0} 个图片")
                
                # 计算处理时间
                elapsed_time = time.time() - start_time
                self.logger.info(f"任务 {task_id} 处理完成，耗时: {elapsed_time:.2f}秒")
                
                # 更新任务状态为completed
                if image_urls:
                    self._update_task_status(
                        task_id,
                        'completed',
                        image_urls=image_urls,
                        processing_time=elapsed_time
                    )
                    self.logger.info(f"任务 {task_id} 状态已更新为completed")
                
            except Exception as e:
                error_message = f"处理任务参数或执行工作流失败: {str(e)}"
                self.logger.error(f"{error_message}")
                self.logger.error(f"异常详情: {traceback.format_exc()}")
                
                # 计算处理时间
                elapsed_time = time.time() - start_time
                
                # 更新任务状态
                self._update_task_status(
                    task_id,
                    'failed',
                    error_message=error_message,
                    processing_time=elapsed_time
                )
                
                return {
                    'status': 'failed',
                    'task_id': task_id,
                    'error': error_message
                }

            # 清理资源
            self._cleanup_task_resources(task_id)
            
            return {
                'status': 'success',
                'task_id': task_id,
                'image_urls': image_urls
            }
            
        except Exception as e:
            error_message = f"处理任务时出错: {str(e)}"
            self.logger.error(f"{error_message}")
            self.logger.error(f"异常详情: {traceback.format_exc()}")
            
            # 计算处理时间
            elapsed_time = time.time() - start_time
            
            # 更新任务状态
            self._update_task_status(
                task_id,
                'failed',
                error_message=error_message,
                processing_time=elapsed_time
            )
            
            # 清理资源
            self._cleanup_task_resources(task_id)
            
            return {
                'status': 'failed',
                'task_id': task_id,
                'error': error_message
            }
        finally:
            # 确保清理资源
            self._cleanup_task_resources(task_id)

    def _execute_workflow(self, helper: ComfyUIHelper, prompt_updates, target_node_id: str, stop_event: Event, task_id: str) -> List[str]:
        """执行工作流并返回生成的图片URL列表"""
        self.logger.info(f"开始执行任务 {task_id} 的工作流，prompt_updates: {prompt_updates}")
        
        try:
            # 检查工作流文件是否存在
            workflow_file = helper.workflow_file
            self.logger.info(f"使用工作流文件: {workflow_file}")
            
            # 获取工作流（从helper实例缓存或文件读取）
            workflow = helper.load_workflow(workflow_file)
            if not workflow:
                raise ValueError(f"无法加载工作流: {workflow_file}")
            
            # 更新提示词
            if prompt_updates:
                workflow = helper.update_workflow(workflow, prompt_updates)
                self.logger.info(f"已更新工作流提示词")
                
            # 准备事件和结果容器
            result = []
            is_cancelled = False
            done_event = Event()
            image_data = None
            last_activity_time = time.time()  # 添加最后活动时间跟踪
            execution_timeout = 300

            def callback(message: dict):
                # 更新最后响应时间，用于心跳检测
                self.last_response_time = time.time()
                
                if message['type'] == 'execution_complete':
                    self.logger.info(f"任务 {task_id} 工作流执行完成")
                    try:
                        # 检查任务是否已经完成
                        task_obj = ComfyUITask.objects.filter(task_id=task_id).first()
                        if task_obj and task_obj.status in ['completed', 'failed', 'cancelled']:
                            self.logger.info(f"任务 {task_id} 已经完成（状态: {task_obj.status}），跳过重复处理")
                            done_event.set()
                            return

                        # 处理所有图像数据
                        if 'data' in message:
                            images_data = message['data']
                            if isinstance(images_data, list):
                                # 处理图像数据列表
                                for image_data in images_data:
                                    try:
                                        # 上传到OSS
                                        image_url = self._upload_to_oss(image_data)
                                        if image_url:
                                            result.append(image_url)
                                            self.logger.info(f"任务 {task_id} 完成，已上传图像: {image_url}")
                                    except Exception as e:
                                        self.logger.error(f"处理图像失败: {str(e)}")
                            elif isinstance(images_data, dict):
                                # 处理包含image_urls的字典
                                if 'image_urls' in images_data:
                                    result.extend(images_data['image_urls'])
                                # 处理包含images的字典
                                elif 'images' in images_data:
                                    for image_data in images_data['images']:
                                        try:
                                            image_url = self._upload_to_oss(image_data)
                                            if image_url:
                                                result.append(image_url)
                                                self.logger.info(f"任务 {task_id} 完成，已上传图像: {image_url}")
                                        except Exception as e:
                                            self.logger.error(f"处理图像失败: {str(e)}")
                            else:
                                self.logger.warning(f"未知的图像数据格式: {type(images_data)}")
                        
                        # 更新任务状态
                        if result:
                            self._update_task_status(
                                task_id,
                                'completed',
                                image_urls=result
                            )
                        else:
                             # If no images were generated but execution completed,
                             # it might still be a successful workflow that produces
                             # other outputs, but for image tasks, this is a warning.
                             # We'll keep it as completed for now, but log a warning.
                             self.logger.warning(f"任务 {task_id} 工作流执行完成，但未生成图片。")
                             self._update_task_status(task_id, 'completed') # Still mark as completed if no error was indicated

                        done_event.set()
                    except Exception as e:
                        self.logger.error(f"处理任务完成回调失败: {str(e)}")
                        # If an exception occurs during image processing/upload after completion,
                        # mark the task as failed.
                        self._update_task_status(
                            task_id,
                            'failed',
                            error_message=f"处理工作流结果失败: {str(e)}"
                        )
                elif message['type'] == 'execution_error':
                    error_message = message.get('data', {}).get('error', '未知错误')
                    self.logger.error(f"任务 {task_id} 执行出错: {error_message}")
                    # Update task status to failed
                    self._update_task_status(
                        task_id,
                        'failed',
                        error_message=f"工作流执行错误: {error_message}"
                    )
                    is_cancelled = True # Treat as cancelled for cleanup purposes
                    done_event.set()
                elif message['type'] == 'execution_cancelled':
                    self.logger.info(f"任务 {task_id} 已被取消")
                    # Update task status to cancelled
                    self._update_task_status(
                        task_id,
                        'cancelled',
                        error_message="任务已被取消"
                    )
                    is_cancelled = True
                    done_event.set()
                elif message['type'] == 'progress':
                    # 处理进度更新消息
                    data = message.get('data', {})
                    if data and 'value' in data and 'max' in data:
                        progress = (data['value'] / data['max']) * 100
                        # 当进度达到100%时，更新心跳间隔
                        if progress >= 100:
                            self.update_task_heartbeat_interval(task_id, 120)  # 更新为120秒
                            self.logger.info(f"任务 {task_id} 进度达到100%，已更新心跳间隔为120秒")

            # 提交工作流到队列，传递task_id参数
            helper.enqueue_workflow(prompt_updates, callback, target_node_id=target_node_id, task_id=task_id)
            
            # 等待任务完成
            if not done_event.wait(timeout=execution_timeout):
                self.logger.error(f"任务 {task_id} 执行超时")
                raise TimeoutError(f"任务执行超时（{execution_timeout}秒）")
            
            if is_cancelled:
                self.logger.info(f"任务 {task_id} 被取消")
                return []
            
            self.logger.info(f"工作流执行完成，获取到 {len(result)} 个图片")
            return result
                
        except Exception as e:
            self.logger.error(f"准备执行工作流时出错: {str(e)}")
            raise

    def _process_image_result(self, images, task_id: str) -> List[str]:
        """
        处理图像结果，将图像数据上传并返回URL列表
        
        :param images: 图像数据列表或图像URL列表
        :param task_id: 任务ID
        :return: 处理后的图像URL列表
        """
        urls = []
        try:
            for i, image in enumerate(images):
                # 情况1: 已经是URL字符串
                if isinstance(image, str) and (image.startswith('http://') or image.startswith('https://')):
                    urls.append(image)
                    self.logger.info(f"图像 #{i+1}: 已有URL格式")
                    continue
                    
                # 情况2: 是二进制图像数据
                if isinstance(image, bytes):
                    try:
                        # 上传图像到OSS并获取URL
                        img_size_kb = len(image) // 1024
                        image_url = self._upload_to_oss(image)
                        if image_url:
                            urls.append(image_url)
                            self.logger.info(f"图像 #{i+1}: 二进制数据({img_size_kb}KB)已上传至OSS: {image_url}")
                    except Exception as e:
                        self.logger.error(f"图像 #{i+1}: 上传OSS失败: {str(e)}")
                        continue
                
                # 情况3: 是一个包含图像信息的字典
                if isinstance(image, dict):
                    if 'url' in image:
                        # 直接有URL
                        urls.append(image['url'])
                        self.logger.info(f"图像 #{i+1}: 字典中URL格式")
                    elif 'filename' in image and 'subfolder' in image and 'type' in image:
                        # 需要从文件系统获取图像
                        try:
                            filename = image['filename']
                            subfolder = image['subfolder']
                            self.logger.info(f"图像 #{i+1}: 从ComfyUI获取文件 {filename}")
                            image_data = self._get_image(filename, subfolder, image['type'])
                            img_size_kb = len(image_data) // 1024
                            image_url = self._upload_to_oss(image_data)
                            if image_url:
                                urls.append(image_url)
                                self.logger.info(f"图像 #{i+1}: 文件{filename}({img_size_kb}KB)已上传至OSS: {image_url}")
                        except Exception as e:
                            self.logger.error(f"图像 #{i+1}: 获取/上传失败: {str(e)}")
                            continue
            
            self.logger.info(f"图像处理结果: {len(images)}个输入，{len(urls)}个URL")
            return urls
            
        except Exception as e:
            self.logger.error(f"处理图像结果时出错: {str(e)}")
            return []

    def _get_image(self, filename: str, subfolder: str, folder_type: str) -> bytes:
        """从ComfyUI服务器获取图像数据"""
        try:
            self.logger.info(f"获取图像: {filename}, {subfolder}, {folder_type}")
            
            # 准备URL参数
            url_values = urllib.parse.urlencode({
                "filename": filename,
                "subfolder": subfolder, 
                "type": folder_type
            })
            
            # 构建基本URL
            url = f"http://{self.default_comfyui_url}/view?{url_values}"
            
            # 发送请求并获取响应
            with urllib.request.urlopen(url) as response:
                image_data = response.read()
                img_size_kb = len(image_data) // 1024
                self.logger.info(f"成功获取图像: {filename}, 大小: {img_size_kb}KB")
                return image_data
                
        except Exception as e:
            self.logger.error(f"获取图像失败: {str(e)}")
            raise

    def cancel_task(self, task_id: str) -> bool:
        """取消指定任务"""
        try:
            if task_id in self.active_helpers:
                helper = self.active_helpers[task_id]
                
                # 1. 取消当前任务处理
                helper.cancel_current_task()
                
                # 2. 直接通过HTTP请求强制中断ComfyUI中的任务
                try:
                    import urllib.request
                    import json
                    
                    # 创建中断请求
                    data = json.dumps({"prompt_id": task_id}).encode('utf-8')
                    req = urllib.request.Request(
                        f"http://{self.default_comfyui_url}/interrupt",
                        data=data,
                        headers={'Content-Type': 'application/json'}
                    )
                    # 发送中断请求
                    urllib.request.urlopen(req)
                    self.logger.info(f"已直接向ComfyUI服务器发送中断请求: {task_id}")
                except Exception as e:
                    self.logger.error(f"直接中断ComfyUI任务失败: {str(e)}")
                
                # 3. 强制关闭WebSocket连接
                if hasattr(helper, 'ws') and helper.ws:
                    try:
                        helper.ws.close()
                        self.logger.info(f"已强制关闭任务 {task_id} 的WebSocket连接")
                    except Exception as e:
                        self.logger.error(f"关闭WebSocket连接失败: {str(e)}")
                
                # 4. 从活跃任务列表中移除
                del self.active_helpers[task_id]
                
                # 5. 标记任务为已取消
                self._update_task_status(
                    task_id,
                    'cancelled',
                    error_message="任务已被用户取消",
                    completed_at=time.time()
                )
                
                return True
            return False
        except Exception as e:
            self.logger.error(f"取消任务 {task_id} 时发生错误: {str(e)}")
            return False

    def _monitor_task(self, task_id: str, stop_event: Event):
        """监控任务超时"""
        try:
            start_time = time.time()
            last_activity_time = start_time
            consecutive_timeouts = 0
            max_consecutive_timeouts = 5
            max_processing_time = 600  # 10分钟最大处理时间
            last_status_check = start_time
            status_check_interval = 5  # 每5秒检查一次任务状态
            heartbeat_grace_period = 30  # 心跳宽限期（秒）
            
            while True:
                current_time = time.time()
                # 如果任务已被外部取消，或者已经超时，退出监控
                if stop_event.is_set():
                    self.logger.info(f"任务 {task_id} 已被外部取消")
                    break
                    
                if current_time - start_time > max_processing_time:
                    self.logger.warning(f"任务 {task_id} 处理超时 ({max_processing_time}秒)，发送中断信号")
                    stop_event.set()  # 设置停止事件，中断任务
                    break
                
                # 定期检查任务状态
                if current_time - last_status_check >= status_check_interval:
                    last_status_check = current_time
                    # 检查任务是否已完成
                    if self.redis_client:
                        task_status = self.redis_client.get(f"task:{task_id}:status")
                        if task_status in ['completed', 'failed', 'cancelled']:
                            self.logger.info(f"任务 {task_id} 已完成，状态为: {task_status}")
                            break
                    if self._sync_task_status(task_id):
                        break
                
                # 获取当前任务的心跳间隔
                heartbeat_interval = self.task_heartbeat_intervals.get(task_id, 60)
                
                # 检查心跳超时，增加宽限期
                if current_time - last_activity_time > (heartbeat_interval + heartbeat_grace_period):
                    consecutive_timeouts += 1
                    self.logger.warning(f"任务 {task_id} 心跳超时 ({consecutive_timeouts}/{max_consecutive_timeouts})")
                    
                    # 在增加超时计数之前，再次检查任务状态
                    if not self._sync_task_status(task_id):
                        if consecutive_timeouts >= max_consecutive_timeouts:
                            self.logger.error(f"任务 {task_id} 连续 {max_consecutive_timeouts} 次心跳超时，发送中断信号")
                            stop_event.set()
                            break
                    else:
                        consecutive_timeouts = 0
                else:
                    consecutive_timeouts = 0  # 重置连续超时计数
                    
                time.sleep(5)
                
            self.logger.info(f"任务 {task_id} 超时监控线程结束")
            self._cleanup_task_resources(task_id)
            
        except Exception as e:
            self.logger.error(f"监控任务 {task_id} 超时时出错: {str(e)}")
            self.logger.error(f"异常详情: {traceback.format_exc()}")
            self._cleanup_task_resources(task_id)