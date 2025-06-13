from rest_framework import serializers
from templateImage.models import templateImage, UserRequest, UserCloudImageStorage


class ImagesSerializer(serializers.ModelSerializer):
    img = serializers.ImageField(
        label="图片",
        max_length=256,
        use_url=True,
        error_messages={

            'invalid': '图片参数错误'
        }
    )


class UserRequestSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    service_type_display = serializers.CharField(
        source='get_service_type_display',
        read_only=True
    )

    class Meta:
        model = UserRequest
        fields = [
            'id',
            'conversation_id',
            'status',
            'status_display',
            'service_type',
            'service_type_display',
            'retry_count',
            'max_retries',
            'error_message'
        ]
        read_only_fields = fields


class UserCloudImageStorageSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserCloudImageStorage
        fields = [
            'id',
            'user',
            'username',
            'image_name',
            'image_url',
            'image_size',
            'image_type',
            'description',
            'source',
            'created_at',
            'updated_at',
            'is_deleted',
            'deleted_at',
            'metadata'
        ]
        read_only_fields = ['image_size', 'created_at', 'updated_at']