from openai import OpenAI
import base64
import logging
import uuid
import requests
from typing import List, Dict, Optional, Tuple
from io import BytesIO
from PIL import Image
from django.conf import settings
import tempfile
import os
import time
import openai
import httpx
import random
import numpy as np
from django.db import transaction

from common.ErrorCode import ErrorCode
from common.volcengine_tos_utils import VolcengineTOSUtils
from exception.business_exception import BusinessException
from templateImage.ImagesRequest import ImageUploadManager


logger = logging.getLogger(__name__)

class ChatGPTImageServiceNew:
    """支持新的GPT图像生成API的服务类"""

    def __init__(self):
        self.log_messages = []
        self.client = OpenAI(
            base_url=settings.CHATGPT_CONFIG_OPENAI['API_URL'],
            api_key=settings.CHATGPT_CONFIG_OPENAI['API_KEY'],
            timeout=180.0,  # 设置超时时间为60秒
            max_retries=1  # 设置最大重试次数为3次
        )

    def _fix_base64_padding(self, base64_string: str) -> str:
        """
        Fix base64 padding by adding missing '=' characters and cleaning the string
        """
        # 移除可能的空白字符
        base64_string = base64_string.strip()
        
        # 移除可能的URL编码字符
        base64_string = base64_string.replace(' ', '+')
        
        # 添加padding
        padding = len(base64_string) % 4
        if padding:
            base64_string += '=' * (4 - padding)
            
        return base64_string

    def _decode_base64_image(self, base64_string: str) -> bytes:
        """
        Safely decode base64 image data with proper error handling
        """
        try:
            # 清理和修复base64字符串
            base64_string = self._fix_base64_padding(base64_string)
            
            # 尝试解码
            try:
                return base64.b64decode(base64_string)
            except Exception as e:
                # 如果解码失败，尝试移除所有非base64字符后重试
                import re
                cleaned_string = re.sub(r'[^A-Za-z0-9+/=]', '', base64_string)
                return base64.b64decode(cleaned_string)
                
        except Exception as e:
            self.log(f"Base64 decoding failed: {str(e)}")
            raise ValueError(f"Failed to decode base64 image data: {str(e)}")

    def log(self, message: str):
        """记录处理日志"""
        logger.info(message)
        self.log_messages.append(message)

    def _validate_image_data(self, img_data: bytes) -> bool:
        """
        验证图像数据的有效性
        
        Args:
            img_data: 图像数据
            
        Returns:
            bool: 数据是否有效
        """
        try:
            # 尝试打开图像
            img = Image.open(BytesIO(img_data))
            
            # 验证图像格式
            if img.format not in ['PNG', 'JPEG', 'JPG']:
                self.log(f"不支持的图像格式: {img.format}")
                return False
                
            # 验证图像大小
            if img.size[0] < 10 or img.size[1] < 10:
                self.log(f"图像尺寸太小: {img.size}")
                return False
                
            # 验证图像模式
            if img.mode not in ['RGB', 'RGBA']:
                self.log(f"不支持的图像模式: {img.mode}")
                return False
                
            return True
        except Exception as e:
            self.log(f"图像验证失败: {str(e)}")
            return False

    def generate_image(
            self,
            prompt: str,
            image_urls: List[str] = None,
            user_id: int = None,
            conversation_id: int = None,
            upload_record_id: int = None,
            seed: int = None,
            size: str = "1024x1024"
    ) -> Dict:
        """
        生成图像并存储结果
        """
        self.log_messages = []  # 重置日志
        try:
            self.log("开始图像生成流程")

            result = self.client.images.generate(
                model=settings.CHATGPT_CONFIG_OPENAI['MODEL'],
                prompt=prompt,
                size=size
            )

            # 处理返回结果
            if not result.data:
                raise ValueError("API未返回图像数据")

            image_data = result.data[0]
            image_base64 = image_data.b64_json
            image_url = image_data.url

            # 获取图像数据
            img_data = None
            if image_base64:
                try:
                    img_data = self._decode_base64_image(image_base64)
                    self.log("成功解码base64图像数据")
                except ValueError as e:
                    self.log(f"Base64解码失败，尝试使用URL: {str(e)}")
                    if not image_url:
                        raise ValueError("无法获取有效的图像数据")
                    try:
                        response = requests.get(image_url, timeout=30)
                        response.raise_for_status()
                        img_data = response.content
                        self.log("成功从URL获取图像数据")
                    except Exception as url_error:
                        self.log(f"URL获取失败: {str(url_error)}")
                        raise ValueError("无法获取有效的图像数据")
            elif image_url:
                try:
                    response = requests.get(image_url, timeout=30)
                    response.raise_for_status()
                    img_data = response.content
                    self.log("成功从URL获取图像数据")
                except Exception as e:
                    self.log(f"URL获取失败: {str(e)}")
                    raise ValueError("无法获取有效的图像数据")
            else:
                raise ValueError("API未返回有效的图像数据")

            if not img_data:
                raise ValueError("无法获取有效的图像数据")

            # 验证图像数据
            if not self._validate_image_data(img_data):
                raise ValueError("图像数据验证失败")

            # 存储到OSS
            try:
                oss_url, filename = self._store_to_oss(img_data, upload_record_id)
                self.log(f"图像已存储到OSS: {oss_url}")
            except Exception as e:
                self.log(f"OSS存储失败: {str(e)}")
                raise ValueError(f"图像存储失败: {str(e)}")

            # 更新数据库记录
            if upload_record_id:
                try:
                    self._update_database_record(
                        upload_record_id=upload_record_id,
                        image_url=oss_url,
                        image_name=filename,
                        prompt=prompt,
                        user_id=user_id,
                        conversation_id=conversation_id,
                        seed=seed,
                        image_paths=image_urls
                    )
                except Exception as e:
                    self.log(f"数据库更新失败: {str(e)}")
                    # 继续执行，因为图像已经成功生成和存储

            return {
                'success': True,
                'image_url': oss_url,
                'image_name': filename,
                'prompt': prompt,
                'seed_used': seed,
                'model_used': settings.CHATGPT_CONFIG_OPENAI['MODEL'],
                'size': size,
                'logs': self.log_messages
            }

        except Exception as e:
            error_msg = f"图像生成失败: {str(e)}"
            self.log(error_msg)
            logger.error(error_msg, exc_info=True)
            
            # 如果上传记录ID存在，标记为失败
            if upload_record_id:
                try:
                    ImageUploadManager.mark_as_failed(
                        record_id=upload_record_id,
                        error_message=error_msg
                    )
                except Exception as db_error:
                    self.log(f"更新失败状态也失败: {str(db_error)}")
            
            return {
                'success': False,
                'error': str(e),
                'message': '图像生成失败',
                'logs': self.log_messages
            }

    def _download_image(self, url):
        """
        从URL下载图片到临时文件
        
        Args:
            url (str): 图片URL
            
        Returns:
            str: 临时文件路径
        """
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            temp_path = temp_file.name
            
            # 保存图片
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return temp_path
        except Exception as e:
            logger.error(f"下载图片失败: {str(e)}")
            raise BusinessException(error_code=ErrorCode.FAIL, data='', errors=f"下载图片失败: {str(e)}")

    def _is_url(self, path):
        """
        判断是否为URL
        
        Args:
            path (str): 路径或URL
            
        Returns:
            bool: 是否为URL
        """
        return path.startswith(('http://', 'https://'))

    def _generate_random_seed(self):
        """生成随机种子"""
        return random.randint(1, 2147483647)  # 使用32位整数的最大值作为上限

    def edit_image(
            self,
            prompt: str,
            image_paths: List[str] = None,
            mask_path: str = None,
            user_id: int = None,
            conversation_id: int = None,
            upload_record_id: int = None,
            operation_type: str = "edit",  # 操作类型：generate/edit/mask_edit
            size: str = "1024x1024"  # 添加size参数，默认值为1024x1024
    ) -> Dict:
        """
        根据不同的操作类型处理图像：
        1. generate: 纯文本生成图像（不需要输入图片）
        2. edit: 基于输入图片进行编辑（可以是多张图片合并）
        3. mask_edit: 使用遮罩进行图像编辑
        
        Args:
            prompt: 生成提示词
            image_paths: 图片路径列表（可选，对于生成模式不需要）
            mask_path: 遮罩图片路径（可选，仅用于mask_edit模式）
            user_id: 用户ID
            conversation_id: 会话ID
            upload_record_id: 上传记录ID
            operation_type: 操作类型（generate/edit/mask_edit）
            
        Returns:
            Dict: 包含处理结果的字典
        """
        temp_files = []
        retry_count = 0
        max_retries = 3
        base_delay = 2  # 基础延迟时间（秒）
        seed = self._generate_random_seed()  # 生成随机种子，仅用于数据库记录

        # 根据操作类型选择合适的处理方法
        if operation_type == "generate":
            # 如果是纯文本生成，直接调用generate_image方法
            return self.generate_image(
                prompt=prompt,
                user_id=user_id,
                conversation_id=conversation_id,
                upload_record_id=upload_record_id,
                seed=seed
            )
        elif operation_type == "edit" and (not image_paths or len(image_paths) > 1):
            # 如果是多图编辑或没有提供图片，调用merge_images方法
            if not image_paths:
                error_msg = "多图编辑模式需要至少提供一张图片"
                self.log(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'message': '图像编辑失败',
                    'logs': self.log_messages
                }
            elif len(image_paths) > 1:
                # 多图编辑模式（合并多张图片）
                return self.merge_images(
                    prompt=prompt,
                    image_paths=image_paths,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    upload_record_id=upload_record_id,
                    size=size
                )

        # 以下为单图编辑模式（可能带遮罩）
        while retry_count < max_retries:
            try:
                self.log(f"开始图像编辑流程, 操作类型: {operation_type}")

                # 处理图片路径
                processed_image_paths = []
                if image_paths:
                    for path in image_paths:
                        if self._is_url(path):
                            temp_path = self._download_image(path)
                            temp_files.append(temp_path)
                            processed_image_paths.append(temp_path)
                        else:
                            processed_image_paths.append(path)
                
                # 确保至少有一张输入图片
                if not processed_image_paths:
                    error_msg = "单图编辑模式需要提供至少一张图片"
                    self.log(error_msg)
                    return {
                        'success': False,
                        'error': error_msg,
                        'message': '图像编辑失败',
                        'logs': self.log_messages
                    }

                # 处理遮罩图片
                processed_mask_path = None
                if operation_type == "mask_edit" and mask_path:
                    if self._is_url(mask_path):
                        temp_path = self._download_image(mask_path)
                        temp_files.append(temp_path)
                        processed_mask_path = temp_path
                    else:
                        processed_mask_path = mask_path

                # 打开图片文件 - 只使用第一张图片
                image_file = open(processed_image_paths[0], "rb")
                mask_file = None
                
                # 只有在mask_edit模式下才打开遮罩文件
                if operation_type == "mask_edit" and processed_mask_path:
                    try:
                        mask_file = open(processed_mask_path, "rb")
                    except Exception as e:
                        self.log(f"打开遮罩文件失败: {str(e)}")
                        # 关闭已打开的文件
                        image_file.close()
                        return {
                            'success': False,
                            'error': f"打开遮罩文件失败: {str(e)}",
                            'message': '图像编辑失败',
                            'logs': self.log_messages
                        }

                try:
                    # 根据操作类型和参数调用不同的API
                    if operation_type == "mask_edit" and mask_file:
                        # 带遮罩的编辑模式
                        self.log("使用带遮罩的编辑模式")
                        result = self.client.images.edit(
                            model=settings.CHATGPT_CONFIG_OPENAI['MODEL'],
                            image=image_file,
                            mask=mask_file,
                            prompt=prompt,
                            size=size
                        )
                    else:
                        # 不带遮罩的编辑模式
                        self.log("使用不带遮罩的编辑模式")
                        result = self.client.images.edit(
                            model=settings.CHATGPT_CONFIG_OPENAI['MODEL'],
                            image=image_file,
                            prompt=prompt,
                            size=size
                        )

                    # 处理返回结果
                    if not result.data:
                        raise ValueError("API未返回图像数据")

                    image_data = result.data[0]
                    image_base64 = image_data.b64_json
                    image_url = image_data.url

                    # 获取图像数据
                    if image_base64:
                        img_data = base64.b64decode(image_base64)
                    elif image_url:
                        response = requests.get(image_url)
                        response.raise_for_status()
                        img_data = response.content
                    else:
                        raise ValueError("API未返回有效的图像数据")

                    # 存储到OSS
                    oss_url, filename = self._store_to_oss(img_data, upload_record_id)
                    self.log(f"编辑后的图像已存储到OSS: {oss_url}")

                    

                    # 更新数据库记录
                    if upload_record_id:
                        self._update_database_record(
                            upload_record_id=upload_record_id,
                            image_url=oss_url,
                            image_name=filename,
                            prompt=prompt,
                            user_id=user_id,
                            conversation_id=conversation_id,
                            seed=seed,
                            image_paths=image_paths
                        )

                    return {
                        'success': True,
                        'image_url': oss_url,
                        'image_name': filename,
                        'prompt': prompt,
                        'model_used': settings.CHATGPT_CONFIG_OPENAI['MODEL'],
                        'seed_used': seed,  # 在返回结果中包含使用的种子
                        'operation_type': operation_type,
                        'size': size,
                        'logs': self.log_messages
                    }

                except Exception as e:
                    error_msg = f"图像编辑失败: {str(e)}"
                    self.log(error_msg)
                    logger.error(error_msg, exc_info=True)
                    
                    # 如果是连接错误，进行重试
                    # if isinstance(e, (openai.APIConnectionError, httpx.RemoteProtocolError)):
                    #     retry_count += 1
                    #     if retry_count < max_retries:
                    #         delay = base_delay * (2 ** (retry_count - 1))  # 指数退避
                    #         self.log(f"连接错误，{delay}秒后进行第{retry_count + 1}次重试")
                    #         time.sleep(delay)
                    #         continue
                    
                    return {
                        'success': False,
                        'error': str(e),
                        'message': '图像编辑失败',
                        'operation_type': operation_type,
                        'size': size,
                        'logs': self.log_messages
                    }
                finally:
                    # 关闭所有打开的文件
                    if image_file:
                        image_file.close()
                    if mask_file:
                        mask_file.close()

            except Exception as e:
                error_msg = f"图像编辑失败: {str(e)}"
                self.log(error_msg)
                logger.error(error_msg, exc_info=True)
                return {
                    'success': False,
                    'error': str(e),
                    'message': '图像编辑失败',
                    'operation_type': operation_type,
                    'size': size,
                    'logs': self.log_messages
                }
            finally:
                # 清理临时文件
                for temp_file in temp_files:
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    except Exception as e:
                        self.log(f"清理临时文件失败: {str(e)}")
                        pass

    def _store_to_oss(self, image_data: bytes, upload_record_id: int = None) -> Tuple[str, str]:
        """存储图像到OSS"""
        try:
            filename = f"{uuid.uuid4()}.png"
            # 验证图像数据有效性
            try:
                Image.open(BytesIO(image_data)).verify()
            except Exception as e:
                if upload_record_id:
                    ImageUploadManager.mark_as_failed(
                        record_id=upload_record_id,
                        error_message=f"无效的图像数据: {str(e)}"
                    )
                raise ValueError(f"无效的图像数据: {str(e)}")

            tos_utils = VolcengineTOSUtils()
            image_url = tos_utils.upload_image(object_name=filename, file_data=image_data)
            return image_url, filename

        except Exception as e:
            self.log(f"OSS存储失败: {str(e)}")
            if upload_record_id:
                ImageUploadManager.mark_as_failed(
                    record_id=upload_record_id,
                    error_message=f"OSS存储失败: {str(e)}"
                )
            raise ValueError(f"OSS存储失败: {str(e)}")

    def _update_database_record(
            self,
            upload_record_id: int,
            image_url: str,
            image_name: str,
            prompt: str,
            user_id: int = None,
            conversation_id: int = None,
            seed: int = None,
            image_paths: List[str] = None
    ):
        """更新数据库记录"""
        try:
            # 格式化图片列表数据
            image_list = ""
            if image_paths:
                # 仅保留文件名或URL，不保存临时文件的完整路径
                formatted_paths = []
                for path in image_paths:
                    # 如果是URL，直接保存
                    if self._is_url(path):
                        formatted_paths.append(path)
                    else:
                        # 如果是本地路径，只保留文件名
                        filename = os.path.basename(path)
                        formatted_paths.append(filename)
                
                # 将路径列表转换为以逗号分隔的字符串
                image_list = ",".join(formatted_paths)
                self.log(f"保存图片路径列表: {image_list}")

            # 标记记录为已完成
            ImageUploadManager.mark_as_completed(
                record_id=upload_record_id,
                image_url=image_url,
                image_name=image_name
            )

            # 更新详细记录
            ImageUploadManager.update_record_by_id(
                record_id=upload_record_id,
                image_url=image_url,
                image_name=image_name,
                prompt=prompt,
                model_used=settings.CHATGPT_CONFIG_OPENAI['MODEL'],
                user_id=user_id,
                conversation_id=conversation_id,
                seed_used=seed,
                image_list=image_list  # 保存图片列表
            )

            self.log(f"数据库记录已更新: {image_url}")
        except Exception as e:
            self.log(f"数据库更新失败: {str(e)}")
            try:
                ImageUploadManager.mark_as_failed(
                    record_id=upload_record_id,
                    error_message=f"数据库更新失败: {str(e)}"
                )
            except Exception as db_error:
                self.log(f"标记失败状态也失败: {str(db_error)}")
            raise ValueError(f"数据库更新失败: {str(e)}")

    def merge_images(self, prompt, image_paths, user_id, conversation_id=None, upload_record_id=None, size: str = "1024x1024"):
        """
        合并多张图片并进行编辑
        
        Args:
            prompt (str): 图片生成提示词
            image_paths (list): 图片路径列表
            user_id (int): 用户ID
            conversation_id (int, optional): 会话ID
            upload_record_id (int, optional): 上传记录ID
            
        Returns:
            dict: 包含处理结果的字典
        """
        temp_files = []
        seed = self._generate_random_seed()  # 生成随机种子
        original_paths = image_paths.copy()  # 保存原始路径，用于数据库记录
        
        try:
            self.log(f"开始合并图片流程，图片数量: {len(image_paths)}")
            
            # 处理图片路径
            processed_image_paths = []
            for path in image_paths:
                if self._is_url(path):
                    temp_path = self._download_image(path)
                    temp_files.append(temp_path)
                    processed_image_paths.append(temp_path)
                else:
                    processed_image_paths.append(path)

            # 读取所有图片
            images = []
            for path in processed_image_paths:
                try:
                    image = Image.open(path)
                    # 确保所有图片都转换为RGB模式
                    image = image.convert('RGB')
                    images.append(image)
                except Exception as e:
                    error_msg = f"读取图片失败: {str(e)}"
                    self.log(error_msg)
                    logger.error(error_msg)
                    return {
                        'success': False,
                        'error': error_msg,
                        'message': '合并图片失败',
                        'operation_type': 'edit',
                        'size': size,
                        'logs': self.log_messages
                    }

            # 确保所有图片尺寸一致
            base_size = images[0].size
            for i in range(1, len(images)):
                if images[i].size != base_size:
                    self.log(f"调整图片 {i+1} 尺寸从 {images[i].size} 到 {base_size}")
                    images[i] = images[i].resize(base_size, Image.Resampling.LANCZOS)

            # 创建合并后的图片
            merged_image = Image.new('RGB', base_size)
            
            # 计算每张图片的权重
            weight = 1.0 / len(images)
            
            # 合并图片
            try:
                # 将图片转换为numpy数组
                merged_array = None
                for i, image in enumerate(images):
                    img_array = np.array(image)
                    # 应用权重
                    img_array = img_array * weight
                    # 添加到合并图片
                    if i == 0:
                        merged_array = img_array
                    else:
                        merged_array += img_array

                # 将numpy数组转回PIL图片
                merged_image = Image.fromarray(merged_array.astype(np.uint8))
            except Exception as e:
                error_msg = f"合并图片时出错: {str(e)}"
                self.log(error_msg)
                logger.error(error_msg, exc_info=True)
                return {
                    'success': False,
                    'error': error_msg,
                    'message': '图片合并失败',
                    'operation_type': 'edit',
                    'size': size,
                    'logs': self.log_messages
                }

            # 保存合并后的图片
            temp_merged_path = f"temp_merged_{upload_record_id if upload_record_id else uuid.uuid4()}.png"
            merged_image.save(temp_merged_path)
            temp_files.append(temp_merged_path)
            self.log(f"已创建合并图片: {temp_merged_path}")

            # 使用合并后的图片进行编辑（不带遮罩）
            self.log("使用合并图片进行编辑")
            # 调用edit_image方法，但传递原始图片路径列表用于数据库记录
            edit_result = self.edit_image(
                prompt=prompt,
                image_paths=[temp_merged_path],
                user_id=user_id,
                conversation_id=conversation_id,
                upload_record_id=upload_record_id,
                operation_type="edit",  # 强制使用edit模式
                size=size
            )
            
            # 如果编辑成功，手动更新数据库记录中的image_list字段
            if edit_result['success'] and upload_record_id:
                try:
                    # 将原始图片路径保存到数据库
                    image_list = ",".join(original_paths)
                    ImageUploadManager.update_record_by_id(
                        record_id=upload_record_id,
                        image_list=image_list
                    )
                    self.log(f"已更新数据库中的图片列表: {image_list}")
                except Exception as e:
                    self.log(f"更新图片列表失败: {str(e)}")

            # 确保结果中包含使用的种子和原始图片路径
            if edit_result['success']:
                edit_result['seed_used'] = seed
                edit_result['merged_image'] = True  # 标记为合并图片结果
                edit_result['original_image_paths'] = original_paths  # 记录原始图片路径

            return edit_result

        except Exception as e:
            error_msg = f"合并图片失败: {str(e)}"
            self.log(error_msg)
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'message': '合并图片失败',
                'operation_type': 'edit',
                'size': size,
                'logs': self.log_messages
            }
        finally:
            # 清理临时文件
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        self.log(f"已删除临时文件: {temp_file}")
                except Exception as e:
                    self.log(f"清理临时文件失败: {str(e)}")
                    pass 