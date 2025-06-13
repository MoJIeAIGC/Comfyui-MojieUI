from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated

def custom_exception_handler(exc, context):
    # 先调用 DRF 原生的异常处理函数
    response = exception_handler(exc, context)

    if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        # 自定义未携带 token 或认证失败的响应
        return Response(
            {
                "error": "认证失败",
                "message": "请提供有效的认证 token",
                "code": 401
            },
            status=status.HTTP_401_UNAUTHORIZED
        )

    if response is not None:
        # 可以对其他异常的响应进行自定义
        response.data = {
            "error": "请求出错",
            "message": response.data.get('detail', '未知错误'),
            "code": response.status_code
        }

    return response