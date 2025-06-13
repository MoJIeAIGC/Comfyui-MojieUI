import random
from pathlib import Path
import os
import datetime
import uuid
from io import BytesIO
from PIL import Image  # 用于处理图片格式
from django.conf import settings

from common import ErrorCode
from exception.business_exception import BusinessException


class Utils:
    def ranstr(num):
        H = 'abcdefghijklmnopqrstuvwxyz0123456789'
        H0 = 'abcdefghijklmnopqrstuvwxyz'

        salt = ''

        salt += random.choice(H0)
        for i in range(num - 1):
            salt += random.choice(H)

        return salt

    # 接收并保存图片
    def save_img(image, dest_father_dir):

        # 创建存储路径
        img_dir1 = os.path.join(settings.MEDIA_ROOT, dest_father_dir)
        if not os.path.exists(img_dir1):
            os.makedirs(img_dir1)

        img_dir2 = os.path.join(img_dir1, datetime.datetime.now().strftime("%Y"))
        if not os.path.exists(img_dir2):
            os.makedirs(img_dir2)

        img_file = os.path.join(img_dir2, datetime.datetime.now().strftime("%m"))
        if not os.path.exists(img_file):
            os.makedirs(img_file)

        # 防重名
        p = Path(image.name)
        img_pure_name = p.stem + '_' + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        img_extend_name = p.suffix
        img_name = img_pure_name + img_extend_name

        # 存储图片
        destination_path = os.path.join(img_file, img_name)
        with open(destination_path, 'wb+') as destination:
            for chunk in image.chunks():
                destination.write(chunk)

        return img_name

    def save_img_text(image, dest_father_dir):
        """
        保存图片文件，统一转换为 PNG 格式。

        :param image: 图片文件，可以是文件对象、BytesIO 或列表。
        :param dest_father_dir: 目标存储目录。
        :return: 存储的图片文件名（包含扩展名）。
        """
        try:
            # 如果输入是列表，取第一个元素
            if isinstance(image, list):
                image = image[0]

            # 将输入转换为 BytesIO 对象
            if isinstance(image, BytesIO):
                img_bytes_io = image
            else:
                # 如果是文件对象，读取内容并转换为 BytesIO
                img_bytes_io = BytesIO(image.read())

            # 使用 Pillow 打开图片
            img = Image.open(img_bytes_io)

            # 如果图片模式不是 RGBA，转换为 RGBA 以支持透明度
            if img.mode != 'RGBA':
                img = img.convert('RGBA')

            # 生成唯一的文件名
            img_pure_name = str(uuid.uuid4())  # 使用 UUID 生成唯一文件名
            img_name = img_pure_name + '.png'  # 统一使用 .png 扩展名

            # 创建存储目录
            img_dir1 = os.path.join(settings.MEDIA_ROOT, dest_father_dir)
            if not os.path.exists(img_dir1):
                os.makedirs(img_dir1)

            img_dir2 = os.path.join(img_dir1, datetime.datetime.now().strftime("%Y"))
            if not os.path.exists(img_dir2):
                os.makedirs(img_dir2)

            img_file = os.path.join(img_dir2, datetime.datetime.now().strftime("%m"))
            if not os.path.exists(img_file):
                os.makedirs(img_file)

            # 存储图片
            img_path = os.path.join(img_file, img_name)
            img.save(img_path, format='PNG', optimize=True)  # 统一保存为 PNG 格式

            return img_name

        except Exception as e:
            # 捕获异常并记录日志
            print(f"保存图片失败: {str(e)}")
            raise BusinessException(error_code=504, data='', errors='图片存储失败')

    # 获取图片 URL
    def get_img_url_text(request, img_file, img_name):
        if request.is_secure():
            protocol = 'https'
        else:
            protocol = 'http'

        # 生成后端存储的相对路径
        backend_relative_path = os.path.join(
            img_file,
            datetime.datetime.now().strftime("%Y"),
            datetime.datetime.now().strftime("%m"),
            img_name
        )

        # 生成前端访问的完整 URL
        relative_path = os.path.join(settings.MEDIA_URL, backend_relative_path).replace("\\", "/")  # 确保路径使用 "/"
        frontend_url = f"{protocol}://{request.META['HTTP_HOST']}{relative_path}"

        return frontend_url

    # 获取图片存储地址
    def get_img_url(request, img_file, img_name):


        if request.is_secure():
            protocol = 'https'
        else:
            protocol = 'http'

        # 传回给后端 ImageField 要存储的图片路径
        backend_relative_path = os.path.join(
            img_file,
            datetime.datetime.now().strftime("%Y"),
            datetime.datetime.now().strftime("%m"),
            img_name
        ).replace("\\", "/")

        # 确保 relative_path 以斜杠开头
        relative_path = os.path.join(settings.MEDIA_URL, backend_relative_path).replace("\\", "/")
        if not relative_path.startswith('/'):
            relative_path = '/' + relative_path

        # 前端显示需要的图片路径
        frontend_url = f"{protocol}://{request.META['HTTP_HOST']}{relative_path}"

        return frontend_url


