from django.http import StreamingHttpResponse
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, OpenApiParameter
from concurrent.futures import ThreadPoolExecutor
import json
import time
import random
from django.db.models import F
from django.core.paginator import Paginator
import datetime
from django.db import transaction

from rest_framework_simplejwt.authentication import JWTAuthentication

from common.ErrorCode import ErrorCode
from common.response_utils import ResponseUtil
from exception.business_exception import BusinessException
from .ChatGPTImageService import ChatGPTImageService
from .ChatGPTImageServiceNew import ChatGPTImageServiceNew
from .FluxKontextProService import FluxKontextProService
from .GeminiService import GeminiImageService
from .ImageUploadDTO import ChatGPTImageRequestDTO, GeminiImageGenerationRequestDTO, TextOnlyDTO, TextDTO, \
    OpenAIImageRequestDTO, TextVolcengineDTO, FluxKontextProRequestDTO
from .ImagesRequest import ImageUploadManager
from .QwenOmniTurboClient import QwenOmniTurboClient
from .RequestService import RequestManager
from .models import SysUser, RequestStatus, PointsDeductionHistory
from django.conf import settings
import logging
from .VolcengineVisualService import VolcengineVisualService

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class GeminiImageGenerationView(APIView):
    """
    Gemini多模态图像生成API V2
    支持图文输入(图片可选)，可选流式返回生成进度
    """
    parser_classes = [JSONParser, MultiPartParser]

    # 使用线程池管理异步任务
    _executor = ThreadPoolExecutor(max_workers=4)

    def _generate_random_seed(self):
        return random.SystemRandom().randint(1, 2 ** 31 - 1)

    def _get_user_credits(self, user_id):
        """获取用户当前积分（辅助方法）"""
        try:
            return SysUser.objects.get(id=user_id).points
        except Exception as e:
            logger.warning(f"获取用户积分失败: {str(e)}")
            return None

    def _check_and_update_user_credits(self, user_id):
        """检查用户积分并更新，优先扣除VIP积分，没有VIP积分则扣除普通积分"""
        try:
            user = SysUser.objects.get(id=user_id)
            
            # 检查是否有足够的积分（VIP积分或普通积分）
            if user.vip_points <= 0 and user.points <= 0:
                raise BusinessException(error_code=ErrorCode.USER_NOT_PRINTS, data='',
                                        errors="用户积分不足，无法使用生图功能")

            # 优先扣除VIP积分
            if user.vip_points > 0:
                updated = SysUser.objects.filter(
                    id=user_id,
                    vip_points__gte=1
                ).update(vip_points=F('vip_points') - 1)
            else:
                # 如果没有VIP积分，扣除普通积分
                updated = SysUser.objects.filter(
                    id=user_id,
                    points__gte=1
                ).update(points=F('points') - 1)

            if not updated:
                raise BusinessException(error_code=ErrorCode.NOT_PRINTS_FAIL, data='',
                                        errors="积分扣除失败，可能积分不足")

            user.refresh_from_db()
            return {
                'points': user.points,
                'vip_points': user.vip_points
            }

        except SysUser.DoesNotExist:
            raise BusinessException(error_code=ErrorCode.USER_NOT_FOUND, data='', errors="用户不存在")
        except Exception as e:
            logger.error(f"更新用户积分失败: {str(e)}", exc_info=True)
            raise BusinessException(error_code=ErrorCode.FAIL, data='', errors="积分处理失败，请稍后再试")

    @extend_schema(
        request=GeminiImageGenerationRequestDTO,
        responses={
            200: None,  # 流式响应
            201: {  # 非流式响应
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "message": {"type": "string"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "image_url": {"type": "string"},
                            "image_name": {"type": "string"},
                            "model_used": {"type": "string"},
                            "seed_used": {"type": "integer"},
                            "prompt": {"type": "string"},
                            "conversation_id": {"type": "integer"}
                        }
                    }
                }
            }
        },
        description="""
            Gemini图像生成API V2

            参数说明：
            - model: 可选Gemini模型名称
            - prompt: 必填，生成提示词
            - image_urls: 可选，参考图片URL列表（不传则仅根据描述生成）
            - aspect_ratio: 图片比例（默认自由比例）
            - temperature: 生成温度(0.0-2.0，默认1.0)
            - seed: 可选随机种子
            - user_id: 必填用户ID
            - stream: 是否流式响应（默认False）
            - conversation_id: 可选会话ID（用于长上下文）
            """
    )
    def post(self, request, *args, **kwargs):
        try:
            # 参数解析与验证
            request_data = self._parse_request_data(request)
            dto = GeminiImageGenerationRequestDTO(data=request_data)
            dto.is_valid(raise_exception=True)
            validated_data = dto.validated_data

            # 提前创建对话内容
            conversation_request = ImageUploadManager.create_upload_record(
                user_id=validated_data['user_id'],
                conversation_id=validated_data['conversation_id'],
                image_list="pending",
                prompt=validated_data['prompt'],
                model_used=validated_data.get('model', settings.GEMINI_CONFIG['DEFAULT_MODEL']),
                image_url="pending",
                image_name="",
                seed_used="",
            )

            # 检查并更新用户积分
            credit_check = self._check_and_update_user_credits(validated_data['user_id'])

            # 创建请求记录
            request_obj = RequestManager.create_request(
                user_id=validated_data['user_id'],
                conversation_id=validated_data.get('conversation_id', ''),
                request_data=validated_data,
                service_type='gemini_image'
            )

            # 标记为处理中
            RequestManager.update_request_status(
                request_obj.id,
                RequestStatus.PROCESSING
            )

            # 构建立即返回的响应数据
            response_data = {
                'request_info': {
                    'request_id': request_obj.id,
                    'status': request_obj.status,
                    'created_at': request_obj.created_at.isoformat(),
                    'service_type': request_obj.service_type
                },
                'user_id': validated_data['user_id'],
                'conversation_id': validated_data.get('conversation_id', ''),
                'message': '请求已接收，正在处理中'
            }

            # 启动后台线程处理请求
            self._executor.submit(
                self._process_gemini_request_async,
                validated_data=validated_data,
                request_obj=request_obj,
                upload_record_id=conversation_request.id,
                is_stream=validated_data.get('stream', False)
            )

            return ResponseUtil.success(
                data=response_data,
                message='请求已接收，正在处理中'
            )

        except ValueError as e:
            logger.warning(f"参数错误: {str(e)}")
            return ResponseUtil.error(errors=str(e), code=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"请求处理失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                errors="请求处理失败",
                data=str(e),
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _process_gemini_request_async(self, validated_data, request_obj, upload_record_id, is_stream):
        """异步处理Gemini图像生成请求"""
        try:
            # 处理图片URL列表
            image_urls = validated_data.get('image_urls', [])
            # 准备生成参数
            generation_params = {
                'prompt': validated_data['prompt'],
                'api_key': settings.GEMINI_CONFIG['API_KEY'],
                'model': validated_data.get('model', settings.GEMINI_CONFIG['DEFAULT_MODEL']),
                'upload_record_id': upload_record_id,
                'image_urls': image_urls if image_urls else None,
                'aspect_ratio': validated_data.get('aspect_ratio', 'Free (自由比例)'),
                'temperature': validated_data.get('temperature', 1.0),
                'seed': validated_data.get('seed', self._generate_random_seed()),
                'user_id': validated_data['user_id'],
                'conversation_id': validated_data.get('conversation_id'),
                'enable_long_context': validated_data.get('enable_long_context', True)
            }

            service = GeminiImageService()

            if is_stream:
                self._handle_streaming_async(service, generation_params, upload_record_id, request_obj)
            else:
                self._handle_normal_async(service, generation_params, upload_record_id, request_obj)

        except Exception as e:
            logger.error(f"异步处理Gemini请求失败: {str(e)}", exc_info=True)
            ImageUploadManager.mark_as_failed(
                record_id=upload_record_id,
                error_message=f"异步处理Gemini请求失败: {str(e)}"
            )
            RequestManager.update_request_status(
                request_obj.id,
                RequestStatus.FAILED,
                error_message=str(e)
            )

    def _handle_streaming_async(self, service, params, upload_record_id, request_obj):
        """异步处理流式响应"""
        try:
            result = service.generate_image(**params)

            if result['success']:
                RequestManager.update_request_status(
                    request_obj.id,
                    RequestStatus.COMPLETED,
                    response_data={
                        'image_url': result['image_url'],
                        'image_name': result['image_name'],
                        'seed_used': params['seed']
                    }
                )
            else:
                RequestManager.update_request_status(
                    request_obj.id,
                    RequestStatus.FAILED,
                    error_message=result.get('error', '生成失败')
                )
        except Exception as e:
            logger.error(f"流式生成失败: {str(e)}", exc_info=True)
            RequestManager.update_request_status(
                request_obj.id,
                RequestStatus.FAILED,
                error_message=str(e)
            )

    def _handle_normal_async(self, service, params, upload_record_id, request_obj):
        """异步处理普通响应"""
        try:
            result = service.generate_image(**params)

            if result['success']:
                RequestManager.update_request_status(
                    request_obj.id,
                    RequestStatus.COMPLETED,
                    response_data={
                        'image_url': result['image_url'],
                        'image_name': result['image_name'],
                        'model_used': params['model'],
                        'seed_used': params['seed'],
                        'prompt': params['prompt'],
                        'conversation_id': params.get('conversation_id')
                    }
                )

                # 标记已经完成的请求
                ImageUploadManager.mark_as_completed(
                    record_id=upload_record_id,
                    image_url=result['image_url'],
                    image_name=result['image_name']
                )
            else:
                ImageUploadManager.mark_as_failed(
                    record_id=upload_record_id,
                    error_message=result.get('error', '生成失败')
                )
                RequestManager.update_request_status(
                    request_obj.id,
                    RequestStatus.FAILED,
                    error_message=result.get('error', '生成失败')
                )
        except Exception as e:
            logger.error(f"图像生成失败: {str(e)}", exc_info=True)
            ImageUploadManager.mark_as_failed(
                record_id=upload_record_id,
                error_message=f"数据库保存失败: {str(e)}"
            )
            RequestManager.update_request_status(
                request_obj.id,
                RequestStatus.FAILED,
                error_message=str(e)
            )

    def _parse_request_data(self, request):
        if isinstance(request.data, dict):
            return request.data
        try:
            data = json.loads(request.body.decode('utf-8'))
            # 处理前端可能传递的空字符串
            if 'image_urls' in data and data['image_urls'] == '':
                data['image_urls'] = []
            return data
        except json.JSONDecodeError:
            raise BusinessException(code=ErrorCode.JSON_NOT_FAIL, data='', errors="无效的JSON数据")


# ChatGPT生成图
@method_decorator(csrf_exempt, name='dispatch')
class ChatGPTImageGenerationView(APIView):
    """
    ChatGPT图像生成API
    支持图文输入，返回生成图像（支持流式和非流式响应）

    特性：
    1. 自动处理多图片URL输入
    2. 结果存储到OSS和MySQL
    3. 支持两种响应模式
    """
    parser_classes = [JSONParser, MultiPartParser]

    def _check_and_update_user_credits(self, user_id):
        """检查用户积分并更新，优先扣除VIP积分，没有VIP积分则扣除普通积分"""
        try:
            user = SysUser.objects.get(id=user_id)
            
            # 检查是否有足够的积分（VIP积分或普通积分）
            if user.vip_points <= 0 and user.points <= 0:
                raise BusinessException(error_code=ErrorCode.USER_NOT_PRINTS, data='',
                                        errors="用户积分不足，无法使用生图功能")

            # 优先扣除VIP积分
            if user.vip_points > 0:
                updated = SysUser.objects.filter(
                    id=user_id,
                    vip_points__gte=1
                ).update(vip_points=F('vip_points') - 1)
            else:
                # 如果没有VIP积分，扣除普通积分
                updated = SysUser.objects.filter(
                    id=user_id,
                    points__gte=1
                ).update(points=F('points') - 1)

            if not updated:
                raise BusinessException(error_code=ErrorCode.NOT_PRINTS_FAIL, data='',
                                        errors="积分扣除失败，可能积分不足")

            user.refresh_from_db()
            return {
                'points': user.points,
                'vip_points': user.vip_points
            }

        except SysUser.DoesNotExist:
            raise BusinessException(error_code=ErrorCode.USER_NOT_FOUND, data='', errors="用户不存在")
        except Exception as e:
            logger.error(f"更新用户积分失败: {str(e)}", exc_info=True)
            raise BusinessException(error_code=ErrorCode.FAIL, data='', errors="积分处理失败，请稍后再试")

    @extend_schema(
        request=ChatGPTImageRequestDTO,
        responses={
            200: None,  # 流式响应
            201: {  # 非流式响应
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "message": {"type": "string"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "image_url": {"type": "string"},
                            "image_name": {"type": "string"},
                            "prompt": {"type": "string"},
                            "model_used": {"type": "string"},
                            "seed_used": {"type": "integer"}
                        }
                    }
                }
            }
        },
        description="""
        ChatGPT图像生成API

        注意：
        - 支持多图输入（最多3张）
        - 返回OSS存储的图片URL
        - 自动记录到数据库
        """
    )
    def post(self, request, *args, **kwargs):
        try:
            # 参数解析与验证
            request_data = self._parse_request_data(request)
            dto = ChatGPTImageRequestDTO(data=request_data)
            dto.is_valid(raise_exception=True)
            validated_data = dto.validated_data

            # 检查并更新用户积分
            self._check_and_update_user_credits(validated_data['user_id'])

            # 初始化服务
            service = ChatGPTImageService()

            if validated_data.get('stream', False):
                return self._handle_streaming_response(service, validated_data)
            return self._handle_normal_response(service, validated_data)

        except Exception as e:
            logger.error(f"请求处理失败: {str(e)}", exc_info=True)

            return ResponseUtil.error(
                data={
                    'status': 'error',
                    'message': '请求处理失败',
                    'error': str(e)
                },
                errors=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _parse_request_data(self, request):
        """统一解析请求数据"""
        if isinstance(request.data, dict):
            return request.data
        try:
            return json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            raise BusinessException(code=ErrorCode.JSON_NOT_FAIL.code, data='', errors="无效的JSON数据")

    def _handle_streaming_response(self, service, validated_data):
        """处理流式响应"""
        seed = validated_data.get('seed') or int(time.time() * 1000) % (2 ** 32)

        def stream_generator():
            try:
                full_response = {
                    'status': 'processing',
                    'progress': 0,
                    'image_url': None,
                    'image_name': None
                }

                # 模拟进度更新
                for progress in range(0, 101, 20):
                    full_response['progress'] = progress
                    yield f"data: {json.dumps(full_response)}\n\n"
                    time.sleep(0.3)

                # 实际生成调用
                result = service.generate_image(
                    prompt=validated_data['prompt'],
                    image_urls=validated_data.get('image_urls', []),
                    api_key=settings.CHATGPT_API_KEY,
                    api_url=settings.CHATGPT_API_URL,
                    model=validated_data.get('model', 'gpt-4o-image'),
                    user_id=validated_data['user_id'],
                    conversation_id=validated_data['conversation_id'],
                    seed=seed
                )

                if result['success']:
                    full_response.update({
                        'progress': 100,
                        'status': 'completed',
                        'image_url': result['image_url'],
                        'image_name': result['image_name'],
                        'seed_used': seed
                    })
                else:
                    full_response.update({
                        'status': 'failed',
                        'error': result.get('error', '生成失败')
                    })

                yield f"data: {json.dumps(full_response)}\n\n"

            except Exception as e:
                logger.error(f"流式生成失败: {str(e)}", exc_info=True)
                yield f"data: {json.dumps({'status': 'failed', 'error': str(e)})}\n\n"

        return StreamingHttpResponse(
            stream_generator(),
            content_type='text/event-stream'
        )

    def _handle_normal_response(self, service, validated_data):
        """处理普通响应"""
        seed = validated_data.get('seed') or random.randint(0, 2 ** 32 - 1)

        result = service.generate_image(
            prompt=validated_data['prompt'],
            image_urls=validated_data.get('image_urls', []),
            api_key=settings.CHATGPT_API_KEY,
            api_url=settings.CHATGPT_API_URL,
            model=validated_data.get('model', 'gpt-4-vision-preview'),
            user_id=validated_data['user_id'],
            conversation_id=validated_data['conversation_id'],
            seed=seed
        )

        if result['success']:
            return ResponseUtil.success(
                data={
                    'image_url': result['image_url'],
                    'image_name': result['image_name'],
                    'prompt': result['prompt'],
                    'model_used': result.get('model_used'),
                    'seed_used': seed
                },
                message='图像生成成功'
            )

        return ResponseUtil.error(
            data={
                'status': 'error',
                'message': result.get('message', '图像生成失败'),
                'error': result.get('error')
            },
            errors=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@method_decorator(csrf_exempt, name='dispatch')
class ChatGPTImageGenerationNewView(APIView):
    """
    ChatGPT图像生成API
    支持图文输入，返回生成图像（支持流式和非流式响应）

    特性：
    1. 自动处理多图片URL输入
    2. 结果存储到OSS和MySQL
    3. 支持两种响应模式
    """
    parser_classes = [JSONParser, MultiPartParser]
    permission_classes = [IsAuthenticated]  # 添加认证要求
    # 使用线程池管理异步任务
    _executor = ThreadPoolExecutor(max_workers=4)

    def _check_and_update_user_credits(self, user_id):
        """检查用户积分并更新，优先扣除VIP积分，没有VIP积分则扣除普通积分"""
        try:
            user = SysUser.objects.get(id=user_id)
            
            # 检查是否有足够的积分（VIP积分或普通积分）
            if user.vip_points <= 0 and user.points <= 0:
                raise BusinessException(error_code=ErrorCode.USER_NOT_PRINTS, data='',
                                        errors="用户积分不足，无法使用生图功能")

            # 优先扣除VIP积分
            if user.vip_points > 0:
                updated = SysUser.objects.filter(
                    id=user_id,
                    vip_points__gte=1
                ).update(vip_points=F('vip_points') - 20)
            else:
                # 如果没有VIP积分，扣除普通积分
                updated = SysUser.objects.filter(
                    id=user_id,
                    points__gte=1
                ).update(points=F('points') - 20)

            if not updated:
                raise BusinessException(error_code=ErrorCode.NOT_PRINTS_FAIL, data='',
                                        errors="积分扣除失败，可能积分不足")

            user.refresh_from_db()
            return {
                'points': user.points,
                'vip_points': user.vip_points
            }

        except SysUser.DoesNotExist:
            raise BusinessException(error_code=ErrorCode.USER_NOT_FOUND, data='', errors="用户不存在")
        except Exception as e:
            logger.error(f"更新用户积分失败: {str(e)}", exc_info=True)
            raise BusinessException(error_code=ErrorCode.FAIL, data='', errors="积分处理失败，请稍后再试")

    @extend_schema(
        request=ChatGPTImageRequestDTO,
        responses={
            200: None,  # 流式响应
            201: {  # 非流式响应
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "message": {"type": "string"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "image_url": {"type": "string"},
                            "image_name": {"type": "string"},
                            "prompt": {"type": "string"},
                            "model_used": {"type": "string"},
                            "seed_used": {"type": "integer"}
                        }
                    }
                }
            }
        },
        description="""
        ChatGPT图像生成API

        注意：
        - 支持多图输入（最多3张）
        - 返回OSS存储的图片URL
        - 自动记录到数据库
        """
    )
    def post(self, request, *args, **kwargs):
        try:
            user = request.user
            # 参数解析与验证
            request_data = self._parse_request_data(request)
            dto = ChatGPTImageRequestDTO(data=request_data)
            dto.is_valid(raise_exception=True)
            validated_data = dto.validated_data

            # 处理图片URL列表
            image_urls = validated_data.get('image_urls', [])
            images_url = ",".join(image_urls) if image_urls else ""
            # 提前创建对话内容
            conversation_request = ImageUploadManager.create_upload_record(
                user_id=user.id,
                conversation_id=validated_data['conversation_id'],
                image_list=images_url,
                prompt=validated_data['prompt'],
                model_used=settings.CHATGPT_CONFIG_NEW['MODEL'],
                image_url=images_url,
                image_name="",
                seed_used="",
            )

            # 检查并更新用户积分
            self._check_and_update_user_credits(user.id)

            # 创建请求记录
            request_obj = RequestManager.create_request(
                user_id=user.id,
                conversation_id=validated_data['conversation_id'],
                request_data=validated_data,
                service_type='chatgpt_image'
            )

            # 标记为处理中
            RequestManager.update_request_status(
                request_id=request_obj.id,
                status=RequestStatus.PROCESSING
            )

            # 构建立即返回的响应数据
            response_data = {
                'request_info': {
                    'request_id': request_obj.id,
                    'status': request_obj.status,
                    'created_at': request_obj.created_at.isoformat(),
                    'service_type': request_obj.service_type
                },
                'message': '请求已接收，正在处理中',
                'user_id': user.id,
                'conversation_id': validated_data['conversation_id']
            }

            # 启动后台线程处理请求
            self._executor.submit(
                self._process_request_async,
                service=ChatGPTImageService(),
                validated_data=validated_data,
                conversation_request_id=conversation_request.id,
                request_obj=request_obj,
                user=user,
                is_stream=validated_data.get('stream', False)
            )

            return ResponseUtil.success(
                data=response_data,
                message='请求已接收，正在处理中'
            )

        except Exception as e:
            logger.error(f"请求处理失败: {str(e)}", exc_info=True)
            if 'request_obj' in locals():
                RequestManager.update_request_status(
                    request_obj.id,
                    RequestStatus.FAILED,
                    error_message=str(e)
                )
            return ResponseUtil.error(
                data={
                    'status': 'error',
                    'message': '请求处理失败',
                    'error': str(e)
                },
                errors=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _process_request_async(self, service, validated_data, conversation_request_id, request_obj, user, is_stream):
        """异步处理请求的方法"""
        try:
            operation_type = validated_data.get('operation_type', 'generate')
            
            if operation_type == 'generate':
                result = service.generate_image(
                    prompt=validated_data['prompt'],
                    user_id=user.id,
                    conversation_id=validated_data.get('conversation_id'),
                    upload_record_id=conversation_request_id,
                    seed=self._generate_random_seed(),
                    size=validated_data.get('size', '1024x1024')
                )
            else:  # edit
                # 处理多张图片
                image_paths = validated_data.get('image_paths', [])
                if not image_paths:
                    error_msg = "编辑操作需要至少一张图片"
                    # 更新ImageUploadRecord状态为失败
                    ImageUploadManager.mark_as_failed(
                        record_id=conversation_request_id,
                        error_message=error_msg
                    )
                    raise BusinessException(error_code=ErrorCode.FAIL, data='', errors=error_msg)

                # 如果只有一张图片，直接使用单图编辑
                if len(image_paths) == 1:
                    result = service.edit_image(
                        prompt=validated_data['prompt'],
                        image_paths=image_paths,
                        mask_path=validated_data.get('mask_path'),
                        user_id=user.id,
                        conversation_id=validated_data.get('conversation_id'),
                        upload_record_id=conversation_request_id
                    )
                else:
                    # 多图编辑，使用图片合并功能
                    result = service.merge_images(
                        prompt=validated_data['prompt'],
                        image_paths=image_paths,
                        user_id=user.id,
                        conversation_id=validated_data.get('conversation_id'),
                        upload_record_id=conversation_request_id
                    )

            if result['success']:
                RequestManager.update_request_status(
                    request_obj.id,
                    RequestStatus.COMPLETED,
                    response_data={
                        'image_url': result['image_url'],
                        'image_name': result['image_name'],
                        'prompt': result['prompt'],
                        'model_used': result.get('model_used'),
                        'seed_used': result.get('seed_used'),
                        'size': result.get('size', '1024x1024'),
                        'operation_type': operation_type,
                        'image_count': len(validated_data.get('image_paths', [])) if operation_type == 'edit' else 0
                    }
                )
            else:
                # 更新ImageUploadRecord状态为失败
                ImageUploadManager.mark_as_failed(
                    record_id=conversation_request_id,
                    error_message=result.get('error', '生成失败')
                )
                RequestManager.update_request_status(
                    request_obj.id,
                    RequestStatus.FAILED,
                    error_message=result.get('error', '生成失败')
                )

        except Exception as e:
            logger.error(f"异步处理请求失败: {str(e)}", exc_info=True)
            # 确保在异常情况下也更新ImageUploadRecord状态
            ImageUploadManager.mark_as_failed(
                record_id=conversation_request_id,
                error_message=f"异步处理请求失败: {str(e)}"
            )
            RequestManager.update_request_status(
                request_obj.id,
                RequestStatus.FAILED,
                error_message=str(e)
            )

    def _parse_request_data(self, request):
        """统一解析请求数据"""
        if isinstance(request.data, dict):
            return request.data
        try:
            return json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            raise BusinessException(code=ErrorCode.JSON_NOT_FAIL.code, data='', errors="无效的JSON数据")

@method_decorator(csrf_exempt, name='dispatch')
class QwenMultimodalAPIView(APIView):
    """
    Qwen多模态生成API
    支持图文输入，流式返回生成内容
    """
    parser_classes = [JSONParser, MultiPartParser]
    permission_classes = [AllowAny]

    @extend_schema(
        request=TextDTO,
        responses={200: None},
        description="接收图片URL和文本，返回生成的文案"
    )
    def post(self, request, *args, **kwargs):
        try:
            # 参数验证
            dto = TextDTO(data=request.data)
            dto.is_valid(raise_exception=True)

            # 获取参数
            image_url = dto.validated_data.get('image_url')
            text = dto.validated_data.get('text', '')
            stream = dto.validated_data.get('stream', True)

            # 初始化客户端
            qwen_client = QwenOmniTurboClient(
                api_key=settings.DASHSCOPE_API_KEY,
                base_url=settings.DASHSCOPE_URL
            )

            if stream:
                # 流式响应生成器
                def stream_generator():
                    full_response = []
                    for chunk in qwen_client.generate_text(
                            text=text,
                            image_url=image_url,
                            stream=True
                    ):
                        if chunk:
                            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                            full_response.append(chunk)

                    # 保存生成记录
                    # if user_id:
                    #     GenerationHistory.objects.create(
                    #         user_id=user_id,
                    #         prompt=text,
                    #         image_url=image_url,
                    #         generated_text=''.join(full_response)
                    #     )

                response = StreamingHttpResponse(
                    stream_generator(),
                    content_type='text/event-stream'
                )
                response['Cache-Control'] = 'no-cache'
                return response
            else:
                # 非流式处理
                result = qwen_client.generate_text(
                    text=text,
                    image_url=image_url,
                    stream=False
                )

                # if user_id:
                #     GenerationHistory.objects.create(
                #         user_id=user_id,
                #         prompt=text,
                #         image_url=image_url,
                #         generated_text=result
                #     )

                return ResponseUtil.success(
                    data={
                        'generated_text': result,
                        'image_url': image_url,
                        'user': {'userAccount': request.user.username} if request.user else None
                    },
                    message="内容生成成功"
                )
        except Exception as e:
            logger.error(f"内容生成失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                message=f"内容生成失败: {str(e)}"
            )


@method_decorator(csrf_exempt, name='dispatch')
class QwenTextOnlyAPIView(APIView):
    """
    纯文本生成API
    仅接收文本输入，返回生成的文本内容
    """
    parser_classes = [JSONParser]

    @extend_schema(
        request=TextOnlyDTO,
        responses={200: None},
        description="接收文本输入，返回生成的文案"
    )
    def post(self, request, *args, **kwargs):
        try:
            # 参数验证
            dto = TextOnlyDTO(data=request.data)
            dto.is_valid(raise_exception=True)

            # 获取参数
            text = dto.validated_data.get('text', '')
            stream = dto.validated_data.get('stream', True)

            # 初始化客户端
            qwen_client = QwenOmniTurboClient(
                api_key=settings.DASHSCOPE_API_KEY,
                base_url=settings.DASHSCOPE_URL
            )

            if stream:
                # 流式响应生成器
                def stream_generator():
                    full_response = []
                    for chunk in qwen_client.generate_text(
                            text=text,
                            stream=True
                    ):
                        if chunk:
                            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                            full_response.append(chunk)

                response = StreamingHttpResponse(
                    stream_generator(),
                    content_type='text/event-stream'
                )
                response['Cache-Control'] = 'no-cache'
                return response
            else:
                # 非流式处理
                result = qwen_client.generate_text(
                    text=text,
                    stream=False
                )

                return ResponseUtil.success(
                    data={
                        'generated_text': result,
                        'user': {'userAccount': request.user.username} if request.user else None
                    },
                    message="文本生成成功"
                )
        except Exception as e:
            logger.error(f"文本生成失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                message=f"文本生成失败: {str(e)}",
                status=500
            )

@method_decorator(csrf_exempt, name='dispatch')
class VolcengineVisualAPIView(APIView):
    """
    火山引擎视觉API
    支持图文输入，返回生成图像
    """
    parser_classes = [JSONParser, MultiPartParser]
    permission_classes = [IsAuthenticated]

    # 使用线程池管理异步任务
    _executor = ThreadPoolExecutor(max_workers=4)

    def _check_and_update_user_credits(self, user):
        """检查用户积分并更新，优先扣除VIP积分，没有VIP积分则扣除普通积分"""
        try:
            # 检查是否有足够的积分（VIP积分或普通积分）
            if user.vip_points <= 0 and user.points <= 0:
                raise BusinessException(error_code=ErrorCode.USER_NOT_PRINTS, data='',
                                        errors="用户积分不足，无法使用生图功能")

            # 优先扣除VIP积分
            if user.vip_points > 0:
                updated = SysUser.objects.filter(
                    id=user.id,
                    vip_points__gte=1
                ).update(vip_points=F('vip_points') - 3)
            else:
                # 如果没有VIP积分，扣除普通积分
                updated = SysUser.objects.filter(
                    id=user.id,
                    points__gte=1
                ).update(points=F('points') - 3)

            if not updated:
                raise BusinessException(error_code=ErrorCode.NOT_PRINTS_FAIL, data='',
                                        errors="积分扣除失败，可能积分不足")

            user.refresh_from_db()
            return {
                'points': user.points,
                'vip_points': user.vip_points
            }

        except Exception as e:
            logger.error(f"更新用户积分失败: {str(e)}", exc_info=True)
            raise BusinessException(error_code=ErrorCode.FAIL, data='', errors="积分处理失败，请稍后再试")

    @extend_schema(
        request={
            'type': 'object',
            'properties': {
                'prompt': {'type': 'string', 'description': '生成提示词'},
                'image_urls': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': '参考图片URL列表（可选）'
                },
                'conversation_id': {'type': 'integer', 'description': '会话ID（可选）'},
                'stream': {'type': 'boolean', 'description': '是否流式响应（默认False）'}
            },
            'required': ['prompt']
        },
        responses={
            200: None,  # 流式响应
            201: {  # 非流式响应
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "message": {"type": "string"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "image_url": {"type": "string"},
                            "image_name": {"type": "string"},
                            "prompt": {"type": "string"}
                        }
                    }
                }
            }
        },
        description="""
        火山引擎视觉API

        注意：
        - 不支持图片输入
        - 返回OSS存储的图片URL
        - 自动记录到数据库
        - 需要在请求头中携带JWT token进行认证
        """
    )
    def post(self, request, *args, **kwargs):
        try:
            # 获取当前认证用户
            user = request.user
            if not user or not user.is_authenticated:
                raise BusinessException(error_code=ErrorCode.USER_NOT_FOUND, data='', errors="用户未认证")

            # 参数解析与验证
            request_data = self._parse_request_data(request)
            dto = TextVolcengineDTO(data=request_data)
            dto.is_valid(raise_exception=True)
            validated_data = dto.validated_data

            # 检查并更新用户积分
            self._check_and_update_user_credits(user)

            # 创建请求记录
            request_obj = RequestManager.create_request(
                user_id=user.id,
                conversation_id=validated_data.get('conversation_id', ''),
                request_data=validated_data,
                service_type='volcengine_visual'
            )

            # 标记为处理中
            RequestManager.update_request_status(
                request_obj.id,
                RequestStatus.PROCESSING
            )

            # 提前创建对话内容
            conversation_request = ImageUploadManager.create_upload_record(
                user_id=user.id,
                conversation_id=validated_data.get('conversation_id', ''),
                image_list="pending",
                prompt=validated_data['text'],
                model_used="volcengine_visual",
                image_url="pending",
                image_name="",
                seed_used="",
            )

            # 构建立即返回的响应数据
            response_data = {
                'request_info': {
                    'request_id': request_obj.id,
                    'status': request_obj.status,
                    'created_at': request_obj.created_at.isoformat(),
                    'service_type': request_obj.service_type
                },
                'user_id': user.id,
                'conversation_id': validated_data.get('conversation_id', ''),
                'message': '请求已接收，正在处理中'
            }

            # 启动后台线程处理请求
            self._executor.submit(
                self._process_request_async,
                validated_data=validated_data,
                request_obj=request_obj,
                upload_record_id=conversation_request.id,
                is_stream=validated_data.get('stream', False),
                user=user
            )

            return ResponseUtil.success(
                data=response_data,
                message='请求已接收，正在处理中'
            )

        except Exception as e:
            logger.error(f"请求处理失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                errors="请求处理失败",
                data=str(e),
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _process_request_async(self, validated_data, request_obj, upload_record_id, is_stream, user):
        """异步处理请求"""
        try:
            service = VolcengineVisualService()
            result = service.generate_image(
                prompt=validated_data['text'],
                user_id=user.id,
                conversation_id=validated_data.get('conversation_id'),
                upload_record_id=upload_record_id,
                image_urls=validated_data.get('image_urls', [])
            )

            if result['success']:
                RequestManager.update_request_status(
                    request_obj.id,
                    RequestStatus.COMPLETED,
                    response_data={
                        'image_url': result['image_url'],
                        'image_name': result['image_name'],
                        'prompt': result['prompt']
                    }
                )
            else:
                RequestManager.update_request_status(
                    request_obj.id,
                    RequestStatus.FAILED,
                    error_message=result.get('error', '生成失败')
                )

        except Exception as e:
            logger.error(f"异步处理请求失败: {str(e)}", exc_info=True)
            RequestManager.update_request_status(
                request_obj.id,
                RequestStatus.FAILED,
                error_message=str(e)
            )

    def _parse_request_data(self, request):
        """统一解析请求数据"""
        if isinstance(request.data, dict):
            return request.data
        try:
            return json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            raise BusinessException(code=ErrorCode.JSON_NOT_FAIL.code, data='', errors="无效的JSON数据")

@method_decorator(csrf_exempt, name='dispatch')
class ChatGPTImageGenerationOpenAIView(APIView):
    """
    OpenAI图像生成API
    支持图文输入，返回生成图像（支持流式和非流式响应）

    特性：
    1. 支持图像生成和编辑
    2. 支持多图片输入
    3. 支持遮罩编辑
    4. 结果存储到OSS和MySQL
    5. 支持两种响应模式
    """
    parser_classes = [JSONParser, MultiPartParser]
    permission_classes = [IsAuthenticated]  # 添加认证要求
    # 使用线程池管理异步任务
    _executor = ThreadPoolExecutor(max_workers=4)


    def _generate_random_seed(self):
        return random.SystemRandom().randint(1, 2 ** 31 - 1)

    def _check_and_update_user_credits(self, user, conversation_request, points):
        """检查用户积分并更新，优先扣除VIP积分，没有VIP积分则扣除普通积分"""
        try:
            # 使用事务和行级锁
            with transaction.atomic():
                # 获取最新的用户信息并加锁
                user = SysUser.objects.select_for_update().get(id=user.id)
                
                # 检查是否有足够的积分（VIP积分或普通积分）
                if user.vip_points <= 0 and user.points <= 0:
                    raise BusinessException(error_code=ErrorCode.USER_NOT_PRINTS, data='',
                                            errors="用户积分不足，无法使用生图功能")

                # 优先扣除VIP积分
                if user.vip_points > 0 and user.vip_points >= points:
                    user.vip_points -= points
                    user.save(update_fields=['vip_points'])
                    points_type = 'VIP'
                # 检查普通积分是否足够
                elif user.points >= points:
                    user.points -= points
                    user.save(update_fields=['points'])
                    points_type = 'REGULAR'
                else:
                    # 两种积分都不够
                    raise BusinessException(error_code=ErrorCode.NOT_PRINTS_FAIL, data='',
                                          errors=f"积分不足{points}点，当前VIP积分：{user.vip_points}，普通积分：{user.points}")

                # 创建积分扣除记录
                PointsDeductionHistory.objects.create(
                    user=user,
                    points_deducted=points,
                    deduction_type=points_type,
                    task_type='flux_kontext_pro_1',
                    image_upload_record=conversation_request
                )

                return {
                    'points': user.points,
                    'vip_points': user.vip_points
                }

        except BusinessException as be:
            # 直接将业务异常传递给上层，保持错误消息完整
            logger.warning(f"用户积分检查失败: {be.errors}")
            raise be
        except Exception as e:
            logger.error(f"更新用户积分失败: {str(e)}", exc_info=True)
            raise BusinessException(error_code=ErrorCode.FAIL, data='', errors="积分处理失败，请稍后再试")

    @extend_schema(
        request=OpenAIImageRequestDTO,
        responses={
            200: None,  # 流式响应
            201: {  # 非流式响应
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "message": {"type": "string"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "image_url": {"type": "string"},
                            "image_name": {"type": "string"},
                            "prompt": {"type": "string"},
                            "model_used": {"type": "string"},
                            "seed_used": {"type": "integer"}
                        }
                    }
                }
            }
        },
        description="""
        OpenAI图像生成API

        注意：
        - 支持图像生成和编辑
        - 支持多图片输入
        - 支持遮罩编辑
        - 返回OSS存储的图片URL
        - 自动记录到数据库
        - 需要在请求头中携带JWT token进行认证
        """
    )
    def post(self, request, *args, **kwargs):
        try:
            # 获取当前认证用户
            user = request.user
            if not user or not user.is_authenticated:
                raise BusinessException(error_code=ErrorCode.USER_NOT_FOUND, data='', errors="用户未认证")

            # 参数解析与验证
            request_data = self._parse_request_data(request)
            dto = OpenAIImageRequestDTO(data=request_data)
            dto.is_valid(raise_exception=True)
            validated_data = dto.validated_data

             # 处理图片URL列表
            image_urls = validated_data.get('image_paths', [])
            images_url = ",".join(image_urls) if image_urls else ""
            # 提前创建对话内容
            conversation_request = ImageUploadManager.create_upload_record(
                user_id=user.id,
                conversation_id=validated_data.get('conversation_id', ''),
                image_list=images_url,
                prompt=validated_data['prompt'],
                model_used=settings.CHATGPT_CONFIG_OPENAI['MODEL'],
                image_url=images_url,
                image_name="",
                seed_used="",
            )

            # 创建请求记录
            request_obj = RequestManager.create_request(
                user_id=user.id,
                conversation_id=validated_data.get('conversation_id', ''),
                request_data=validated_data,
                service_type='openai_image'
            )

            # 检查并更新用户积分
            self._check_and_update_user_credits(user, conversation_request, settings.CHATGPT_CONFIG_OPENAI['points'])

            # 标记为处理中
            RequestManager.update_request_status(
                request_id=request_obj.id,
                status=RequestStatus.PROCESSING
            )

            # 构建立即返回的响应数据
            response_data = {
                'request_info': {
                    'request_id': request_obj.id,
                    'status': request_obj.status,
                    'created_at': request_obj.created_at.isoformat(),
                    'service_type': request_obj.service_type
                },
                'message': '请求已接收，正在处理中',
                'user_id': user.id,
                'conversation_id': validated_data.get('conversation_id', '')
            }

            # 启动后台线程处理请求
            self._executor.submit(
                self._process_request_async,
                service=ChatGPTImageServiceNew(),
                validated_data=validated_data,
                conversation_request_id=conversation_request.id,
                request_obj=request_obj,
                is_stream=validated_data.get('stream', False),
                user=user
            )

            return ResponseUtil.success(
                data=response_data,
                message='请求已接收，正在处理中'
            )

        except BusinessException as be:
            # 捕获业务异常，直接返回业务错误信息
            logger.warning(f"业务异常: {be.errors}")
            return ResponseUtil.error(
                message=be.errors,
                code=be.error_code.code if hasattr(be.error_code, 'code') else 500
            )
        except Exception as e:
            logger.error(f"请求处理失败: {str(e)}", exc_info=True)

            if 'request_obj' in locals():
                RequestManager.update_request_status(
                    request_obj.id,
                    RequestStatus.FAILED,
                    error_message=str(e)
                )
            return ResponseUtil.error(
                data={
                    'status': 'error',
                    'message': '请求处理失败',
                    'error': str(e)
                },
                errors=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _process_request_async(self, service, validated_data, conversation_request_id, request_obj, is_stream, user):
        """异步处理请求的方法"""
        try:
            operation_type = validated_data.get('operation_type', 'generate')
            
            if operation_type == 'generate':
                result = service.generate_image(
                    prompt=validated_data['prompt'],
                    user_id=user.id,
                    conversation_id=validated_data.get('conversation_id'),
                    upload_record_id=conversation_request_id,
                    seed=self._generate_random_seed(),
                    size=validated_data.get('size', '1024x1024')
                )
            else:  # edit
                # 处理多张图片
                image_paths = validated_data.get('image_paths', [])
                if not image_paths:
                    error_msg = "编辑操作需要至少一张图片"
                    # 更新ImageUploadRecord状态为失败
                    ImageUploadManager.mark_as_failed(
                        record_id=conversation_request_id,
                        error_message=error_msg
                    )
                    raise BusinessException(error_code=ErrorCode.FAIL, data='', errors=error_msg)

                # 如果只有一张图片，直接使用单图编辑
                if len(image_paths) == 1:
                    result = service.edit_image(
                        prompt=validated_data['prompt'],
                        image_paths=image_paths,
                        mask_path=validated_data.get('mask_path'),
                        user_id=user.id,
                        conversation_id=validated_data.get('conversation_id'),
                        upload_record_id=conversation_request_id,
                        size=validated_data.get('size', '1024x1024')
                    )
                else:
                    # 多图编辑，使用图片合并功能
                    result = service.merge_images(
                        prompt=validated_data['prompt'],
                        image_paths=image_paths,
                        user_id=user.id,
                        conversation_id=validated_data.get('conversation_id'),
                        upload_record_id=conversation_request_id,
                        size=validated_data.get('size', '1024x1024')
                    )

            if result['success']:
                RequestManager.update_request_status(
                    request_obj.id,
                    RequestStatus.COMPLETED,
                    response_data={
                        'image_url': result['image_url'],
                        'image_name': result['image_name'],
                        'prompt': result['prompt'],
                        'model_used': result.get('model_used'),
                        'seed_used': result.get('seed_used'),
                        'size': result.get('size', '1024x1024'),
                        'operation_type': operation_type,
                        'image_count': len(validated_data.get('image_paths', [])) if operation_type == 'edit' else 0
                    }
                )
            else:
                # 更新ImageUploadRecord状态为失败
                ImageUploadManager.mark_as_failed(
                    record_id=conversation_request_id,
                    error_message=result.get('error', '生成失败')
                )
                RequestManager.update_request_status(
                    request_obj.id,
                    RequestStatus.FAILED,
                    error_message=result.get('error', '生成失败')
                )

        except Exception as e:
            logger.error(f"异步处理请求失败: {str(e)}", exc_info=True)
            # 确保在异常情况下也更新ImageUploadRecord状态
            ImageUploadManager.mark_as_failed(
                record_id=conversation_request_id,
                error_message=f"异步处理请求失败: {str(e)}"
            )
            RequestManager.update_request_status(
                request_obj.id,
                RequestStatus.FAILED,
                error_message=str(e)
            )

    def _parse_request_data(self, request):
        """统一解析请求数据"""
        if isinstance(request.data, dict):
            return request.data
        try:
            return json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            raise BusinessException(code=ErrorCode.JSON_NOT_FAIL.code, data='', errors="无效的JSON数据")

@method_decorator(csrf_exempt, name='dispatch')
class FluxKontextProImageView(APIView):
    """
    Flux Kontext Pro 图像生成API
    支持图文输入，返回生成图像（支持流式和非流式响应）

    特性：
    1. 支持图像生成和编辑
    2. 支持多图片输入
    3. 支持图片比例设置
    4. 结果存储到OSS和MySQL
    5. 支持两种响应模式
    """
    parser_classes = [JSONParser, MultiPartParser]
    permission_classes = [IsAuthenticated]  # 添加认证要求
    # 使用线程池管理异步任务
    _executor = ThreadPoolExecutor(max_workers=4)

    def _generate_random_seed(self):
        return random.SystemRandom().randint(1, 2 ** 31 - 1)

    def _check_and_update_user_credits(self, user, conversation_request, points):
        """检查用户积分并更新，优先扣除VIP积分，没有VIP积分则扣除普通积分"""
        try:
            # 使用事务和行级锁
            with transaction.atomic():
                # 获取最新的用户信息并加锁
                user = SysUser.objects.select_for_update().get(id=user.id)
                
                # 检查是否有足够的积分（VIP积分或普通积分）
                if user.vip_points <= 0 and user.points <= 0:
                    raise BusinessException(error_code=ErrorCode.USER_NOT_PRINTS, data='',
                                            errors="用户积分不足，无法使用生图功能")

                # 优先扣除VIP积分
                if user.vip_points > 0 and user.vip_points >= points:
                    user.vip_points -= points
                    user.save(update_fields=['vip_points'])
                    points_type = 'VIP'
                # 检查普通积分是否足够
                elif user.points >= points:
                    user.points -= points
                    user.save(update_fields=['points'])
                    points_type = 'REGULAR'
                else:
                    # 两种积分都不够
                    raise BusinessException(error_code=ErrorCode.NOT_PRINTS_FAIL, data='',
                                          errors=f"积分不足{points}点，当前VIP积分：{user.vip_points}，普通积分：{user.points}")

                # 创建积分扣除记录
                PointsDeductionHistory.objects.create(
                    user=user,
                    points_deducted=points,
                    deduction_type=points_type,
                    task_type='flux_kontext_pro_1',
                    image_upload_record=conversation_request
                )

                return {
                    'points': user.points,
                    'vip_points': user.vip_points
                }

        except BusinessException as be:
            # 直接将业务异常传递给上层，保持错误消息完整
            logger.warning(f"用户积分检查失败: {be.errors}")
            raise be
        except Exception as e:
            logger.error(f"更新用户积分失败: {str(e)}", exc_info=True)
            raise BusinessException(error_code=ErrorCode.FAIL, data='', errors="积分处理失败，请稍后再试")

    @extend_schema(
        request=FluxKontextProRequestDTO,
        responses={
            200: None,  # 流式响应
            201: {  # 非流式响应
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "message": {"type": "string"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "image_url": {"type": "string"},
                            "image_name": {"type": "string"},
                            "prompt": {"type": "string"},
                            "model_used": {"type": "string"},
                            "seed_used": {"type": "integer"},
                            "aspect_ratio": {"type": "string"},
                            "output_format": {"type": "string"}
                        }
                    }
                }
            }
        },
        description="""
        Flux Kontext Pro 图像生成API

        注意：
        - 支持图像生成和编辑
        - 支持多图片输入
        - 支持图片比例设置
        - 返回OSS存储的图片URL
        - 自动记录到数据库
        - 需要在请求头中携带JWT token进行认证
        """
    )
    def post(self, request, *args, **kwargs):
        try:
            # 获取当前认证用户
            user = request.user
            if not user or not user.is_authenticated:
                raise BusinessException(error_code=ErrorCode.USER_NOT_FOUND, data='', errors="用户未认证")

            # 参数解析与验证
            request_data = self._parse_request_data(request)
            dto = FluxKontextProRequestDTO(data=request_data)
            dto.is_valid(raise_exception=True)
            validated_data = dto.validated_data

            # 处理图片URL列表
            image_urls = validated_data.get('image_paths', [])
            images_url = ",".join(image_urls) if image_urls else ""

            # 提前创建对话内容
            conversation_request = ImageUploadManager.create_upload_record(
                user_id=user.id,
                conversation_id=validated_data.get('conversation_id', ''),
                image_list=images_url,
                prompt=validated_data['prompt'],
                model_used='flux_kontext_pro_1',
                image_url=images_url,
                image_name="",
                seed_used="",
            )

            # 创建请求记录
            request_obj = RequestManager.create_request(
                user_id=user.id,
                conversation_id=validated_data.get('conversation_id', ''),
                request_data=validated_data,
                service_type='flux_kontext_pro_1'
            )

            # 检查并更新用户积分
            self._check_and_update_user_credits(user, conversation_request, settings.FLUX_KONEXT_POINTS)

            # 标记为处理中
            RequestManager.update_request_status(
                request_id=request_obj.id,
                status=RequestStatus.PROCESSING
            )

            # 构建立即返回的响应数据
            response_data = {
                'request_info': {
                    'request_id': request_obj.id,
                    'status': request_obj.status,
                    'created_at': request_obj.created_at.isoformat(),
                    'service_type': request_obj.service_type
                },
                'message': '请求已接收，正在处理中',
                'user_id': user.id,
                'conversation_id': validated_data.get('conversation_id', '')
            }

            # 启动后台线程处理请求
            self._executor.submit(
                self._process_request_async,
                service=FluxKontextProService(),
                validated_data=validated_data,
                conversation_request_id=conversation_request.id,
                request_obj=request_obj,
                is_stream=validated_data.get('stream', False),
                user=user
            )

            return ResponseUtil.success(
                data=response_data,
                message='请求已接收，正在处理中'
            )

        except BusinessException as be:
            # 捕获业务异常，直接返回业务错误信息
            logger.warning(f"业务异常: {be.errors}")
            return ResponseUtil.error(
                message=be.errors,
                code=be.error_code.code if hasattr(be.error_code, 'code') else 500
            )
        except Exception as e:
            logger.error(f"请求处理失败: {str(e)}", exc_info=True)

            if 'request_obj' in locals():
                RequestManager.update_request_status(
                    request_obj.id,
                    RequestStatus.FAILED,
                    error_message=str(e)
                )
            return ResponseUtil.error(
                data={
                    'status': 'error',
                    'message': '请求处理失败',
                    'error': str(e)
                },
                errors=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _process_request_async(self, service, validated_data, conversation_request_id, request_obj, is_stream, user):
        """异步处理请求的方法"""
        try:
            result = service.generate_image(
                prompt=validated_data['prompt'],
                image_urls=validated_data.get('image_paths', []),
                user_id=user.id,
                conversation_id=validated_data.get('conversation_id'),
                upload_record_id=conversation_request_id,
                seed=validated_data.get('seed') or self._generate_random_seed(),
                aspect_ratio=validated_data.get('aspect_ratio'),
                output_format=validated_data.get('output_format', 'png'),
                prompt_upsampling=validated_data.get('prompt_upsampling', False),
                safety_tolerance=validated_data.get('safety_tolerance', 2)
            )

            if result['success']:
                RequestManager.update_request_status(
                    request_obj.id,
                    RequestStatus.COMPLETED,
                    response_data={
                        'image_url': result['image_url'],
                        'image_name': result['image_name'],
                        'prompt': result['prompt'],
                        'model_used': result.get('model_used'),
                        'seed_used': result.get('seed_used'),
                        'aspect_ratio': validated_data.get('aspect_ratio'),
                        'output_format': validated_data.get('output_format', 'png')
                    }
                )
            else:
                # 更新ImageUploadRecord状态为失败
                ImageUploadManager.mark_as_failed(
                    record_id=conversation_request_id,
                    error_message=result.get('error', '生成失败')
                )
                RequestManager.update_request_status(
                    request_obj.id,
                    RequestStatus.FAILED,
                    error_message=result.get('error', '生成失败')
                )

        except Exception as e:
            logger.error(f"异步处理请求失败: {str(e)}", exc_info=True)
            # 确保在异常情况下也更新ImageUploadRecord状态
            ImageUploadManager.mark_as_failed(
                record_id=conversation_request_id,
                error_message=f"异步处理请求失败: {str(e)}"
            )
            RequestManager.update_request_status(
                request_obj.id,
                RequestStatus.FAILED,
                error_message=str(e)
            )

    def _parse_request_data(self, request):
        """统一解析请求数据"""
        if isinstance(request.data, dict):
            return request.data
        try:
            return json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            raise BusinessException(code=ErrorCode.JSON_NOT_FAIL.code, data='', errors="无效的JSON数据")

@method_decorator(csrf_exempt, name='dispatch')
class FluxKontextProImageFluxView(APIView):
    """
    Flux Kontext Pro 图像生成API
    支持图文输入，返回生成图像（支持流式和非流式响应）

    特性：
    1. 支持图像生成和编辑
    2. 支持多图片输入
    3. 支持图片比例设置
    4. 结果存储到OSS和MySQL
    5. 支持两种响应模式
    """
    parser_classes = [JSONParser, MultiPartParser]
    permission_classes = [IsAuthenticated]  # 添加认证要求
    # 使用线程池管理异步任务
    _executor = ThreadPoolExecutor(max_workers=4)

    def _generate_random_seed(self):
        return random.SystemRandom().randint(1, 2 ** 31 - 1)

    def _check_and_update_user_credits(self, user, conversation_request, points):
        """检查用户积分并更新，优先扣除VIP积分，没有VIP积分则扣除普通积分"""
        try:
            # 使用事务和行级锁
            with transaction.atomic():
                # 获取最新的用户信息并加锁
                user = SysUser.objects.select_for_update().get(id=user.id)
                
                # 检查是否有足够的积分（VIP积分或普通积分）
                if user.vip_points <= 0 and user.points <= 0:
                    raise BusinessException(error_code=ErrorCode.USER_NOT_PRINTS, data='',
                                            errors="用户积分不足，无法使用生图功能")

                # 优先扣除VIP积分
                if user.vip_points > 0 and user.vip_points >= points:
                    user.vip_points -= points
                    user.save(update_fields=['vip_points'])
                    points_type = 'VIP'
                # 检查普通积分是否足够
                elif user.points >= points:
                    user.points -= points
                    user.save(update_fields=['points'])
                    points_type = 'REGULAR'
                else:
                    # 两种积分都不够
                    raise BusinessException(error_code=ErrorCode.NOT_PRINTS_FAIL, data='',
                                          errors=f"积分不足{points}点，当前VIP积分：{user.vip_points}，普通积分：{user.points}")

                # 创建积分扣除记录
                PointsDeductionHistory.objects.create(
                    user=user,
                    points_deducted=points,
                    deduction_type=points_type,
                    task_type='flux_kontext_pro_2',
                    image_upload_record=conversation_request
                )

                return {
                    'points': user.points,
                    'vip_points': user.vip_points
                }

        except BusinessException as be:
            # 直接将业务异常传递给上层，保持错误消息完整
            logger.warning(f"用户积分检查失败: {be.errors}")
            raise be
        except Exception as e:
            logger.error(f"更新用户积分失败: {str(e)}", exc_info=True)
            raise BusinessException(error_code=ErrorCode.FAIL, data='', errors="积分处理失败，请稍后再试")

    @extend_schema(
        request=FluxKontextProRequestDTO,
        responses={
            200: None,  # 流式响应
            201: {  # 非流式响应
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "message": {"type": "string"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "image_url": {"type": "string"},
                            "image_name": {"type": "string"},
                            "prompt": {"type": "string"},
                            "model_used": {"type": "string"},
                            "seed_used": {"type": "integer"},
                            "aspect_ratio": {"type": "string"},
                            "output_format": {"type": "string"}
                        }
                    }
                }
            }
        },
        description="""
        Flux Kontext Pro 图像生成API

        注意：
        - 支持图像生成和编辑
        - 支持多图片输入
        - 支持图片比例设置
        - 返回OSS存储的图片URL
        - 自动记录到数据库
        - 需要在请求头中携带JWT token进行认证
        """
    )
    def post(self, request, *args, **kwargs):
        try:
            # 获取当前认证用户
            user = request.user
            if not user or not user.is_authenticated:
                raise BusinessException(error_code=ErrorCode.USER_NOT_FOUND, data='', errors="用户未认证")

            # 参数解析与验证
            request_data = self._parse_request_data(request)
            dto = FluxKontextProRequestDTO(data=request_data)
            dto.is_valid(raise_exception=True)
            validated_data = dto.validated_data

            # 处理图片URL列表
            image_urls = validated_data.get('image_paths', [])
            images_url = ",".join(image_urls) if image_urls else ""

            # 提前创建对话内容
            conversation_request = ImageUploadManager.create_upload_record(
                user_id=user.id,
                conversation_id=validated_data.get('conversation_id', ''),
                image_list=images_url,
                prompt=validated_data['prompt'],
                model_used='flux_kontext_pro_2',
                image_url=images_url,
                image_name="",
                seed_used="",
            )

            # 创建请求记录
            request_obj = RequestManager.create_request(
                user_id=user.id,
                conversation_id=validated_data.get('conversation_id', ''),
                request_data=validated_data,
                service_type='flux_kontext_pro_2'
            )

            # 检查并更新用户积分
            self._check_and_update_user_credits(user, conversation_request, settings.FLUX_KONEXT_POINTS)

            # 标记为处理中
            RequestManager.update_request_status(
                request_id=request_obj.id,
                status=RequestStatus.PROCESSING
            )

            # 构建立即返回的响应数据
            response_data = {
                'request_info': {
                    'request_id': request_obj.id,
                    'status': request_obj.status,
                    'created_at': request_obj.created_at.isoformat(),
                    'service_type': request_obj.service_type
                },
                'message': '请求已接收，正在处理中',
                'user_id': user.id,
                'conversation_id': validated_data.get('conversation_id', '')
            }

            # 启动后台线程处理请求
            self._executor.submit(
                self._process_request_async,
                service=FluxKontextProService(),
                validated_data=validated_data,
                conversation_request_id=conversation_request.id,
                request_obj=request_obj,
                is_stream=validated_data.get('stream', False),
                user=user
            )

            return ResponseUtil.success(
                data=response_data,
                message='请求已接收，正在处理中'
            )

        except BusinessException as be:
            # 捕获业务异常，直接返回业务错误信息
            logger.warning(f"业务异常: {be.errors}")
            return ResponseUtil.error(
                message=be.errors,
                code=be.error_code.code if hasattr(be.error_code, 'code') else 500
            )
        except Exception as e:
            logger.error(f"请求处理失败: {str(e)}", exc_info=True)

            if 'request_obj' in locals():
                RequestManager.update_request_status(
                    request_obj.id,
                    RequestStatus.FAILED,
                    error_message=str(e)
                )
            return ResponseUtil.error(
                data={
                    'status': 'error',
                    'message': '请求处理失败',
                    'error': str(e)
                },
                errors=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _process_request_async(self, service, validated_data, conversation_request_id, request_obj, is_stream, user):
        """异步处理请求的方法"""
        try:
            result = service.generate_image(
                prompt=validated_data['prompt'],
                image_urls=validated_data.get('image_paths', []),
                user_id=user.id,
                conversation_id=validated_data.get('conversation_id'),
                upload_record_id=conversation_request_id,
                seed=validated_data.get('seed') or self._generate_random_seed(),
                aspect_ratio=validated_data.get('aspect_ratio'),
                output_format=validated_data.get('output_format', 'png'),
                prompt_upsampling=validated_data.get('prompt_upsampling', False),
                safety_tolerance=validated_data.get('safety_tolerance', 2)
            )

            if result['success']:
                RequestManager.update_request_status(
                    request_obj.id,
                    RequestStatus.COMPLETED,
                    response_data={
                        'image_url': result['image_url'],
                        'image_name': result['image_name'],
                        'prompt': result['prompt'],
                        'model_used': result.get('model_used'),
                        'seed_used': result.get('seed_used'),
                        'aspect_ratio': validated_data.get('aspect_ratio'),
                        'output_format': validated_data.get('output_format', 'png')
                    }
                )
            else:
                # 更新ImageUploadRecord状态为失败
                ImageUploadManager.mark_as_failed(
                    record_id=conversation_request_id,
                    error_message=result.get('error', '生成失败')
                )
                RequestManager.update_request_status(
                    request_obj.id,
                    RequestStatus.FAILED,
                    error_message=result.get('error', '生成失败')
                )

        except Exception as e:
            logger.error(f"异步处理请求失败: {str(e)}", exc_info=True)
            # 确保在异常情况下也更新ImageUploadRecord状态
            ImageUploadManager.mark_as_failed(
                record_id=conversation_request_id,
                error_message=f"异步处理请求失败: {str(e)}"
            )
            RequestManager.update_request_status(
                request_obj.id,
                RequestStatus.FAILED,
                error_message=str(e)
            )

    def _parse_request_data(self, request):
        """统一解析请求数据"""
        if isinstance(request.data, dict):
            return request.data
        try:
            return json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            raise BusinessException(code=ErrorCode.JSON_NOT_FAIL.code, data='', errors="无效的JSON数据")

@method_decorator(csrf_exempt, name='dispatch')
class UserPointsDeductionHistoryView(APIView):
    """
    查询用户积分扣除历史记录
    支持分页和条件查询
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='page', description='页码', type=int, required=False),
            OpenApiParameter(name='page_size', description='每页大小', type=int, required=False),
            OpenApiParameter(name='deduction_type', description='扣除类型(VIP/REGULAR)', type=str, required=False),
            OpenApiParameter(name='task_type', description='任务类型', type=str, required=False),
            OpenApiParameter(name='start_date', description='开始日期(YYYY-MM-DD)', type=str, required=False),
            OpenApiParameter(name='end_date', description='结束日期(YYYY-MM-DD)', type=str, required=False),
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'results': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'integer'},
                                'deduction_time': {'type': 'string'},
                                'points_deducted': {'type': 'integer'},
                                'deduction_type': {'type': 'string'},
                                'task_type': {'type': 'string'},
                                'task_id': {'type': 'integer'},
                                'image_url': {'type': 'string'},
                                'image_name': {'type': 'string'}
                            }
                        }
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
        description='查询用户积分扣除历史记录'
    )
    def get(self, request, *args, **kwargs):
        try:
            # 获取查询参数
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
            deduction_type = request.query_params.get('deduction_type')
            task_type = request.query_params.get('task_type')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            # 获取当前用户
            user = request.user
            
            # 构建基础查询
            queryset = PointsDeductionHistory.objects.filter(user=user)
            
            # 应用过滤条件
            if deduction_type:
                queryset = queryset.filter(deduction_type=deduction_type)
            if task_type:
                queryset = queryset.filter(task_type=task_type)
                
            # 日期过滤
            if start_date:
                try:
                    start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
                    queryset = queryset.filter(deduction_time__date__gte=start_date)
                except ValueError:
                    pass
                
            if end_date:
                try:
                    end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
                    queryset = queryset.filter(deduction_time__date__lte=end_date)
                except ValueError:
                    pass
            
            # 排序
            queryset = queryset.order_by('-deduction_time')
            
            # 分页
            paginator = Paginator(queryset, page_size)
            try:
                page_obj = paginator.page(page)
            except Exception:
                return ResponseUtil.error(message="请求的页码不存在")
            
            # 构建响应数据
            results = []
            for record in page_obj.object_list:
                record_data = {
                    'id': record.id,
                    'deduction_time': record.deduction_time.isoformat(),
                    'points_deducted': record.points_deducted,
                    'deduction_type': record.deduction_type,
                    'task_type': record.task_type,
                    'task_id': record.task_id,
                }
                
                # 如果有关联的图片记录，添加图片信息
                if record.image_upload_record:
                    record_data.update({
                        'image_url': record.image_upload_record.image_url,
                        'image_name': record.image_upload_record.image_name
                    })
                
                results.append(record_data)
            
            # 构建分页信息
            pagination = {
                'total': paginator.count,
                'page': page,
                'page_size': page_size,
                'pages': paginator.num_pages
            }
            
            return ResponseUtil.success(
                data={
                    'results': results,
                    'pagination': pagination
                },
                message="查询成功"
            )
            
        except Exception as e:
            logger.error(f"查询积分扣除历史失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                message=f"查询积分扣除历史失败: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
