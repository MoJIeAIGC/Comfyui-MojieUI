from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView

from common.response_utils import ResponseUtil
import logging
from user.models import SysUser
from rest_framework.response import Response
import http.client
import json
from configparser import ConfigParser
from rest_framework.permissions import AllowAny,IsAuthenticated
import requests
logger = logging.getLogger(__name__)
from common.response_utils import ResponseUtil
from .models import templateVideo
import datetime

# 数字人视频生成接口
class RunningHubVideoAPIView(APIView):
    """
    调用RunningHub API生成视频的接口
    """
    # permission_classes = [AllowAny] 
    permission_classes = [IsAuthenticated]  

    
    def post(self, request):
        # 从config.ini读取apiKey
        config = ConfigParser()
        # config = configparser.ConfigParser()
        config.read('config/config.ini')
        # config.read('f:/project/mjapplication_server_new/config/config.ini')
        api_key = config.get('runninghub', 'apiKey')
        
        # 获取请求参数
        # text = request.data.get('text', '3d0272b7c83695a30f8dc8ed8f9748fbf03797e6458ce185ec8e2560458028dd.mp4')
        # video1 = request.data.get('video', '3d0272b7c83695a30f8dc8ed8f9748fbf03797e6458ce185ec8e2560458028dd.mp4')
        # audio1 = request.data.get('audio', '69f836b46299093a0d6d2dbd2d7a96027bdb1750d72ca0debedf6897de2cd072.mp3')
        
        video1 = request.data.get('video')
        audio1 = request.data.get('audio')
        if not video1 or not audio1:
            return ResponseUtil.error(message = '视频和音频不能为空')
        # if not text:
            # return Response({'error': 'text参数不能为空'}, status=400)
            
        try:
            # 调用RunningHub API
            conn = http.client.HTTPSConnection("www.runninghub.cn")
            payload = json.dumps({
                "apiKey": api_key,
                "workflowId": "1925527587681136642",
                "webhookUrl": "https://www.qihuaimage.com/api/video/callback/",
                "nodeInfoList": [
                    {
                        "nodeId": "1",
                        "fieldName": "file",
                        "fieldValue": video1
                        # "fieldValue": text
                    },
                    {
                        "nodeId": "4",
                        "fieldName": "audio",
                        "fieldValue": audio1
                        # "fieldValue": text
                    }
                ]
            })
            headers = {
                'Host': 'www.runninghub.cn',
                'Content-Type': 'application/json'
            }
            conn.request("POST", "/task/openapi/create", payload, headers)
            res = conn.getresponse()
            data = res.read()
            logger.info(f"RunningHub API响应: {data.decode('utf-8')}")
            # user = SysUser.objects.get(id=41)
            user = request.user
            numman = templateVideo.objects.create(
                video_name=video1,
                audeo_address=audio1,
                create_time=datetime.datetime.now(),
                isDelete=0,
                status=0,
                userVideo=user,
                task_id=json.loads(data.decode("utf-8"))['data']['taskId']
            )
            
            response_data = json.loads(data.decode("utf-8"))
            response_data['video_record_id'] = numman.id
            
            return ResponseUtil.success(data=response_data)
            
        except Exception as e:
            logger.error(f"调用RunningHub API失败: {e}")
            return Response({'error': str(e)}, status=500)


# 查询状态接口
class TemplateVideoStatusAPIView(APIView):
    """
    根据videoid查询templateVideo状态并调用RunningHub API获取输出
    """
    # permission_classes = [AllowAny]
    permission_classes = [IsAuthenticated]  

    def get(self, request, videoid):
        try:
            # 从config.ini读取apiKey
            config = ConfigParser()
            config.read('config/config.ini')
            api_key = config.get('runninghub', 'apiKey')
            
            # 获取视频记录
            video = templateVideo.objects.get(id=videoid)
            if video.status == 1:  # 如果状态为1，直接返回视频地址
                return ResponseUtil.success(data={
                    'id': video.id,
                    'video_address': video.video_address,
                    'task_status': 'completed'
                })
            
            # 调用RunningHub API获取输出
            url = "https://www.runninghub.cn/task/openapi/outputs"
            headers = {
                'Host': 'www.runninghub.cn',
                'Content-Type': 'application/json'
            }
            payload = json.dumps({
                "apiKey": api_key,
                "taskId": video.task_id  # 假设task_id已存储在video对象中
            })
            
            response = requests.post(url, headers=headers, data=payload)
            response_data = response.json()
            
            if response_data.get('code') == 0 and response_data.get('data'):
                # 更新视频记录
                video.status = 1
                video.video_address = response_data['data'][0]['fileUrl']
                video.save()
                
                return ResponseUtil.success(data={
                    'id': video.id,
                    'video_address': video.video_address,
                    'task_status': 'completed'
                })
            else:
                return ResponseUtil.success(data={
                    'status': 0,
                    'message': '生成中',
                    'task_status': 'processing'
                })
                
        except templateVideo.DoesNotExist:
            return ResponseUtil.error(message="视频不存在", code=404)
        except Exception as e:
            logger.error(f"查询视频状态失败: {str(e)}")
            return ResponseUtil.error(message=f"查询失败: {str(e)}", code=500)

