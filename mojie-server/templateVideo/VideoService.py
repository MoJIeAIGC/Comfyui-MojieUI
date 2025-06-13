from django.core.files.uploadedfile import InMemoryUploadedFile
from templateVideo.models import templateVideo
from templateVideo.utils import Utils
from exception.business_exception import BusinessException
from common  import ErrorCode
import logging
import os

logger = logging.getLogger(__name__)

# 导入新的工作流模块
from templateVideo.workflow import Workflow

class VideoService:
    @staticmethod
    def text_video(description: str, user, request=None) -> str:
        """
        文生视频业务
        :param description: 视频描述（必填）
        :param user: 用户信息（必填）
        :return: 视频的完整 URL
        """
        # 定义参数
        # server_address = "192.168.1.16:8188"  # ComfyUI 服务器地址
        # # 获取当前项目根目录
        # project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # # 构建工作流 JSON 文件路径
        # workflow_file = os.path.join(project_root, 'workflows', 'text_video.json')  # 工作流 JSON 文件路径
        # prompt_updates = {
        #     "12": {"inputs": {"value": description}},  # 正例文本
        #     "13": {"inputs": {"value": ""}},  # 反例文本
        # }

        # # 调用方法并获取文件对象
        # file_objects = Workflow.generate_videos(server_address, workflow_file, prompt_updates)
        # print(file_objects)

        # # 2. 保存视频到指定目录
        # video_file = "news_video"  # 视频存储的文件夹
        # from templateVideo.utils import Utils  # 导入 Utils 类
        # video_name = Utils.save_video(file_objects, video_file)  # 假设 utils.save_video 是保存视频的工具函数
        # print(video_name)
        # video_url = Utils.get_video_url(request, video_file, video_name)  # 获取视频的完整 URL
        # print(video_url)
        video_dict = {
            "sexy girl1": "http://192.168.1.16:8000/media/news_video/text_video/example_video_1.mp4",
            "sexy girl2": "http://192.168.1.16:8000/media/news_video/text_video/example_video_2.mp4",
            "sexy girl3": "http://192.168.1.16:8000/media/news_video/text_video/example_video_3.mp4",
            "sexy girl4": "http://192.168.1.16:8000/media/news_video/text_video/example_video_4.mp4"
            }
        video_url = video_dict.get(description)

        # 3. 将视频信息保存到数据库
        from templateVideo.models import templateVideo  # 导入 templateVideo 模型
        templateVideo.objects.create(
            video_name=description,
            video_address=video_url,
            description=description,
            video_method="user",
            userVideo=user,
            isDelete=0
        )

        return video_url