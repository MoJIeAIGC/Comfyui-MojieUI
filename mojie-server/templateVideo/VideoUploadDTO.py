from rest_framework import serializers

class VideoUploadDTO(serializers.Serializer):
    video = serializers.FileField(required=True)
    description = serializers.CharField(max_length=500, required=True)
    method = serializers.CharField(max_length=100, required=True)
    user_id = serializers.IntegerField(required=True)

class TextVideoDTO(serializers.Serializer):
    description = serializers.CharField(max_length=500, required=True)
    user_id = serializers.IntegerField(required=True)