# 上传接口
class FileUploadAPIView(APIView):
    """上传视频/音频文件到RunningHub的接口"""
    # permission_classes = [AllowAny]
    permission_classes = [IsAuthenticated]  
    
    def post(self, request):
        try:
            # 从config.ini读取apiKey
            config = ConfigParser()
            config.read('config/config.ini')
            api_key = config.get('runninghub', 'apiKey')
            
            # 获取上传的文件
            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                return Response({'error': '请上传文件'}, status=400)
            
            # 调用RunningHub上传API
            url = "https://www.runninghub.cn/task/openapi/upload"
            headers = {
                'Host': 'www.runninghub.cn',
                'Authorization': f'Bearer {api_key}'
            }
            files = {
                'file': (uploaded_file.name, uploaded_file, uploaded_file.content_type)
            }
            payload={
                "apiKey": api_key,
            }
            
            response = requests.post(url, headers=headers,data=payload, files=files)
            response_data = response.json()
            
            return ResponseUtil.success(data = response_data)
            
        except Exception as e:
            logger.error(f"文件上传处理失败: {e}")
            return Response({'error': str(e)}, status=500)


# 查询生成记录
class TemplateVideoListAPIView(APIView):
    """
    查询templateVideo列表
    """
    # permission_classes = [AllowAny]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        videos = templateVideo.objects.filter(userVideo=request.user,isDelete=0).order_by('-create_time')
        video_list = []
        for video in videos:
            video_list.append({
                'id': video.id,
                'video_name': video.video_name,
                # 'audeo_address': video.audeo_address,
                'video_address': video.video_address,
                'create_time': video.create_time,
            })
        return ResponseUtil.success(data=video_list)

# 删除接口
class TemplateVideoDeleteAPIView(APIView):
    """
    删除templateVideo记录
    """
    # permission_classes = [AllowAny]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            videoid = request.data.get('id')
            # 逻辑删除，将isDelete字段设置为1
            video = templateVideo.objects.get(id=videoid)
            video.isDelete = 1
            video.save()
            return ResponseUtil.success(message="删除成功")
        except templateVideo.DoesNotExist:
            return ResponseUtil.error(message="视频不存在", code=404)
        except Exception as e:
            logger.error(f"删除视频失败: {str(e)}")
            return ResponseUtil.error(message=f"删除失败: {str(e)}", code=500)

# 回调接口
@method_decorator(csrf_exempt, name='dispatch')
class RunningHubCallbackAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            if data.get('event') != 'TASK_END':
                return ResponseUtil.error(message="Invalid event type")
            
            task_id = data.get('taskId')
            if not task_id:
                return ResponseUtil.error(message="Missing taskId")
            
            try:
                event_data = json.loads(data.get('eventData', '{}'))
                file_url = event_data.get('data', [{}])[0].get('fileUrl')
                if not file_url:
                    return ResponseUtil.error(message="Missing fileUrl in eventData")
                
                # 查找并更新记录
                from templateVideo.models import TemplateVideo
                video = TemplateVideo.objects.filter(task_id=task_id).first()
                if not video:
                    return ResponseUtil.error(message="Video record not found")
                
                video.status = 1
                video.video_address = file_url
                video.save()
                
                return ResponseUtil.success(message="Video record updated successfully")
                
            except json.JSONDecodeError:
                return ResponseUtil.error(message="Invalid eventData format")
            except Exception as e:
                return ResponseUtil.error(message=f"Update failed: {str(e)}")
                
        except Exception as e:
            return ResponseUtil.error(message=f"Callback processing failed: {str(e)}")

        
