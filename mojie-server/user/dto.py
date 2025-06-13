from rest_framework import serializers

class UserRegisterDTO(serializers.Serializer):
    """
    用户注册 DTO
    """
    userAccount = serializers.CharField(required=True, max_length=100, help_text="用户账号")
    userPassword = serializers.CharField(required=True, max_length=100, help_text="用户密码")
    checkPassword = serializers.CharField(required=True, max_length=100, help_text="确认密码")

    def validate(self, data):
        """
        自定义验证逻辑
        """
        if data['userPassword'] != data['checkPassword']:
            raise serializers.ValidationError("两次输入的密码不一致")
        return data


class UserLoginDTO(serializers.Serializer):
    """
    用户登录 DTO
    """
    userAccount = serializers.CharField(required=True, max_length=100, help_text="用户账号")
    userPassword = serializers.CharField(required=True, max_length=100, help_text="用户密码")