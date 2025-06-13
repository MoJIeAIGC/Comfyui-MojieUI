from rest_framework.response import Response
from rest_framework import status


"""
返回工具类
"""
class ResponseUtil:
    @staticmethod
    def success(data=None, message="Success",status_code=status.HTTP_200_OK, content_type=None):
        """
        成功响应
        :param data: 返回的数据
        :param message: 返回的消息
        :return: Response 对象
        """
        return ResponseUtil.custom_response(
            code=200,
            data=data,
            message=message,
            status_code=status_code
        )
        if content_type:
            response["Content-Type"] = content_type
        return response

    @staticmethod
    def error(data=None, message="Error", code=500, errors=None):
        """
        失败响应
        :param data: 返回的数据
        :param message: 返回的消息
        :param code: 自定义错误码
        :param errors: 错误信息
        :return: Response 对象
        """
        return ResponseUtil.custom_response(
            code=code,
            data=data,
            message=message,
            errors=errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
        


    @staticmethod
    def custom_response(code, data=None, message="", errors=None, status_code=status.HTTP_200_OK):
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