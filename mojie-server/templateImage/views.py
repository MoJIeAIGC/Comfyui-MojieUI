import re
from datetime import time
import datetime
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import F
from django.http import StreamingHttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, status
from concurrent.futures import ThreadPoolExecutor
import random
import time
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser, MultiPartParser
from drf_spectacular.utils import extend_schema
# 前面封装的业务类
from rest_framework.renderers import JSONRenderer
import datetime
from django.forms.models import model_to_dict
from django.core.cache import cache
from rest_framework.permissions import AllowAny,IsAuthenticated
from django.core.paginator import Paginator

from rest_framework.generics import get_object_or_404, ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.utils import json
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.BaiduTranslateService import BaiduTranslateService
from common.ErrorCode import ErrorCode
from djangoProject import settings
from exception.business_exception import BusinessException
from templateImage.ChatGPTImageService import ChatGPTImageService
from templateImage.GeminiService import GeminiImageService
from templateImage.ImageService import ImageService
from templateImage.ImageUploadDTO import ImageUploadDTO, ImagesImageDTO, TextImageDTO, ImagesProductDTO, \
    WhiteBackgroundImageDTO, ImagesClueImageDTO, TextDTO, TextOnlyDTO, GeminiImageGenerationRequestDTO, \
    ChatGPTImageRequestDTO, ImagesProductWorkflowDTO, ImagesFineDetailWorkflowDTO, TextImageNewDTO, \
    WidePictureWorkflowDTO, InternalSupplementationWorkflowDTO, InternalSupplementationAndRemovalWorkflowDTO, \
    CompleteRedrawingWorkflowDTO, WhiteBackgroundImageOnlyDTO, MultiImageToImageDTO
from templateImage.QwenOmniTurboClient import QwenOmniTurboClient
from templateImage.TemplateImageVOSerializer import TemplateImageVOSerializer, TemplateImageAdminVOSerializer
from templateImage.models import templateImage, RequestStatus, UserRequest, UserCloudImageStorage
from templateImage.tenplateImageSerializer import ImagesSerializer, UserRequestSerializer, UserCloudImageStorageSerializer
from rest_framework.views import APIView
from io import BytesIO

from PIL import Image, ImageFont
from PIL.ImageDraw import ImageDraw
from django.conf import settings
from django.http import HttpResponse
import time
import random
from common.response_utils import ResponseUtil
import logging
from rest_framework import mixins, viewsets
from rest_framework.response import Response
from user.models import SysUser
from . import RequestService

from .ImagesRequest import ImageUploadManager
from .RequestService import RequestManager
from .models import ConversationList, ImageUploadRecord
from common.response_utils import ResponseUtil
from rest_framework.permissions import IsAuthenticated, AllowAny
from .task_utils import TaskUtils
from django.utils import timezone

from common import ErrorCode
from common.volcengine_tos_utils import VolcengineTOSUtils
from exception.business_exception import BusinessException
from templateImage.queue_service import QueueService
from templateImage.models import templateImage, ComfyUITask
from django.conf import settings

from user.models import SysUser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ComfyUITask
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import requests
import hashlib

logger = logging.getLogger(__name__)


# Create your views here.
class ImageViewSet(viewsets.ModelViewSet):
    queryset = templateImage.objects.all()  # 必需
    serializer_class = ImagesSerializer


# 图片
@method_decorator(csrf_exempt, name='dispatch')
class ImageUploadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='image', description='图片文件', type=OpenApiTypes.BINARY),
            OpenApiParameter(name='description', description='图片描述', type=str),
            OpenApiParameter(name='method', description='图片类别', type=str),
            OpenApiParameter(name='method_su', description='图片细分', type=str),
            OpenApiParameter(name='related_id', description='对应图片ID', type=int),
        ],
        responses={200: None},
    )

    def post(self, request):
        """
        上传图片并保存图片信息到数据库
        """
        try:
            # 使用 DTO 类验证请求参数
            dto = ImageUploadDTO(data=request.data)
            dto.is_valid(raise_exception=True)  # 如果验证失败，会抛出 ValidationError

            user = request.user  # 获取当前用户

            print("user:", user)

            # 获取验证后的数据
            image = dto.validated_data['image']  # 这里应该是文件对象
            description = dto.validated_data.get('description', '')
            image_method = dto.validated_data.get('method', '')
            method_su = dto.validated_data.get('method_su', '')
            user_id = user.id
            related_id = dto.validated_data['related_id']
            user = get_object_or_404(SysUser, id=user_id)
            related = get_object_or_404(templateImage, id=related_id)
            # 调用 ImageService 上传图片
            img = ImageService.upload_image(image, description, image_method, method_su, related, user, request)

            # 返回成功响应
            return ResponseUtil.success(
                data={"image_url": img['image_url'], "img_id": img['image_id'], "userAccount": user.username},
                message="图片上传成功")
        except Exception as error:
            # 记录错误日志并返回错误响应
            logger.error('图片上传失败，错误: %s' % (error))
            return ResponseUtil.error(errors='图片上传失败！服务器内部错误')


class TemplateImagePagination(PageNumberPagination):
    page_size = 10  # 每页显示 10 条数据
    page_size_query_param = 'page_size'  # 允许客户端通过 `page_size` 参数自定义每页大小
    max_page_size = 100  # 每页最大显示 100 条数据


@method_decorator(csrf_exempt, name='dispatch')
class TemplateGetUserListImagesView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = TemplateImagePagination  # 分页类

    @extend_schema(
        parameters=[
            OpenApiParameter(name='related', description='关联图片 ID', type=int, required=False),
            OpenApiParameter(name='method', description='图片类别', type=str, required=False),
            OpenApiParameter(name='id', description='用户ID（管理员可查看其他用户的图片）', type=int, required=False),
            OpenApiParameter(name='page', description='页码', type=int, required=False),
            OpenApiParameter(name='page_size', description='每页大小', type=int, required=False),
        ],
        responses={200: TemplateImageVOSerializer(many=True)},
    )
    def get(self, request):
        """
        获取图片列表，支持分页和过滤
        参数查询的使用例子：
        GET /api/images/?method=category
        自定义每页大小例子：
        GET /api/images/?page_size=20
        联合查询：
        GET /api/images/?related=1&method=category
        管理员可以查看指定用户的图片：
        GET /api/images/?id=1&method=user_product
        """
        # 获取查询参数
        related_image = request.query_params.get('related')  # 关联图片 ID
        image_method = request.query_params.get('method')  # 图片类别
        method_su = request.query_params.get('method_su')  # 图片类别
        specified_user_id = request.query_params.get('id')  # 用户 ID
        
        # 获取当前用户
        user = request.user

        # 构建查询条件
        queryset = templateImage.objects.all().order_by('id')  # 确保查询集是有序的
        
        # 处理用户权限和过滤
        if user.is_superuser and specified_user_id:
            # 管理员可以查看指定用户的图片
            queryset = queryset.filter(userImage_id=specified_user_id)
        else:
            # 普通用户只能查看自己的图片
            queryset = queryset.filter(userImage=user)
            
        # 应用其他过滤条件
        if related_image:
            queryset = queryset.filter(related_image=related_image)
        if image_method:
            queryset = queryset.filter(image_method=image_method)
        if method_su:
            queryset = queryset.filter(method_sub=method_su)

        # 分页
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        # 序列化数据
        serializer = TemplateImageVOSerializer(page, many=True)

        # 手动构建分页响应数据
        response_data = {
            'results': serializer.data,  # 当前页的数据
            'pagination': {
                'total': paginator.page.paginator.count,  # 总记录数
                'page': paginator.page.number,  # 当前页码
                'page_size': paginator.get_page_size(request),  # 每页大小
                'next': paginator.get_next_link(),  # 下一页的链接
                'previous': paginator.get_previous_link(),  # 上一页的链接
            }
        }

        # 返回分页结果
        return ResponseUtil.success(data=response_data, message="图片列表查询成功")


