import os
import datetime
import random
import uuid
from django.conf import settings
from pathlib import Path


class Utils:
    @staticmethod
    def save_video(video, dest_father_dir):
        # 创建存储路径
        video_dir1 = os.path.join(settings.MEDIA_ROOT, dest_father_dir)
        if not os.path.exists(video_dir1):
            os.mkdir(video_dir1)
        video_dir2 = os.path.join(video_dir1, datetime.datetime.now().strftime("%Y"))
        if not os.path.exists(video_dir2):
            os.mkdir(video_dir2)
        video_file = os.path.join(video_dir2, datetime.datetime.now().strftime("%m"))
        if not os.path.exists(video_file):
            os.mkdir(video_file)

        # 防重名
        p = Path(video.name)
        video_pure_name = p.stem + Utils.ranstr(5)
        video_extend_name = p.suffix
        video_name = video_pure_name + video_extend_name

        # 存储视频
        destination = open(os.path.join(video_file, video_name), 'wb+')
        for chunk in video.chunks():
            destination.write(chunk)
        destination.close()

        return video_name

    @staticmethod
    def get_video_url(request, video_file, video_name):
        if request.is_secure():
            protocol = 'https'
        else:
            protocol = 'http'
        # 传回给后端VideoField要存储的视频路径
        backend_relative_path = video_file + '/' + datetime.datetime.now().strftime(
            "%Y") + '/' + datetime.datetime.now().strftime("%m") + '/' + video_name
        relative_path = settings.MEDIA_URL + backend_relative_path
        # 前端显示需要的视频路径
        frontend_url = protocol + '://' + str(request.META['HTTP_HOST']) + relative_path
        return {"url": frontend_url, "backend_path": backend_relative_path}

    @staticmethod
    def ranstr(num):
        H = 'abcdefghijklmnopqrstuvwxyz0123456789'
        H0 = 'abcdefghijklmnopqrstuvwxyz'

        salt = ''

        salt += random.choice(H0)
        for i in range(num - 1):
            salt += random.choice(H)

        return salt