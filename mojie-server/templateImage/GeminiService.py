import base64
import io
import json
import random
import uuid
import logging
import requests
from io import BytesIO
from typing import List, Dict, Optional, Tuple
from PIL import Image
from rest_framework.generics import get_object_or_404
from django.utils import timezone
from translate import Translator
from common.BaiduTranslateService import BaiduTranslateService
from common.ErrorCode import ErrorCode
from common.aliyunOSS_utills import upload_file, bucket
from common.volcengine_tos_utils import VolcengineTOSUtils
from djangoProject import settings
from exception.business_exception import BusinessException
from templateImage.ImagesRequest import ImageUploadManager
from templateImage.models import templateImage , ImageUploadRecord, ConversationList
from user.models import SysUser

logger = logging.getLogger(__name__)


class GeminiImageService:

    """Google Gemini 图像生成服务（支持长上下文）"""

    def __init__(self):
        self.max_token_limit = 30720  # Gemini 1.5 的上下文窗口大小
        self.max_image_count = 16

    # def generate_image(
    #         self,
    #         prompt: str,
    #         api_key: str,
    #         model: str,
    #         image_urls: Optional[List[str]] = None,
    #         aspect_ratio: str = "Free (自由比例)",
    #         temperature: float = 1.0,
    #         seed: Optional[int] = None,
    #         user_id: Optional[int] = None,
    #         conversation_id: Optional[int] = None,
    #         enable_long_context: bool = True
    # ) -> Dict:
    #     """
    #     生成图像并存储结果（支持长上下文）
    #
    #     参数说明:
    #     :param conversation_id: 会话ID（使用数据库自增ID）
    #     :param enable_long_context: 是否启用长上下文支持
    #     """
    #     try:
    #         # 验证必要参数
    #         if not api_key:
    #             raise ValueError("API密钥不能为空")
    #
    #         # 处理随机种子
    #         seed = seed if seed is not None else random.randint(1, 2 ** 31 - 1)
    #
    #         # 获取或创建会话
    #         conversation = self._get_or_create_conversation(
    #             user_id=user_id,
    #             conversation_id=conversation_id,
    #             enable_long_context=enable_long_context
    #         )
    #
    #         # # 创建翻译服务实例
    #         # translator = BaiduTranslateService()
    #         #
    #         # # 执行翻译
    #         # translated_text = translator.translate(prompt)
    #
    #         translated_text = Translator(from_lang="ZH", to_lang="EN-US").translate(prompt)
    #
    #         print(translated_text)
    #         # 构建分块内容
    #         contents = self._build_chunked_contents(
    #             prompt=translated_text,
    #             image_urls=image_urls,
    #             aspect_ratio=aspect_ratio,
    #             conversation=conversation,
    #             enable_long_context=enable_long_context
    #         )
    #
    #         # 调用Gemini API
    #         response = self._call_gemini_api(
    #             api_key=api_key,
    #             model=model,
    #             contents=contents,
    #             temperature=temperature,
    #             seed=seed
    #         )
    #
    #         # 处理响应并存储结果
    #         result = self._process_and_store_response(
    #             response=response,
    #             prompt=prompt,
    #             model_used=model,
    #             seed_used=seed,
    #             conversation_id=conversation_id,
    #             user_id=user_id,
    #             image_urls=image_urls
    #         )
    #
    #         # 更新会话历史
    #         if enable_long_context and conversation:
    #             self._update_conversation_history(
    #                 conversation=conversation,
    #                 prompt=prompt,
    #                 image_urls=image_urls,
    #                 response=result
    #             )
    #
    #         return result
    #
    #     except Exception as e:
    #         logger.error(f"图像生成失败: {str(e)}", exc_info=True)
    #         return {
    #             'success': False,
    #             'error': str(e),
    #             'message': '图像生成失败'
    #         }
    def generate_image(
            self,
            prompt: str,
            api_key: str,
            model: str,
            upload_record_id: int,
            image_urls: Optional[List[str]] = None,
            aspect_ratio: str = "Free (自由比例)",
            temperature: float = 1.0,
            seed: Optional[int] = None,
            user_id: Optional[int] = None,
            conversation_id: Optional[int] = None,
            enable_long_context: bool = False
    ) -> Dict:
        """
        生成图像并存储结果
        """
        try:
            # 准备FastAPI请求数据
            request_data = {
                "prompt": prompt,
                "model": model,
                "image_urls": image_urls,
                "aspect_ratio": aspect_ratio,
                "temperature": temperature,
                "seed": seed
            }

            # 调用FastAPI服务
            headers = {"X-API-Key": api_key}
            response = requests.post(
                f"{settings.FASTAPI_URL}/generate-image",
                json=request_data,
                headers=headers,
                timeout=220
            )

            if response.status_code != 200:
                raise BusinessException(
                    error_code=ErrorCode.API_REQUEST,
                    data='',
                    errors=f"FastAPI服务请求失败: {response.text}"
                )

            result = response.json()

            if not result.get('success'):
                raise BusinessException(
                    error_code=ErrorCode.API_REQUEST,
                    data='',
                    errors=result.get('error', 'Gemini API请求失败')
                )

            # 从response中提取图像数据
            # result_sum = result['result']
            result_mj = self._process_and_store_result(
                         response=result,
                         prompt=prompt,
                         model_used=model,
                         seed_used=seed,
                         conversation_id=conversation_id,
                         user_id=user_id,
                         upload_record_id=upload_record_id,
                         image_urls=image_urls
            )


            # image_data = self._extract_image_data(gemini_response)
            #
            # # 存储图像到OSS
            # image_url, image_name = self._save_to_oss(image_data)
            #
            # # 保存到数据库
            # self._save_to_database(
            #     image_name=image_name,
            #     image_url=image_url,
            #     prompt=prompt,
            #     user_id=user_id,
            #     seed_used=result['seed_used'],
            #     image_urls=image_urls,
            #     model_used=model
            # )
            # 处理响应并存储结果
            return result_mj

        except Exception as e:
            logger.error(f"图像生成失败: {str(e)}", exc_info=True)
            ImageUploadManager.mark_as_failed(
                record_id=upload_record_id,
                error_message=f"图像生成失败: {str(e)}"
            )
            return {
                'success': False,
                'error': str(e),
                'message': '图像生成失败'
            }

    def generate_image_stream(
            self,
            prompt: str,
            api_key: str,
            model: str,
            image_urls: Optional[List[str]] = None,
            aspect_ratio: str = "Free (自由比例)",
            temperature: float = 1.0,
            seed: Optional[int] = None,
            user_id: Optional[int] = None
    ):
        """流式图像生成"""
        try:
            # 准备FastAPI请求数据
            request_data = {
                "prompt": prompt,
                "model": model,
                "image_urls": image_urls,
                "aspect_ratio": aspect_ratio,
                "temperature": temperature,
                "seed": seed
            }

            # 调用FastAPI流式服务
            headers = {"X-API-Key": api_key}
            response = requests.post(
                f"{self.fastapi_url}/generate-image-stream",
                json=request_data,
                headers=headers,
                stream=True,
                timeout=60
            )

            if response.status_code != 200:
                raise BusinessException(
                    error_code=ErrorCode.API_REQUEST.code,
                    data='',
                    errors=f"FastAPI流式服务请求失败: {response.text}"
                )

            def process_stream():
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line.decode('utf-8').replace('data: ', ''))

                        if data['status'] == 'completed' and data.get('image_data'):
                            # 存储图像到OSS
                            image_url, image_name = self._save_to_oss(data['image_data'])

                            # 保存到数据库
                            self._save_to_database(
                                image_name=image_name,
                                image_url=image_url,
                                prompt=prompt,
                                user_id=user_id,
                                seed_used=data['seed_used'],
                                image_urls=image_urls,
                                model_used=model
                            )

                            # 更新响应数据
                            data.update({
                                'image_url': image_url,
                                'image_name': image_name
                            })

                        yield f"data: {json.dumps(data)}\n\n"

            return process_stream()

        except Exception as e:
            logger.error(f"流式图像生成失败: {str(e)}", exc_info=True)
            raise

    def _get_or_create_conversation(
            self,
            user_id: Optional[int],
            conversation_id: Optional[int],
            enable_long_context: bool
    ) -> Optional[ConversationList]:
        """获取或创建会话记录（使用自增ID）"""
        if not enable_long_context or not user_id:
            return None

        try:
            if conversation_id:
                return ConversationList.objects.get(
                    id=conversation_id,
                    user_id=user_id
                )
            else:
                # 创建新会话
                new_conversation = ConversationList.objects.create(
                    user_id=user_id,
                    upload_time=timezone.now()
                )
                return new_conversation
        except ConversationList.DoesNotExist:
            logger.warning(f"会话不存在: {conversation_id}")
            return None
        except Exception as e:
            logger.warning(f"会话管理失败: {str(e)}")
            return None


    def _process_and_store_result(
            self,
            response: Dict,
            prompt: str,
            model_used: str,
            seed_used: int,
            conversation_id: int,
            user_id: Optional[int],
            upload_record_id: int,
            image_urls: Optional[List[str]] = None
    ) -> Dict:
        """处理响应并存储结果"""
        try:
            # 提取图像数据
            if not isinstance(response, dict):
                raise BusinessException(
                    error_code=ErrorCode.API_REQUEST,
                    data='',
                    errors="响应格式不正确"
                )

            # 检查响应结构
            if 'result' not in response:
                raise BusinessException(
                    error_code=ErrorCode.API_REQUEST,
                    data='',
                    errors="响应中缺少result字段"
                )

            result = response.get('result', {})
            if not result:
                raise BusinessException(
                    error_code=ErrorCode.API_REQUEST,
                    data='',
                    errors="响应中没有结果数据"
                )

            # 提取result中的各个字段
            image_url = result.get('image_url')
            image_name = result.get('image_name')
            prompt = result.get('prompt', prompt)  # 如果result中有prompt则使用，否则用传入的
            seed_used = result.get('seed_used', seed_used)  # 同上
            model_used = result.get('model_used', model_used)  # 同上

            if not image_url or not image_name:
                raise BusinessException(
                    error_code=ErrorCode.NOT_IMAGE_URL,
                    data='',
                    errors="响应中缺少图像URL或图像名称"
                )

            # 保存到数据库（如果提供了用户ID）
            if user_id:
                user_info = get_object_or_404(SysUser, id=user_id)
                self._save_to_database(
                    image_name=image_name,
                    image_url=image_url,
                    prompt=prompt,
                    user_info=user_info,
                    user_id=user_id,
                    seed_used=seed_used,
                    image_urls=image_urls,
                    conversation_id=conversation_id,
                    upload_record_id=upload_record_id
                )

            return {
                'success': True,
                'image_url': image_url,
                'image_name': image_name,
                'prompt': prompt,
                'seed_used': seed_used,
                'model_used': model_used
            }

        except Exception as e:
            ImageUploadManager.mark_as_failed(
                record_id=upload_record_id,
                error_message=f"结果保存失败: {str(e)}"
            )
            raise BusinessException(
                error_code=ErrorCode.SAVE_FAIL,
                data='',
                errors=str(e)
            )

    def _process_and_store_response(
            self,
            response: Dict,
            prompt: str,
            model_used: str,
            seed_used: int,
            conversation_id: int,
            user_id: Optional[int],
            upload_record_id: int,
            image_urls: Optional[List[str]] = None
    ) -> Dict:
        """处理响应并存储结果"""
        try:
            # 提取图像数据
            if not isinstance(response, dict):
                raise BusinessException(
                    error_code=ErrorCode.API_REQUEST,
                    data='',
                    errors="响应格式不正确"
                )

            # 检查响应结构
            if 'candidates' not in response:
                raise BusinessException(
                    error_code=ErrorCode.API_REQUEST,
                    data='',
                    errors="响应中缺少candidates字段"
                )

            candidates = response.get('candidates', [])
            if not candidates:
                raise BusinessException(
                    error_code=ErrorCode.API_REQUEST,
                    data='',
                    errors="响应中没有候选结果"
                )

            first_candidate = candidates[0]
            if 'content' not in first_candidate or 'parts' not in first_candidate['content']:
                raise BusinessException(
                    error_code=ErrorCode.API_REQUEST,
                    data='',
                    errors="响应结构不完整"
                )

            parts = first_candidate['content']['parts']
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    img_data = part.inline_data.data
                    # # 修复 Base64 长度问题
                    # padding = len(base64_img_data) % 4
                    # if padding:
                    #     base64_img_data += "=" * (4 - padding)
                    #
                    # # 解码
                    # binary_data = base64.b64decode(base64_img_data)
                    # Image.open(io.BytesIO(binary_data)).verify()
                    # 存储到OSS
                    img_url, img_name = self._save_to_oss(img_data, upload_record_id)
                    logger.info(f"img_url: {img_url}")
                    # 保存到数据库（如果提供了用户ID）
                    if user_id:
                        user_info = get_object_or_404(SysUser, id=user_id)
                        self._save_to_database(
                            image_name=img_name,
                            image_url=img_url,
                            prompt=prompt,
                            user_info=user_info,
                            user_id=user_id,
                            seed_used=seed_used,
                            image_urls=image_urls,
                            conversation_id=conversation_id,
                            upload_record_id=upload_record_id
                        )

                    return {
                        'success': True,
                        'image_url': img_url,
                        'image_name': img_name,
                        'prompt': prompt,
                        'seed_used': seed_used,
                        'model_used': model_used
                    }

            raise BusinessException(
                error_code=ErrorCode.NOT_IMAGE_URL,
                data='',
                errors="响应中未找到图像数据"
            )

        except Exception as e:
            raise BusinessException(
                error_code=ErrorCode.SAVE_FAIL,
                data='',
                errors=str(e)
            )

    def _build_chunked_contents(
            self,
            prompt: str,
            image_urls: Optional[List[str]],
            aspect_ratio: str,
            conversation: Optional[ConversationList],
            enable_long_context: bool
    ) -> List[Dict]:
        """构建分块内容（支持长上下文）"""
        # 基础提示词构建
        prompt_text = self._build_prompt(prompt, aspect_ratio)

        # 初始化内容列表
        contents = []

        # 1. 添加历史上下文（如果启用长上下文且有会话）
        if enable_long_context and conversation:
            try:
                history = self._load_conversation_history(conversation)
                contents.extend(history)
            except Exception as e:
                logger.warning(f"加载历史上下文失败: {str(e)}")

        # 2. 添加当前提示
        contents.append({"text": prompt_text})

        # 3. 处理图片（分块处理）
        if image_urls:
            image_urls = image_urls[:self.max_image_count]  # 限制图片数量
            for url in image_urls:
                try:
                    image_data = self._download_image(url)
                    contents.append({
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": image_data
                        }
                    })
                except Exception as e:
                    logger.warning(f"图片下载失败（{url}）: {str(e)}")
                    continue

        logger.info(f"构建了包含{len(contents)}个内容块的请求")
        return contents

    def _load_conversation_history(self, conversation: ConversationList) -> List[Dict]:
        """从数据库加载会话历史"""
        history = []
        records = ImageUploadRecord.objects.filter(
            conversation_id=conversation.id
        ).order_by('upload_time')[:10]  # 限制历史记录数量

        for record in records:
            # 添加历史提示
            history.append({"text": record.prompt})

            # 添加历史图片（如果有）
            if record.image_list:
                for url in record.image_list.split(','):
                    if url.strip():
                        try:
                            image_data = self._download_image(url.strip())
                            history.append({
                                "inline_data": {
                                    "mime_type": "image/png",
                                    "data": image_data
                                }
                            })
                        except Exception as e:
                            logger.warning(f"历史图片加载失败: {str(e)}")
                            continue

        return history

    def _update_conversation_history(
            self,
            conversation: ConversationList,
            prompt: str,
            image_urls: Optional[List[str]],
            response: Dict
    ):
        """更新会话历史记录（保存当前生成记录）"""
        try:
            # 1. 更新会话时间
            conversation.update_time = timezone.now()
            conversation.save()

            # 2. 保存当前记录到历史
            if response.get('success'):
                ImageUploadRecord.objects.create(
                    image_name=response['image_name'],
                    image_url=response['image_url'],
                    prompt=prompt,
                    model_used="gemini_generation",
                    user_id=conversation.user_id,
                    image_list=",".join(image_urls) if image_urls else "",
                    conversation_id=conversation.id,
                    upload_time=timezone.now(),
                    seed_used=response.get('seed_used', 0)
                )
                logger.info(f"会话历史已更新: {conversation.id}")

        except Exception as e:
            logger.error(f"更新会话历史失败: {str(e)}", exc_info=True)

    def _build_contents(
            self,
            prompt: str,
            image_urls: Optional[List[str]],
            aspect_ratio: str
    ) -> List[Dict]:
        """构建API请求内容"""
        prompt_text = self._build_prompt(prompt, aspect_ratio)
        contents = [{"text": prompt_text}]

        if image_urls:
            for url in image_urls:
                try:
                    image_data = self._download_image(url)
                    contents.append({
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": image_data
                        }
                    })
                except Exception as e:
                    logger.warning(f"图片下载失败（{url}）: {str(e)}")
                    continue

        logger.info(f"构建了包含{len(contents) - 1}张参考图像的请求")
        return contents

    def _build_prompt(self, prompt: str, aspect_ratio: str) -> str:
        """根据比例构建提示词"""
        prompt_templates = {
            "Free (自由比例)": f"Create a detailed image of: {prompt}",
            "Landscape (横屏)": (
                "Generate a wide rectangular image (width > height). "
                f"Create a detailed image of: {prompt}"
            ),
            "Portrait (竖屏)": (
                "Generate a tall rectangular image (height > width). "
                f"Create a detailed image of: {prompt}"
            ),
            "Square (方形)": (
                "Generate a square image (width = height). "
                f"Create a detailed image of: {prompt}"
            )
        }
        return prompt_templates.get(aspect_ratio, prompt_templates["Free (自由比例)"])

    def _download_image(self, url: str) -> bytes:
        """下载图像并返回二进制数据"""
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # 验证图像格式并转换为PNG
        img = Image.open(BytesIO(response.content))
        if img.format != 'PNG':
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            return buffered.getvalue()
        return response.content

    def _call_gemini_api(
            self,
            api_key: str,
            model: str,
            contents: List[Dict],
            temperature: float,
            seed: int
    ) -> Dict:
        """调用Gemini API"""
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            config = types.GenerateContentConfig(
                temperature=temperature,
                seed=seed,
                response_modalities=['Text', 'Image']
            )

            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )

            if not hasattr(response, 'candidates') or not response.candidates:
                raise BusinessException(error_code=ErrorCode.API_RESPONSE_NULL.code, data='',
                                        errors="API响应为空")

            return response

        except ImportError:
            raise ImportError("请安装google-genai库: pip install google-genai")
        except Exception as e:
            raise BusinessException(error_code=ErrorCode.API_REQUEST.code, data='', errors=str(e))


    def _save_to_oss(self, image_data: bytes, upload_record_id: int) -> Tuple[str, str]:
        """存储图像到OSS"""
        try:
            filename = f"{uuid.uuid4()}.png"
            tos_utils = VolcengineTOSUtils()
            image_url = tos_utils.upload_image(object_name=filename, file_data=image_data)
            logger.info(f"图片已存储到OSS: {image_url}")
            return image_url, filename
        except Exception as e:
            logger.error(f"OSS存储失败: {str(e)}")
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
            seed_used: int,
            image_urls: List[str],
            user_id: int,
            conversation_id: int,
            upload_record_id: int
    ):
        """保存记录到MySQL数据库"""
        try:
            templateImage.objects.create(
                image_name=image_name,
                image_address=image_url,
                description=prompt,
                image_method="gemini_generation",
                method_sub="ai_image",
                userImage=user_info,
                isDelete=0
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
            #     model_used="gemini_generation",
            #     user_id=user_id,
            #     image_list=images_url,  # 保存image_urls
            #     conversation_id=conversation_id,
            #     upload_time=current_time,
            #     seed_used=seed_used,
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
                model_used="gemini_generation",
                user_id=user_id,
                image_list=images_url,
                conversation_id=conversation_id,
                upload_time=current_time,
                seed_used=seed_used
            )
            logger.info(f"已保存记录到数据库: {image_url}")
        except Exception as e:
            logger.error(f"数据库保存失败: {str(e)}")
            ImageUploadManager.mark_as_failed(
                record_id=upload_record_id,
                error_message=f"数据库保存失败: {str(e)}"
            )
            raise BusinessException(error_code=ErrorCode.SAVE_FAIL, data='', errors=str(e))

    def generate_empty_image(self, width: int, height: int) -> bytes:
        """生成空白图像（用于错误处理）"""
        from PIL import Image
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()