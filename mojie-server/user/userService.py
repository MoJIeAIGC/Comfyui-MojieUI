from django.contrib.auth.hashers import make_password, check_password

from common.ErrorCode import ErrorCode
from exception.business_exception import BusinessException
from user.models import SysUser

class UserService:
    @staticmethod
    def register_user(user_account: str, user_password: str, check_password: str) -> SysUser:
        """
        处理用户注册逻辑，并返回创建的用户对象
        """
        # 1. 参数校验
        if not all([user_account, user_password, check_password]):
            raise BusinessException(code=ErrorCode.NOT_PARAMETER, message='参数不能为空')

        if len(user_account) < 4:
            raise BusinessException(code=ErrorCode.NOT_LENGTH, message='用户账号过短')

        if len(user_password) < 8 or len(check_password) < 8:
            raise BusinessException(code=ErrorCode.NOT_LENGTH, message='用户密码过短')

        if user_password != check_password:
            raise BusinessException(code=ErrorCode.USER_PASSWORD, message='两次输入的密码不一致')

        # 2. 检查账号是否重复
        if SysUser.objects.filter(user_account=user_account).exists():
            raise BusinessException(code=ErrorCode.USER_FOUND, message='账号已存在')

        # 3. 加密密码
        encrypt_password = make_password(user_password)

        # 4. 创建用户
        user = SysUser.objects.create(
            avatar="",
            username=user_account,
            password=encrypt_password,
            userRole="default",
            userAITime="30s",
            isDelete=0
        )

        return user

    @staticmethod
    def login(user_account: str, user_password: str) -> SysUser:
        """
        处理用户登录逻辑，并返回用户对象
        """
        # 1. 参数校验
        if not all([user_account, user_password]):
            raise BusinessException(code=ErrorCode.NOT_PARAMETER, message='参数不能为空')

        # 2. 检查用户是否存在
        try:
            user = SysUser.objects.get(user_account=user_account)
        except SysUser.DoesNotExist:
            raise BusinessException(code=ErrorCode.USER_NOT_FOUND, message='用户不存在')

        # 3. 验证密码
        if not check_password(user_password, user.password):
            raise BusinessException(code=ErrorCode.USER_PASSWORD, message='密码错误')

        # 4. 返回用户对象
        return user