import json
import logging
import random
from concurrent.futures import ThreadPoolExecutor

from django.db import transaction
from django.db.models import F
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser, MultiPartParser

from common.response_utils import ResponseUtil
from djangoProject import settings
from exception.business_exception import BusinessException
from templateImage.ImageUploadDTO import VolcengineImageGenerationDTO
from templateImage.ImagesRequest import ImageUploadManager

from common.ErrorCode import ErrorCode
from templateImage.RequestService import RequestManager
from templateImage.models import RequestStatus, PointsDeductionHistory

from user.models import SysUser
from templateImage.VolcengineVisualServiceSDK import VolcengineVisualServiceSDK

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class VolcengineVisualAPIViewSDK(APIView):
    """
    火山引擎视觉API (使用SDK)
    支持文本输入生成图像，提供多种图像生成参数选项
    """
    parser_classes = [JSONParser, MultiPartParser]
    permission_classes = [IsAuthenticated]

    # 使用线程池管理异步任务
    _executor = ThreadPoolExecutor(max_workers=4)

    def _check_and_update_user_credits(self, user, conversation_request, points):
        """
        检查并扣除用户积分
        优先扣除VIP积分，没有VIP积分则扣除普通积分
        使用事务和行级锁确保并发安全
        """
        try:
            # 使用事务和行级锁
            with transaction.atomic():
                # 获取最新的用户信息并加锁
                user = SysUser.objects.select_for_update().get(id=user.id)
                
                # 记录原始积分值，用于日志
                original_vip_points = user.vip_points
                original_points = user.points
                
                # 检查积分是否足够
                if user.vip_points < 0 and user.points < 0:
                    raise BusinessException(
                        error_code=ErrorCode.USER_NOT_PRINTS,
                        data='',
                        errors=f"积分不足，当前VIP积分：{user.vip_points}，普通积分：{user.points}"
                    )

                # 优先扣除VIP积分
                if user.vip_points >= points:
                    user.vip_points -= points
                    user.save(update_fields=['vip_points'])
                    points_type = "VIP积分"
                    points_before = original_vip_points
                    points_after = user.vip_points

                    # 创建VIP积分扣除记录
                    PointsDeductionHistory.objects.create(
                        user=user,
                        points_deducted=points,
                        deduction_type='VIP',
                        task_type='volcengine_visual_sdk',
                        image_upload_record=conversation_request
                    )
                else:
                    # 扣除普通积分
                    user.points -= points
                    user.save(update_fields=['points'])
                    points_type = "普通积分"
                    points_before = original_points
                    points_after = user.points

                    # 创建普通积分扣除记录
                    PointsDeductionHistory.objects.create(
                        user=user,
                        points_deducted=points,
                        deduction_type='REGULAR',
                        task_type='volcengine_visual_sdk',
                        image_upload_record=conversation_request
                    )

                # 记录积分变动日志
                logger.info(
                    f"用户 {user.username}(ID:{user.id}) {points_type}扣除成功: "
                    f"扣除前 {points_before} -> 扣除后 {points_after}"
                )

                # 返回更新后的积分信息
                return {
                    'points': user.points,
                    'vip_points': user.vip_points,
                    'deducted_points': points,
                    'points_type': points_type
                }

        except BusinessException as be:
            # 业务异常直接抛出
            logger.warning(f"用户积分检查失败: {be.errors}")
            raise be
        except Exception as e:
            # 其他异常记录详细日志并抛出业务异常
            logger.error(
                f"更新用户积分失败 - 用户ID: {user.id}, "
                f"错误信息: {str(e)}", 
                exc_info=True
            )
            raise BusinessException(
                error_code=ErrorCode.FAIL,
                data='',
                errors="积分处理失败，请稍后再试"
            )

    def _generate_random_seed(self):
        """生成随机种子"""
        return random.randint(1, 999999999)

    @extend_schema(
        request=VolcengineImageGenerationDTO,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "message": {"type": "string"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "request_info": {
                                "type": "object",
                                "properties": {
                                    "request_id": {"type": "integer"},
                                    "status": {"type": "string"},
                                    "created_at": {"type": "string", "format": "date-time"},
                                    "service_type": {"type": "string"}
                                }
                            },
                            "user_id": {"type": "integer"},
                            "conversation_id": {"type": "integer"},
                            "message": {"type": "string"}
                        }
                    }
                }
            }
        },
        description="""
        火山引擎图像生成API (使用SDK)

        功能：
        - 根据文本提示生成高质量图像
        - 支持多种参数自定义，包括图像尺寸、比例、添加水印等
        - 返回OSS存储的图片URL
        - 自动记录到数据库
        
        注意：
        - 必须提供text参数作为图像生成提示
        - seed参数会自动生成，无需手动指定
        - 需要在请求头中携带JWT token进行认证
        """
    )
    def post(self, request, *args, **kwargs):
        conversation_request = None
        try:
            # 获取当前认证用户
            user = request.user
            if not user or not user.is_authenticated:
                raise BusinessException(error_code=ErrorCode.USER_NOT_FOUND, data='', errors="用户未认证")

            # 参数解析与验证
            request_data = self._parse_request_data(request)
            dto = VolcengineImageGenerationDTO(data=request_data)
            dto.is_valid(raise_exception=True)
            validated_data = dto.validated_data

            # 生成随机种子（如果未提供）
            if 'seed' not in validated_data:
                validated_data['seed'] = self._generate_random_seed()



            # 创建请求记录
            request_obj = RequestManager.create_request(
                user_id=user.id,
                conversation_id=validated_data.get('conversation_id', ''),
                request_data=validated_data,
                service_type='volcengine_visual_sdk'
            )

            # 标记为处理中
            RequestManager.update_request_status(
                request_obj.id,
                RequestStatus.PROCESSING
            )

            # 准备存储的图片列表
            image_list = ",".join(validated_data.get('image_urls', [])) if 'image_urls' in validated_data else ""

            # 提前创建对话内容
            conversation_request = ImageUploadManager.create_upload_record(
                user_id=user.id,
                conversation_id=validated_data.get('conversation_id', ''),
                image_list=image_list,
                prompt=validated_data['text'],
                model_used="volcengine_visual_sdk",
                image_url="pending",
                image_name="",
                seed_used=str(validated_data['seed']),
            )

            # 检查并更新用户积分
            self._check_and_update_user_credits(user, conversation_request, settings.VOLCENGINE_VISUAL_CONFIG['POINTS'])

            # 构建立即返回的响应数据
            response_data = {
                'request_info': {
                    'request_id': request_obj.id,
                    'status': request_obj.status,
                    'created_at': request_obj.created_at.isoformat(),
                    'service_type': request_obj.service_type
                },
                'conversation_id': validated_data.get('conversation_id', ''),
                'upload_record_id': conversation_request.id,
                'seed': validated_data['seed'],
                'message': '请求已接收，正在处理中'
            }

            # 启动后台线程处理请求
            self._executor.submit(
                self._process_request_async,
                validated_data=validated_data,
                request_obj=request_obj,
                upload_record_id=conversation_request.id,
                user=user
            )

            return ResponseUtil.success(
                data=response_data,
                message='请求已接收，正在处理中'
            )

        except Exception as e:
            logger.error(f"请求处理失败: {str(e)}", exc_info=True)
            # 记录失败状态到上传记录
            if conversation_request and hasattr(conversation_request, 'id'):
                ImageUploadManager.mark_as_failed(
                    record_id=conversation_request.id,
                    error_message=f"请求处理失败: {str(e)}"
                )
            return ResponseUtil.error(
                errors="请求处理失败",
                data=str(e),
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _process_request_async(self, validated_data, request_obj, upload_record_id, user):
        """异步处理请求"""
        try:
            service = VolcengineVisualServiceSDK()

            # 准备参数
            image_urls = validated_data.get('image_urls', [])

            # 构建参数字典 - 将DTO中的所有参数传递给服务
            params = {k: v for k, v in validated_data.items() if k not in ['text', 'conversation_id', 'image_urls']}

            # 特殊处理logo相关参数
            if 'logo_position' in validated_data:
                params['position'] = validated_data['logo_position']

            if 'logo_language' in validated_data:
                params['language'] = validated_data['logo_language']

            if 'logo_opacity' in validated_data:
                params['opacity'] = validated_data['logo_opacity']

            if 'logo_text' in validated_data:
                params['logo_text'] = validated_data['logo_text']

            # 调用服务生成图像
            result = service.generate_image(
                prompt=validated_data['text'],
                user_id=user.id,
                conversation_id=validated_data.get('conversation_id'),
                upload_record_id=upload_record_id,
                image_urls=image_urls,
                **params
            )

            if result['success']:
                RequestManager.update_request_status(
                    request_obj.id,
                    RequestStatus.COMPLETED,
                    response_data={
                        'image_url': result['image_url'],
                        'image_name': result['image_name'],
                        'prompt': result['prompt'],
                        'seed': validated_data.get('seed', -1)
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
            # 记录失败状态到上传记录
            if upload_record_id:
                ImageUploadManager.mark_as_failed(
                    record_id=upload_record_id,
                    error_message=f"图像生成失败: {str(e)}"
                )

    def _parse_request_data(self, request):
        """统一解析请求数据"""
        if isinstance(request.data, dict):
            return request.data
        try:
            return json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            raise BusinessException(code=ErrorCode.JSON_NOT_FAIL.code, data='', errors="无效的JSON数据")
