import websocket
import uuid
import json
import urllib.request
import urllib.parse
import io
import time
import logging
from queue import Queue
from threading import Lock, Thread, Event
from typing import Dict, List, Optional, Union
from PIL import Image
import os
import threading


class ComfyUIHelper:
    def __init__(self, server_address: str, workflow_file: str, username: str = None, password: str = None):
        """增强版ComfyUIHelper，支持任务中断和认证"""
        self.server_address = server_address
        self.workflow_file = workflow_file
        self.client_id = str(uuid.uuid4())
        self.ws = None
        self.task_queue = Queue()
        self.current_task = None
        self.lock = Lock()
        self.is_processing = False
        self.stop_event = Event()  # 停止事件
        self.logger = self._setup_logger()
        self.is_running = True  # 添加运行状态标志
        
        # 添加任务计时器管理
        self.task_timers = {}  # 存储每个任务的计时器
        self.task_last_check = {}  # 存储每个任务最后检查时间
        
        # 认证方式处理 - 只支持token认证
        self.token = None
        if password:  # 任何情况下提供的password都会被视为token
            self.token = password
            self.logger.info("使用token认证模式")
        else:
            self.logger.info("未提供认证信息，使用匿名模式")
        
        # 忽略username参数，保留参数但不使用
        self.username = None
        self.password = None

        # 启动队列处理线程
        self.process_thread = Thread(target=self._process_queue, daemon=True)
        self.process_thread.start()
        self.logger.info("ComfyUIHelper 初始化完成，处理线程已启动")

        self.last_heartbeat = time.time()
        self.heartbeat_interval = 60  # 默认心跳间隔为60秒
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 2  # 初始重连延迟（秒）
        self.max_reconnect_delay = 30  # 最大重连延迟（秒）
        self.request_timeout = 10  # 请求超时时间（秒）
        self.retry_delay = 2  # 重试延迟（秒）
        self.max_retries = 3  # 最大重试次数
        self.max_wait_time = 10  # 最大等待时间（秒）
        self.initial_wait_time = 2  # 初始等待时间（秒）
        self.connection_lock = threading.Lock()
        self.is_connected = False
        self.heartbeat_thread = None
        self.heartbeat_stop_event = Event()

    def _setup_logger(self):
        """设置日志记录器"""
        logger = logging.getLogger('ComfyUIHelper')
        # 如果已经有处理器，就不再添加
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            ch.setFormatter(formatter)
            logger.addHandler(ch)
        return logger

    def cancel_current_task(self) -> bool:
        """取消当前正在执行的任务"""
        if self.is_processing and self.current_task:
            self.stop_event.set()
            self.logger.info(f"已发送中断信号给任务 {self.current_task['id']}")
            return True
        return False

    def _add_auth_to_url(self, url: str) -> str:
        """将认证token添加到URL中"""
        if self.token:
            if '?' in url:
                return f"{url}&token={self.token}"
            else:
                return f"{url}?token={self.token}"
        return url

    def _queue_prompt(self, prompt: dict) -> str:
        """将工作流发送到服务器并获取 prompt_id"""
        try:
            p = {"prompt": prompt, "client_id": self.client_id}
            data = json.dumps(p).encode('utf-8')

            # 准备URL和请求头
            headers = {'Content-Type': 'application/json'}
            url = f"http://{self.server_address}/prompt"
            
            # 添加认证信息
            if self.token:
                url = self._add_auth_to_url(url)
                headers['Authorization'] = f'Bearer {self.token}'
                self.logger.info("提交工作流使用token认证")
            else:
                self.logger.info("提交工作流未使用认证")

            req = urllib.request.Request(
                url,
                data=data,
                headers=headers
            )
            response = urllib.request.urlopen(req)
            return json.loads(response.read())['prompt_id']
        except Exception as e:
            self.logger.error(f"提交工作流失败: {str(e)}")
            raise

    def _get_image(self, filename: str, subfolder: str, folder_type: str) -> bytes:
        """从服务器下载图像"""
        try:
            # 准备URL参数
            data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
            url_values = urllib.parse.urlencode(data)
            
            # 构建基本URL
            url = f"http://{self.server_address}/view?{url_values}"
            
            # 添加认证信息
            if self.token:
                url = self._add_auth_to_url(url)
                self.logger.info("图像请求使用token认证")
            else:
                self.logger.info("图像请求未使用认证")
                
            # 发送请求并获取响应
            with urllib.request.urlopen(url) as response:
                image_data = response.read()
                # 保存图像数据到实例属性
                self.last_image_data = image_data
                self.logger.info(f"成功获取图像 {filename}，大小: {len(image_data)//1024}KB")
                return image_data
                
        except Exception as e:
            self.logger.error(f"获取图像失败: {str(e)}")
            raise

    def _get_history(self, prompt_id: str) -> dict:
        """获取工作流的执行历史"""
        try:
            # 构建基本URL
            url = f"http://{self.server_address}/history/{prompt_id}"
            
            # 准备请求头
            headers = {}
            
            # 添加认证信息
            if self.token:
                url = self._add_auth_to_url(url)
                headers['Authorization'] = f'Bearer {self.token}'
                self.logger.info("历史记录请求使用token认证")
            else:
                self.logger.info("历史记录请求未使用认证")
            
            # 发送请求并获取响应
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                history = json.loads(response.read())
            
            if history and prompt_id in history:
                self.logger.info(f"成功获取任务 {prompt_id} 的历史记录")
                return history
            self.logger.info(f"任务 {prompt_id} 无历史记录，可能已被取消")
            return {prompt_id: {'outputs': {}}}  # 返回一个包含空输出的历史记录
        except Exception as e:
            self.logger.error(f"获取执行历史失败: {str(e)}")
            raise

    def _cleanup_gpu_resources(self):
        """通过运行空负载工作流来清理GPU资源"""
        try:
            # 获取空负载工作流文件路径
            from .ConfigPathManager import ConfigPathManager
            empty_workflow_path = ConfigPathManager.get_workflow_file_path("comfyuiEmptyGPUWorkflow")
            
            # 加载空负载工作流
            with open(empty_workflow_path, 'r', encoding='utf-8') as f:
                empty_workflow = json.load(f)
            
            # 确保所有节点ID都是字符串类型
            empty_workflow = {str(k): v for k, v in empty_workflow.items()}
            
            # 提交空负载工作流
            empty_prompt_id = self._queue_prompt(empty_workflow)
            self.logger.info(f"已提交空负载工作流，ID: {empty_prompt_id}")
            
            # 等待空负载工作流完成
            max_wait_time = 10  # 最大等待10秒
            start_time = time.time()
            execution_complete = False
            
            # 首先尝试通过WebSocket直接监控
            while not execution_complete and time.time() - start_time < max_wait_time:
                try:
                    out = self.ws.recv()
                    if isinstance(out, str):
                        message = json.loads(out)
                        if not isinstance(message, dict):
                            continue
                            
                        message_type = message.get('type')
                        if not message_type:
                            continue
                            
                        if message_type == 'executing':
                            data = message.get('data', {})
                            if not data:
                                continue
                                
                            node = data.get('node')
                            prompt_id = data.get('prompt_id')
                            if node is None and prompt_id == empty_prompt_id:
                                self.logger.info("空负载工作流执行完成，GPU资源已清理")
                                execution_complete = True
                                break
                        elif message_type == 'execution_error':
                            data = message.get('data', {})
                            error_message = data.get('error', '未知错误')
                            self.logger.warning(f"空负载工作流执行错误: {error_message}")
                            break
                            
                except websocket.WebSocketConnectionClosedException:
                    self.logger.warning("WebSocket连接已关闭，尝试从历史记录获取状态")
                    break
                except Exception as e:
                    self.logger.warning(f"监控空负载工作流状态时出错: {str(e)}")
                    break
                
                time.sleep(0.1)  # 短暂等待，避免CPU占用过高
            
            # 如果WebSocket监控失败，尝试从历史记录获取状态
            if not execution_complete:
                self.logger.info("尝试从历史记录获取空负载工作流状态...")
                try:
                    history = self._get_history(empty_prompt_id)
                    if empty_prompt_id in history and history[empty_prompt_id].get('outputs'):
                        self.logger.info("从历史记录确认空负载工作流执行完成，GPU资源已清理")
                        execution_complete = True
                except Exception as e:
                    self.logger.warning(f"从历史记录获取状态失败: {str(e)}")
            
            if not execution_complete:
                self.logger.warning("空负载工作流执行超时")
                return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"清理GPU资源失败: {str(e)}")
            return False

    def execute_workflow(self, prompt_updates: dict, target_node_id: Optional[str] = None) -> Union[dict, list]:
        """执行工作流的核心方法（支持中断）"""
        try:
            self.logger.info("正在加载工作流文件...")
            try:
                workflow = self.load_workflow(self.workflow_file)
            except FileNotFoundError:
                self.logger.error(f"找不到工作流文件: {self.workflow_file}")
                raise
            except Exception as e:
                self.logger.error(f"加载工作流文件失败: {str(e)}")
                raise
                # 检查是否是产品替换工作流
            is_product_replace = False
            try:
                from .ConfigPathManager import ConfigPathManager
                product_replace_workflow = ConfigPathManager.get_workflow_file_path(
                    "comfyuiProductImageInTemplateReplace")
                if self.workflow_file == product_replace_workflow:
                    is_product_replace = True
                    self.logger.info("检测到产品替换工作流，跳过GPU资源清理")
            except Exception as e:
                self.logger.warning(f"检查工作流类型时出错: {str(e)}")

            # 更新工作流参数
            self.logger.info("正在更新工作流参数...")
            for node_id, updates in prompt_updates.items():
                if node_id in workflow:
                    workflow[node_id]["inputs"].update(updates["inputs"])
                else:
                    self.logger.warning(f"节点 {node_id} 不在工作流中，无法更新")

            # 确保WebSocket连接
            if not self._ensure_connection():
                raise ConnectionError("无法建立WebSocket连接")

            # 发送工作流并获取 prompt_id
            self.logger.info("正在提交工作流到队列...")
            try:
                prompt_id = self._queue_prompt(workflow)
                self.logger.info(f"工作流已提交，ID: {prompt_id}")
                self.current_prompt_id = prompt_id  # 保存当前prompt_id
            except Exception as e:
                self.logger.error(f"提交工作流失败: {str(e)}")
                raise

            # 监听 WebSocket 消息，直到工作流执行完成
            self.logger.info("正在监控执行进度...")
            execution_complete = False
            last_message_time = time.time()
            message_timeout = 300  # 增加到300秒无消息超时
            heartbeat_interval = 90  # 增加到60秒发送一次心跳
            last_heartbeat_time = time.time()
            output_images = {}  # 存储输出图像
            last_progress_time = time.time()  # 添加最后进度更新时间
            progress_reached_100 = False  # 添加进度达到100%的标志

            while not execution_complete:
                if self.stop_event.is_set():
                    self.logger.info("收到中断信号，正在取消任务...")
                    self._interrupt_prompt(prompt_id)
                    raise InterruptedError("任务被用户中断")

                try:
                    current_time = time.time()
                    
                    # 检查是否需要发送心跳
                    if current_time - last_heartbeat_time > heartbeat_interval:
                        # 如果最近有进度更新或消息，不发送心跳
                        if current_time - last_progress_time < heartbeat_interval:
                            last_heartbeat_time = current_time
                            continue
                            
                        # 如果进度达到100%，增加心跳间隔
                        if progress_reached_100:
                            heartbeat_interval = 120  # 进度100%后使用120秒的心跳间隔
                            message_timeout = 600  # 进度100%后使用600秒的消息超时
                            
                        try:
                            self.ws.ping()
                            last_heartbeat_time = current_time
                            self.logger.debug("心跳检测成功")
                        except Exception as e:
                            self.logger.warning(f"心跳检测失败: {str(e)}")
                            # 心跳失败时尝试重新连接
                            if not self._ensure_connection():
                                time.sleep(5)
                                if not self._ensure_connection():
                                    raise ConnectionError("重连失败")
                            last_heartbeat_time = current_time

                    # 检查消息超时
                    if current_time - last_message_time > message_timeout:
                        self.logger.warning("消息接收超时，尝试重新连接...")
                        # 先关闭现有连接
                        if self.ws:
                            try:
                                self.ws.close()
                                self.logger.info("已关闭超时的WebSocket连接")
                            except Exception as e:
                                self.logger.error(f"关闭超时的WebSocket连接失败: {str(e)}")
                            finally:
                                self.ws = None
                        
                        # 尝试重新连接
                        if not self._ensure_connection():
                            time.sleep(5)
                            if not self._ensure_connection():
                                raise ConnectionError("重连失败")
                        last_message_time = current_time

                    out = self.ws.recv()
                    if isinstance(out, str):
                        last_message_time = time.time()
                        try:
                            message = json.loads(out)
                            if not isinstance(message, dict):
                                self.logger.warning(f"收到非字典类型的消息: {type(message)}")
                                continue
                                
                            message_type = message.get('type')
                            if not message_type:
                                self.logger.warning("收到没有type字段的消息")
                                continue
                                
                            if message_type == 'executing':
                                data = message.get('data', {})
                                if not data:
                                    self.logger.warning("executing消息没有data字段")
                                    continue
                                    
                                node = data.get('node')
                                prompt_id = data.get('prompt_id')
                                if node is None and prompt_id == self.current_prompt_id:
                                    self.logger.info("工作流执行完成")
                                    execution_complete = True
                                    break
                            elif message_type == 'status':
                                data = message.get('data', {})
                                if data:
                                    self.logger.info(f"状态更新: {data.get('status', '未知状态')}")
                                    last_progress_time = time.time()  # 更新最后进度时间
                            elif message_type == 'execution_error':
                                data = message.get('data', {})
                                error_message = data.get('error', '未知错误')
                                self.logger.error(f"工作流执行错误: {error_message}")
                                raise Exception(f"工作流执行错误: {error_message}")
                            elif message_type == 'progress':
                                data = message.get('data', {})
                                if data and 'value' in data and 'max' in data:
                                    progress = (data['value'] / data['max']) * 100
                                    self.logger.info(f"执行进度: {progress:.1f}%")
                                    last_progress_time = time.time()  # 更新最后进度时间
                                    
                                    # 检查进度是否达到100%
                                    if progress >= 100 and not progress_reached_100:
                                        progress_reached_100 = True
                                        heartbeat_interval = 120  # 进度100%后使用120秒的心跳间隔
                                        message_timeout = 600  # 进度100%后使用600秒的消息超时
                                        self.logger.info("进度达到100%，调整心跳间隔为120秒")
                            elif message_type == 'executed':
                                data = message.get('data', {})
                                if not data:
                                    self.logger.warning("executed消息没有data字段")
                                    continue
                                    
                                output = data.get('output', {})
                                if not output:
                                    self.logger.warning("executed消息没有output字段")
                                    continue
                                    
                                images = output.get('images', [])
                                if not images:
                                    self.logger.warning("executed消息没有images字段")
                                    continue
                                    
                                node_id = data.get('node')
                                if not node_id:
                                    self.logger.warning("executed消息没有node字段")
                                    continue
                                    
                                if node_id not in output_images:
                                    output_images[node_id] = []
                                    
                                for image in images:
                                    if not isinstance(image, dict):
                                        self.logger.warning(f"图像数据格式错误: {type(image)}")
                                        continue
                                        
                                    filename = image.get('filename')
                                    if not filename:
                                        self.logger.warning("图像数据缺少filename字段")
                                        continue
                                        
                                    try:
                                        image_data = self._get_image(
                                            filename,
                                            image.get('subfolder', ''),
                                            image.get('type', 'output')
                                        )
                                        output_images[node_id].append(image_data)
                                        self.logger.info(f"成功获取节点 {node_id} 的图像: {filename}")
                                        last_progress_time = time.time()  # 更新最后进度时间
                                    except Exception as e:
                                        self.logger.error(f"获取图像失败: {str(e)}")
                        except json.JSONDecodeError as e:
                            self.logger.error(f"JSON解析错误: {str(e)}")
                            continue
                        except Exception as e:
                            self.logger.error(f"处理消息时出错: {str(e)}")
                            continue

                except websocket.WebSocketConnectionClosedException:
                    self.logger.error("WebSocket连接已关闭")
                    if self.stop_event.is_set():
                        self.logger.info("检测到任务已被取消，WebSocket连接关闭是预期行为")
                        raise InterruptedError("任务被用户中断")
                    
                    # 尝试重新连接
                    if not self._ensure_connection():
                        # 如果重连失败，确保关闭连接
                        if self.ws:
                            try:
                                self.ws.close()
                                self.logger.info("已关闭失败的WebSocket连接")
                            except Exception as e:
                                self.logger.error(f"关闭失败的WebSocket连接时出错: {str(e)}")
                            finally:
                                self.ws = None
                        raise ConnectionError("重连失败")
                    continue

                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON解析错误: {str(e)}")
                    # 确保关闭连接
                    if self.ws:
                        try:
                            self.ws.close()
                            self.logger.info("已关闭JSON解析错误时的WebSocket连接")
                        except Exception as close_error:
                            self.logger.error(f"关闭JSON解析错误时的WebSocket连接失败: {str(close_error)}")
                        finally:
                            self.ws = None
                    if self.stop_event.is_set():
                        self.logger.info("检测到任务已被取消，JSON解析错误是预期行为")
                        raise InterruptedError("任务被用户中断")
                    raise

                except Exception as e:
                    self.logger.error(f"接收消息失败: {str(e)}")
                    # 确保关闭连接
                    if self.ws:
                        try:
                            self.ws.close()
                            self.logger.info("已关闭接收消息失败时的WebSocket连接")
                        except Exception as close_error:
                            self.logger.error(f"关闭接收消息失败时的WebSocket连接失败: {str(close_error)}")
                        finally:
                            self.ws = None
                    if self.stop_event.is_set():
                        self.logger.info(f"检测到任务已被取消，错误 {str(e)} 是预期行为")
                        raise InterruptedError("任务被用户中断")
                    raise

            # 检查是否获取到任何结果
            total_images = sum(len(imgs) for imgs in output_images.values())
            if total_images == 0 and not execution_complete:
                # 只有在以下所有条件都满足时才尝试从历史记录获取：
                # 1. 没有获取到任何图像
                # 2. 执行未完成
                # 3. 没有收到任何进度更新超过60秒
                if current_time - last_progress_time > 60:
                    self.logger.warning("长时间未收到进度更新，尝试从历史记录中获取...")
                    try:
                        # 只尝试一次获取历史记录
                        history = self._get_history(prompt_id)[prompt_id]
                        if history and 'outputs' in history:
                            self.logger.info(f"成功从历史记录获取结果，包含 {len(history['outputs'])} 个输出节点")
                            
                            # 处理历史记录中的图像
                            for node_id, node_output in history['outputs'].items():
                                if 'images' in node_output:
                                    if node_id not in output_images:
                                        output_images[node_id] = []
                                    for image in node_output['images']:
                                        try:
                                            image_data = self._get_image(
                                                image['filename'],
                                                image.get('subfolder', ''),
                                                image.get('type', 'output')
                                            )
                                            output_images[node_id].append(image_data)
                                            self.logger.info(f"从历史记录成功获取节点 {node_id} 的图像: {image['filename']}")
                                        except Exception as e:
                                            self.logger.error(f"从历史记录获取图像失败: {str(e)}")
                    except Exception as e:
                        self.logger.error(f"尝试从历史记录获取结果时出错: {str(e)}")
            else:
                # 检查是否成功获取到图像
                total_images = sum(len(imgs) for imgs in output_images.values())
                if total_images > 0:
                    self.logger.info(f"已从WebSocket消息成功获取到 {total_images} 张图像")
                    # 只有非产品替换类型的任务才清理GPU资源
                    if not is_product_replace:
                        self.logger.info("开始清理GPU资源...")
                        self._cleanup_gpu_resources()
                    else:
                        self.logger.info("产品替换类型任务，跳过GPU资源清理")
                else:
                    self.logger.warning("WebSocket连接正常但未获取到图像")

            # 处理输出结果
            if target_node_id:
                # 从指定节点获取图像
                if target_node_id in output_images:
                    self.logger.info(f"从节点 {target_node_id} 获取到 {len(output_images[target_node_id])} 张图像")
                    result = output_images[target_node_id]
                else:
                    self.logger.warning(f"目标节点 {target_node_id} 没有图像输出")
                    result = []
            else:
                # 返回所有节点的图像
                total_images = sum(len(imgs) for imgs in output_images.values())
                self.logger.info(f"所有节点处理完成，共获取到 {total_images} 张图像")
                result = output_images

            # 关闭WebSocket连接
            if self.ws:
                try:
                    self.ws.close()
                    self.logger.info("WebSocket连接已关闭")
                except Exception as e:
                    self.logger.error(f"关闭WebSocket连接时出错: {str(e)}")
                finally:
                    self.ws = None

            return result

        except Exception as e:
            self.logger.error(f"工作流执行出错: {str(e)}")
            # 即使出错也尝试清理GPU资源
            try:
                self.logger.info("工作流执行出错，尝试清理GPU资源...")
                self._cleanup_gpu_resources()
            except Exception as cleanup_error:
                self.logger.warning(f"清理GPU资源失败: {str(cleanup_error)}")
            raise
        finally:
            self.stop_event.clear()
            # 确保在发生异常时也关闭WebSocket连接
            if self.ws:
                try:
                    self.ws.close()
                    self.logger.info("WebSocket连接已关闭")
                except Exception as e:
                    self.logger.error(f"关闭WebSocket连接时出错: {str(e)}")
                finally:
                    self.ws = None

    def _interrupt_prompt(self, prompt_id: str):
        """中断指定的prompt"""
        try:
            data = json.dumps({"prompt_id": prompt_id}).encode('utf-8')
            
            # 构建基本URL和请求头
            url = f"http://{self.server_address}/interrupt"
            headers = {'Content-Type': 'application/json'}
            
            # 添加认证信息
            if self.token:
                url = self._add_auth_to_url(url)
                self.logger.info("中断请求使用token认证")
            else:
                self.logger.info("中断请求未使用认证")

            req = urllib.request.Request(
                url,
                data=data,
                headers=headers
            )
            urllib.request.urlopen(req)
            self.logger.info(f"已成功中断prompt {prompt_id}")
        except Exception as e:
            self.logger.error(f"中断prompt失败: {str(e)}")
            raise

    def _process_queue(self):
        """处理队列中的任务"""
        while self.is_running:  # 使用运行状态标志
            task = None  # 初始化task变量
            try:
                with self.lock:
                    # 严格检查：只有当队列不为空且当前没有任务在处理时才获取新任务
                    if not self.task_queue.empty() and not self.is_processing:
                        self.is_processing = True
                        task = self.task_queue.get()
                        # 初始化任务计时器
                        if task['id'] not in self.task_timers:
                            self.task_timers[task['id']] = time.time()
                            self.task_last_check[task['id']] = time.time()
                        self.logger.info(f"从队列中获取任务: {task['id']}")
                    else:
                        # 如果队列为空或有任务正在处理，等待一小段时间
                        time.sleep(0.1)
                        continue

                if not task:  # 确保task存在
                    continue

                self.logger.info(f"开始处理任务: {task['id']}")
                self.current_task = task
                self.stop_event.clear()

                # 执行工作流
                self.logger.info(f"开始执行工作流: {task['id']}")
                result = self.execute_workflow(
                    task['prompt_updates'],
                    task.get('target_node_id')
                )
                self.logger.info(f"工作流执行完成: {task['id']}")

                # 确保回调被调用
                if task['callback']:
                    self.logger.info(f"调用任务回调: {task['id']}")
                    try:
                        # 处理返回结果，确保格式一致性
                        callback_data = result
                        # 如果结果是图像数据列表，直接传递
                        if isinstance(result, list):
                            message = {
                                'type': 'execution_complete',
                                'data': result
                            }
                        else:
                            # 如果结果是复杂结构，构建一个标准格式的消息
                            message = {
                                'type': 'execution_complete',
                                'data': {
                                    'image_urls': result.get(task.get('target_node_id', ''), []) if isinstance(result, dict) else result
                                }
                            }
                        # 调用回调
                        task['callback'](message)
                        self.logger.info(f"任务回调完成: {task['id']}")
                    except Exception as e:
                        self.logger.error(f"任务回调处理失败: {str(e)}")
                        # 尝试以最简单的格式发送错误回调
                        try:
                            task['callback']({
                                'type': 'execution_error',
                                'data': {
                                    'error': str(e)
                                }
                            })
                        except Exception as callback_error:
                            self.logger.error(f"发送错误回调失败: {str(callback_error)}")

            except InterruptedError:
                if task and task['callback']:
                    self.logger.info(f"任务 {task['id']} 被中断")
                    try:
                        task['callback']({
                            'type': 'execution_interrupted'
                        })
                    except Exception as callback_error:
                        self.logger.error(f"中断任务回调失败: {str(callback_error)}")
            except json.JSONDecodeError as json_error:
                if task and task['callback']:
                    self.logger.error(f"JSON解析错误: {str(json_error)}")
                    # 检查是否是因为取消导致的JSON解析错误
                    if self.stop_event.is_set():
                        self.logger.info("检测到任务已被取消，JSON解析错误是预期行为")
                        try:
                            task['callback']({
                                'type': 'execution_interrupted'
                            })
                        except Exception as callback_error:
                            self.logger.error(f"JSON错误后调用回调失败: {str(callback_error)}")
                    else:
                        try:
                            task['callback']({
                                'type': 'execution_error',
                                'error': {
                                    'type': 'json_error',
                                    'message': str(json_error)
                                }
                            })
                        except Exception as callback_error:
                            self.logger.error(f"JSON错误后调用回调失败: {str(callback_error)}")
            except Exception as e:
                if task and task['callback']:
                    self.logger.error(f"任务失败: {str(e)}")
                    try:
                        task['callback']({
                            'type': 'execution_error',
                            'error': {
                                'type': 'unknown',
                                'message': str(e)
                            }
                        })
                    except Exception as callback_error:
                        self.logger.error(f"错误回调失败: {str(callback_error)}")
            finally:
                with self.lock:
                    # 清理任务状态和计时器
                    if task:
                        if task['id'] in self.task_timers:
                            del self.task_timers[task['id']]
                        if task['id'] in self.task_last_check:
                            del self.task_last_check[task['id']]
                    self.current_task = None
                    self.is_processing = False  # 确保在处理完成后重置处理标志
                    if task:  # 只在task存在时记录完成
                        self.logger.info(f"任务处理完成: {task['id']}")

    def enqueue_workflow(self, prompt_updates: dict, callback, target_node_id: Optional[str] = None,
                         task_id: Optional[str] = None) -> str:
        """
        将工作流加入队列并返回任务ID
        :param prompt_updates: 工作流参数更新
        :param callback: 回调函数
        :param target_node_id: 目标节点ID
        :param task_id: 外部传入的任务ID（可选）
        :return: 任务ID
        """
        if not task_id:
            raise ValueError("task_id is required")

        task = {
            'id': task_id,  # 使用传入的task_id
            'prompt_updates': prompt_updates,
            'callback': callback,
            'target_node_id': target_node_id,
            'status': 'pending'
        }

        with self.lock:
            self.task_queue.put(task)
            self.logger.info(f"任务已加入队列: {task['id']}")
            return task['id']

    def get_queue_size(self) -> int:
        """获取队列中等待的任务数量"""
        with self.lock:
            return self.task_queue.qsize()

    def get_current_task(self) -> Optional[dict]:
        """获取当前正在执行的任务信息"""
        with self.lock:
            return self.current_task

    @staticmethod
    def save_image(image_data: bytes, file_path: str = None):
        """
        将图像数据保存到文件对象中
        """
        try:
            image = Image.open(io.BytesIO(image_data))

            if file_path:
                image.save(file_path)
                return file_path
            else:
                file_obj = io.BytesIO()
                image.save(file_obj, format='PNG')
                file_obj.seek(0)
                return file_obj
        except Exception as e:
            raise ValueError(f"保存图像失败: {str(e)}")

    def cleanup(self):
        """Clean up resources and close WebSocket connection"""
        if self.ws:
            try:
                self.ws.close()
                self.logger.info("WebSocket连接已关闭")
            except:
                pass
            self.ws = None

    def __del__(self):
        """Destructor to ensure WebSocket connection is closed when object is destroyed"""
        self.cleanup()
        self.is_running = False
        if hasattr(self, 'process_thread') and self.process_thread.is_alive():
            self.process_thread.join(timeout=1.0)

    def load_workflow(self, workflow_file: str) -> dict:
        """加载工作流文件"""
        try:
            # 输出日志，显示我们尝试查找文件的所有位置
            self.logger.info(f"尝试加载工作流文件: {workflow_file}")
            self.logger.info(f"当前工作目录: {os.getcwd()}")

            # 尝试多种可能的路径
            possible_paths = []

            # 1. 原始路径
            possible_paths.append(workflow_file)

            # 2. 相对于当前工作目录的路径
            possible_paths.append(os.path.join(os.getcwd(), workflow_file))

            # 3. 相对于当前工作目录的comfyui子目录的路径
            possible_paths.append(os.path.join(os.getcwd(), "comfyui", os.path.basename(workflow_file)))

            # 4. 相对于项目根目录的路径
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            possible_paths.append(os.path.join(project_root, workflow_file))

            # 5. 相对于项目根目录的comfyui子目录的路径
            possible_paths.append(os.path.join(project_root, "comfyui", os.path.basename(workflow_file)))

            # 6. 尝试使用ConfigPathManager（如果可用）
            try:
                from .ConfigPathManager import ConfigPathManager

                # 6.1 使用ConfigPathManager获取项目根目录
                config_project_root = ConfigPathManager.get_project_root()
                possible_paths.append(os.path.join(config_project_root, workflow_file))
                possible_paths.append(os.path.join(config_project_root, "comfyui", os.path.basename(workflow_file)))

                # 6.2 使用ConfigPathManager获取comfyui目录
                comfyui_dir = ConfigPathManager.get_comfyui_dir()
                possible_paths.append(os.path.join(comfyui_dir, os.path.basename(workflow_file)))

                # 6.3 尝试直接通过ConfigPathManager获取工作流文件路径
                basename = os.path.basename(workflow_file)
                workflow_key = os.path.splitext(basename)[0]  # 移除.json后缀
                # 格式化为comfyui<CamelCase>的格式
                workflow_key = "comfyui" + workflow_key[0].upper() + workflow_key[1:]
                try:
                    config_path = ConfigPathManager.get_workflow_file_path(workflow_key)
                    possible_paths.append(config_path)
                except Exception as e:
                    self.logger.warning(f"通过ConfigPathManager获取工作流文件路径失败: {str(e)}")
            except ImportError:
                self.logger.warning("无法导入ConfigPathManager，跳过相关路径检查")

            # 去除重复路径
            possible_paths = list(dict.fromkeys(possible_paths))

            # 遍历所有可能的路径，找到第一个存在的文件
            for path in possible_paths:
                self.logger.info(f"尝试路径: {path}")
                if os.path.exists(path):
                    self.logger.info(f"找到工作流文件: {path}")
                    # 更新当前实例的workflow_file为找到的有效路径
                    self.workflow_file = path
                    with open(path, encoding="utf-8") as f:
                        return json.loads(f.read())

            # 如果所有路径都失败，打印详细信息并抛出错误
            self.logger.error(f"无法找到工作流文件: {workflow_file}")
            self.logger.error(f"尝试过的所有路径: {possible_paths}")
            raise FileNotFoundError(f"找不到工作流文件: {workflow_file}")
        except Exception as e:
            self.logger.error(f"加载工作流文件失败: {str(e)}")
            raise

    def update_workflow(self, workflow: dict, prompt_updates: dict, target_node_id: str = None) -> dict:
        """更新工作流参数"""
        self.logger.info(f"目标节点数据：{prompt_updates}")
        self.logger.info(f"当前 workflow 的节点: {list(workflow.keys())}")
        try:
            if prompt_updates:
                for node_id, updates in prompt_updates.items():
                    if node_id in workflow:
                        self.logger.info(f"已更新节点 {node_id} 的输入: {updates}")
                        workflow[node_id]["inputs"].update(updates["inputs"])  # 注意层级！
                    else:
                        self.logger.info(f"警告: 节点 {node_id} 不在 workflow 中")
            self.logger.info("工作流参数更新成功")
            return workflow
        except Exception as e:
            self.logger.error(f"更新工作流参数失败: {str(e)}")
            raise

    def update_workflow_params(self, prompt_updates: dict):
        """
        更新工作流参数的入口方法
        :param prompt_updates: 需要更新的参数
        """
        try:
            self.logger.info(f"准备更新工作流参数: {prompt_updates}")
            # 首先加载工作流
            workflow = self.load_workflow(self.workflow_file)
            if not workflow:
                raise ValueError("工作流加载失败")
                
            # 调用现有的update_workflow方法更新参数
            updated_workflow = self.update_workflow(workflow, prompt_updates)
            self.logger.info("工作流参数更新成功")
            return updated_workflow
        except Exception as e:
            self.logger.error(f"更新工作流参数失败: {str(e)}")
            raise

    def get_history(self, prompt_id: str) -> dict:
        """获取工作流执行历史"""
        try:
            # 尝试多次获取历史记录
            max_retries = 3
            retry_delay = 1  # 秒

            for attempt in range(max_retries):
                try:
                    # 构建基本URL
                    url = f"http://{self.server_address}/history/{prompt_id}"
                    
                    # 添加认证信息
                    if self.token:
                        url = self._add_auth_to_url(url)
                        self.logger.info("历史记录请求使用token认证")
                    else:
                        self.logger.info("历史记录请求未使用认证")
                    
                    # 发送请求并获取响应
                    with urllib.request.urlopen(url) as response:
                        history = json.loads(response.read())
                    
                    if history and prompt_id in history:
                        self.logger.info(f"成功获取任务 {prompt_id} 的历史记录")
                        return history
                    self.logger.info(f"任务 {prompt_id} 无历史记录，可能已被取消")
                    return {prompt_id: {'outputs': {}}}  # 返回一个包含空输出的历史记录
                except urllib.error.HTTPError as e:
                    if e.code == 404:
                        self.logger.info(f"任务 {prompt_id} 不存在或已被取消")
                        return {prompt_id: {'outputs': {}}}  # 返回一个包含空输出的历史记录
                    if attempt < max_retries - 1:
                        self.logger.warning(f"获取历史记录失败 (HTTP错误 {e.code}，尝试 {attempt+1}/{max_retries}): {str(e)}")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                    else:
                        raise
                except Exception as e:
                    if attempt < max_retries - 1:
                        self.logger.warning(f"获取历史记录失败 (尝试 {attempt+1}/{max_retries}): {str(e)}")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                    else:
                        self.logger.error(f"获取历史记录失败，已达到最大重试次数: {str(e)}")
                        raise
        except Exception as e:
            self.logger.error(f"获取执行历史失败: {str(e)}")
            raise

    def cancel_workflow(self):
        """取消当前正在执行的工作流"""
        try:
            self.logger.info("尝试取消当前执行的工作流")
            
            # 1. 检查任务是否已经完成
            if hasattr(self, 'current_prompt_id') and self.current_prompt_id:
                try:
                    history = self._get_history(self.current_prompt_id)
                    if history and self.current_prompt_id in history:
                        task_history = history[self.current_prompt_id]
                        if task_history.get('outputs'):
                            self.logger.info(f"任务 {self.current_prompt_id} 已经完成，无需取消")
                            return True
                except Exception as e:
                    self.logger.error(f"检查任务状态失败: {str(e)}")
            
            # 2. 尝试通过API中断执行
            if hasattr(self, 'current_prompt_id') and self.current_prompt_id:
                try:
                    import urllib.request
                    import json
                    
                    # 创建中断请求
                    data = json.dumps({"prompt_id": self.current_prompt_id}).encode('utf-8')
                    url = f"http://{self.server_address}/interrupt"
                    
                    # 添加认证信息
                    if self.token:
                        url = self._add_auth_to_url(url)
                        self.logger.info("中断请求使用token认证")
                    
                    req = urllib.request.Request(
                        url,
                        data=data,
                        headers={'Content-Type': 'application/json'}
                    )
                    # 发送中断请求
                    response = urllib.request.urlopen(req)
                    self.logger.info(f"已向ComfyUI服务器发送中断请求: {self.current_prompt_id}, 响应: {response.status}")
                    
                    # 等待一小段时间，确保服务器有时间处理中断请求
                    time.sleep(1)
                except Exception as e:
                    self.logger.error(f"通过API中断工作流失败: {str(e)}")
            
            # 3. 如果有WebSocket连接，尝试关闭它
            if hasattr(self, 'ws') and self.ws:
                try:
                    self.ws.close()
                    self.logger.info("已关闭WebSocket连接")
                except Exception as e:
                    self.logger.error(f"关闭WebSocket连接失败: {str(e)}")
            
            # 4. 如果有工作队列，清空它
            if hasattr(self, 'task_queue'):
                try:
                    while not self.task_queue.empty():
                        self.task_queue.get(False)
                    self.logger.info("已清空工作队列")
                except Exception as e:
                    self.logger.error(f"清空工作队列失败: {str(e)}")
                    
            # 5. 重置处理标志
            if hasattr(self, 'is_processing'):
                self.is_processing = False
                self.logger.info("已重置处理标志")
                
            # 6. 重置当前任务
            if hasattr(self, 'current_task'):
                self.current_task = None
                self.logger.info("已重置当前任务")
                
            # 7. 重新连接准备下一次任务
            self._ensure_connection()
                
            return True
        except Exception as e:
            self.logger.error(f"取消工作流失败: {str(e)}")
            return False

    def _ensure_connection(self) -> bool:
        """确保WebSocket连接可用"""
        try:
            if not self.ws or not self.is_connected:
                self.logger.debug("WebSocket连接不可用，尝试重新连接")
                if self.ws:
                    try:
                        self.ws.close()
                    except:
                        pass
                self.ws = None
                self.is_connected = False
                
                # 使用指数退避策略进行重连
                if self.reconnect_attempts < self.max_reconnect_attempts:
                    delay = min(self.reconnect_delay * (2 ** self.reconnect_attempts), self.max_reconnect_delay)
                    self.logger.info(f"尝试重新连接 (第 {self.reconnect_attempts + 1} 次)，等待 {delay} 秒")
                    time.sleep(delay)
                    
                    try:
                        # 构建WebSocket URL，包含认证信息
                        ws_url = f"ws://{self.server_address}/ws?clientId={self.client_id}"
                        if self.token:
                            ws_url = f"{ws_url}&token={self.token}"
                            self.logger.info("WebSocket连接使用token认证")
                        
                        self.ws = websocket.WebSocket()
                        self.ws.connect(ws_url, timeout=self.request_timeout)
                        self.is_connected = True
                        self.reconnect_attempts = 0
                        self.logger.info("WebSocket连接已恢复")
                        return True
                    except Exception as e:
                        self.reconnect_attempts += 1
                        self.logger.error(f"重连失败: {str(e)}")
                        return False
                else:
                    self.logger.error(f"达到最大重连次数 ({self.max_reconnect_attempts})")
                    return False
            return True
        except Exception as e:
            self.logger.error(f"确保连接时出错: {str(e)}")
            return False

    def _heartbeat_loop(self):
        """心跳检测循环"""
        while not self.heartbeat_stop_event.is_set():
            try:
                current_time = time.time()
                if current_time - self.last_heartbeat >= self.heartbeat_interval:
                    self.logger.debug(f"发送心跳检测，间隔: {self.heartbeat_interval}秒")
                    if self._ensure_connection():
                        self.last_heartbeat = current_time
                    else:
                        self.logger.warning("心跳检测失败，尝试重新连接")
                        if not self._ensure_connection():
                            self.logger.error("重连失败，停止心跳检测")
                            break
                time.sleep(5)  # 每5秒检查一次
            except Exception as e:
                self.logger.error(f"心跳检测出错: {str(e)}")
                time.sleep(5)

    def _on_message(self, ws, message):
        """处理WebSocket消息"""
        try:
            data = json.loads(message)
            self.last_heartbeat = time.time()  # 更新最后心跳时间
            
            if data.get('type') == 'pong':
                self.logger.debug("收到心跳响应")
                return
                
            # 处理其他消息...
            
        except Exception as e:
            self.logger.error(f"处理WebSocket消息失败: {str(e)}")

    def _on_error(self, ws, error):
        """处理WebSocket错误"""
        self.logger.error(f"WebSocket错误: {str(error)}")
        self.is_connected = False
        if "Connection timed out" in str(error):
            self.logger.info("连接超时，尝试重新连接...")
            self._ensure_connection()

    def _on_close(self, ws, close_status_code, close_msg):
        """处理WebSocket连接关闭"""
        self.logger.info(f"WebSocket连接关闭: {close_status_code} - {close_msg}")
        self.is_connected = False
        if not self.heartbeat_stop_event.is_set():
            self.logger.info("连接意外关闭，尝试重新连接...")
            self._ensure_connection()

    def _on_open(self, ws):
        """处理WebSocket连接打开"""
        self.logger.info("WebSocket连接已打开")
        self.is_connected = True
        self.last_heartbeat = time.time()

    def close(self):
        """关闭WebSocket连接"""
        self.heartbeat_stop_event.set()
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        if self.ws:
            self.ws.close()
        self.is_connected = False
        self.logger.info("WebSocket连接已关闭")

    def _execute_workflow(self, stop_event: Event = None, task_id: str = None) -> List[str]:
        """
        执行工作流并返回生成的图片URL列表
        :param stop_event: 停止事件
        :param task_id: 任务ID
        :return: 图片URL列表
        """
        try:
            # 确保连接
            if not self._ensure_connection():
                raise Exception("无法建立WebSocket连接")

            # 发送工作流
            self.ws.send(json.dumps(self.workflow))
            self.logger.info("工作流已发送")

            # 等待执行完成
            image_urls = []
            start_time = time.time()
            last_progress = 0
            progress_check_interval = 5  # 每5秒检查一次进度
            last_progress_check = start_time

            while True:
                if stop_event and stop_event.is_set():
                    self.logger.info("收到停止信号，中断工作流执行")
                    break

                # 检查是否超时
                if time.time() - start_time > 600:  # 10分钟超时
                    self.logger.error("工作流执行超时")
                    break

                # 定期检查进度
                current_time = time.time()
                if current_time - last_progress_check >= progress_check_interval:
                    last_progress_check = current_time
                    try:
                        history = self._get_history(task_id)
                        if history and task_id in history:
                            task_history = history[task_id]
                            progress = task_history.get('progress', 0)
                            
                            # 更新心跳时间
                            self.last_heartbeat_time = current_time
                            
                            # 如果进度达到100%，增加心跳间隔
                            if progress >= 100 and last_progress < 100:
                                self.heartbeat_interval = 120  # 增加到120秒
                                self.logger.info(f"任务进度达到100%，心跳间隔已调整为 {self.heartbeat_interval} 秒")
                            
                            last_progress = progress
                            
                            # 检查是否有输出
                            if task_history.get('outputs'):
                                self.logger.info("工作流执行完成，获取到输出")
                                image_urls = self._process_outputs(task_history['outputs'])
                                break
                    except Exception as e:
                        self.logger.debug(f"检查进度时出错: {str(e)}")

                time.sleep(1)

            return image_urls
        except Exception as e:
            self.logger.error(f"执行工作流时出错: {str(e)}")
            raise

    def _get_history(self, task_id: str = None) -> Dict:
        """
        获取任务历史记录
        :param task_id: 任务ID
        :return: 历史记录
        """
        try:
            if not self._ensure_connection():
                raise Exception("无法建立WebSocket连接")

            # 发送历史请求
            self.ws.send(json.dumps({"type": "history"}))
            
            # 等待响应
            start_time = time.time()
            wait_time = self.initial_wait_time
            retry_count = 0
            
            while retry_count < self.max_retries:
                try:
                    response = self.ws.recv()
                    if response:
                        history = json.loads(response)
                        if task_id and task_id in history:
                            self.logger.debug(f"成功获取任务 {task_id} 的历史记录")
                            return history
                        elif not task_id:
                            return history
                except Exception as e:
                    self.logger.debug(f"获取历史记录失败: {str(e)}")
                
                # 如果还没超时，继续等待
                if time.time() - start_time < self.max_wait_time:
                    time.sleep(wait_time)
                    wait_time = min(wait_time * 2, self.max_wait_time)
                    retry_count += 1
                else:
                    break
            
            self.logger.warning(f"获取历史记录超时，已重试 {retry_count} 次")
            return None
        except Exception as e:
            self.logger.error(f"获取历史记录时出错: {str(e)}")
            return None
