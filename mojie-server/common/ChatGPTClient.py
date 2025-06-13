from typing import List, Dict, Any, Optional
import logging
from common.APIRoundRobin import APIRoundRobin
from django.http import JsonResponse
import json

from common.ErrorCode import ErrorCode
from exception.business_exception import BusinessException

logger = logging.getLogger(__name__)


class ChatGPTClient:
    def __init__(self, api_configs: List[Dict[str, Any]]):
        """
        优化后的ChatGPT客户端，支持API竞速模式和不同模型
        :param api_configs: API配置列表，每个配置应包含:
            - url: 完整API地址
            - key: API密钥
            - model: 该API使用的模型
            - timeout: 超时时间(秒)
            - priority: 可选，API优先级(数值越大优先级越高)
        """
        self.api_configs = sorted(
            api_configs,
            key=lambda x: x.get('priority', 1),
            reverse=True
        )
        self.api_client = APIRoundRobin(self.api_configs)
        self.log_messages = []

    def log(self, message: str, level: str = 'info'):
        """增强的日志记录方法"""
        log_msg = f"[ChatGPTClient] {message}"
        self.log_messages.append(log_msg)
        if level == 'error':
            logger.error(log_msg)
        else:
            logger.info(log_msg)

    def send_request(
            self,
            contents: List[Dict],
            model: Optional[str] = None,
            seed: Optional[int] = None,
            **kwargs
    ) -> Dict:
        """
        发送ChatGPT请求（竞速模式）
        :param contents: 消息内容
        :param model: 可选，指定模型（如果提供则覆盖API配置中的模型）
        :param seed: 随机种子
        :return: API响应字典
        """
        self.log_messages = []

        try:
            # 获取所有可用的模型信息用于日志
            models_info = ", ".join(f"{cfg.get('model', 'default')}@{cfg['url']}"
                                    for cfg in self.api_configs)
            self.log(f"开始请求，可用模型: {models_info}，种子: {seed}")

            # 构建基础payload（不带model）
            payload = {
                "messages": contents,
                **({"seed": seed} if seed is not None else {}),
                **kwargs
            }

            self.log(f"请求负载: {str(payload)[:200]}...")

            # 获取响应（可能是JsonResponse或dict）
            response = self.api_client.send_request(
                method='POST',
                json=payload,
                model_override=model  # 传递模型覆盖参数
            )

            # 处理响应
            if isinstance(response, JsonResponse):
                response_data = json.loads(response.content)
                status_code = response.status_code
            else:
                response_data = response
                status_code = 200

            if status_code != 200:
                error_msg = (f"API请求失败，状态码: {status_code}, "
                             f"错误: {response_data.get('error', {}).get('message', '未知错误')}")
                self.log(error_msg, 'error')
                raise BusinessException(error_code=ErrorCode.API_REQUEST.code, data='',
                                        errors=error_msg)

            self.log("API请求成功")
            return response_data

        except Exception as e:
            self.log(f"请求失败: {str(e)}", 'error')
            self.log(f"尝试的API端点: {[cfg['url'] for cfg in self.api_configs]}", 'error')
            raise BusinessException(error_code=ErrorCode.API_REQUEST.code, data='', errors=str(e))

    def get_request_logs(self) -> List[str]:
        """获取本次请求的完整日志"""
        return self.log_messages.copy()