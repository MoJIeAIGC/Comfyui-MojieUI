from rest_framework import serializers
from templateVideo.models import templateVideo

class VideosSerializer(serializers.ModelSerializer):
    video = serializers.FileField(
        label="视频",
        max_length=256,
        use_url=True,
        error_messages={
            'invalid': '视频参数错误'
        }
    )

    class Meta:
        model = templateVideo
        fields = '__all__'