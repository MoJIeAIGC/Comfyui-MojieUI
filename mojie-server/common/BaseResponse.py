from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class BaseResponse(APIView):
    """
        自定义 API 视图基类
        """

    def base_response(self, code, data=None, message="", errors=None, status_code=status.HTTP_200_OK):
        """
        自定义响应格式
        :param code: 状态码（自定义业务码）
        :param data: 返回的数据
        :param message: 返回的消息
        :param errors: 错误信息
        :param status_code: HTTP 状态码
        :return: Response 对象
        """
        response_data = {
            "code": code,
            "data": data,
            "message": message,
        }
        if errors is not None:
            response_data["errors"] = errors
        return Response(response_data, status=status_code)