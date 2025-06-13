import requests
import concurrent.futures
from typing import Dict, Any, Optional, List
from django.http import JsonResponse


class APIRoundRobin:
    def __init__(self, api_configs: List[Dict[str, Any]]):
        """
        支持模型覆盖的API轮询工具类
        """
        self.api_configs = api_configs

    def _build_headers(self, api_key: str, custom_headers: Optional[Dict] = None) -> Dict:
        """构建请求头"""
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        if custom_headers:
            headers.update(custom_headers)
        return headers

    def _send_single_request(
            self,
            api: Dict,
            method: str,
            url: str,
            params: Dict,
            data: Dict,
            json_payload: Dict,
            custom_headers: Dict,
            model_override: Optional[str] = None
    ) -> Optional[JsonResponse]:
        """发送单个API请求（支持模型覆盖）"""
        try:
            # 使用API配置中的模型，除非有覆盖
            final_model = model_override if model_override else api.get('model')
            if not final_model:
                raise ValueError("API配置中未指定模型且未提供模型覆盖")

            # 构建最终payload
            final_payload = {**json_payload, "model": final_model}

            headers = self._build_headers(api['key'], custom_headers)
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=final_payload,
                timeout=api.get('timeout', 2)
            )
            response.raise_for_status()
            return JsonResponse(response.json())
        except requests.exceptions.RequestException:
            return None

    def send_request(
            self,
            method: str = 'GET',
            full_url: Optional[str] = None,
            params: Optional[Dict] = None,
            data: Optional[Dict] = None,
            json: Optional[Dict] = None,
            custom_headers: Optional[Dict] = None,
            model_override: Optional[str] = None
    ) -> JsonResponse:
        """
        发送请求（支持模型覆盖）
        """
        if full_url:
            try:
                api = self.api_configs[0]
                final_model = model_override if model_override else api.get('model')
                if not final_model:
                    return JsonResponse(
                        {'error': 'No model specified'},
                        status=400
                    )

                final_payload = {**json, "model": final_model}
                headers = self._build_headers(api['key'], custom_headers)
                response = requests.request(
                    method=method,
                    url=full_url,
                    headers=headers,
                    params=params,
                    data=data,
                    json=final_payload,
                    timeout=api.get('timeout', 2)
                )
                response.raise_for_status()
                return JsonResponse(response.json())
            except requests.exceptions.RequestException as e:
                return JsonResponse(
                    {'error': 'API request failed', 'detail': str(e)},
                    status=503
                )

        # 并发请求
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for api in self.api_configs:
                future = executor.submit(
                    self._send_single_request,
                    api=api,
                    method=method,
                    url=api['url'],
                    params=params,
                    data=data,
                    json_payload=json,
                    custom_headers=custom_headers,
                    model_override=model_override
                )
                futures.append(future)

            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result is not None:
                    for f in futures:
                        f.cancel()
                    return result

        return JsonResponse(
            {'error': 'All API endpoints failed'},
            status=503
        )