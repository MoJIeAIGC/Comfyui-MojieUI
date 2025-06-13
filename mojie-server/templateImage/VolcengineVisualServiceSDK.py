import logging
import base64
import os
import datetime
import json
import tempfile
import uuid
from typing import Dict, Optional, List, Any, Tuple
from urllib.parse import urlparse
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

from volcengine.visual.VisualService import VisualService
from django.conf import settings
from rest_framework.generics import get_object_or_404

from common.volcengine_tos_utils import VolcengineTOSUtils
from templateImage.ImagesRequest import ImageUploadManager
from templateImage.models import templateImage, ImageUploadRecord
from user.models import SysUser

logger = logging.getLogger(__name__)

def get_volcengine_ak():
    """获取火山引擎访问密钥"""
    try:
        return settings.VOLCENGINE_VISUAL_CONFIG['ACCESS_KEY']
    except (AttributeError, KeyError):
        logger.error("无法从设置中获取VOLCENGINE_ACCESS_KEY")
        return None

def get_volcengine_sk():
    """获取火山引擎访问密钥"""
    try:
        return settings.VOLCENGINE_VISUAL_CONFIG['SECRET_KEY']
    except (AttributeError, KeyError):
        logger.error("无法从设置中获取VOLCENGINE_SECRET_KEY")
        return None

