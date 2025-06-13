import base64
import uuid
import logging
import re
import json
import requests
from typing import List, Dict, Optional, Tuple
from rest_framework.generics import get_object_or_404
from io import BytesIO
from PIL import Image
from translate import Translator

from common.BaiduTranslateService import BaiduTranslateService
from common.ChatGPTClient import ChatGPTClient
from common.aliyunOSS_utills import upload_file, bucket
from common.volcengine_tos_utils import VolcengineTOSUtils
from djangoProject import settings
from templateImage.ImagesRequest import ImageUploadManager
from templateImage.models import templateImage, ImageUploadRecord, ConversationList

from user.models import SysUser
from django.utils import timezone
logger = logging.getLogger(__name__)


class ChatGPTImageService:
    """支持多种图像返回格式的ChatGPT图像生成服务"""

    def __init__(self):
        self.log_messages = []
        # 初始化ChatGPT客户端（实际使用时会在generate_image方法中根据参数重新初始化）
        self.chatgpt_client = None

    def log(self, message: str):
        """记录处理日志"""
        logger.info(message)
        self.log_messages.append(message)

    def generate_image(
            self,
            prompt: str,
            image_urls: List[str],
            api_key: str,
            api_url: str,
            model: str,
            user_id: int,
            conversation_id: int,
            upload_record_id: int,
            seed: int = None
    ) -> Dict:
        """
        生成图像并存储结果到OSS和MySQL
        """
        self.log_messages = []  # 重置日志
        try:
            self.log("开始图像生成流程")
            user_info = get_object_or_404(SysUser, id=user_id)

            # 初始化ChatGPT客户端（使用轮询功能）
            self.chatgpt_client = ChatGPTClient([
                # {
                #     'url': api_url,
                #     'key': api_key,
                #     'model': model,  # 第一个API使用的模型
                #     'timeout': 220,
                #     'priority': 2
                # },
                {
                    'url': settings.CHATGPT_API_URL,
                    'key': settings.CHATGPT_API_KEY,
                    'model': 'gpt-4o-image-vip',  # 备用API使用的模型
                    'timeout': 220,
                    'priority': 1
                }
            ])

            # 构建多模态请求
            contents = self._build_multimodal_content(prompt, image_urls)
            self.log(f"构建了包含{len(image_urls)}张参考图像的请求")

            # 发送API请求
            response = self._send_chatgpt_request(
                contents=contents,
                model='gpt-4o-image-vip',
                seed=seed
            )
            self.log("API请求发送成功")

            # 处理响应并存储结果
            result = self._process_and_store_response(
                response=response,
                prompt=prompt,
                model_used=model,
                seed=seed,
                user_info=user_info,
                user_id=user_id,
                image_urls=image_urls,
                conversation_id=conversation_id,
                upload_record_id=upload_record_id
            )
            self.log("图像处理存储完成")
            return result

        except Exception as e:
            error_msg = f"图像生成失败: {str(e)}"
            self.log(error_msg)
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'message': '图像生成失败',
                'logs': self.log_messages
            }

    def _send_chatgpt_request(
            self,
            contents: List[Dict],
            model: str,
            seed: int = None
    ) -> Dict:
        """
        发送ChatGPT API请求（使用ChatGPTClient工具类）
        :param contents: 消息内容列表
        :param model: 使用的模型
        :param seed: 随机种子
        :return: API响应字典
        """
        try:
            # 使用ChatGPTClient发送请求
            response = self.chatgpt_client.send_request(
                contents=[{"role": "user", "content": contents}],
                model=model,
                seed=seed
            )

            # 记录API响应状态
            self.log(f"API请求成功，模型: {model}")
            return response

        except ValueError as e:
            # ChatGPTClient已经记录了错误日志
            self.log(f"API请求失败: {str(e)}")
            raise
        except Exception as e:
            self.log(f"API请求异常: {str(e)}")
            raise ValueError(f"API请求失败: {str(e)}")

    def _build_multimodal_content(self, prompt: str, image_urls: List[str]) -> List[Dict]:
        """构建明确的多模态请求内容"""
        contents = [{
            "type": "text",
            "text": prompt
        }]

        for url in image_urls:
            contents.append({
                "type": "image_url",
                "image_url": {"url": url}
            })

        return contents


    def _process_and_store_response(
            self,
            response: Dict,
            prompt: str,
            model_used: str,
            image_urls: List[str],
            seed: int,
            user_info: SysUser,
            user_id: int,
            conversation_id: int,
            upload_record_id: int
    ) -> Dict:
        """处理响应并存储到OSS和数据库"""
        try:
            # 提取响应内容
            content = response['choices'][0]['message']['content']
            self.log(f"提取到响应内容: {content[:200]}...")

            # 等待完整响应
            if not content or len(content.strip()) == 0:
                raise ValueError("响应内容为空")

            # 检查响应是否完整
            if not content.endswith(('.', '!', '?', '"', "'", ']', '}')):
                raise ValueError("响应内容不完整")

            # 尝试提取图像URL
            image_url = self._extract_image_url(content)
            if image_url:
                self.log(f"发现图像URL: {image_url}")
                img_data = self._download_image(image_url, upload_record_id)
            else:
                # 尝试提取base64数据
                base64_data = self._extract_base64_image(content)
                if not base64_data:
                    raise ValueError("响应中未找到有效的图像URL或base64数据")
                self.log("发现base64图像数据")
                img_data = base64.b64decode(base64_data)

            # 存储到OSS
            oss_url, filename = self._store_to_oss(img_data, upload_record_id)
            self.log(f"图像已存储到OSS: {oss_url}")

            # 保存到数据库
            self._save_to_database(
                image_name=filename,
                image_url=oss_url,
                prompt=prompt,
                user_info=user_info,
                user_id=user_id,
                image_urls=image_urls,  # 传递image_urls参数
                seed=seed,
                conversation_id=conversation_id,
                upload_record_id=upload_record_id
            )

            return {
                'success': True,
                'image_url': oss_url,
                'image_name': filename,
                'prompt': prompt,
                'seed_used': seed,
                'model_used': model_used,
                'logs': self.log_messages
            }

        except Exception as e:
            self.log(f"处理响应失败: {str(e)}")
            raise

    def _extract_image_url(self, content: str) -> Optional[str]:
        """从内容中提取图像URL"""
        # 匹配常见图片格式URL
        pattern = r'https?://[^\s<>"]+\.(?:jpg|jpeg|png|gif|webp|bmp)'
        matches = re.findall(pattern, content)
        return matches[0] if matches else None

    def _extract_base64_image(self, content: str) -> Optional[str]:
        """从内容中提取base64图像数据"""
        # 匹配标准data URI格式
        pattern = r'data:image\/[^;]+;base64,([a-zA-Z0-9+/=]+)'
        matches = re.findall(pattern, content)
        if matches:
            return matches[0]

        # 尝试匹配纯base64数据
        if re.match(r'^[a-zA-Z0-9+/=]+$', content.strip()):
            return content.strip()

        return None

    def _download_image(self, url: str, upload_record_id: int) -> bytes:
        """下载图像并返回二进制数据"""
        try:
            self.log(f"开始下载图像: {url}")
            response = requests.get(url, timeout=15)
            response.raise_for_status()

            # 验证确实是图像
            if 'image/' not in response.headers.get('Content-Type', ''):
                raise ValueError("URL未返回图像内容")

            return response.content
        except Exception as e:
            self.log(f"图像下载失败: {str(e)}")
            # 示例3：失败处理
            ImageUploadManager.mark_as_failed(
                record_id=upload_record_id,
                error_message=f"图像下载失败: {str(e)}"
            )
            raise ValueError(f"无法下载图像: {str(e)}")

    def _store_to_oss(self, image_data: bytes, upload_record_id: int) -> Tuple[str, str]:
        """存储图像到OSS"""
        try:
            filename = f"{uuid.uuid4()}.png"
            # 验证图像数据有效性
            try:
                Image.open(BytesIO(image_data)).verify()
            except Exception as e:
                ImageUploadManager.mark_as_failed(
                    record_id=upload_record_id,
                    error_message=f"无效的图像数据: {str(e)}"
                )
                filter_white = self.generate_empty_image
                tos_utils = VolcengineTOSUtils()
                image_url = tos_utils.upload_image(object_name=filename, file_data=filter_white)
                return image_url, filename

            tos_utils = VolcengineTOSUtils()
            image_url = tos_utils.upload_image(object_name=filename, file_data=image_data)
            return image_url, filename
        except Exception as e:
            self.log(f"OSS存储失败: {str(e)}")
            # 示例3：失败处理
            ImageUploadManager.mark_as_failed(
                record_id=upload_record_id,
                error_message=f"OSS存储失败: {str(e)}"
            )
            filter_white = self.generate_empty_image
            tos_utils = VolcengineTOSUtils()
            image_url = tos_utils.upload_image(object_name=filename, file_data=filter_white)
            return image_url, filename

    def _save_to_database(
            self,
            image_name: str,
            image_url: str,
            prompt: str,
            user_info: SysUser,
            image_urls: List[str],
            user_id: int,
            seed: int,
            conversation_id: int,
            upload_record_id: int
    ):
        """保存记录到MySQL数据库"""
        try:
            templateImage.objects.create(
                image_name=image_name,
                image_address=image_url,
                description=prompt,
                image_method="chatgpt_generation",
                method_sub="ai_image",
                userImage=user_info,
                isDelete=0,
            )
            # images_url = ""
            current_time = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            # for url in image_urls:
            #     images_url += url + ","
            images_url = ",".join(image_urls) if image_urls else ""
            # ImageUploadRecord.objects.create(
            #     image_name=image_name,
            #     image_url=image_url,
            #     prompt=prompt,
            #     model_used="chatgpt_generation",
            #     user_id=user_id,
            #     image_list=images_url,  # 保存image_urls
            #     conversation_id=conversation_id,
            #     upload_time=current_time,
            #     seed_used=seed,
            # )

            # 标记已经完成的请求
            ImageUploadManager.mark_as_completed(
                record_id=upload_record_id,
                image_url=images_url,
                image_name=image_name
            )

            # 示例1：基础更新
            ImageUploadManager.update_record_by_id(
                record_id=upload_record_id,
                image_url=images_url,
                image_name=image_name,
                prompt=prompt,
                model_used="chatgpt_generation",
                user_id=user_id,
                image_list=images_url,
                conversation_id=conversation_id,
                upload_time=current_time,
                seed_used=seed
            )

            self.log(f"数据库记录已创建: {image_url}")
        except Exception as e:
            self.log(f"数据库保存失败: {str(e)}")
            ImageUploadManager.mark_as_failed(
                record_id=upload_record_id,
                error_message=f"记录保存失败: {str(e)}"
            )
            raise ValueError(f"记录保存失败: {str(e)}")

    def generate_empty_image(self, width: int, height: int) -> bytes:
        """生成空白图像（用于错误处理）"""
        from PIL import Image
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()