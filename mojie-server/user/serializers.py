from rest_framework import serializers
from user.models import SysUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysUser
        fields = ['id', 'username', 'password', 'avatar', 'email', 'phone', 'userRole', 'points', 'userAITime', 'isDelete', 'create_time', 'update_time', 'remark']


class SysUserVOSerializer(serializers.ModelSerializer):
    """
    用户信息序列化器（对外暴露的VO版本）
    包含 is_vip 等计算属性
    """
    is_vip = serializers.BooleanField(read_only=True)  # 显式声明计算字段
    vip_expire_date = serializers.DateTimeField(read_only=True)
    vip_level = serializers.CharField(read_only=True)

    class Meta:
        model = SysUser
        fields = [
            'id',
            'username',
            'avatar',
            'email',
            'phone',
            'userRole',
            'role',
            'points',
            'create_time',
            'is_vip',  # 现在已明确定义
            'vip_expire_date',
            'vip_level'
        ]
        read_only_fields = ['id', 'create_time', 'is_vip', 'vip_expire_date', 'vip_level']

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        # 确保这些字段存在（提供默认值）
        vip_status = {
            'is_vip': representation.get('is_vip', False),
            'expire_date': representation.get('vip_expire_date'),
            'level': representation.get('vip_level')
        }

        # 移除原始字段
        representation.pop('is_vip', None)
        representation.pop('vip_expire_date', None)
        representation.pop('vip_level', None)

        # 添加组合后的VIP状态
        representation['vip_status'] = vip_status

        # 时间格式转换（示例）
        if representation.get('create_time'):
            representation['create_time'] = instance.create_time.strftime('%Y-%m-%d %H:%M:%S')

        return representation



class SysuserSerializer(serializers.ModelSerializer):
    """
    用于序列化和反序列化 Product 模型的序列化器。

    这个序列化器将 Product 模型的字段映射到 JSON 数据，以便在 API 中进行传输。
    它支持创建和更新 Product 实例。
    """
    class Meta:
        model = SysUser
        fields = [
            'id','email',  'points'
        ]
