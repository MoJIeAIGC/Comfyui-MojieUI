import json
import sys
import os
import base64
import datetime
import hashlib
import hmac
import requests
import logging
from typing import Dict, Optional, List
from django.conf import settings
from rest_framework.generics import get_object_or_404
from common.volcengine_tos_utils import VolcengineTOSUtils
from templateImage.ImagesRequest import ImageUploadManager
from templateImage.models import templateImage, ImageUploadRecord
from user.models import SysUser

logger = logging.getLogger(__name__)

class VolcengineVisualService:
    """火山引擎视觉服务类"""

    def __init__(self):
        self.config = settings.VOLCENGINE_VISUAL_CONFIG
        self.method = 'POST'
        self.host = self.config['HOST']
        self.region = self.config['REGION']
        self.endpoint = self.config['ENDPOINT']
        self.service = self.config['SERVICE']
        self.version = self.config['VERSION']

    def _sign(self, key: bytes, msg: str) -> bytes:
        """生成HMAC签名"""
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

    def _get_signature_key(self, key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
        """生成签名密钥"""
        k_date = self._sign(key.encode('utf-8'), date_stamp)
        k_region = self._sign(k_date, region_name)
        k_service = self._sign(k_region, service_name)
        k_signing = self._sign(k_service, 'request')
        return k_signing

    def _format_query(self, parameters: Dict) -> str:
        """格式化查询参数"""
        request_parameters = ''
        for key in sorted(parameters):
            request_parameters += f"{key}={parameters[key]}&"
        return request_parameters[:-1]

    def _sign_v4_request(self, req_query: str, req_body: str) -> Dict:
        """生成V4签名请求"""
        access_key = self.config['ACCESS_KEY']
        secret_key = self.config['SECRET_KEY']

        if not access_key or not secret_key:
            raise ValueError('Access key or secret key is not available')

        t = datetime.datetime.utcnow()
        current_date = t.strftime('%Y%m%dT%H%M%SZ')
        datestamp = t.strftime('%Y%m%d')

        canonical_uri = '/'
        signed_headers = 'content-type;host;x-content-sha256;x-date'
        payload_hash = hashlib.sha256(req_body.encode('utf-8')).hexdigest()
        content_type = 'application/json'

        canonical_headers = (
            f'content-type:{content_type}\n'
            f'host:{self.host}\n'
            f'x-content-sha256:{payload_hash}\n'
            f'x-date:{current_date}\n'
        )

        canonical_request = (
            f'{self.method}\n'
            f'{canonical_uri}\n'
            f'{req_query}\n'
            f'{canonical_headers}\n'
            f'{signed_headers}\n'
            f'{payload_hash}'
        )

        algorithm = 'HMAC-SHA256'
        credential_scope = f'{datestamp}/{self.region}/{self.service}/request'
        string_to_sign = (
            f'{algorithm}\n'
            f'{current_date}\n'
            f'{credential_scope}\n'
            f'{hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()}'
        )

        signing_key = self._get_signature_key(secret_key, datestamp, self.region, self.service)
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

        authorization_header = (
            f'{algorithm} Credential={access_key}/{credential_scope}, '
            f'SignedHeaders={signed_headers}, Signature={signature}'
        )

        return {
            'X-Date': current_date,
            'Authorization': authorization_header,
            'X-Content-Sha256': payload_hash,
            'Content-Type': content_type
        }

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
        """
        try:
            # 准备请求参数
            query_params = {
                'Action': 'CVProcess',
                'Version': self.version,
            }
            formatted_query = self._format_query(query_params)

            # 准备请求体
            body_params = {
                "req_key": "text_to_image",  # 根据火山引擎文档修改为正确的 req_key
                "prompt": prompt,
                "prompt_strength": 7,  # 提示词强度，范围1-10
                "width": 1024,  # 图片宽度
                "height": 1024,  # 图片高度
                "style": "none",  # 风格设置
                "image_urls": image_urls or [],
                **kwargs
            }
            formatted_body = json.dumps(body_params)
            
            # 记录请求信息
            logger.info(f"火山引擎API请求: URL={self.endpoint}?{formatted_query}, Body={formatted_body}")

            # 生成签名请求头
            headers = self._sign_v4_request(formatted_query, formatted_body)
            
            # 记录请求头
            logger.info(f"火山引擎API请求头: {headers}")

            # 发送请求
            request_url = f"{self.endpoint}?{formatted_query}"
            response = requests.post(request_url, headers=headers, data=formatted_body, timeout=30)
            
            # 记录响应状态
            logger.info(f"火山引擎API响应状态: {response.status_code}")
            logger.info(f"火山引擎API响应内容: {response.text}")

            if response.status_code != 200:
                raise ValueError(f"API请求失败: {response.text}")

            # 处理响应
            result = response.json()
            # 火山引擎API成功状态码为0
            if result.get('code', -1) != 0:
                raise ValueError(f"图像生成失败: {result.get('message', '未知错误')}")

            # 处理生成的图像
            image_data = self._process_image_response(result)
            
            # 存储到OSS
            image_url, image_name = self._store_to_oss(image_data, upload_record_id)

            # 保存到数据库
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
                    upload_record_id=upload_record_id
                )

            return {
                'success': True,
                'image_url': image_url,
                'image_name': image_name,
                'prompt': prompt
            }

        except Exception as e:
            logger.error(f"图像生成失败: {str(e)}", exc_info=True)
            if upload_record_id:
                ImageUploadManager.mark_as_failed(
                    record_id=upload_record_id,
                    error_message=f"图像生成失败: {str(e)}"
                )
            return {
                'success': False,
                'error': str(e),
                'message': '图像生成失败'
            }

    def _process_image_response(self, response: Dict) -> bytes:
        """处理API响应中的图像数据"""
        try:
            # 根据火山引擎文生图API的响应格式提取图像数据
            # 文生图接口返回的是 response["data"]["image_list"][0]["image"]
            if "data" in response and "image_list" in response["data"] and len(response["data"]["image_list"]) > 0:
                image_base64 = response["data"]["image_list"][0].get("image", "")
                if not image_base64:
                    raise ValueError("响应中未找到图像数据")
                
                # base64编码的图像数据
                return base64.b64decode(image_base64)
            
            # 兼容旧的响应格式
            image_data = response.get('image_data')
            if not image_data:
                raise ValueError("响应中未找到图像数据: " + json.dumps(response))

            # 如果是base64编码的图像数据
            if isinstance(image_data, str):
                return base64.b64decode(image_data)
            
            # 如果是二进制数据
            return image_data

        except Exception as e:
            logger.error(f"处理图像响应失败: {str(e)}, 响应内容: {json.dumps(response)}")
            raise ValueError(f"处理图像响应失败: {str(e)}")

    def _store_to_oss(self, image_data: bytes, upload_record_id: Optional[int] = None) -> tuple:
        """存储图像到OSS"""
        try:
            filename = f"volcengine_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            tos_utils = VolcengineTOSUtils()
            image_url = tos_utils.upload_image(object_name=filename, file_data=image_data)
            return image_url, filename
        except Exception as e:
            logger.error(f"OSS存储失败: {str(e)}")
            if upload_record_id:
                ImageUploadManager.mark_as_failed(
                    record_id=upload_record_id,
                    error_message=f"OSS存储失败: {str(e)}"
                )
            raise

    def _save_to_database(
            self,
            image_name: str,
            image_url: str,
            prompt: str,
            user_info: SysUser,
            user_id: int,
            image_urls: Optional[List[str]],
            conversation_id: Optional[int],
            upload_record_id: Optional[int]
    ):
        """保存记录到数据库"""
        try:
            # 保存到templateImage表
            templateImage.objects.create(
                image_name=image_name,
                image_address=image_url,
                description=prompt,
                image_method="volcengine_generation",
                method_sub="ai_image",
                userImage=user_info,
                isDelete=0
            )

            # 更新上传记录
            if upload_record_id:
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                images_url = ",".join(image_urls) if image_urls else ""

                ImageUploadManager.mark_as_completed(
                    record_id=upload_record_id,
                    image_url=images_url,
                    image_name=image_name
                )

                ImageUploadManager.update_record_by_id(
                    record_id=upload_record_id,
                    image_url=images_url,
                    image_name=image_name,
                    prompt=prompt,
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