@method_decorator(csrf_exempt, name='dispatch')
class TemplateImageGetListView(APIView):
    """
    查询图片列表，支持分页
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = TemplateImagePagination

    @extend_schema(
        parameters=[
            OpenApiParameter(name='method', description='图片类别', type=str, required=False),
            OpenApiParameter(name='id', description='用户ID（管理员可查看其他用户的图片）', type=int, required=False),
        ],
        responses={200: None},
    )
    def get(self, request):
        """
        获取后台图片列表，支持分页和过滤
        """

        # 获取验证后的数据
        image_method = request.query_params.get('method', '')
        specified_user_id = request.query_params.get('id')
        
        # 获取当前用户
        user = request.user

        # 构建查询条件
        queryset = templateImage.objects.all()
        
        # 处理用户权限和过滤
        if user.is_superuser and specified_user_id:
            # 管理员可以查看指定用户的图片
            queryset = queryset.filter(userImage_id=specified_user_id)
        else:
            # 普通用户只能查看自己的图片
            queryset = queryset.filter(userImage=user)
            
        # 应用其他过滤条件
        if image_method:
            queryset = queryset.filter(image_method=image_method)

        # 分页
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        # 序列化数据
        serializer = TemplateImageAdminVOSerializer(page, many=True)

        # 返回分页结果
        return ResponseUtil.success(data=paginator.get_paginated_response(serializer.data),
                                    message="图片列表查询成功")


# 查询指定用户指定会话id的消息
class get_user_conversation_images(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    # permission_classes = [AllowAny]

    def get(self, request):
        userid = request.user.id
        sessionid = request.GET.get('sessionid')
        print(userid)
        if userid:
            if request.user.openid:
                if sessionid:
                    conversations = ConversationList.objects.filter(user_id=userid, id=sessionid).order_by('-upload_time')
                else:
                    conversations = ConversationList.objects.filter(user_id=userid).order_by('-upload_time')
                
                # 先获取所有记录
                all_records = []
                for conversation in conversations:
                    records = ImageUploadRecord.objects.filter(conversation=conversation)
                    for record in records:
                        print("记录id",record.id)
                        if record.comfyUI_task or record.comfyUI_task_id:
                            continue
                        record_data = {
                            "id": record.id,
                            'image_url': record.image_url,
                            'sessionid': conversation.id,
                            'prompt': record.prompt,
                            'image_list': record.image_list,
                            'upload_time': record.upload_time,
                            'model_used': record.model_used,
                            'image_name': record.image_name,
                            'seed_used': record.seed_used,
                            'status': record.status,
                            'comfyUI_task_id': record.comfyUI_task.task_id if record.comfyUI_task else None,
                        }
                        all_records.append(record_data)
                
                # 对整个结果集进行分页
                paginator = Paginator(all_records, int(request.GET.get('page_size', 10)))
                page_number = request.GET.get('page', 1)
                try:
                    page_obj = paginator.page(page_number)
                except Exception:
                    return ResponseUtil.error(message="请求的页码不存在")
                
                return ResponseUtil.success(data={
                    'data': list(page_obj.object_list),
                    'total': paginator.count,
                    'page': page_number,
                    'page_size': paginator.per_page
                }, message="获取成功")

                
            try:
                conversations = ConversationList.objects.filter(user_id=userid, id=sessionid)
                print(conversations)
                result = {}
                for conversation in conversations:
                    print(conversation.name)
                    records = ImageUploadRecord.objects.filter(conversation=conversation)
                    print(1212)
                    conversation_data = []
                    for record in records:
                        record_data = {
                            'id': record.id,
                            'image_url': record.image_url,
                            'prompt': record.prompt,
                            'image_list': record.image_list,
                            'model_used': record.model_used,
                            'image_name': record.image_name,
                            'seed_used': record.seed_used,
                            'status': record.status,
                            'comfyUI_task_id': record.comfyUI_task.task_id if record.comfyUI_task else None,
                        }
                        
                        # 如果有关联的任务ID，获取任务详情
                        if record.comfyUI_task:
                            try:
                                # 获取任务状态
                                task_status = TaskUtils.get_task_status(record.comfyUI_task.task_id)
                                # 添加任务信息到返回数据中
                                record_data['task_info'] = {
                                    'status': task_status.get('status'),
                                    'created_at': task_status.get('created_at'),
                                    'updated_at': task_status.get('updated_at'),
                                    'completed_at': task_status.get('completed_at') if 'completed_at' in task_status else None,
                                    'processing_time': task_status.get('processing_time'),
                                    'error': task_status.get('error'),
                                    'input_data': task_status.get('input_data'),
                                    'result': task_status.get('output_data'),
                                    'execution_time_seconds': task_status.get('execution_time_seconds')
                                }
                            except Exception as e:
                                # 如果获取任务信息失败，记录错误但不中断流程
                                print(f"获取任务 {record.comfyUI_task.task_id} 信息失败: {str(e)}")
                                record_data['task_info'] = {'error': f"获取任务信息失败: {str(e)}"}
                        
                        conversation_data.append(record_data)
                    result[conversation.id] = conversation_data
                    print("------")
                return ResponseUtil.success(data=result, message="获取成功")
            except Exception as e:
                return ResponseUtil.error(message=f"获取失败: {str(e)}")
        else:
            return ResponseUtil.error(message="获取失败")


# 会话记录删除
class ImageUploadRecordDeleteView(APIView):
    """
    图片上传记录逻辑删除接口
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            record_id = request.data.get('record_id')
            record = ImageUploadRecord.objects.get(id=record_id, user=request.user)
            record.delete()  # 直接删除记录
            return ResponseUtil.success(message="记录已删除")
        except Exception as e:
            logger.error(f"Error deleting record: {str(e)}")
            return ResponseUtil.error(message="记录不存在或无权操作")


# 查询指定用户的历史对话
class get_ConversationList(APIView):
    # authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    # permission_classes = [AllowAny]

    def get(self, request):
        userid = request.user.id
        print(userid)
        if userid:
            try:
                conversations = ConversationList.objects.filter(user_id=userid, is_delete=0).order_by('-upload_time')
                order_list = [model_to_dict(order) for order in conversations]
                return ResponseUtil.success(data=order_list, message="获取成功")
            except Exception as e:
                error_message = f"Error retrieving conversations for userid {userid}: {str(e)}"
                logger.error(error_message)  # 记录错误日志
                return ResponseUtil.error(message=error_message)
        else:
            return ResponseUtil.error(message="获取失败")


