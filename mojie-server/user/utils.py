from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import MiniProgramUser

class MiniProgramUserTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        if isinstance(user, MiniProgramUser):
            # 这里可以根据需求添加自定义逻辑
            token = super().get_token(user)
            return token
        return super().get_token(user)

class MiniProgramUserTokenObtainPairView(TokenObtainPairView):
    serializer_class = MiniProgramUserTokenObtainPairSerializer