class VolcengineVisualServiceSDK:
    """火山引擎视觉服务SDK封装类"""

    def __init__(self):
        """初始化火山引擎视觉服务"""
        try:
            from volcengine.visual.VisualService import VisualService
            import logging
            import json
            
            self.logger = logging.getLogger('VolcengineVisualService')
            
            # 获取配置信息
            self.ak = get_volcengine_ak()
            self.sk = get_volcengine_sk()
            self.action = "CVProcess"  # 使用固定的API动作
            self.version = "2022-08-31"  # 使用固定的API版本

            # 初始化服务
            self.visual_service = VisualService()
            self.visual_service.set_ak(self.ak)
            self.visual_service.set_sk(self.sk)
            
            # 设置API信息
            self.visual_service.set_api_info(self.action, self.version)
            
            # 设置请求超时
            self.visual_service.set_host("visual.volcengineapi.com")
            self.visual_service.set_connection_timeout(30)
            self.visual_service.set_socket_timeout(30)
            
            self.logger.info("火山引擎视觉服务初始化成功")
            
        except ImportError as e:
            self.logger.error(f"导入Volcengine SDK失败: {str(e)}")
            raise ImportError(f"未安装Volcengine SDK: {str(e)}")
        except Exception as e:
            self.logger.error(f"初始化Volcengine服务失败: {str(e)}")
            raise Exception(f"初始化Volcengine服务失败: {str(e)}")

    def generate_image(
            self,
            prompt: str,
            user_id: int,
            conversation_id: Optional[int] = None,
            upload_record_id: Optional[int] = None,
            image_urls: Optional[List[str]] = None,
            **kwargs
    ) -> Dict:
        """
        生成图像并存储结果
        
        参数:
        - prompt: 生成提示词
        - user_id: 用户ID
        - conversation_id: 会话ID (可选)
        - upload_record_id: 上传记录ID (可选)
        - image_urls: 输入图片URL列表 (可选)
        
        扩展参数 (通过 **kwargs):
        - req_key: API请求键，默认为 "high_aes_general_v30l_zt2i"
        - seed: 随机种子，默认为 -1 (随机)
        - scale: 缩放比例，默认为 2.5
        - width: 图片宽度，默认为 1328
        - height: 图片高度，默认为 1328
        - add_logo: 是否添加logo，默认为 False
        - position: logo位置，默认为 0
        - language: logo语言，默认为 0
        - opacity: logo透明度，默认为 0.3
        - logo_text: logo文本内容，默认为 ""
        
        返回:
        - 包含生成结果的字典
        """
        original_url = None
        request_id = "unknown"
        
        try:
            logger.info(f"开始调用火山引擎文生图API, prompt={prompt}")
            
            # 从kwargs中获取req_key，如果未指定则使用默认值
            req_key = kwargs.get("req_key", "high_aes_general_v30l_zt2i")
            
            # 参数构建 - 基于用户输入的可变参数
            form = {
                "req_key": req_key,  # 可以在kwargs中指定不同的req_key
                "prompt": prompt,
                "seed": kwargs.get("seed", -1),
                "scale": kwargs.get("scale", 2.5),
                "width": kwargs.get("width", 1328),
                "height": kwargs.get("height", 1328),
                "return_url": True,  # 始终设为True以获取URL
                "logo_info": {
                    "add_logo": kwargs.get("add_logo", False),
                    "position": kwargs.get("position", 0),
                    "language": kwargs.get("language", 0),
                    "opacity": kwargs.get("opacity", 0.3),
                    "logo_text_content": kwargs.get("logo_text", "")
                }
            }
            
            # 添加其他可能的参数
            for key, value in kwargs.items():
                if key not in ["req_key", "seed", "scale", "width", "height", "add_logo", 
                              "position", "language", "opacity", "logo_text"] and not key.startswith("_"):
                    form[key] = value
            
            logger.info(f"火山引擎API请求参数: {json.dumps(form, ensure_ascii=False)}")
            
            # 调用文生图API
            resp = self.visual_service.cv_json_api(self.action, form)
            logger.info(f"火山引擎文生图API响应状态: code={resp.get('code', 'unknown')}, message={resp.get('message', 'unknown')}")
            
            # 检查响应
            if isinstance(resp, dict) and resp.get('code', -1) != 10000:  # 成功状态码是10000
                error_message = f"火山引擎文生图API调用失败: {resp.get('message', '未知错误')}, 请求ID: {resp.get('request_id', 'unknown')}"
                logger.error(error_message)
                
                # 创建一个错误结果图像
                if upload_record_id:
                    # 生成错误图像
                    image_url, image_name = self._store_to_oss(self._generate_empty_image(), upload_record_id)
                    
                    # 保存记录
                    if user_id:
                        user_info = get_object_or_404(SysUser, id=user_id)
                        self._save_to_database(
                            image_name=image_name,
                            image_url=image_url,
                            prompt=prompt,
                            user_info=user_info,
                            user_id=user_id,
                            image_urls=image_urls,
                            conversation_id=conversation_id,
                            upload_record_id=upload_record_id,
                            seed_used=kwargs.get("seed", -1),
                            is_error=True
                        )
                
                raise ValueError(error_message)
            
            # 获取生成的图像URL
            if isinstance(resp, dict) and "data" in resp and "image_urls" in resp["data"] and len(resp["data"]["image_urls"]) > 0:
                # 获取图片URL
                original_url = resp["data"]["image_urls"][0]
                request_id = resp.get("request_id", "")
                logger.info(f"成功获取火山引擎生成的图片URL: {original_url}, 请求ID: {request_id}")
                
                try:
                    # 下载图片
                    image_response = requests.get(original_url, timeout=30)
                    if image_response.status_code != 200:
                        raise ValueError(f"下载图片失败: HTTP {image_response.status_code}")
                    
                    image_data = image_response.content
                    
                    # 提取文件名
                    image_name = f"volcengine_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                    if request_id:
                        image_name = f"volcengine_{request_id}.png"
                    
                    # 存储到OSS
                    oss_image_url, image_path = self._store_to_oss(image_data, upload_record_id)
                    logger.info(f"成功将图片保存到OSS: {oss_image_url}")
                    
                    # 保存到数据库
                    if user_id:
                        user_info = get_object_or_404(SysUser, id=user_id)
                        self._save_to_database(
                            image_name=image_name,
                            image_url=oss_image_url,
                            prompt=prompt,
                            user_info=user_info,
                            user_id=user_id,
                            image_urls=image_urls,
                            conversation_id=conversation_id,
                            upload_record_id=upload_record_id,
                            seed_used=kwargs.get("seed", -1)
                        )
                    
                    return {
                        'success': True,
                        'image_url': oss_image_url,
                        'image_name': image_name,
                        'prompt': prompt,
                        'original_response': resp,  # 可选：包含原始响应以供调试
                        'request_id': request_id
                    }
                except Exception as download_error:
                    logger.error(f"下载或处理图片时发生错误: {str(download_error)}", exc_info=True)
                    # 仍然返回图片URL给客户端
                    return {
                        'success': True,
                        'image_url': original_url,  # 返回原始URL
                        'image_name': f"volcengine_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.png",
                        'prompt': prompt,
                        'error': f"图片处理错误: {str(download_error)}",
                        'original_url': True,  # 标记这是原始URL
                        'request_id': request_id
                    }
            else:
                error_msg = f"处理图像响应失败: 无法解析图像URL，响应内容: {json.dumps(resp) if isinstance(resp, dict) else str(resp)}"
                logger.error(error_msg)
                
                # 创建一个错误结果图像
                if upload_record_id:
                    # 生成错误图像
                    image_url, image_name = self._store_to_oss(self._generate_empty_image(), upload_record_id)
                    
                    # 保存记录
                    if user_id:
                        user_info = get_object_or_404(SysUser, id=user_id)
                        self._save_to_database(
                            image_name=image_name,
                            image_url=image_url,
                            prompt=prompt,
                            user_info=user_info,
                            user_id=user_id,
                            image_urls=image_urls,
                            conversation_id=conversation_id,
                            upload_record_id=upload_record_id,
                            seed_used=kwargs.get("seed", -1),
                            is_error=True
                        )
                
                raise ValueError(error_msg)
                
        except Exception as e:
            logger.error(f"图像生成失败: {str(e)}", exc_info=True)
            if upload_record_id:
                # 尝试创建空白图像
                try:
                    # 生成空白图像并存储到OSS
                    empty_image = self._generate_empty_image()
                    image_url, image_name = self._store_to_oss(empty_image, upload_record_id)
                    
                    # 尝试保存到数据库
                    if user_id:
                        try:
                            user_info = get_object_or_404(SysUser, id=user_id)
                            self._save_to_database(
                                image_name=image_name,
                                image_url=image_url,
                                prompt=prompt,
                                user_info=user_info,
                                user_id=user_id,
                                image_urls=image_urls,
                                conversation_id=conversation_id,
                                upload_record_id=upload_record_id,
                                seed_used=kwargs.get("seed", -1),
                                is_error=True
                            )
                        except Exception as db_error:
                            logger.error(f"保存错误图像到数据库失败: {str(db_error)}")
                    
                    return {
                        'success': False,
                        'error': str(e),
                        'message': '图像生成失败',
                        'prompt': prompt,
                        'image_url': image_url,  # 返回错误图像URL
                        'image_name': image_name,
                        'is_error_image': True
                    }
                except Exception as img_error:
                    logger.error(f"生成错误图像失败: {str(img_error)}")
                    
                ImageUploadManager.mark_as_failed(
                    record_id=upload_record_id,
                    error_message=f"图像生成失败: {str(e)}"
                )
            
            # 如果有原始URL，尝试返回
            if original_url:
                return {
                    'success': False,
                    'error': str(e),
                    'message': '图像生成失败，但有原始URL',
                    'prompt': prompt,
                    'image_url': original_url,
                    'original_url': True,
                    'request_id': request_id
                }
                
            return {
                'success': False,
                'error': str(e),
                'message': '图像生成失败',
                'prompt': prompt
            }

    def _store_to_oss(self, image_data: bytes, upload_record_id: Optional[int] = None) -> tuple:
        """将图像数据存储到OSS
        
        Args:
            image_data: 图像二进制数据
            upload_record_id: 上传记录ID (可选)
            
        Returns:
            (str, str): 图像URL和图像路径
        """
        try:
            # 生成随机文件名
            now = datetime.datetime.now()
            filename = f"volcengine_{now.strftime('%Y%m%d%H%M%S')}.png"
            
            # 验证图像数据有效性
            try:
                from PIL import Image
                from io import BytesIO
                Image.open(BytesIO(image_data)).verify()
            except Exception as e:
                logger.error(f"无效的图像数据: {str(e)}")
                if upload_record_id:
                    try:
                        ImageUploadManager.mark_as_failed(
                            record_id=upload_record_id,
                            error_message=f"无效的图像数据: {str(e)}"
                        )
                    except Exception as db_error:
                        logger.error(f"更新记录状态失败: {str(db_error)}")
                # 生成空白图像作为替代
                empty_image = self._generate_empty_image()
                tos_utils = VolcengineTOSUtils()
                image_url = tos_utils.upload_image(object_name=filename, file_data=empty_image)
                return image_url, filename
            
            # 存储到OSS
            tos_utils = VolcengineTOSUtils()
            image_url = tos_utils.upload_image(object_name=filename, file_data=image_data)
            
            # 如果有上传记录，更新记录状态
            if upload_record_id:
                try:
                    ImageUploadManager.update_oss_info(
                        record_id=upload_record_id,
                        oss_url=image_url
                    )
                except Exception as e:
                    logger.error(f"更新OSS信息失败: {str(e)}")
                    try:
                        ImageUploadManager.mark_as_failed(
                            record_id=upload_record_id,
                            error_message=f"更新OSS信息失败: {str(e)}"
                        )
                    except Exception as db_error:
                        logger.error(f"更新记录状态失败: {str(db_error)}")
            
            return image_url, filename
                
        except Exception as e:
            logger.error(f"存储图像到OSS失败: {str(e)}", exc_info=True)
            if upload_record_id:
                try:
                    ImageUploadManager.mark_as_failed(
                        record_id=upload_record_id,
                        error_message=f"存储图像到OSS失败: {str(e)}"
                    )
                except Exception as db_error:
                    logger.error(f"更新记录状态失败: {str(db_error)}")
            # 上传失败时，创建一个空白图像并上传
            try:
                empty_image = self._generate_empty_image()
                filename = f"error_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                tos_utils = VolcengineTOSUtils()
                image_url = tos_utils.upload_image(object_name=filename, file_data=empty_image)
                return image_url, filename
            except Exception as e2:
                logger.error(f"创建空白图像也失败: {str(e2)}")
                raise ValueError(f"图像存储完全失败: {str(e)} -> {str(e2)}")
                
    def _generate_empty_image(self) -> bytes:
        """生成一个空白的错误图像"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            from io import BytesIO
            
            # 创建空白图像
            width, height = 800, 600
            image = Image.new('RGB', (width, height), color=(255, 255, 255))
            draw = ImageDraw.Draw(image)
            
            # 添加错误文本
            error_text = "图像生成失败"
            try:
                # 尝试使用系统字体
                font = ImageFont.truetype("arial.ttf", 40)
            except:
                # 如果没有可用字体，使用默认字体
                font = ImageFont.load_default()
                
            # 计算文本位置使其居中
            text_width = draw.textlength(error_text, font=font)
            text_position = ((width - text_width) / 2, height / 2 - 20)
            
            # 绘制文本
            draw.text(text_position, error_text, fill=(255, 0, 0), font=font)
            
            # 转换为字节流
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"生成空白图像失败: {str(e)}")
            # 如果连PIL也不可用，生成一个最小的PNG图像
            return bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010100000000376ef9240000001049444154789c626001000000ffff03000006000557bfabd40000000049454e44ae426082")  # 1x1透明PNG

    def _save_to_database(
            self,
            image_name: str,
            image_url: str,
            prompt: str,
            user_info: SysUser,
            user_id: int,
            image_urls: Optional[List[str]],
            conversation_id: Optional[int],
            upload_record_id: Optional[int],
            seed_used: int = -1,
            is_error: bool = False
    ):
        """保存记录到数据库
        
        Args:
            image_name: 图像名称
            image_url: 图像URL
            prompt: 提示词
            user_info: 用户信息
            user_id: 用户ID
            image_urls: 原始图像URL列表 (可选)
            conversation_id: 会话ID (可选)
            upload_record_id: 上传记录ID (可选)
            seed_used: 使用的种子值 (可选)
            is_error: 是否为错误图像 (可选)
        """
        try:
            # 保存到templateImage表
            method_sub = "ai_image_error" if is_error else "ai_image"
            
            templateImage.objects.create(
                image_name=image_name,
                image_address=image_url,
                description=prompt + (" [生成失败]" if is_error else ""),
                image_method="volcengine_generation",
                method_sub=method_sub,
                userImage=user_info,
                isDelete=0
            )

            # 更新上传记录
            if upload_record_id:
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                images_url = ",".join(image_urls) if image_urls else ""

                # 如果是错误图像，标记为失败
                if is_error:
                    ImageUploadManager.mark_as_failed(
                        record_id=upload_record_id,
                        error_message=f"图像生成失败，已创建错误图像"
                    )
                else:
                    ImageUploadManager.mark_as_processed(
                        record_id=upload_record_id,
                        result_url=image_url,
                        seed_used=seed_used
                    )

                ImageUploadManager.update_record_by_id(
                    record_id=upload_record_id,
                    image_url=image_url,
                    image_name=image_name,
                    prompt=prompt + (" [生成失败]" if is_error else ""),
                    model_used="volcengine_generation",
                    user_id=user_id,
                    image_list=images_url,
                    conversation_id=conversation_id,
                    upload_time=current_time
                )

        except Exception as e:
            logger.error(f"数据库保存失败: {str(e)}")
            if upload_record_id:
                ImageUploadManager.mark_as_failed(
                    record_id=upload_record_id,
                    error_message=f"数据库保存失败: {str(e)}"
                )
            raise 