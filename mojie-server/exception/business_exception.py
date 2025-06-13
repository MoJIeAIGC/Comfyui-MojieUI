class BusinessException(Exception):
    """
    自定义异常类
    """
    def __init__(self, error_code, data=None, errors=None):
        """
        初始化异常
        :param error_code: 错误码枚举值
        :param data: 返回的数据
        :param errors: 错误信息
        """
        self.error_code = error_code
        self.data = data
        self.errors = errors
        super().__init__(self.error_code.message)

    def to_dict(self):
        """
        将异常信息转换为字典
        """
        return {
            "code": self.error_code.code,
            "message": self.error_code.message,
            "data": self.data,
            "errors": self.errors
        }