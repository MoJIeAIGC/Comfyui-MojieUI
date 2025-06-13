from enum import Enum

class ErrorCode(Enum):
    # 成功
    SUCCESS = (0, "Success")
    # 服务异常
    FAIL = (4004, "请求处理异常！")
    SYSTEM_ERROR = (4005, "创建异步任务失败！")

    # 数据异常
    JSON_NOT_FAIL = (3000, "无效的JSON数据")
    NOT_IMAGE_URL = (3001, "响应中未包含图像数据")
    IMAGE_UPLOAD_FAIL = (3002, "响应中未包含图像数据")

    # 通用错误
    INVALID_REQUEST = (1001, "Invalid request")
    UNAUTHORIZED = (1002, "Unauthorized")
    FORBIDDEN = (1003, "Forbidden")
    NOT_FOUND = (1004, "未找到")
    INTERNAL_ERROR = (1005, "Internal server error")
    USER_NOT_POWER = (1006, "访问，无权限！")
    NOT_PARAMETER = (1007, "参数不为空！")
    NOT_LENGTH = (1008, "参数位数不足！")
    REQUEST_DATA_ERROR = (1009, "请求出体格式错误！")
    SERVICE_ERROR = (1010, "服务器内部错误！")
    # 业务错误
    USER_PASSWORD = (2000, "输入的两次密码不一致！")
    USER_NOT_FOUND = (2001, "用户未找到")
    USER_FOUND = (2003, "User found")
    INVALID_CREDENTIALS = (2002, "参数错误")
    NOT_PRINTS_FAIL = (2010, "积分扣除失败，可能积分不足")
    USER_NOT_PRINTS = (2011, "用户积分不足，无法使用生图功能！")
    SAVE_FAIL = (2013, "数据存储失败！")
    # 请求API错误
    API_REQUEST = (4000, "请求API失败！")
    API_RESPONSE_NULL = (4001, "API响应为空！")

    def __init__(self, code, message):
        self.code = code
        self.message = message

    @property
    def value(self):
        return {
            "code": self.code,
            "message": self.message
        }