# 后台查询所有的历史对话
class get_all_conversation_images(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    # permission_classes = [AllowAny]

    def get(self, request):
        try:
            # 获取分页参数
            page = request.GET.get('page', 1)
            page_size = request.GET.get('page_size', 10)
            
            # 查询所有数据并按上传时间降序排列
            records = ImageUploadRecord.objects.all().order_by('-upload_time')
            
            # 分页处理
            paginator = Paginator(records, page_size)
            try:
                page_obj = paginator.page(page)
            except Exception:
                return ResponseUtil.error(message="请求的页码不存在")

            result = []
            for record in page_obj.object_list:
                record_data = {
                    'id': record.id,
                    'user_name': record.user.username,
                    'user_id': record.user_id,
                    'image_url': record.image_url,
                    'prompt1': record.prompt,
                    'prompt': record.prompt,
                    'image_list': record.image_list,
                    'model_used': record.model_used,
                    'image_name': record.image_name,
                    'seed_used': record.seed_used,
                    'upload_time': record.upload_time,
                }
                # 如果有关联的任务ID，获取任务详情
                if record.comfyUI_task:
                    try:
                        # 获取任务状态
                        task_status = TaskUtils.get_task_status(record.comfyUI_task.task_id)
                        # 添加任务信息到返回数据中
                        record_data['prompt'] = ''.join(re.findall(r'[\u4e00-\u9fa5]+', task_status.get('input_data').get('metadata').get('add_new_data'))),

                    except Exception as e:
                        # 如果获取任务信息失败，记录错误但不中断流程
                        print(f"获取任务 {record.comfyUI_task.task_id} 信息失败: {str(e)}")
                        record_data['task_info'] = {'error': f"获取任务信息失败: {str(e)}"}
                result.append(record_data)
            return ResponseUtil.success(data={
                'data': result,
                'total': paginator.count,
                'page': page,
                'page_size': page_size
            }, message="获取成功")
        except Exception as e:
            return ResponseUtil.error(message=str(e))


# 新增会话
class newConversation(APIView):
    # permission_classes = [AllowAny]

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            userid = request.user.id
            name = request.data.get("name")
            user = SysUser.objects.get(id=userid)
            conversation = ConversationList.objects.create(
                name=name,
                user=user,
                upload_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )

            return ResponseUtil.success(
                data={
                    "id": conversation.id,
                },
                message="创建成功"
            )


        except Exception as e:
            logger.error(f'获取数据失败: {e}')
            return ResponseUtil.error(
                message=f'获取数据失败: {e}'
            )


# 删除会话
class deleteConversation(APIView):
    # permission_classes = [AllowAny]

    def delete(self, request):
        try:
            id = request.data.get("id")
            print(id)
            # 修改为查询并更新 is_delete 字段
            conversation = ConversationList.objects.get(id=id)
            conversation.is_delete = 1
            conversation.save()

            return ResponseUtil.success(
                message="删除成功"
            )

        except Exception as e:
            logger.error(f'获取数据失败: {e}')
            return ResponseUtil.error(
                message=f'获取数据失败: {e}'
            )


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# 获取图形验证码
class getCaptcha(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # my_cookie = request.COOKIES.get('my_cookie')
        # print("没有：" , my_cookie)
        # session_id = request.session.session_key
        # print(session_id)
        # if not session_id:
        #     print("没有session_id，创建一个新的session_id")
        #     request.session.create()
        #     session_id = request.session.session_key
        #     print(session_id)
        mode = "RGB"  # 颜色模式
        size = (200, 100)  # 画布大小

        red = random.randrange(255)
        green = random.randrange(255)
        blue = random.randrange(255)
        color_bg = (red, green, blue)  # 背景色

        image = Image.new(mode=mode, size=size, color=color_bg)  # 画布
        imagedraw = ImageDraw(image, mode=mode)  # 画笔
        source = "0123456789qwertyuioplkjhgfdsazxcvbnmQWERTYUIOPLKJHGFDSAZXCVBNM"
        verify_code = ""
        for i in range(4):
            verify_code += random.choice(source)
        # verify_code = generate_code()    # 内容
        # 这里是关键，存入session
        # request.session['reg_verify_code'] = [verify_code,time.time()]  # code加入到session中
        # cache.set('reg_verify_code',verify_code)
        # cache.expire('reg_verify_code', 3 * 60)
        client_ip = get_client_ip(request)
        # print(f"客户端 IP 地址: {client_ip}")
        cache.set(client_ip, verify_code, 60)
        print(verify_code)
        print(cache.get(client_ip))
        imagefont = ImageFont.truetype("static/font.ttf", 100)  # 字体 样式 大小
        # 字体 颜色
        for i in range(len(verify_code)):
            fill = (random.randrange(255), random.randrange(255), random.randrange(255))
            imagedraw.text(xy=(50 * i, 0), text=verify_code[i], fill=fill, font=imagefont)

        # 噪点
        for i in range(1000):
            fill = (random.randrange(255), random.randrange(255), random.randrange(255))
            xy = (random.randrange(201), random.randrange(100))
            imagedraw.point(xy=xy, fill=fill)

        fp = BytesIO()

        image.save(fp, "png")
        import base64
        if cache.get(client_ip+'errorlogin'):
            print("有验证码")
            return ResponseUtil.success(
                data={
                    'image_data': base64.b64encode(fp.getvalue()).decode('utf-8'),
                    'errorlogin': cache.get(client_ip+'errorlogin')
                },
                message="验证码图片获取成功"
            )
        else:
            return ResponseUtil.success(
                data={
                    'image_data': base64.b64encode(fp.getvalue()).decode('utf-8'),
                    'errorlogin': cache.get(client_ip+'errorlogin')
                },
                message="验证码图片获取成功"
            )

        # response = HttpResponse(
        #     content=fp.getvalue(),
        #     content_type="image/png")
        # if cache.get(client_ip+'errorlogin'):
        #     print("有验证码")
        #     response.set_cookie('errorlogin', cache.get(client_ip+'errorlogin'))
        # response.headers['Access-Control-Expose-Headers'] = 'Date, Set-Cookie'
        # return response
        # return ResponseUtil.success(data=fp.getvalue(), content_type="image/png")


@method_decorator(csrf_exempt, name='dispatch')
class UserRequestListView(APIView):
    """
    用户请求历史查询API（基于APIView实现）
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='conversation_id', description='会话ID', type=str, required=True),
        ],
        responses={200: UserRequestSerializer(many=True)},
    )
    def get(self, request):
        """
        根据当前用户和会话ID查询请求列表
        """
        # 获取查询参数
        conversation_id = request.query_params.get('conversation_id')

        # 验证参数
        if not conversation_id:
            return ResponseUtil.error(message="conversation_id参数不能为空")

        # 获取当前用户
        user = request.user

        # 构建查询条件
        queryset = UserRequest.objects.filter(
            user=user,
            conversation_id=conversation_id,
            is_delete=0  # 只查询未删除的记录
        ).order_by('-created_at')

        # 序列化数据
        serializer = UserRequestSerializer(queryset, many=True)

        # 返回结果
        return ResponseUtil.success(data=serializer.data, message="请求列表查询成功")


@method_decorator(csrf_exempt, name='dispatch')
class UserInputAutoSaveView(APIView):
    """
    用户输入实时保存API
    功能：
    1. 实时保存用户输入的文本和图片URL
    2. 自动创建或更新请求记录
    3. 支持断点续传
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request={
            'type': 'object',
            'properties': {
                'conversation_id': {'type': 'string', 'description': '会话ID'},
                'text_input': {'type': 'string', 'description': '用户输入的文本'},
                'image_urls': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': '上传的图片URL列表'
                },
                'service_type': {
                    'type': 'string',
                    'enum': ['chatgpt_image', 'gemini_image'],
                    'description': '服务类型'
                }
            },
            'required': ['conversation_id']
        },
        responses={
            201: {
                'description': '保存成功',
                'type': 'object',
                'properties': {
                    'request_id': {'type': 'integer'},
                    'status': {'type': 'string'}
                }
            }
        }
    )
    def post(self, request, *args, **kwargs):
        try:
            user = request.user
            data = request.data

            # 获取或创建请求记录
            request_obj, created = UserRequest.objects.get_or_create(
                user=user,
                conversation_id=data.get('conversation_id'),
                defaults={
                    'request_data': {
                        'text_input': data.get('text_input', ''),
                        'image_urls': data.get('image_urls', [])
                    },
                    'status': RequestStatus.PENDING,
                    'service_type': data.get('service_type', 'chatgpt_image')
                }
            )

            # 如果是已存在的记录，更新数据
            if not created:
                request_data = request_obj.request_data or {}

                # 更新文本输入（如果提供了新文本）
                if 'text_input' in data:
                    request_data['text_input'] = data['text_input']

                # 更新图片URL（追加新图片）
                if 'image_urls' in data:
                    existing_urls = request_data.get('image_urls', [])
                    new_urls = [url for url in data['image_urls'] if url not in existing_urls]
                    request_data['image_urls'] = existing_urls + new_urls

                # 更新服务类型（如果变更）
                if 'service_type' in data:
                    request_obj.service_type = data['service_type']

                request_obj.request_data = request_data
                request_obj.save(update_fields=['request_data', 'service_type', 'updated_at'])

            return ResponseUtil.success(
                data={
                    'request_id': request_obj.id,
                    'status': request_obj.status,
                    'created': created
                },
                message='输入保存成功',
                code=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.error(f"保存用户输入失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                message='保存用户输入失败',
                errors=str(e),
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        parameters=[
            OpenApiParameter(name='conversation_id', description='会话ID', type=str, required=True)
        ],
        responses={
            200: {
                'description': '获取成功',
                'type': 'object',
                'properties': {
                    'text_input': {'type': 'string'},
                    'image_urls': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    },
                    'status': {'type': 'string'}
                }
            }
        }
    )
    def get(self, request, *args, **kwargs):
        """获取已保存的用户输入"""
        try:
            conversation_id = request.query_params.get('conversation_id')
            if not conversation_id:
                return ResponseUtil.error(
                    message='缺少conversation_id参数',
                    code=status.HTTP_400_BAD_REQUEST
                )

            request_obj = UserRequest.objects.filter(
                user=request.user,
                conversation_id=conversation_id,
                is_delete=0
            ).first()

            if not request_obj:
                return ResponseUtil.error(
                    message='未找到相关记录',
                    code=status.HTTP_404_NOT_FOUND
                )

            response_data = {
                'text_input': request_obj.request_data.get('text_input', ''),
                'image_urls': request_obj.request_data.get('image_urls', []),
                'status': request_obj.status,
                'request_id': request_obj.id
            }

            return ResponseUtil.success(
                data=response_data,
                message='获取成功'
            )

        except Exception as e:
            logger.error(f"获取用户输入失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                message='获取用户输入失败',
                errors=str(e),
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        request={
            'type': 'object',
            'properties': {
                'conversation_id': {'type': 'string'},
                'image_url': {'type': 'string'}
            },
            'required': ['conversation_id', 'image_url']
        },
        responses={
            200: {
                'description': '图片删除成功',
                'type': 'object',
                'properties': {
                    'remaining_urls': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    }
                }
            }
        }
    )
    def delete(self, request, *args, **kwargs):
        """从已保存数据中删除特定图片URL"""
        try:
            conversation_id = request.data.get('conversation_id')
            image_url = request.data.get('image_url')

            if not conversation_id or not image_url:
                return ResponseUtil.error(
                    message='缺少conversation_id或image_url参数',
                    code=status.HTTP_400_BAD_REQUEST
                )

            request_obj = UserRequest.objects.filter(
                user=request.user,
                conversation_id=conversation_id,
                is_delete=0
            ).first()

            if not request_obj:
                return ResponseUtil.error(
                    message='未找到相关记录',
                    code=status.HTTP_404_NOT_FOUND
                )

            request_data = request_obj.request_data or {}
            image_urls = request_data.get('image_urls', [])

            # 移除指定的图片URL
            updated_urls = [url for url in image_urls if url != image_url]
            request_data['image_urls'] = updated_urls
            request_obj.request_data = request_data
            request_obj.save(update_fields=['request_data', 'updated_at'])

            return ResponseUtil.success(
                data={'remaining_urls': updated_urls},
                message='图片删除成功'
            )

        except Exception as e:
            logger.error(f"删除图片URL失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                message='删除图片失败',
                errors=str(e),
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class UserInputAutoSaveView(APIView):
    """
    增强版用户输入实时保存API
    功能：
    1. 支持多维度识别参数(user_id, conversation_id, session_id, client_id)
    2. 结构化存储输入数据(文本、图片、元数据)
    3. 完善的版本控制和历史记录
    4. 支持多种内容类型(文本、图片、文件)
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request={
            'type': 'object',
            'properties': {
                'conversation_id': {'type': 'string', 'description': '主会话ID', 'example': 'conv_123'},
                'session_id': {'type': 'string', 'description': '子会话ID(可选)', 'example': 'sess_456'},
                'client_id': {'type': 'string', 'description': '客户端设备ID(可选)', 'example': 'device_789'},
                'text_content': {'type': 'string', 'description': '用户输入的文本内容'},
                'attachments': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'url': {'type': 'string'},
                            'type': {'type': 'string', 'enum': ['image', 'file', 'audio', 'video']},
                            'name': {'type': 'string'},
                            'size': {'type': 'integer'}
                        }
                    },
                    'description': '附件列表'
                },
                'metadata': {
                    'type': 'object',
                    'description': '附加元数据'
                },
                'service_type': {
                    'type': 'string',
                    'enum': ['chatgpt_image', 'gemini_image', 'other'],
                    'description': '服务类型'
                }
            },
            'required': ['conversation_id']
        },
        responses={
            201: {
                'description': '保存成功',
                'type': 'object',
                'properties': {
                    'request_id': {'type': 'integer'},
                    'version': {'type': 'integer'},
                    'last_updated': {'type': 'string'}
                }
            }
        }
    )
    def post(self, request, *args, **kwargs):
        try:
            user = request.user
            data = request.data

            # 构建唯一识别键
            lookup_params = {
                'user': user,
                'conversation_id': data['conversation_id'],
                'is_delete': 0
            }

            # 可选识别参数
            if data.get('session_id'):
                lookup_params['session_id'] = data['session_id']
            if data.get('client_id'):
                lookup_params['client_id'] = data['client_id']

            # 获取或创建请求记录
            request_obj, created = UserRequest.objects.get_or_create(
                **lookup_params,
                defaults={
                    'request_data': self._build_request_data(data),
                    'status': RequestStatus.PENDING,
                    'service_type': data.get('service_type', 'chatgpt_image'),
                    'version': 1  # 初始版本
                }
            )

            # 更新现有记录
            if not created:
                self._update_existing_record(request_obj, data)

            return ResponseUtil.success(
                data={
                    'request_id': request_obj.id,
                    'version': request_obj.version,
                    'last_updated': request_obj.updated_at.isoformat(),
                    'identifiers': {
                        'conversation_id': request_obj.conversation_id,
                        'session_id': request_obj.session_id,
                        'client_id': request_obj.client_id
                    }
                },
                message='输入保存成功',
                code=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.error(f"保存用户输入失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                message='保存用户输入失败',
                errors=str(e),
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _build_request_data(self, data):
        """构建结构化的请求数据"""
        return {
            'content': {
                'text': data.get('text_content', ''),
                'attachments': data.get('attachments', []),
            },
            'metadata': {
                'client_info': {
                    'ip': self.request.META.get('REMOTE_ADDR'),
                    'user_agent': self.request.META.get('HTTP_USER_AGENT')
                },
                'custom_data': data.get('metadata', {})
            },
            'timestamps': {
                'created': time.timezone.now().isoformat()
            }
        }

    def _update_existing_record(self, request_obj, data):
        """更新现有记录"""
        request_data = request_obj.request_data or {'content': {}, 'metadata': {}}

        # 更新文本内容
        if 'text_content' in data:
            request_data['content']['text'] = data['text_content']
            # 保留历史版本
            if 'history' not in request_data:
                request_data['history'] = []
            request_data['history'].append({
                'text': request_data['content']['text'],
                'updated': time.timezone.now().isoformat()
            })

        # 更新附件
        if 'attachments' in data:
            existing_attachments = request_data['content'].get('attachments', [])
            new_attachments = [
                att for att in data['attachments']
                if not any(existing['url'] == att['url'] for existing in existing_attachments)
            ]
            request_data['content']['attachments'] = existing_attachments + new_attachments

        # 更新元数据
        if 'metadata' in data:
            request_data['metadata']['custom_data'].update(data['metadata'])

        request_obj.request_data = request_data
        request_obj.version += 1
        request_obj.save(update_fields=['request_data', 'version', 'updated_at'])

    @extend_schema(
        parameters=[
            OpenApiParameter(name='conversation_id', description='主会话ID', required=True),
            OpenApiParameter(name='session_id', description='子会话ID(可选)'),
            OpenApiParameter(name='client_id', description='客户端设备ID(可选)')
        ],
        responses={
            200: {
                'description': '获取成功',
                'type': 'object',
                'properties': {
                    'content': {
                        'type': 'object',
                        'properties': {
                            'text': {'type': 'string'},
                            'attachments': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'url': {'type': 'string'},
                                        'type': {'type': 'string'},
                                        'name': {'type': 'string'}
                                    }
                                }
                            }
                        }
                    },
                    'metadata': {'type': 'object'},
                    'version': {'type': 'integer'}
                }
            }
        }
    )
    def get(self, request, *args, **kwargs):
        """获取已保存的用户输入"""
        try:
            lookup_params = {
                'user': request.user,
                'conversation_id': request.query_params['conversation_id'],
                'is_delete': 0
            }

            if 'session_id' in request.query_params:
                lookup_params['session_id'] = request.query_params['session_id']
            if 'client_id' in request.query_params:
                lookup_params['client_id'] = request.query_params['client_id']

            request_obj = UserRequest.objects.filter(**lookup_params).first()

            if not request_obj:
                return ResponseUtil.error(
                    message='未找到相关记录',
                    code=status.HTTP_404_NOT_FOUND
                )

            response_data = {
                'content': request_obj.request_data.get('content', {}),
                'metadata': request_obj.request_data.get('metadata', {}),
                'version': request_obj.version,
                'status': request_obj.status,
                'identifiers': {
                    'request_id': request_obj.id,
                    'conversation_id': request_obj.conversation_id,
                    'session_id': request_obj.session_id,
                    'client_id': request_obj.client_id
                }
            }

            return ResponseUtil.success(
                data=response_data,
                message='获取成功'
            )

        except Exception as e:
            logger.error(f"获取用户输入失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                message='获取用户输入失败',
                errors=str(e),
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        request={
            'type': 'object',
            'properties': {
                'conversation_id': {'type': 'string', 'required': True},
                'session_id': {'type': 'string'},
                'client_id': {'type': 'string'},
                'attachment_url': {'type': 'string', 'required': True}
            }
        },
        responses={
            200: {
                'description': '删除成功',
                'type': 'object',
                'properties': {
                    'remaining_attachments': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'url': {'type': 'string'},
                                'type': {'type': 'string'}
                            }
                        }
                    },
                    'version': {'type': 'integer'}
                }
            }
        }
    )
    def delete(self, request, *args, **kwargs):
        """从已保存数据中删除特定附件"""
        try:
            lookup_params = {
                'user': request.user,
                'conversation_id': request.data['conversation_id'],
                'is_delete': 0
            }

            if request.data.get('session_id'):
                lookup_params['session_id'] = request.data['session_id']
            if request.data.get('client_id'):
                lookup_params['client_id'] = request.data['client_id']

            request_obj = UserRequest.objects.filter(**lookup_params).first()

            if not request_obj:
                return ResponseUtil.error(
                    message='未找到相关记录',
                    code=status.HTTP_404_NOT_FOUND
                )

            request_data = request_obj.request_data or {'content': {}}
            attachments = request_data['content'].get('attachments', [])

            # 移除指定的附件
            updated_attachments = [
                att for att in attachments
                if att['url'] != request.data['attachment_url']
            ]

            if len(updated_attachments) != len(attachments):
                request_data['content']['attachments'] = updated_attachments
                request_obj.request_data = request_data
                request_obj.version += 1
                request_obj.save(update_fields=['request_data', 'version', 'updated_at'])

            return ResponseUtil.success(
                data={
                    'remaining_attachments': updated_attachments,
                    'version': request_obj.version
                },
                message='附件删除成功'
            )

        except Exception as e:
            logger.error(f"删除附件失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                message='删除附件失败',
                errors=str(e),
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class BaiduTranslate(APIView):
    """
    百度翻译API
    支持多语言翻译，自动检测源语言
    """
    permission_classes = [AllowAny]

    @extend_schema(
        request={
            'type': 'object',
            'properties': {
                'text': {'type': 'string', 'description': '需要翻译的文本'},
                'from_lang': {'type': 'string', 'description': '源语言，默认自动检测'},
                'to_lang': {'type': 'string', 'description': '目标语言，默认中文'}
            },
            'required': ['text']
        },
        responses={
            200: {
                'description': '翻译成功',
                'type': 'object',
                'properties': {
                    'translated_text': {'type': 'string'}
                }
            }
        }
    )
    def post(self, request):
        try:
            text = request.data.get('text')
            from_lang = request.data.get('from_lang', 'auto')
            to_lang = request.data.get('to_lang', 'zh')

            if not text:
                return ResponseUtil.error(errors='请提供需要翻译的文本')

            # 调用百度翻译服务
            translate_service = BaiduTranslateService()
            result = translate_service.translate(text)

            return ResponseUtil.success(data={'translated_text': result}, message='翻译成功')
        except Exception as e:
            logger.error(f'翻译失败: {str(e)}')
            return ResponseUtil.error(errors='翻译失败，请稍后重试')


class CloudImagePagination(PageNumberPagination):
    page_size = 20  # 每页显示 20 条数据
    page_size_query_param = 'page_size'  # 允许客户端通过 `page_size` 参数自定义每页大小
    max_page_size = 100  # 每页最大显示 100 条数据


@method_decorator(csrf_exempt, name='dispatch')
class UserCloudImageAddView(APIView):
    """
    将图片添加到用户云空间
    支持通过图片URL添加图片，可一次性添加多张图片
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser]
    
    @extend_schema(
        request={
            'type': 'object',
            'properties': {
                'image_url': {
                    'type': 'string',
                    'description': '单张图片URL (已保留向后兼容)'
                },
                'image_urls': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': '多张图片URL列表'
                },
                'image_name': {
                    'type': 'string',
                    'description': '图片名称(批量添加时将自动添加序号)'
                },
                'description': {
                    'type': 'string',
                    'description': '图片描述'
                },
                'source': {
                    'type': 'string',
                    'description': '图片来源，默认comfyui'
                },
                'image_type': {
                    'type': 'string',
                    'description': '图片类型，如image/png、image/jpeg等'
                },
                'metadata': {
                    'type': 'object',
                    'description': '其他元数据信息'
                }
            },
            'required': ['image_url or image_urls']
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'images': {
                        'type': 'array',
                        'items': {'type': 'object'}
                    },
                    'count': {'type': 'integer'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string'},
                    'error': {'type': 'string'}
                }
            }
        },
        description='添加一张或多张图片到用户云空间'
    )
    def post(self, request, *args, **kwargs):
        try:
            # 获取当前用户
            user = request.user
            
            # 获取图片URL(支持多个URL或单个URL)
            image_urls = request.data.get('image_urls', [])
            single_image_url = request.data.get('image_url')
            
            # 如果提供了单个image_url但没有提供image_urls列表，将单个URL添加到列表中
            if single_image_url and not image_urls:
                image_urls = [single_image_url]
            # 如果提供了字符串形式的image_urls，尝试解析为列表
            elif isinstance(image_urls, str):
                try:
                    # 尝试将字符串解析为JSON数组
                    import json
                    image_urls = json.loads(image_urls)
                except json.JSONDecodeError:
                    # 如果不是有效的JSON，按逗号分隔
                    image_urls = [url.strip() for url in image_urls.split(',') if url.strip()]
            
            # 验证是否有要处理的URL
            if not image_urls:
                return ResponseUtil.error(message="需要提供至少一个图片URL", code=status.HTTP_400_BAD_REQUEST)
            
            # 获取其他参数
            base_image_name = request.data.get('image_name', f"image_{int(time.time())}")
            description = request.data.get('description', '')
            source = request.data.get('source', 'comfyui')
            image_type = request.data.get('image_type', 'image/png')
            metadata = request.data.get('metadata', {})
            
            # 创建的图片对象列表
            created_images = []
            failed_urls = []
            
            # 批量处理图片URL
            for i, image_url in enumerate(image_urls):
                try:
                    # 为多张图片自动添加序号
                    if len(image_urls) > 1:
                        image_name = f"{base_image_name}_{i+1}"
                    else:
                        image_name = base_image_name
                    
                    # 获取图片大小
                    image_size = UserCloudImageStorage.get_image_size_from_url(image_url)
                    
                    # 如果无法获取图片大小，设置一个默认值
                    if image_size == 0:
                        logger.warning(f"无法获取图片大小: {image_url}")
                        image_size = 102400  # 默认100KB
                    
                    # 创建图片记录
                    cloud_image = UserCloudImageStorage.objects.create(
                        user=user,
                        image_url=image_url,
                        image_name=image_name,
                        image_size=image_size,
                        image_type=image_type,
                        description=description,
                        source=source,
                        metadata=metadata
                    )
                    
                    # 添加到结果列表
                    created_images.append(UserCloudImageStorageSerializer(cloud_image).data)
                    
                except Exception as e:
                    logger.error(f"处理图片URL失败: {image_url}, 错误: {str(e)}")
                    failed_urls.append({"url": image_url, "error": str(e)})
            
            # 返回结果
            result = {
                "images": created_images,
                "count": len(created_images),
            }
            
            if failed_urls:
                result["failed"] = failed_urls
                
            return ResponseUtil.success(
                data=result,
                message=f"成功添加 {len(created_images)} 张图片到云空间" +
                       (f", {len(failed_urls)} 张图片添加失败" if failed_urls else "")
            )
            
        except Exception as e:
            logger.error(f"添加图片到云空间失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                message=f"添加图片到云空间失败: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class UserCloudImageListView(APIView):
    """
    查询用户云空间图片
    支持分页和条件查询
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = CloudImagePagination
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='source', description='图片来源', type=str, required=False),
            OpenApiParameter(name='is_deleted', description='是否已删除', type=bool, required=False),
            OpenApiParameter(name='page', description='页码', type=int, required=False),
            OpenApiParameter(name='page_size', description='每页大小', type=int, required=False),
            OpenApiParameter(name='start_date', description='开始日期(YYYY-MM-DD)', type=str, required=False),
            OpenApiParameter(name='end_date', description='结束日期(YYYY-MM-DD)', type=str, required=False),
            OpenApiParameter(name='search', description='搜索关键词(图片名称或描述)', type=str, required=False),
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'results': {
                        'type': 'array',
                        'items': {'type': 'object'}
                    },
                    'pagination': {
                        'type': 'object',
                        'properties': {
                            'total': {'type': 'integer'},
                            'page': {'type': 'integer'},
                            'page_size': {'type': 'integer'},
                            'pages': {'type': 'integer'}
                        }
                    }
                }
            }
        },
        description='查询用户云空间图片列表'
    )
    def get(self, request, *args, **kwargs):
        try:
            # 初始化查询参数
            source = request.query_params.get('source')
            is_deleted = request.query_params.get('is_deleted')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            search = request.query_params.get('search')
            
            # 获取当前用户
            user = request.user
            
            # 构建基础查询
            queryset = UserCloudImageStorage.objects.all()
            
            # 应用过滤条件
            # 非管理员只能查看自己的图片
            if not user.is_superuser:
                queryset = queryset.filter(user=user)
            
            if source:
                queryset = queryset.filter(source=source)
                
            if is_deleted is not None:
                is_deleted_bool = is_deleted.lower() in ['true', '1', 't']
                queryset = queryset.filter(is_deleted=is_deleted_bool)
            else:
                # 默认只显示未删除的图片
                queryset = queryset.filter(is_deleted=False)
                
            # 日期过滤
            if start_date:
                try:
                    start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
                    queryset = queryset.filter(created_at__date__gte=start_date)
                except ValueError:
                    pass
                
            if end_date:
                try:
                    end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
                    queryset = queryset.filter(created_at__date__lte=end_date)
                except ValueError:
                    pass
                
            # 搜索功能
            if search:
                queryset = queryset.filter(
                    Q(image_name__icontains=search) | 
                    Q(description__icontains=search)
                )
                
            # 排序
            queryset = queryset.order_by('-created_at')
            
            # 分页
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(queryset, request)
            
            # 序列化
            serializer = UserCloudImageStorageSerializer(page, many=True)
            
            # 构建分页响应
            response_data = {
                'results': serializer.data,
                'pagination': {
                    'total': paginator.page.paginator.count,
                    'page': paginator.page.number,
                    'page_size': paginator.get_page_size(request),
                    'pages': paginator.page.paginator.num_pages
                }
            }
            
            return ResponseUtil.success(
                data=response_data,
                message="查询成功"
            )
            
        except Exception as e:
            logger.error(f"查询云空间图片失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                message=f"查询云空间图片失败: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class UserCloudImageDeleteView(APIView):
    """
    逻辑删除或恢复用户云空间图片
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request={
            'type': 'object',
            'properties': {
                'image_id': {
                    'type': 'integer',
                    'description': '图片ID'
                },
                'permanent': {
                    'type': 'boolean',
                    'description': '是否永久删除，默认为False(逻辑删除)'
                }
            },
            'required': ['image_id']
        },
        responses={200: None},
        description='删除用户云空间图片'
    )
    def delete(self, request, *args, **kwargs):
        try:
            image_id = request.data.get('image_id')
            permanent = request.data.get('permanent', False)
            
            if not image_id:
                return ResponseUtil.error(message="图片ID不能为空", code=status.HTTP_400_BAD_REQUEST)
            
            # 查询图片
            image = get_object_or_404(UserCloudImageStorage, id=image_id)
            
            # 检查权限（仅图片所有者或管理员可删除）
            if image.user != request.user and not request.user.is_superuser:
                return ResponseUtil.error(
                    message="没有权限删除此图片",
                    code=status.HTTP_403_FORBIDDEN
                )
            
            # 永久删除或逻辑删除
            if permanent:
                image.delete()
                message = "图片已永久删除"
            else:
                image.is_deleted = True
                image.deleted_at = timezone.now()
                image.save()
                message = "图片已移至回收站"
            
            return ResponseUtil.success(message=message)
            
        except Exception as e:
            logger.error(f"删除云空间图片失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                message=f"删除云空间图片失败: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        request={
            'type': 'object',
            'properties': {
                'image_id': {
                    'type': 'integer',
                    'description': '图片ID'
                }
            },
            'required': ['image_id']
        },
        responses={200: None},
        description='恢复已删除的云空间图片'
    )
    def post(self, request, *args, **kwargs):
        try:
            image_id = request.data.get('image_id')
            
            if not image_id:
                return ResponseUtil.error(message="图片ID不能为空", code=status.HTTP_400_BAD_REQUEST)
            
            # 查询图片
            image = get_object_or_404(UserCloudImageStorage, id=image_id)
            
            # 检查权限（仅图片所有者或管理员可恢复）
            if image.user != request.user and not request.user.is_superuser:
                return ResponseUtil.error(
                    message="没有权限恢复此图片",
                    code=status.HTTP_403_FORBIDDEN
                )
            
            # 恢复图片
            image.is_deleted = False
            image.deleted_at = None
            image.save()
            
            return ResponseUtil.success(message="图片已恢复")
            
        except Exception as e:
            logger.error(f"恢复云空间图片失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                message=f"恢复云空间图片失败: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@method_decorator(csrf_exempt, name='dispatch')
class UserCloudImageImportFromComfyUIView(APIView):
    """
    从ComfyUI任务中导入图片到用户云空间
    支持批量导入指定任务ID的图片或指定日期范围内的所有任务图片
    无视任务的auto_save_to_cloud设置，强制保存
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request={
            'type': 'object',
            'properties': {
                'task_ids': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': '要导入的ComfyUI任务ID列表'
                },
                'start_date': {
                    'type': 'string',
                    'format': 'date',
                    'description': '开始日期(YYYY-MM-DD)，用于批量导入日期范围内的任务'
                },
                'end_date': {
                    'type': 'string',
                    'format': 'date',
                    'description': '结束日期(YYYY-MM-DD)，用于批量导入日期范围内的任务'
                },
                'overwrite': {
                    'type': 'boolean',
                    'description': '是否覆盖已导入的任务图片，默认False'
                }
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'imported_tasks': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    },
                    'imported_images': {'type': 'integer'},
                    'failed_tasks': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'task_id': {'type': 'string'},
                                'error': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        },
        description='从ComfyUI任务中导入图片到用户云空间，无视自动保存开关设置'
    )
    def post(self, request, *args, **kwargs):
        try:
            # 获取当前用户
            user = request.user
            
            # 获取请求参数
            task_ids = request.data.get('task_ids', [])
            start_date = request.data.get('start_date')
            end_date = request.data.get('end_date')
            overwrite = request.data.get('overwrite', False)
            
            # 如果提供了字符串形式的task_ids，尝试解析
            if isinstance(task_ids, str):
                try:
                    import json
                    task_ids = json.loads(task_ids)
                except json.JSONDecodeError:
                    task_ids = [tid.strip() for tid in task_ids.split(',') if tid.strip()]
            
            # 构建查询条件
            query = ComfyUITask.objects.filter(status=ComfyUITask.STATUS_COMPLETED)
            
            # 非管理员只能导入自己的任务
            if not user.is_superuser:
                query = query.filter(user=user)
            
            # 如果指定了任务ID，则只导入这些任务
            if task_ids:
                query = query.filter(task_id__in=task_ids)
            # 如果指定了日期范围，则导入该范围内的任务
            elif start_date or end_date:
                if start_date:
                    start_datetime = datetime.datetime.strptime(start_date, "%Y-%m-%d").replace(
                        hour=0, minute=0, second=0
                    )
                    query = query.filter(completed_at__gte=start_datetime)
                
                if end_date:
                    end_datetime = datetime.datetime.strptime(end_date, "%Y-%m-%d").replace(
                        hour=23, minute=59, second=59
                    )
                    query = query.filter(completed_at__lte=end_datetime)
            else:
                # 如果没有指定任务ID和日期范围，返回错误
                return ResponseUtil.error(
                    message="必须指定任务ID列表或日期范围",
                    code=status.HTTP_400_BAD_REQUEST
                )
            
            # 如果不覆盖，则排除已导入的任务
            if not overwrite:
                query = query.filter(saved_to_cloud=False)
                
            # 执行查询
            tasks = query.all()
            
            if not tasks:
                return ResponseUtil.success(
                    data={
                        "imported_tasks": [],
                        "imported_images": 0,
                        "message": "没有找到符合条件的任务或所有任务已导入"
                    },
                    message="没有找到需要导入的任务"
                )
            
            # 批量导入图片
            imported_tasks = []
            imported_images_count = 0
            failed_tasks = []
            
            for task in tasks:
                try:
                    # 导入图片到云空间（使用force=True强制保存，无视自动保存开关）
                    if task.save_to_user_cloud(force=True):
                        imported_tasks.append(task.task_id)
                        # 统计已导入的图片数量
                        if 'images' in task.output_data:
                            images = task.output_data.get('images', [])
                            if isinstance(images, list):
                                imported_images_count += len(images)
                            else:
                                imported_images_count += 1
                    else:
                        failed_tasks.append({
                            "task_id": task.task_id,
                            "error": "没有找到可导入的图片或导入失败"
                        })
                except Exception as e:
                    logger.error(f"导入任务 {task.task_id} 图片失败: {str(e)}")
                    failed_tasks.append({
                        "task_id": task.task_id,
                        "error": str(e)
                    })
            
            # 返回结果
            result = {
                "imported_tasks": imported_tasks,
                "imported_images": imported_images_count
            }
            
            if failed_tasks:
                result["failed_tasks"] = failed_tasks
            
            return ResponseUtil.success(
                data=result,
                message=f"成功从 {len(imported_tasks)} 个任务中导入 {imported_images_count} 张图片到云空间"
            )
            
        except Exception as e:
            logger.error(f"导入ComfyUI任务图片失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                message=f"导入ComfyUI任务图片失败: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@method_decorator(csrf_exempt, name='dispatch')
class ComfyUITaskAutoSaveSettingView(APIView):
    """
    设置ComfyUI任务自动保存到云空间的开关
    支持设置全局默认值或特定任务的设置
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request={
            'type': 'object',
            'properties': {
                'task_id': {
                    'type': 'string',
                    'description': '特定任务ID（可选，不提供则设置全局默认值）'
                },
                'auto_save': {
                    'type': 'boolean',
                    'description': '是否自动保存到云空间'
                },
                'task_ids': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': '要设置的多个任务ID列表（可选）'
                }
            },
            'required': ['auto_save']
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'updated_tasks': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    },
                    'default_setting': {'type': 'boolean'},
                    'failed_tasks': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    }
                }
            }
        },
        description='设置ComfyUI任务自动保存到云空间的开关'
    )
    def post(self, request, *args, **kwargs):
        try:
            # 获取当前用户
            user = request.user
            
            # 获取请求参数
            task_id = request.data.get('task_id')
            task_ids = request.data.get('task_ids', [])
            auto_save = request.data.get('auto_save')
            
            # 验证必要参数
            if auto_save is None:
                return ResponseUtil.error(
                    message="必须指定auto_save参数",
                    code=status.HTTP_400_BAD_REQUEST
                )
            
            # 将auto_save转换为布尔值
            auto_save = bool(auto_save)
            
            # 如果提供了字符串形式的task_ids，尝试解析
            if isinstance(task_ids, str):
                try:
                    import json
                    task_ids = json.loads(task_ids)
                except json.JSONDecodeError:
                    task_ids = [tid.strip() for tid in task_ids.split(',') if tid.strip()]
            
            # 如果提供了单个task_id，加入到task_ids列表中
            if task_id and task_id not in task_ids:
                task_ids.append(task_id)
            
            result = {
                "updated_tasks": [],
                "failed_tasks": []
            }
            
            # 如果指定了任务ID列表，更新这些任务的设置
            if task_ids:
                # 构建任务查询
                query = ComfyUITask.objects.filter(task_id__in=task_ids)
                
                # 非管理员只能更新自己的任务
                if not user.is_superuser:
                    query = query.filter(user=user)
                
                # 批量更新
                updated_count = query.update(auto_save_to_cloud=auto_save)
                
                # 获取更新成功的任务ID列表
                updated_tasks = list(query.values_list('task_id', flat=True))
                result["updated_tasks"] = updated_tasks
                
                # 计算更新失败的任务
                failed_tasks = list(set(task_ids) - set(updated_tasks))
                result["failed_tasks"] = failed_tasks
                
                return ResponseUtil.success(
                    data=result,
                    message=f"已将 {len(updated_tasks)} 个任务的自动保存设置更新为 {'开启' if auto_save else '关闭'}"
                )
            else:
                # 如果没有指定任务ID，则更新系统默认设置
                # 这里可以保存到系统设置表或缓存中（示例使用缓存）
                cache_key = f"comfyui_auto_save_default_{user.id}" if not user.is_superuser else "comfyui_auto_save_default_global"
                cache.set(cache_key, auto_save, timeout=None)  # 永不过期
                
                result["default_setting"] = auto_save
                
                return ResponseUtil.success(
                    data=result,
                    message=f"已将{'全局' if user.is_superuser else '用户'} ComfyUI 任务自动保存默认设置更新为 {'开启' if auto_save else '关闭'}"
                )
                
        except Exception as e:
            logger.error(f"设置自动保存开关失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                message=f"设置自动保存开关失败: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='task_id', description='任务ID（可选）', type=str, required=False),
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'auto_save': {'type': 'boolean'},
                    'task_id': {'type': 'string'}
                }
            }
        },
        description='获取ComfyUI任务自动保存设置'
    )
    def get(self, request, *args, **kwargs):
        try:
            # 获取当前用户
            user = request.user
            
            # 获取任务ID（可选）
            task_id = request.query_params.get('task_id')
            
            # 如果指定了任务ID，获取该任务的设置
            if task_id:
                try:
                    task = ComfyUITask.objects.get(task_id=task_id)
                    
                    # 非管理员只能查看自己的任务
                    if not user.is_superuser and task.user != user:
                        return ResponseUtil.error(
                            message="没有权限查看此任务",
                            code=status.HTTP_403_FORBIDDEN
                        )
                    
                    return ResponseUtil.success(
                        data={
                            "task_id": task_id,
                            "auto_save": task.auto_save_to_cloud
                        },
                        message=f"任务 {task_id} 的自动保存设置为 {'开启' if task.auto_save_to_cloud else '关闭'}"
                    )
                    
                except ComfyUITask.DoesNotExist:
                    return ResponseUtil.error(
                        message=f"任务 {task_id} 不存在",
                        code=status.HTTP_404_NOT_FOUND
                    )
            else:
                # 如果没有指定任务ID，获取默认设置
                # 明确设置默认值为False，确保当缓存中没有值时返回False
                cache_key = f"comfyui_auto_save_default_{user.id}" if not user.is_superuser else "comfyui_auto_save_default_global"
                auto_save = cache.get(cache_key, False)  # 默认为关闭
                
                return ResponseUtil.success(
                    data={
                        "auto_save": auto_save,
                        "is_global": user.is_superuser
                    },
                    message=f"{'全局' if user.is_superuser else '用户'} ComfyUI 任务自动保存默认设置为 {'开启' if auto_save else '关闭'}"
                )
                
        except Exception as e:
            logger.error(f"获取自动保存设置失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                message=f"获取自动保存设置失败: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class TemplateImageDeleteView(APIView):
    """
    删除模板图片及其在对象存储中的实际文件
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request={
            'type': 'object',
            'properties': {
                'image_id': {
                    'type': 'integer',
                    'description': '要删除的图片ID'
                }
            },
            'required': ['image_id']
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'image_id': {'type': 'integer'},
                    'db_deleted': {'type': 'boolean'},
                    'object_deleted': {'type': 'boolean'},
                    'object_name': {'type': 'string'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'}
                }
            },
            404: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'}
                }
            }
        },
        description='删除指定ID的图片及其在对象存储中的文件'
    )
    def delete(self, request, *args, **kwargs):
        try:
            # 获取图片ID
            image_id = request.data.get('image_id')
            
            if not image_id:
                return ResponseUtil.error(
                    message="必须提供图片ID",
                    code=status.HTTP_400_BAD_REQUEST
                )
            
            # 获取当前用户
            user = request.user
            
            # 调用ImageService的delete_image方法删除图片
            result = ImageService.delete_image(image_id=image_id, user=user)
            
            return ResponseUtil.success(
                data=result,
                message="图片删除成功" if result.get("db_deleted") and result.get("object_deleted") else
                        "图片部分删除成功" if result.get("db_deleted") or result.get("object_deleted") else
                        "图片删除失败"
            )
            
        except BusinessException as be:
            # 处理业务异常
            logger.error(f"删除图片失败，业务异常: {be.errors}")
            return ResponseUtil.error(
                message=be.errors,
                code=be.error_code if hasattr(be, 'error_code') else status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # 处理其他异常
            logger.error(f"删除图片失败，系统异常: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                message=f"删除图片失败: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@method_decorator(csrf_exempt, name='dispatch')
class WhiteBackgroundOnlyAPIView(APIView):
    """
    图像生成白底图像并返回任务信息。(独立不经过comfyUI工作流)
    调用专门的抠图服务接口，将结果上传至OSS并保存到数据库
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=WhiteBackgroundImageOnlyDTO,
        responses={200: None},
    )
    def post(self, request, *args, **kwargs):
        try:
            # 使用 DTO 类验证请求参数
            dto = WhiteBackgroundImageOnlyDTO(data=request.data)
            dto.is_valid(raise_exception=True)  # 如果验证失败，会抛出 ValidationError
            image = dto.validated_data['image']  # 这里应该是文件对象
            # 获取验证后的数据
            description = dto.validated_data.get('description', 'White')
            user = request.user
            
            if not image:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER, data='', errors="图片参数不能为空")
            if not description:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER, data='', errors="描述参数不能为空")
            
            # 调用抠图服务接口
            segment_api_url = settings.WHITE_SERVER_ADDRESS
            try:
                # 使用form-data格式，参数名为file
                files = {'file': (image.name, image, image.content_type)}
                
                response = requests.post(
                    segment_api_url,
                    files=files
                )
                
                if response.status_code != 200:
                    logger.error(f"抠图服务返回错误：状态码 {response.status_code}, 响应: {response.text}")
                    raise BusinessException(error_code=ErrorCode.FAIL, data='', errors=f"抠图服务响应错误：{response.status_code}")
                
                # 获取返回的二进制图片数据
                result_image_binary = response.content
                
                # 生成唯一文件名
                current_time = timezone.now().strftime("%Y%m%d%H%M%S")
                random_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                filename = f"white_bg_{current_time}_{random_str}.png"
                
                # 上传到OSS
                tos_utils = VolcengineTOSUtils()
                image_url = tos_utils.upload_image(
                    object_name=filename,
                    file_data=result_image_binary
                )

                # 3. 将图片信息保存到数据库
                template_image = templateImage.objects.create(
                    image_name=filename,
                    image_address=image_url,
                    description=description,
                    image_method='white_background',
                    userImage=user,
                    isDelete=0
                )
                
                # 返回成功响应
                return ResponseUtil.success(
                    data={
                        "image_url": image_url,
                        "image_id": template_image.id,
                        "userAccount": user.username
                    },
                    message="白底图生成成功"
                )
                
            except requests.RequestException as e:
                logger.error(f"调用抠图服务失败: {str(e)}")
                raise BusinessException(error_code=ErrorCode.FAIL, data='', errors=f"调用抠图服务失败: {str(e)}")

        except BusinessException as be:
            logger.error(f"业务异常: {str(be)}")
            return ResponseUtil.error(message=be.errors)
        except Exception as e:
            logger.error(f"WhiteBackgroundAPIView 处理失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(message=f"白底图生成失败: {str(e)}")

@method_decorator(csrf_exempt, name='dispatch')
class ColorAdjustmentImageView(APIView):
    """
    色彩调节图片视图
    接收输入图片URL和输出图片URL，创建新会话并记录图片信息
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='input_image_url', description='修改之前的图片', type=str, required=False),
            OpenApiParameter(name='output_image_url', description='修改之后的图片url', type=str, required=False),
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'conversation_id': {'type': 'integer'},
                    'image_record_id': {'type': 'integer'},
                    'message': {'type': 'string'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'}
                }
            }
        },
        description='创建色彩调节会话并记录图片信息'
    )
    def post(self, request, *args, **kwargs):
        try:
            # 获取请求参数
            input_image_url = request.data.get('input_image_url')
            output_image_url = request.data.get('output_image_url')
            conversation_name = request.data.get('conversation_name', '色彩调节')
            
            # 参数验证
            if not input_image_url or not output_image_url:
                return ResponseUtil.error(
                    message="输入图片URL和输出图片URL不能为空",
                    code=status.HTTP_400_BAD_REQUEST
                )
            
            # 获取当前用户
            user = request.user
            
            # 从输出图片URL中提取图片名称
            try:
                # 尝试从URL中提取文件名
                output_image_name = output_image_url.split('/')[-1]
                # 如果文件名包含查询参数，去除查询参数
                if '?' in output_image_name:
                    output_image_name = output_image_name.split('?')[0]
            except Exception:
                # 如果提取失败，使用默认名称
                output_image_name = f"color_adjusted_image_{int(time.time())}"
            
            # 创建新会话
            conversation = ConversationList.objects.create(
                name=conversation_name,
                user=user,
                upload_time=timezone.now()
            )
            
            # 生成随机种子
            random_seed = str(random.randint(1000000, 9999999))
            
            # 创建图片上传记录
            image_record = ImageUploadRecord.objects.create(
                user=user,
                image_list=input_image_url,  # 输入图片URL
                image_url=output_image_url,  # 输出图片URL
                image_name=output_image_name,
                prompt="色彩调节",
                seed_used=random_seed,
                model_used="色彩调节模型",
                status=RequestStatus.COMPLETED,  # 已完成状态
                conversation=conversation  # 关联到新创建的会话
            )
            
            # 返回成功响应
            return ResponseUtil.success(
                data={
                    "conversation_id": conversation.id,
                    "image_record_id": image_record.id
                },
                message="色彩调节图片记录创建成功"
            )
            
        except Exception as e:
            logger.error(f"色彩调节图片记录创建失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                message=f"色彩调节图片记录创建失败: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

