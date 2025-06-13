import base64
import logging
import uuid
import requests
import time
import json
from typing import List, Dict, Optional, Tuple
from io import BytesIO
from PIL import Image
from django.conf import settings
import numpy as np

from common.BaiduTranslateService import BaiduTranslateService
from common.ErrorCode import ErrorCode
from common.volcengine_tos_utils import VolcengineTOSUtils
from exception.business_exception import BusinessException
from templateImage.ImagesRequest import ImageUploadManager

logger = logging.getLogger(__name__)

class FluxKontextProService:
    """Flux Kontext Pro API 图像生成服务"""

    def __init__(self):
        self.log_messages = []
        self.api_url = settings.FLUX_KONEXT_PRO_URL
        self.max_retries = 3
        self.polling_interval = 2  # 轮询间隔（秒）

    def log(self, message: str):
        """记录处理日志"""
        logger.info(message)
        self.log_messages.append(message)

    def _validate_image_data(self, img_data: bytes) -> bool:
        """验证图像数据的有效性"""
        try:
            img = Image.open(BytesIO(img_data))
            if img.format not in ['PNG', 'JPEG', 'JPG']:
                self.log(f"不支持的图像格式: {img.format}")
                return False
            if img.size[0] < 10 or img.size[1] < 10:
                self.log(f"图像尺寸太小: {img.size}")
                return False
            if img.mode not in ['RGB', 'RGBA']:
                self.log(f"不支持的图像模式: {img.mode}")
                return False
            return True
        except Exception as e:
            self.log(f"图像验证失败: {str(e)}")
            return False

    def _download_image(self, url: str) -> bytes:
        """从URL下载图片"""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # 验证确实是图像
            if 'image/' not in response.headers.get('Content-Type', ''):
                raise ValueError("URL未返回图像内容")
                
            return response.content
        except Exception as e:
            self.log(f"图像下载失败: {str(e)}")
            raise BusinessException(error_code=ErrorCode.FAIL, data='', errors=f"下载图片失败: {str(e)}")

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
                image_list = ",".join(image_paths)
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
                user_id=user_id,
                conversation_id=conversation_id,
                seed_used=seed,
                image_list=image_list
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

    def _poll_result(self, polling_url: str, max_retries: int = 60) -> Dict:
        """轮询获取结果"""
        retry_count = 0
        self.log(f"polling_url结果: {polling_url}")
        while retry_count < max_retries:
            try:
                response = requests.get(polling_url, timeout=10)  # 设置单次请求超时
                response.raise_for_status()
                result = response.json()
                
                if result.get('status') == 'Ready':
                    return result
                elif result.get('status') == 'Failed':
                    raise ValueError(f"任务处理失败: {result.get('details', '未知错误')}")
                
                # 等待后继续轮询
                time.sleep(self.polling_interval)
                retry_count += 1
                
            except requests.exceptions.Timeout:
                self.log(f"轮询请求超时，重试中... ({retry_count + 1}/{max_retries})")
                retry_count += 1
                continue
            except requests.exceptions.RequestException as e:
                self.log(f"轮询请求异常: {str(e)}，重试中... ({retry_count + 1}/{max_retries})")
                retry_count += 1
                continue
            except Exception as e:
                self.log(f"轮询失败: {str(e)}")
                raise ValueError(f"获取结果失败: {str(e)}")
        
        raise ValueError("轮询超时，请稍后重试")

    def generate_image(
            self,
            prompt: str,
            image_urls: List[str] = None,
            user_id: int = None,
            conversation_id: int = None,
            upload_record_id: int = None,
            seed: int = None,
            aspect_ratio: str = None,
            output_format: str = "png",
            prompt_upsampling: bool = False,
            safety_tolerance: int = 2
    ) -> Dict:
        """
        生成或编辑图像
        
        Args:
            prompt: 生成提示词
            image_urls: 输入图片URL列表（可选）
            user_id: 用户ID
            conversation_id: 会话ID
            upload_record_id: 上传记录ID
            seed: 随机种子
            aspect_ratio: 图片比例（可选）
            output_format: 输出格式（png/jpeg）
            prompt_upsampling: 是否进行提示词上采样
            safety_tolerance: 安全容忍度（0-6）
            
        Returns:
            Dict: 包含处理结果的字典
        """
        self.log_messages = []  # 重置日志
        try:
            self.log("开始图像生成流程")

            translate_service = BaiduTranslateService()
            result = translate_service.translate(prompt)

            # 准备请求数据
            payload = {
                "prompt": result,
                "input_image": None,  # 初始化为None，后续如果有图片再设置
                "seed": seed,
                "aspect_ratio": aspect_ratio if aspect_ratio else None,
                "output_format": output_format,
                "prompt_upsampling": prompt_upsampling,
                "safety_tolerance": safety_tolerance
            }

            # 处理输入图片
            if image_urls:
                # 下载并合并图片
                image_data = self._process_input_images(image_urls)
                if image_data:
                    payload["input_image"] = image_data

            # 移除值为None的键
            payload = {k: v for k, v in payload.items() if v is not None}

            # 记录构建的payload（隐藏图片数据）
            log_payload = payload.copy()
            if "input_image" in log_payload:
                log_payload["input_image"] = "<base64_image_data>"
            self.log(f"构建的请求payload: {json.dumps(log_payload, indent=2)}")

            # 发送请求
            headers = {
                "x-key": settings.FLUX_KONEXT_PRO_API_KEY,
                "Content-Type": "application/json"
            }

            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=120  # 设置初始请求超时
            )
            response.raise_for_status()
            result = response.json()

            # 检查响应
            if not result.get('polling_url'):
                raise ValueError("API未返回轮询URL")

            # 轮询获取结果
            try:
                final_result = self._poll_result(result['polling_url'])
            except ValueError as e:
                if "轮询超时" in str(e):
                    # 如果轮询超时，检查是否已经有结果
                    if upload_record_id:
                        record = ImageUploadManager.get_record_by_id(upload_record_id)
                        if record and record.image_url and record.image_url != "pending":
                            self.log("检测到已有生成结果，使用已有结果")
                            return {
                                'success': True,
                                'image_url': record.image_url,
                                'image_name': record.image_name,
                                'prompt': prompt,
                                'seed_used': seed,
                                'model_used': 'flux_kontext_pro',
                                'logs': self.log_messages
                            }
                raise e

            if not final_result.get('result', {}).get('sample'):
                raise ValueError("未获取到生成的图片URL")

            # 下载生成的图片
            image_url = final_result['result']['sample']
            img_data = self._download_image(image_url)

            # 验证图像数据
            if not self._validate_image_data(img_data):
                raise ValueError("图像数据验证失败")

            # 存储到OSS
            oss_url, filename = self._store_to_oss(img_data, upload_record_id)
            self.log(f"图像已存储到OSS: {oss_url}")

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
                    image_paths=image_urls
                )

            return {
                'success': True,
                'image_url': oss_url,
                'image_name': filename,
                'prompt': prompt,
                'seed_used': seed,
                'model_used': 'flux_kontext_pro',
                'logs': self.log_messages
            }

        except Exception as e:
            error_msg = f"图像生成失败: {str(e)}"
            self.log(error_msg)
            logger.error(error_msg, exc_info=True)
            
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

    def _process_input_images(self, image_urls: List[str]) -> Optional[str]:
        """处理输入图片，返回base64编码的图片数据"""
        try:
            if not image_urls:
                return None

            # 如果只有一张图片，直接处理并返回
            if len(image_urls) == 1:
                img_data = self._download_image(image_urls[0])
                img = Image.open(BytesIO(img_data))
                # 确保图片为RGB模式
                img = img.convert('RGB')
                
                # 转换为base64
                img_byte_arr = BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                
                return base64.b64encode(img_byte_arr).decode('utf-8')

            # 多张图片的情况，进行网格拼接处理
            self.log(f"处理多张图片，数量: {len(image_urls)}")
            images = []
            for url in image_urls:
                img_data = self._download_image(url)
                img = Image.open(BytesIO(img_data))
                # 确保所有图片都转换为RGB模式
                img = img.convert('RGB')
                images.append(img)

            # 计算网格布局
            num_images = len(images)
            # 计算网格的行数和列数
            if num_images <= 2:
                rows, cols = 1, num_images
            elif num_images <= 4:
                rows, cols = 2, 2
            elif num_images <= 6:
                rows, cols = 2, 3
            elif num_images <= 9:
                rows, cols = 3, 3
            else:
                rows, cols = 3, 4

            self.log(f"使用 {rows}x{cols} 网格布局")

            # 计算单个图片的目标尺寸
            # 使用第一张图片的尺寸作为基准
            base_width, base_height = images[0].size
            target_width = base_width
            target_height = base_height

            # 创建空白画布
            canvas_width = target_width * cols
            canvas_height = target_height * rows
            merged_image = Image.new('RGB', (canvas_width, canvas_height))

            # 在网格中放置图片
            for idx, img in enumerate(images):
                if idx >= rows * cols:
                    break  # 如果图片数量超过网格容量，停止处理
                
                # 调整图片大小
                img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                
                # 计算图片在网格中的位置
                row = idx // cols
                col = idx % cols
                x = col * target_width
                y = row * target_height
                
                # 将图片粘贴到对应位置
                merged_image.paste(img, (x, y))

            # 转换为base64
            img_byte_arr = BytesIO()
            merged_image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            return base64.b64encode(img_byte_arr).decode('utf-8')

        except Exception as e:
            self.log(f"处理输入图片失败: {str(e)}")
            raise ValueError(f"处理输入图片失败: {str(e)}") 