from rest_framework import serializers
from .models import templateImage
from user.models import SysUser  # 假设 SysUser 模型在 user 应用中

class TemplateImageVOSerializer(serializers.ModelSerializer):
    """
    模板图片的序列化器:前台
    """
    userImage = serializers.PrimaryKeyRelatedField(queryset=SysUser.objects.all(), write_only=True)
    related_image = serializers.PrimaryKeyRelatedField(queryset=templateImage.objects.all(), required=False)

    class Meta:
        model = templateImage
        fields = [
            'id', 'image_name', 'image_address', 'description', 'image_method',
            'userImage', 'related_image'
        ]  # 显式指定需要的字段

    def to_representation(self, instance):
        """
        自定义序列化输出格式
        """
        representation = super().to_representation(instance)

        # 将 userImage 从 ID 转换为用户名的形式
        representation['userImage'] = instance.userImage.username if instance.userImage else None

        # 将 related_image 从 ID 转换为图片名称的形式
        representation['related_image'] = instance.related_image.id if instance.related_image else None

        return representation




class TemplateImageAdminVOSerializer(serializers.ModelSerializer):
    """
    模板图片的序列化器:后台
    """
    userImage = serializers.PrimaryKeyRelatedField(queryset=SysUser.objects.all(), write_only=True)
    related_image = serializers.PrimaryKeyRelatedField(queryset=templateImage.objects.all(), required=False)

    class Meta:
        model = templateImage
        fields = '__all__'  # 包含所有字段
        read_only_fields = ('id', 'create_time', 'update_time')  # 只读字段

    def to_representation(self, instance):
        """
        自定义序列化输出格式
        """
        representation = super().to_representation(instance)

        # 将 userImage 从 ID 转换为用户名的形式
        representation['userImage'] = instance.userImage.username if instance.userImage else None

        # 将 related_image 从 ID 转换为图片名称的形式
        representation['related_image'] = instance.related_image.id if instance.related_image else None

        return representation