from typing import re

from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import timedelta
import random
import logging
import uuid
from rest_framework.pagination import PageNumberPagination

from rest_framework_simplejwt.authentication import JWTAuthentication

from common.ErrorCode import ErrorCode
from djangoProject import settings
from templateImage.ImageUploadDTO import TextImageDTO, TextImageNewDTO, CompleteRedrawingWorkflowDTO, \
    InternalSupplementationAndRemovalWorkflowDTO, InternalSupplementationWorkflowDTO, WidePictureWorkflowDTO, \
    ImagesImageDTO, ImagesProductDTO, ImagesProductWorkflowDTO, ImagesFineDetailWorkflowDTO, ImagesClueImageDTO, \
    WhiteBackgroundImageDTO, TextImageNewModelDTO, MultiImageToImageDTO, CombinedImageGenerationDTO
# 使用单例模块中的queue_service
from templateImage.queue_service_singleton import queue_service, initialize_queue_service
from templateVideo import serializers

from user.models import SysUser
from templateImage.models import ComfyUITask, ConversationList, ImageUploadRecord, TaskType
from templateImage.task_utils import TaskUtils
from templateImage import task_manager

from templateImage.ImageService import ImageService
from exception.business_exception import BusinessException
from common.response_utils import ResponseUtil
from rest_framework import status
from django.db.models import F
from drf_spectacular.utils import extend_schema
import json

# 尝试导入PointsManager，如不存在则使用空函数替代
try:
    from user.points import PointsManager
except ImportError:
    # 创建一个临时的PointsManager类
    class PointsManager:
        @staticmethod
        def deduct_points(user, points, reason):
            logging.warning(f"PointsManager未定义，无法扣除积分 {points} 点，原因: {reason}")
            return {'success': False, 'message': 'PointsManager未定义'}

logger = logging.getLogger(__name__)

# 初始化队列服务
try:
    initialize_queue_service()
    logger.info("队列服务已在comfyui_views中初始化")
except Exception as e:
    logger.error(f"初始化队列服务失败: {str(e)}")

# 辅助函数：创建会话和记录
def create_conversation_and_record(user, task_type, description, task_id, image_url="", image_list="", conversation_id=None):
    """
    创建会话和初始记录
    :param user: 用户对象
    :param task_type: 任务类型
    :param description: 描述
    :param task_id: 任务ID
    :param image_url: 图片URL
    :param image_list: 图片列表
    :param conversation_id: 会话ID，如果提供则使用已有会话
    :return: (conversation, record) 元组
    """
    try:
        # 任务类型英文到中文的映射
        task_type_names = {
            'text_to_image': '文生图',
            'image_to_image': '图生图',
            'product_replace': '产品替换',
            'white_background': '白底图',
            'product_clue': '产品线索',
            'clue_product': '线索产品',
            'fine_detail': '细节精修',
            'wide_picture': '扩图',
            'internal_supplementation': '内补',
            'internal_supplementation_and_removal': '内补去除',
            'complete_redrawing': '重绘精修',
            'multi_image_to_image': '多图生图'
        }
        
        # 如果提供了会话ID，尝试获取已有会话
        conversation = None
        if conversation_id:
            try:
                conversation = ConversationList.objects.get(id=conversation_id, user=user)
                logger.info(f"使用已有会话: {conversation.id}, 会话名称: {conversation.name}")
            except ConversationList.DoesNotExist:
                logger.warning(f"未找到指定的会话ID: {conversation_id}，将创建新会话")
        
        # 如果没有找到已有会话，创建新会话
        if not conversation:
            # 获取中文任务类型名称，如果没有对应的则使用原始任务类型
            conversation_name = task_type_names.get(task_type, task_type)
            
            # 创建新会话
            conversation = ConversationList.objects.create(
                name=conversation_name,
                user=user
            )
            logger.info(f"为用户 {user.id} 创建新会话: {conversation.id}，会话名称: {conversation_name}")
        
        # 根据任务类型确定存储方式
        image_method = {
            'text_to_image': 'ai_text',
            'image_to_image': 'ai_image',
            'product_replace': 'ai_product',
            'white_background': 'white',
            'product_clue': 'clue',
            'clue_product': 'clue_image',
            'multi_image_to_image': 'multi_image',
            'fine_detail': 'fine_detail',
            'wide_picture': 'wide_picture',
            'internal_supplementation': 'internal_supplementation',
            'internal_supplementation_and_removal': 'internal_supplementation_and_removal',
            'complete_redrawing': 'complete_redrawing',
        }.get(task_type, 'ai_custom')
        
        # 为每张图片生成唯一名称
        image_name = f"{task_id}_pending.png"
        
        # 保存图片记录到ImageUploadRecord
        record = ImageUploadRecord.objects.create(
            user=user,
            conversation=conversation,
            image_url=image_url,
            image_name=image_name,
            prompt=description or f"AI生成-{task_id}",
            image_list=image_list,
            model_used=image_method,
            status='pending'
        )
        logger.info(f"已创建初始记录: {image_name}, ID: {record.id}")
        
        return conversation, record
    except Exception as e:
        logger.error(f"创建会话和记录失败: {str(e)}")
        raise


@method_decorator(csrf_exempt, name='dispatch')
class TaskStatusAPIView(APIView):
    """
    获取任务状态的API视图
    """
    permission_classes = [AllowAny]

    @extend_schema(
        responses={200: None},
        description="获取任务状态"
    )
    def get(self, request, task_id):
        try:
            logger.info(f"开始查询任务状态: {task_id}")

            # 使用TaskUtils获取任务状态（保持一致性）
            task_status = TaskUtils.get_task_status(task_id)
            
            # 记录任务状态来源，用于调试
            if task_status:
                status_source = task_status.get('from_source', 'unknown')
                logger.info(f"任务 {task_id} 状态数据来源: {status_source}")
                
                # 记录Redis任务状态内容（调试用）
                if status_source == 'redis':
                    redis_keys = list(task_status.keys())
                    logger.info(f"Redis中任务 {task_id} 的数据包含字段: {redis_keys}")
                    if 'status' in task_status:
                        logger.info(f"Redis中任务 {task_id} 的状态为: {task_status['status']}")
                    if 'image_urls' in task_status:
                        logger.info(f"Redis中任务 {task_id} 有 {len(task_status['image_urls'])} 个图片URL")
                    elif 'output_data' in task_status and task_status['output_data']:
                        logger.info(f"Redis中任务 {task_id} 的output_data类型: {type(task_status['output_data'])}")
                
                # 特殊处理 processing_completed 状态 - 这是一个临时状态
                if task_status.get('status') == 'processing_completed':
                    # 检查是否有输出结果
                    has_results = False
                    
                    # 检查是否有图片URL
                    if 'image_urls' in task_status and task_status['image_urls']:
                        has_results = True
                        logger.info(f"发现任务 {task_id} 处于processing_completed状态但已有图片URLs，应转为completed状态")
                    
                    # 检查是否有输出数据
                    elif 'output_data' in task_status and task_status['output_data']:
                        output_data = task_status['output_data']
                        if isinstance(output_data, dict) and 'image_urls' in output_data and output_data['image_urls']:
                            has_results = True
                            logger.info(f"发现任务 {task_id} 处于processing_completed状态但已有输出数据，应转为completed状态")
                    
                    # 如果有结果，强制更新状态为completed
                    if has_results:
                        # 更新Redis和MySQL状态
                        if hasattr(queue_service, '_update_task_status'):
                            try:
                                # 强制更新任务状态为completed
                                queue_service._update_task_status(task_id, 'completed', force_redis_update=True)
                                logger.info(f"已将任务 {task_id} 状态从processing_completed更新为completed")
                                
                                # 更新任务状态字典，用于返回给前端
                                task_status['status'] = 'completed'
                            except Exception as e:
                                logger.error(f"更新任务状态失败: {str(e)}")
            
            if not task_status or task_status.get('status') == 'unknown':
                logger.warning(f"任务不存在: {task_id}")
                return ResponseUtil.error(
                    message="任务不存在",
                    code=404
                )
                
            # 在Redis找不到状态时，可能需要从MySQL获取完整任务对象以获取某些字段
            task = None
            if task_status.get('from_source') == 'mysql' or not task_status.get('output_data'):
                task = ComfyUITask.objects.filter(task_id=task_id).first()
            
            # 准备响应数据
            response_data = {
                'task_id': task_id,
                'status': task_status.get('status'),
                'created_at': task_status.get('created_at'),
                'updated_at': task_status.get('updated_at'),
                'priority': task_status.get('priority'),
                'progress': task_status.get('progress', 0.0),
            }
            
            # 确保created_at字段存在值
            if not response_data['created_at']:
                # 如果Redis中没有创建时间，尝试从MySQL获取
                if task is None:
                    task = ComfyUITask.objects.filter(task_id=task_id).first()
                if task and task.created_at:
                    response_data['created_at'] = task.created_at.isoformat()
                    logger.info(f"从MySQL获取到任务 {task_id} 的创建时间")
                else:
                    # 如果MySQL也没有，使用当前时间
                    response_data['created_at'] = timezone.now().isoformat()
                    logger.warning(f"任务 {task_id} 的创建时间未知，使用当前时间代替")
            
            # 添加处理时间（如果有）
            if 'processing_time' in task_status:
                response_data['processing_time'] = task_status['processing_time']
            
            # 添加输入数据（如果有）
            if 'input_data' in task_status:
                response_data['input_data'] = task_status['input_data']
            elif task and task.input_data:
                response_data['input_data'] = task.input_data
            
            # 添加输出数据（如果有）
            if 'output_data' in task_status and task_status['output_data']:
                output_data = task_status['output_data']
                if isinstance(output_data, dict):
                    # 已是字典格式
                    response_data['result'] = output_data
                else:
                    # 尝试解析JSON字符串
                    try:
                        parsed_data = json.loads(output_data) if isinstance(output_data, str) else output_data
                        response_data['result'] = parsed_data
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"无法解析任务 {task_id} 的输出数据: {output_data}")
                        response_data['result'] = {'data': output_data}
            elif task and task.output_data:
                response_data['result'] = task.output_data
            # 检查图片URL结果
            elif 'image_urls' in task_status:
                response_data['result'] = {'image_urls': task_status['image_urls']}
            else:
                logger.warning(f"任务 {task_id} 没有output_data")
                # 如果已完成但无output_data，尝试从关联的ImageUploadRecord获取URL
                if task_status.get('status') == 'completed':
                    if task is None:
                        task = ComfyUITask.objects.filter(task_id=task_id).first()
                        
                    if task:
                        records = ImageUploadRecord.objects.filter(comfyUI_task=task)
                        if records.exists():
                            urls = [record.image_url for record in records if record.image_url]
                            if urls:
                                logger.info(f"任务 {task_id} 从关联记录获取到 {len(urls)} 个图片URL")
                                response_data['result'] = {'image_urls': urls}
                            else:
                                response_data['result'] = {'image_urls': []}
                        else:
                            response_data['result'] = {'image_urls': []}
                    else:
                        response_data['result'] = {'image_urls': []}
                else:
                    response_data['result'] = {'image_urls': []}
            
            # 添加错误信息（如果有）
            if 'error_message' in task_status and task_status['error_message']:
                response_data['error'] = task_status['error_message']
            elif task and task.error_message:
                response_data['error'] = task.error_message
            
            # 添加执行时间
            if task_status.get('completed_at') and task_status.get('created_at'):
                try:
                    # 确保时间格式一致
                    from_time = None
                    to_time = None
                    
                    # 处理created_at
                    if isinstance(task_status['created_at'], str):
                        try:
                            from_time = parse_datetime(task_status['created_at'])
                        except (ValueError, TypeError):
                            logger.warning(f"无法解析created_at时间字符串: {task_status['created_at']}")
                    else:
                        from_time = task_status['created_at']
                    
                    # 处理completed_at
                    if isinstance(task_status['completed_at'], str):
                        try:
                            to_time = parse_datetime(task_status['completed_at'])
                        except (ValueError, TypeError):
                            logger.warning(f"无法解析completed_at时间字符串: {task_status['completed_at']}")
                    else:
                        to_time = task_status['completed_at']
                    
                    # 计算执行时间
                    if from_time and to_time:
                        execution_time = (to_time - from_time).total_seconds()
                        response_data['execution_time_seconds'] = round(execution_time, 2)
                    else:
                        logger.warning(f"无法计算执行时间: from_time={from_time}, to_time={to_time}")
                except Exception as e:
                    logger.warning(f"计算执行时间时出错: {str(e)}")
                    # 尝试从MySQL获取执行时间
                    if task and task.completed_at and task.created_at:
                        execution_time = (task.completed_at - task.created_at).total_seconds()
                        response_data['execution_time_seconds'] = round(execution_time, 2)
                        logger.info(f"从MySQL计算得到任务 {task_id} 的执行时间: {round(execution_time, 2)}秒")
            elif task and task.completed_at and task.created_at:
                execution_time = (task.completed_at - task.created_at).total_seconds()
                response_data['execution_time_seconds'] = round(execution_time, 2)
                logger.info(f"从MySQL计算得到任务 {task_id} 的执行时间: {round(execution_time, 2)}秒")
            
            # 记录任务状态
            logger.info(f"任务状态查询成功: {task_id}, 状态: {task_status.get('status')}")
            
            # 特殊处理: 检测是否有图片结果但状态不匹配的情况
            if (task_status.get('status') == 'processing' or task_status.get('status') == 'processing_completed') and 'result' in response_data and 'image_urls' in response_data['result'] and response_data['result']['image_urls']:
                logger.info(f"检测到任务 {task_id} 状态为{task_status.get('status')}但已有结果图片，自动将状态更新为completed")
                
                # 处理任务完成相关逻辑（例如积分扣除等）
                if task is None:
                    task = ComfyUITask.objects.filter(task_id=task_id).first()
                    
                if task and task.user:
                    # 尝试扣除积分
                    try:
                        # 获取任务类型对应的积分
                        task_info = ComfyUITask.TASK_TYPE_INFO.get(task.task_type, {})
                        points_required = task_info.get('points', 0)
                
                        # 如果需要扣除积分
                        if points_required > 0:
                            # 获取用户信息
                            user = task.user
                            
                            # 检查是否已经扣除过积分
                            if not hasattr(task, 'is_points_deducted') or not task.is_points_deducted:
                                # 导入PointsManager
                                from user.points import PointsManager
                                
                                # 扣除积分
                                result = PointsManager.deduct_points(
                                    user=user, 
                                    points=points_required, 
                                    reason=f"使用{task_info.get('name', task.task_type)}功能",
                                    notes=f"任务ID: {task_id}",
                                    transaction_type="AI生成"
                                )
            
                                if result['success']:
                                    logger.info(f"已扣除用户 {user.username} 的普通积分 {points_required} 点")
                                    # 标记为已扣除
                                    task.is_points_deducted = True
                                    task.save(update_fields=['is_points_deducted'])
                                else:
                                    logger.warning(f"扣除积分失败: {result['message']}")
                            else:
                                logger.info(f"任务 {task_id} 已扣除过积分，跳过")
                                
                            logger.info(f"任务 {task_id} 成功完成，已扣除用户积分")
                        
                        # 检查是否需要自动保存到云空间
                        auto_save = task_info.get('auto_save_to_cloud', False)
                        if auto_save:
                            # TODO: 实现自动保存到云空间逻辑
                            logger.info(f"任务 {task_id} 自动保存到云空间功能已开启，准备保存图片")
                        else:
                            logger.info(f"任务 {task_id} 自动保存到云空间功能已关闭，不自动保存图片")
                    except Exception as e:
                        logger.error(f"处理积分扣除时出错: {str(e)}")
                
                # 更新任务状态为已完成
                TaskUtils._update_task_status(
                    task_id,
                    'completed',
                    force_redis_update=True,
                    output_data=response_data.get('result'),
                    completed_at=timezone.now()
                )
                            
                # 更新返回给前端的状态
                response_data['status'] = 'completed'
                logger.info(f"已自动将任务 {task_id} 状态从{task_status.get('status')}更新为completed")
            
            # 同步记录状态
            if task_status.get('status') == 'completed':
                logger.info(f"任务完成，图片URL: {response_data.get('result', {}).get('image_urls', [])}")
                
                # 使用sync_record_status方法确保所有记录状态和image_url都是最新的
                sync_result = TaskUtils.sync_record_status(task_id, force=True)
                if sync_result['success'] and sync_result['updated_count'] > 0:
                    logger.info(f"任务状态查询: 使用sync_record_status同步更新了 {sync_result['updated_count']} 条记录")
                elif not sync_result['success']:
                    logger.error(f"任务状态查询: 同步记录状态失败: {sync_result.get('message', '未知错误')}")
                
            elif task_status.get('status') == 'failed':
                if task is None:
                    task = ComfyUITask.objects.filter(task_id=task_id).first()
                
                if task:
                    logger.error(f"任务失败: {task.error_message or '未知错误'}")
                    
                    # 使用TaskUtils.sync_record_status方法同步记录状态
                    sync_result = TaskUtils.sync_record_status(task_id, force=False)
                    if sync_result['success'] and sync_result['updated_count'] > 0:
                        logger.info(f"任务状态查询: 已同步 {sync_result['updated_count']} 条记录状态为failed")
                    elif not sync_result['success']:
                        logger.error(f"任务状态查询: 同步记录状态失败: {sync_result.get('message', '未知错误')}")

            return ResponseUtil.success(
                data=response_data,
                message="任务状态获取成功"
            )

        except Exception as e:
            logger.error(f"获取任务状态失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                message=f"获取任务状态失败: {str(e)}",
                code=500
            )


@method_decorator(csrf_exempt, name='dispatch')
class TaskCancelAPIView(APIView):
    """
    取消任务的API视图
    """
    permission_classes = [AllowAny]

    @extend_schema(
        responses={200: None},
        description="取消任务"
    )
    def post(self, request, task_id):
        try:
            result = TaskUtils.cancel_task(task_id)
            
            # 更新关联的记录状态为已取消
            task = ComfyUITask.objects.filter(task_id=task_id).first()
            if task:
                # 更新相关记录状态
                records = ImageUploadRecord.objects.filter(comfyUI_task=task)
                for record in records:
                    record.status = 'cancelled'
                    record.save()
                    logger.info(f"已更新记录状态为已取消: ID: {record.id}")
            
            return ResponseUtil.success(
                data=result,
                message="任务已取消"
            )
        except BusinessException as e:
            return ResponseUtil.error(
                message=str(e.errors),
                code=400
            )
        except Exception as e:
            logger.error(f"取消任务失败: {str(e)}")
            return ResponseUtil.error(
                message=f"取消任务失败: {str(e)}"
            )

    @extend_schema(
        responses={200: None},
        description="获取任务状态"
    )
    def get(self, request, task_id):
        """
        获取任务状态
        """
        try:
            task_status = TaskUtils.get_task_status(task_id)
            return ResponseUtil.success(
                data=task_status,
                message="获取任务状态成功"
            )
        except Exception as e:
            logger.error(f"获取任务状态失败: {str(e)}")
            return ResponseUtil.error(
                message=f"获取任务状态失败: {str(e)}"
            )


class QueueInfoAPIView(APIView):
    """
    获取队列信息
    """

    def get(self, request):
        try:
            # 获取所有任务的状态统计
            status_stats = ComfyUITask.objects.values('status').annotate(
                count=Count('task_id')
            )

            # 获取各优先级的任务数量 (包括待处理和正在处理的任务)
            priority_stats = ComfyUITask.objects.filter(
                Q(status='pending') | Q(status='processing')
            ).values('priority').annotate(
                count=Count('task_id')
            )

            # 获取最近24小时的任务统计
            last_24h = timezone.now() - timedelta(hours=24)
            recent_stats = ComfyUITask.objects.filter(
                created_at__gte=last_24h
            ).values('status').annotate(
                count=Count('task_id')
            )

            # 在查询任务队列之前，重新计算所有队列位置
            TaskUtils._recalculate_queue_positions()
            
            # 手动设置正在处理的任务的队列位置为0（最高优先级）
            processing_tasks = ComfyUITask.objects.filter(status='processing')
            for task in processing_tasks:
                task.queue_position = 0
                task.save(update_fields=['queue_position'])
                logger.info(f"手动设置处理中任务 {task.task_id} 的队列位置为0")

            # 获取当前队列中的任务（包括待处理和正在处理的任务，按状态、优先级和创建时间排序）
            queue_tasks = ComfyUITask.objects.filter(
                Q(status='pending') | Q(status='processing')
            ).order_by(
                # 先按状态排序，使处理中的任务显示在前面
                F('status').desc(),
                'priority',
                'created_at'
            ).values(
                'task_id',
                'status',
                'priority',
                'queue_position',
                'created_at',
                'progress'
            )

            # 获取正在处理的任务
            processing_tasks = ComfyUITask.objects.filter(
                status='processing'
            ).values(
                'task_id',
                'priority',
                'progress'
            )

            return ResponseUtil.success(
                 data={
                    'status_stats': list(status_stats),
                    'priority_stats': list(priority_stats),
                    'recent_stats': list(recent_stats),
                    'queue_tasks': list(queue_tasks),
                    'processing_tasks': list(processing_tasks)},
                 message="获取队列信息成功！"
            )

        except Exception as e:
            return ResponseUtil.error(message=str(e), code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class WidePictureWorkflowAPIView(APIView):
    """
    阔图工作流接口。
    """
    permission_classes = [IsAuthenticated]

    def generate_six_digit_random(self):
        return random.SystemRandom().randint(100000, 999999)

    @extend_schema(
        request=WidePictureWorkflowDTO,
        responses={200: None},
    )
    def post(self, request, *args, **kwargs):
        """
        阔图功能 - 扩展图像边界。
        接收原图URL、扩展边界参数和文本描述，返回生成的图像任务信息。
        支持优先级设置: low, medium, high（默认为medium）
        """
        try:
            # 获取请求数据
            description = request.data.get('description', '')
            url = request.data.get('url')
            left = int(request.data.get('left', 0))
            top = int(request.data.get('top', 0))
            right = int(request.data.get('right', 0))
            bottom = int(request.data.get('bottom', 0))
            user_id = request.user.id
            priority = request.data.get('priority', 'medium')
            conversation_id = request.data.get('conversation_id')  # 获取会话ID
            add_new_data = request.data.get('add_new_data', '')  # 获取新增数据
            # 验证优先级值是否有效
            valid_priorities = ['low', 'medium', 'high']
            if priority not in valid_priorities:
                priority = 'medium'  # 默认为中等优先级

            # 验证数据
            if not url:
                raise ValidationError('缺少必要参数：url')

            # 查询用户
            try:
                user = SysUser.objects.get(id=user_id)
            except SysUser.DoesNotExist:
                raise ValidationError('指定的用户不存在')

            # 检查用户任务并发限制
            if not TaskUtils.check_user_concurrent_limit(user):
                return ResponseUtil.error(
                    message="您在队列中的任务已满！", 
                    code=status.HTTP_429_TOO_MANY_REQUESTS
                )

            # 随机数字作为种子
            seed = self.generate_six_digit_random()
            
            # 创建会话和初始记录
            conversation, record = create_conversation_and_record(
                user=user,
                task_type='wide_picture',
                description=description,
                task_id=f"temp_{uuid.uuid4()}",
                image_url="",
                image_list=url,
                conversation_id=conversation_id  # 传递会话ID
            )

            # 生成图像任务
            task_info = ImageService.wide_picture_workflow(
                description=description,
                url=url,
                left=left,
                top=top,
                right=right,
                bottom=bottom,
                seed=seed,
                user=user,
                priority=priority,
                add_new_data=add_new_data
            )
            
            # 更新记录中的任务ID和任务对象
            try:
                task = ComfyUITask.objects.get(task_id=task_info['task_id'])
                record.comfyUI_task = task
                record.image_name = f"{task_info['task_id']}_pending.png"
                record.save()
                logger.info(f"已更新记录的任务ID: {task_info['task_id']}, 记录ID: {record.id}")
            except Exception as e:
                logger.error(f"更新记录任务ID失败: {str(e)}")

            # 添加消息提示
            task_info['message'] = '阔图任务已创建'
            # 添加会话和记录信息
            task_info['conversation_id'] = conversation.id
            task_info['record_id'] = record.id

            return ResponseUtil.success(data=task_info, message=task_info['message'])

        except ValidationError as e:
            return ResponseUtil.error(message=str(e), code=400)
        except BusinessException as e:
            return ResponseUtil.error(message=e.errors, code=400)
        except Exception as e:
            return ResponseUtil.error(message=str(e), code=500)


@method_decorator(csrf_exempt, name='dispatch')
class InternalSupplementationWorkflowAPIView(APIView):
    """
    内补工作流接口。
    """
    permission_classes = [IsAuthenticated]

    def generate_six_digit_random(self):
        return random.SystemRandom().randint(100000, 999999)

    @extend_schema(
        request=InternalSupplementationWorkflowDTO,
        responses={200: None},
    )
    def post(self, request, *args, **kwargs):
        """
        内补功能 - 填充图像内部区域。
        接收原图URL、蒙版URL和文本描述，返回生成的图像任务信息。
        支持优先级设置: low, medium, high（默认为medium）
        """
        try:
            # 获取请求数据
            description = request.data.get('description', '')
            url = request.data.get('url')
            mask_url = request.data.get('mask_url')
            user_id = request.user.id
            priority = request.data.get('priority', 'medium')
            conversation_id = request.data.get('conversation_id')  # 获取会话ID
            add_new_data = request.data.get('add_new_data', '')  # 获取新增数据
            # 验证优先级值是否有效
            valid_priorities = ['low', 'medium', 'high']
            if priority not in valid_priorities:
                priority = 'medium'  # 默认为中等优先级

            # 验证数据
            if not url:
                raise ValidationError('缺少必要参数：url')
            if not mask_url:
                raise ValidationError('缺少必要参数：mask_url')

            # 查询用户
            try:
                user = SysUser.objects.get(id=user_id)
            except SysUser.DoesNotExist:
                raise ValidationError('指定的用户不存在')

            # 检查用户任务并发限制
            if not TaskUtils.check_user_concurrent_limit(user):
                return ResponseUtil.error(
                    message="您在队列中的任务已满！", 
                    code=status.HTTP_429_TOO_MANY_REQUESTS
                )

            # 随机数字作为种子
            seed = self.generate_six_digit_random()
            
            # 创建会话和初始记录
            conversation, record = create_conversation_and_record(
                user=user,
                task_type='internal_supplementation',
                description=description,
                task_id=f"temp_{uuid.uuid4()}",
                image_url="",
                image_list=url,
                conversation_id=conversation_id  # 传递会话ID
            )

            # 生成图像任务
            task_info = ImageService.internal_supplementation_workflow(
                description=description,
                url=url,
                mask_url=mask_url,
                seed=seed,
                user=user,
                priority=priority,
                add_new_data=add_new_data
            )
            
            # 更新记录中的任务ID和任务对象
            try:
                task = ComfyUITask.objects.get(task_id=task_info['task_id'])
                record.comfyUI_task = task
                record.image_name = f"{task_info['task_id']}_pending.png"
                record.save()
                logger.info(f"已更新记录的任务ID: {task_info['task_id']}, 记录ID: {record.id}")
            except Exception as e:
                logger.error(f"更新记录任务ID失败: {str(e)}")

            # 添加消息提示
            task_info['message'] = '内补任务已创建'
            # 添加会话和记录信息
            task_info['conversation_id'] = conversation.id
            task_info['record_id'] = record.id

            return ResponseUtil.success(data=task_info, message=task_info['message'])

        except ValidationError as e:
            return ResponseUtil.error(message=str(e), code=400)
        except BusinessException as e:
            return ResponseUtil.error(message=e.errors, code=400)
        except Exception as e:
            return ResponseUtil.error(message=str(e), code=500)


@method_decorator(csrf_exempt, name='dispatch')
class InternalSupplementationAndRemovalWorkflowAPIView(APIView):
    """
    内补去除工作流接口。
    """
    permission_classes = [IsAuthenticated]

    def generate_six_digit_random(self):
        return random.SystemRandom().randint(100000, 999999)

    @extend_schema(
        request=InternalSupplementationAndRemovalWorkflowDTO,
        responses={200: None},
    )
    def post(self, request, *args, **kwargs):
        """
        内补去除功能 - 移除并填充图像内部区域。
        接收原图URL和蒙版URL，返回生成的图像任务信息。
        支持优先级设置: low, medium, high（默认为medium）
        """
        try:
            # 获取请求数据
            url = request.data.get('url')
            mask_url = request.data.get('mask_url')
            user_id = request.user.id
            priority = request.data.get('priority', 'medium')
            conversation_id = request.data.get('conversation_id')  # 获取会话ID
            add_new_data = request.data.get('add_new_data', '')  # 获取新增数据
            # 验证优先级值是否有效
            valid_priorities = ['low', 'medium', 'high']
            if priority not in valid_priorities:
                priority = 'medium'  # 默认为中等优先级

            # 验证数据
            if not url:
                raise ValidationError('缺少必要参数：url')
            if not mask_url:
                raise ValidationError('缺少必要参数：mask_url')

            # 查询用户
            try:
                user = SysUser.objects.get(id=user_id)
            except SysUser.DoesNotExist:
                raise ValidationError('指定的用户不存在')

            # 检查用户任务并发限制
            if not TaskUtils.check_user_concurrent_limit(user):
                return ResponseUtil.error(
                    message="您在队列中的任务已满！", 
                    code=status.HTTP_429_TOO_MANY_REQUESTS
                )

            # 随机数字作为种子
            seed = self.generate_six_digit_random()
            
            # 创建会话和初始记录
            conversation, record = create_conversation_and_record(
                user=user,
                task_type='internal_supplementation_and_removal',
                description='内补去除',
                task_id=f"temp_{uuid.uuid4()}",
                image_url="",
                image_list=url,
                conversation_id=conversation_id  # 传递会话ID
            )

            # 生成图像任务
            task_info = ImageService.internal_supplementation_and_removal_workflow(
                url=url,
                mask_url=mask_url,
                seed=seed,
                user=user,
                priority=priority,
                add_new_data=add_new_data
            )
            
            # 更新记录中的任务ID和任务对象
            try:
                task = ComfyUITask.objects.get(task_id=task_info['task_id'])
                record.comfyUI_task = task
                record.image_name = f"{task_info['task_id']}_pending.png"
                record.save()
                logger.info(f"已更新记录的任务ID: {task_info['task_id']}, 记录ID: {record.id}")
            except Exception as e:
                logger.error(f"更新记录任务ID失败: {str(e)}")

            # 添加消息提示
            task_info['message'] = '内补去除任务已创建'
            # 添加会话和记录信息
            task_info['conversation_id'] = conversation.id
            task_info['record_id'] = record.id

            return ResponseUtil.success(data=task_info, message=task_info['message'])

        except ValidationError as e:
            return ResponseUtil.error(message=str(e), code=400)
        except BusinessException as e:
            return ResponseUtil.error(message=e.errors, code=400)
        except Exception as e:
            return ResponseUtil.error(message=str(e), code=500)


@method_decorator(csrf_exempt, name='dispatch')
class CompleteRedrawingWorkflowAPIView(APIView):
    """
    重绘精修工作流接口。
    """
    permission_classes = [IsAuthenticated]

    def generate_six_digit_random(self):
        return random.SystemRandom().randint(100000, 999999)

    @extend_schema(
        request=CompleteRedrawingWorkflowDTO,
        responses={200: None},
    )
    def post(self, request, *args, **kwargs):
        """
        重绘精修功能 - 完整重绘和精修整张图像。
        接收原图URL、调整级别和文本描述，返回生成的图像任务信息。
        支持优先级设置: low, medium, high（默认为medium）
        """
        try:
            # 获取请求数据
            description = request.data.get('description', '')
            level = float(request.data.get('level', 0.6))
            url = request.data.get('url')
            user_id = request.user.id
            priority = request.data.get('priority', 'medium')
            conversation_id = request.data.get('conversation_id')  # 获取会话ID
            add_new_data = request.data.get('add_new_data', '')  # 获取新增数据

            # 验证优先级值是否有效
            valid_priorities = ['low', 'medium', 'high']
            if priority not in valid_priorities:
                priority = 'medium'  # 默认为中等优先级

            # 验证数据
            if not url:
                raise ValidationError('缺少必要参数：url')

            # 查询用户
            try:
                user = SysUser.objects.get(id=user_id)
            except SysUser.DoesNotExist:
                raise ValidationError('指定的用户不存在')

            # 检查用户任务并发限制
            if not TaskUtils.check_user_concurrent_limit(user):
                return ResponseUtil.error(
                    message="您在队列中的任务已满！", 
                    code=status.HTTP_429_TOO_MANY_REQUESTS
                )

            # 随机数字作为种子
            seed = self.generate_six_digit_random()
            
            # 创建会话和初始记录
            conversation, record = create_conversation_and_record(
                user=user,
                task_type='complete_redrawing',
                description=description,
                task_id=f"temp_{uuid.uuid4()}",
                image_url="",
                image_list=url,
                conversation_id=conversation_id  # 传递会话ID
            )

            # 生成图像任务
            task_info = ImageService.xl_wholeimagefix_complete_redrawing_and_refinement_of_the_entire_image_workflow(
                description=description,
                level=level,
                url=url,
                seed=seed,
                user=user,
                priority=priority,
                add_new_data=add_new_data
            )
            
            # 更新记录中的任务ID和任务对象
            try:
                task = ComfyUITask.objects.get(task_id=task_info['task_id'])
                record.comfyUI_task = task
                record.image_name = f"{task_info['task_id']}_pending.png"
                record.save()
                logger.info(f"已更新记录的任务ID: {task_info['task_id']}, 记录ID: {record.id}")
            except Exception as e:
                logger.error(f"更新记录任务ID失败: {str(e)}")

            # 添加消息提示
            task_info['message'] = '重绘精修任务已创建'
            # 添加会话和记录信息
            task_info['conversation_id'] = conversation.id
            task_info['record_id'] = record.id

            return ResponseUtil.success(data=task_info, message=task_info['message'])

        except ValidationError as e:
            return ResponseUtil.error(message=str(e), code=400)
        except BusinessException as e:
            return ResponseUtil.error(message=e.errors, code=400)
        except Exception as e:
            return ResponseUtil.error(message=str(e), code=500)


@method_decorator(csrf_exempt, name='dispatch')
class TextImageAPIView(APIView):
    """
    生成文本图像并返回任务信息。
    """
    permission_classes = [AllowAny]

    @extend_schema(
        request=TextImageDTO,
        responses={200: None},
    )
    def post(self, request, *args, **kwargs):
        """
        接收文本，返回生成的图像任务信息。
        支持优先级设置: low, medium, high（默认为medium）
        """
        try:
            # 获取请求数据
            description = request.data.get('description')
            user_id = request.data.get('user_id')
            priority = request.data.get('priority', 'medium')  # 获取优先级参数
            conversation_id = request.data.get('conversation_id')  # 获取会话ID

            # 验证优先级值是否有效
            valid_priorities = ['low', 'medium', 'high']
            if priority not in valid_priorities:
                priority = 'medium'  # 默认为中等优先级

            # 验证数据
            if not description:
                raise ValidationError('缺少必要参数：description')

            if not user_id:
                raise ValidationError('缺少必要参数：user_id')

            # 查询用户
            try:
                user = SysUser.objects.get(id=user_id)
            except SysUser.DoesNotExist:
                raise ValidationError('指定的用户不存在')
                
            # 创建会话和初始记录
            conversation, record = create_conversation_and_record(
                user=user,
                task_type='text_to_image',
                description=description,
                task_id=f"temp_{uuid.uuid4()}",
                conversation_id=conversation_id  # 传递会话ID
            )

            # 生成图像任务
            task_info = ImageService.text_to_image(
                description=description,
                user=user,
                priority=priority,  # 传递优先级
                **kwargs
            )
            
            # 更新记录中的任务ID和任务对象
            try:
                task = ComfyUITask.objects.get(task_id=task_info['task_id'])
                record.comfyUI_task = task
                record.image_name = f"{task_info['task_id']}_pending.png"
                record.save()
                logger.info(f"已更新记录的任务ID: {task_info['task_id']}, 记录ID: {record.id}")
            except Exception as e:
                logger.error(f"更新记录任务ID失败: {str(e)}")

            # 添加消息提示
            task_info['message'] = '文生图任务已提交'
            # 添加会话和记录信息
            task_info['conversation_id'] = conversation.id
            task_info['record_id'] = record.id

            return ResponseUtil.success(data=task_info, message=task_info['message'])

        except ValidationError as e:
            return ResponseUtil.error(message=str(e), code=400)
        except BusinessException as e:
            return ResponseUtil.error(message=e.errors, code=400)
        except Exception as e:
            return ResponseUtil.error(message=str(e), code=500)


@method_decorator(csrf_exempt, name='dispatch')
class ImagesImageAPIView(APIView):
    """
    生成图像图像并返回任务信息。
    """
    permission_classes = [AllowAny]

    @extend_schema(
        request=ImagesImageDTO,
        responses={200: None},
    )
    def post(self, request, *args, **kwargs):
        """
        接收图片URL和文本，返回生成的图像任务信息。
        支持优先级设置: low, medium, high（默认为medium）
        """
        try:
            # 获取请求数据
            description = request.data.get('description')
            url = request.data.get('url')
            user_id = request.data.get('user_id')
            priority = request.data.get('priority', 'medium')  # 获取优先级参数
            conversation_id = request.data.get('conversation_id')  # 获取会话ID

            # 验证优先级值是否有效
            valid_priorities = ['low', 'medium', 'high']
            if priority not in valid_priorities:
                priority = 'medium'  # 默认为中等优先级

            # 验证数据
            if not description:
                raise ValidationError('缺少必要参数：description')

            if not url:
                raise ValidationError('缺少必要参数：url')

            if not user_id:
                raise ValidationError('缺少必要参数：user_id')

            # 查询用户
            try:
                user = SysUser.objects.get(id=user_id)
            except SysUser.DoesNotExist:
                raise ValidationError('指定的用户不存在')
                
            # 检查用户任务并发限制
            if not TaskUtils.check_user_concurrent_limit(user):
                return ResponseUtil.error(
                    message="您在队列中的任务已满！", 
                    code=status.HTTP_429_TOO_MANY_REQUESTS
                )
                
            # 创建会话和初始记录
            conversation, record = create_conversation_and_record(
                user=user,
                task_type='image_to_image',
                description=description,
                task_id=f"temp_{uuid.uuid4()}",
                image_url="",
                image_list=url,
                conversation_id=conversation_id  # 传递会话ID
            )

            # 生成图像任务
            task_info = ImageService.images_image(
                description=description,
                url=url,
                user=user,
                priority=priority  # 传递优先级
            )
            
            # 更新记录中的任务ID和任务对象
            try:
                task = ComfyUITask.objects.get(task_id=task_info['task_id'])
                record.comfyUI_task = task
                record.image_name = f"{task_info['task_id']}_pending.png"
                record.save()
                logger.info(f"已更新记录的任务ID: {task_info['task_id']}, 记录ID: {record.id}")
            except Exception as e:
                logger.error(f"更新记录任务ID失败: {str(e)}")

            # 添加消息提示
            task_info['message'] = '图生图任务已提交'
            # 添加会话和记录信息
            task_info['conversation_id'] = conversation.id
            task_info['record_id'] = record.id

            return ResponseUtil.success(data=task_info, message=task_info['message'])

        except ValidationError as e:
            return ResponseUtil.error(message=str(e), code=400)
        except BusinessException as e:
            return ResponseUtil.error(message=e.errors, code=400)
        except Exception as e:
            return ResponseUtil.error(message=str(e), code=500)


@method_decorator(csrf_exempt, name='dispatch')
class ImagesTextImagesImageAPIView(APIView):
    """
    家具图片替换任务。
    """
    permission_classes = [AllowAny]

    @extend_schema(
        request=ImagesProductDTO,
        responses={200: None},
    )
    def post(self, request, *args, **kwargs):
        """
        接收图片URL和文本，返回生成的图像任务信息。
        支持优先级设置: low, medium, high（默认为medium）
        """
        try:
            # 获取请求数据
            description = request.data.get('description')
            level = float(request.data.get('level', 0.6))
            white_background_product_url = request.data.get('white_url')
            template_url = request.data.get('template_url')
            mask_url = request.data.get('mask_url')
            user_id = request.data.get('user_id')
            priority = request.data.get('priority', 'medium')  # 获取优先级参数
            conversation_id = request.data.get('conversation_id')  # 获取会话ID

            # 验证优先级值是否有效
            valid_priorities = ['low', 'medium', 'high']
            if priority not in valid_priorities:
                priority = 'medium'  # 默认为中等优先级

            # 验证数据
            if not description:
                raise ValidationError('缺少必要参数：description')

            if not white_background_product_url:
                raise ValidationError('缺少必要参数：white_background_product_url')

            if not template_url:
                raise ValidationError('缺少必要参数：template_url')

            if not mask_url:
                raise ValidationError('缺少必要参数：mask_url')

            if not user_id:
                raise ValidationError('缺少必要参数：user_id')

            # 查询用户
            try:
                user = SysUser.objects.get(id=user_id)
            except SysUser.DoesNotExist:
                raise ValidationError('指定的用户不存在')
                
            # 检查用户任务并发限制
            if not TaskUtils.check_user_concurrent_limit(user):
                return ResponseUtil.error(
                    message="您在队列中的任务已满！", 
                    code=status.HTTP_429_TOO_MANY_REQUESTS
                )
                
            # 创建会话和初始记录
            conversation, record = create_conversation_and_record(
                user=user,
                task_type='product_replace',
                description=description,
                task_id=f"temp_{uuid.uuid4()}",
                image_url="",
                image_list=f"{white_background_product_url},{template_url}",
                conversation_id=conversation_id  # 传递会话ID
            )

            # 生成图像任务
            task_info = ImageService.images_image_image_text(
                description=description,
                level=level,
                white_background_product_url=white_background_product_url,
                template_url=template_url,
                mask_url=mask_url,
                user=user,
                priority=priority
            )
            
            # 更新记录中的任务ID和任务对象
            try:
                task = ComfyUITask.objects.get(task_id=task_info['task_id'])
                record.comfyUI_task = task
                record.image_name = f"{task_info['task_id']}_pending.png"
                record.save()
                logger.info(f"已更新记录的任务ID: {task_info['task_id']}, 记录ID: {record.id}")
            except Exception as e:
                logger.error(f"更新记录任务ID失败: {str(e)}")

            # 添加消息提示
            task_info['message'] = '产品替换任务已提交'
            # 添加会话和记录信息
            task_info['conversation_id'] = conversation.id
            task_info['record_id'] = record.id

            return ResponseUtil.success(data=task_info, message=task_info['message'])

        except ValidationError as e:
            return ResponseUtil.error(message=str(e), code=400)
        except BusinessException as e:
            return ResponseUtil.error(message=e.errors, code=400)
        except Exception as e:
            return ResponseUtil.error(message=str(e), code=500)


@method_decorator(csrf_exempt, name='dispatch')
class ProductReplacementWorkflowAPIView(APIView):
    """
    上线正式版本家具图片替换任务。
    """
    permission_classes = [IsAuthenticated]
    def generate_six_digit_random(self):
        return random.SystemRandom().randint(100000, 999999)

    @extend_schema(
        request=ImagesProductWorkflowDTO,
        responses={200: None},
    )
    def post(self, request, *args, **kwargs):
        """
        接收图片URL和文本，返回生成的图像任务信息。
        支持优先级设置: low, medium, high（默认为medium）
        """
        try:
            # 获取请求数据
            description = request.data.get('description')
            level = float(request.data.get('level', 0.6))
            white_background_product_url = request.data.get('white_url')
            white_mask_url = request.data.get('white_mask_url', "https://qihuaimage.tos-cn-guangzhou.volces.com/f7bd296e-fa3c-49e7-87b8-988ce8deb33a.png")  # 添加默认蒙版URL
            template_url = request.data.get('template_url')
            mask_url = request.data.get('mask_url')
            user_id = request.user.id  # 直接获取用户 ID
            priority = request.data.get('priority', 'medium')  # 获取优先级参数
            conversation_id = request.data.get('conversation_id')  # 获取会话ID
            add_new_data = request.data.get('add_new_data', '')  # 获取新增数据
            # 验证优先级值是否有效
            valid_priorities = ['low', 'medium', 'high']
            if priority not in valid_priorities:
                priority = 'medium'  # 默认为中等优先级

            # 验证数据
            if not description:
                raise ValidationError('缺少必要参数：description')

            if not white_background_product_url:
                raise ValidationError('缺少必要参数：white_background_product_url')

            if not template_url:
                raise ValidationError('缺少必要参数：template_url')

            if not mask_url:
                raise ValidationError('缺少必要参数：mask_url')

            if not user_id:
                raise ValidationError('缺少必要参数：user_id')
            # 随机数字
            seed = self.generate_six_digit_random()

            # 查询用户
            try:
                user = SysUser.objects.get(id=user_id)
            except SysUser.DoesNotExist:
                raise ValidationError('指定的用户不存在')

            # 检查用户任务并发限制
            if not TaskUtils.check_user_concurrent_limit(user):
                return ResponseUtil.error(
                    message="您在队列中的任务已满！", 
                    code=status.HTTP_429_TOO_MANY_REQUESTS
                )

            # 创建会话和初始记录
            conversation, record = create_conversation_and_record(
                user=user,
                task_type='product_replace',
                description=description,
                task_id=f"temp_{uuid.uuid4()}",
                image_url="",
                image_list=f"{white_background_product_url},{template_url}",
                conversation_id=conversation_id  # 传递会话ID
            )

            # 生成图像任务
            task_info = ImageService.product_replacement_workflow(
                description=description,
                level=level,
                seed=seed,
                white_background_product_url=white_background_product_url,
                white_mask_url=white_mask_url,
                template_url=template_url,
                mask_url=mask_url,
                user=user,
                priority=priority,
                add_new_data=add_new_data
            )
            
            # 更新记录中的任务ID和任务对象
            try:
                task = ComfyUITask.objects.get(task_id=task_info['task_id'])
                record.comfyUI_task = task
                record.image_name = f"{task_info['task_id']}_pending.png"
                record.save()
                logger.info(f"已更新记录的任务ID: {task_info['task_id']}, 记录ID: {record.id}")
            except Exception as e:
                logger.error(f"更新记录任务ID失败: {str(e)}")

            # 添加消息提示
            task_info['message'] = '产品替换任务已提交'
            # 添加会话和记录信息
            task_info['conversation_id'] = conversation.id
            task_info['record_id'] = record.id

            return ResponseUtil.success(data=task_info, message=task_info['message'])

        except ValidationError as e:
            return ResponseUtil.error(message=str(e), code=400)
        except BusinessException as e:
            return ResponseUtil.error(message=e.errors, code=400)
        except Exception as e:
            return ResponseUtil.error(message=str(e), code=500)


@method_decorator(csrf_exempt, name='dispatch')
class FineDetailWorkflowAPIView(APIView):
    """
    上线正式版本细节精修。
    """
    permission_classes = [IsAuthenticated]

    def generate_six_digit_random(self):
        return random.SystemRandom().randint(100000, 999999)

    @extend_schema(
        request=ImagesFineDetailWorkflowDTO,
        responses={200: None},
    )
    def post(self, request, *args, **kwargs):
        """
        上线正式版本细节精修。
        接收图片URL和文本，返回生成的图像任务信息。
        支持优先级设置: low, medium, high（默认为medium）
        """
        try:
            # 获取请求数据
            description = request.data.get('description')
            level = float(request.data.get('level', 0.6))
            url = request.data.get('url')
            mask_url = request.data.get('mask_url')
            # user_id = request.data.get('user_id')
            user_id = request.user.id  # 直接获取用户 ID
            priority = request.data.get('priority', 'medium')  # 获取优先级参数
            conversation_id = request.data.get('conversation_id')  # 获取会话ID
            add_new_data = request.data.get('add_new_data', '')  # 获取新增数据
            # 验证优先级值是否有效
            valid_priorities = ['low', 'medium', 'high']
            if priority not in valid_priorities:
                priority = 'medium'  # 默认为中等优先级

            # 验证数据
            if not description:
                raise ValidationError('缺少必要参数：description')

            if not url:
                raise ValidationError('缺少必要参数：url')

            if not mask_url:
                raise ValidationError('缺少必要参数：mask_url')

            if not user_id:
                raise ValidationError('缺少必要参数：user_id')
            # 查询用户
            try:
                user = SysUser.objects.get(id=user_id)
            except SysUser.DoesNotExist:
                raise ValidationError('指定的用户不存在')

            # 检查用户任务并发限制
            if not TaskUtils.check_user_concurrent_limit(user):
                return ResponseUtil.error(
                    message="您在队列中的任务已满！", 
                    code=status.HTTP_429_TOO_MANY_REQUESTS
                )

            # 随机数字
            seed = self.generate_six_digit_random()
            
            # 创建会话和初始记录
            conversation, record = create_conversation_and_record(
                user=user,
                task_type='fine_detail',
                description=description,
                task_id=f"temp_{uuid.uuid4()}",
                image_url="",
                image_list=url,
                conversation_id=conversation_id  # 传递会话ID
            )

            # 生成图像任务
            task_info = ImageService.fine_detail_workflow(
                description=description,
                level=level,
                url=url,
                mask_url=mask_url,
                seed=seed,
                user=user,
                priority=priority,
                add_new_data=add_new_data
            )
            
            # 更新记录中的任务ID和任务对象
            try:
                task = ComfyUITask.objects.get(task_id=task_info['task_id'])
                record.comfyUI_task = task
                record.image_name = f"{task_info['task_id']}_pending.png"
                record.save()
                logger.info(f"已更新记录的任务ID: {task_info['task_id']}, 记录ID: {record.id}")
            except Exception as e:
                logger.error(f"更新记录任务ID失败: {str(e)}")

            # 添加消息提示
            task_info['message'] = '细节精修任务'
            # 添加会话和记录信息
            task_info['conversation_id'] = conversation.id
            task_info['record_id'] = record.id

            return ResponseUtil.success(data=task_info, message=task_info['message'])

        except ValidationError as e:
            return ResponseUtil.error(message=str(e), code=400)
        except BusinessException as e:
            return ResponseUtil.error(message=e.errors, code=400)
        except Exception as e:
            return ResponseUtil.error(message=str(e), code=500)


@method_decorator(csrf_exempt, name='dispatch')
class ProductTextImageAPIView(APIView):
    """
    家具工作流动生成文本图像并返回任务信息。
    """
    permission_classes = [AllowAny]

    @extend_schema(
        request=TextImageDTO,
        responses={200: None},
    )
    def post(self, request, *args, **kwargs):
        try:
            # 使用 DTO 类验证请求参数
            dto = TextImageDTO(data=request.data)
            dto.is_valid(raise_exception=True)  # 如果验证失败，会抛出 ValidationError

            # 获取验证后的数据
            description = dto.validated_data.get('description', '')
            user_id = dto.validated_data['user_id']
            conversation_id = dto.validated_data.get('conversation_id')  # 获取会话ID

            if not description:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER.code, data='', errors="参数不能为空")
            if not user_id:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER.code, data='', errors="参数不能为空")

            # 获取用户信息
            user = get_object_or_404(SysUser, id=user_id)
            
            # 检查用户任务并发限制
            if not TaskUtils.check_user_concurrent_limit(user):
                return ResponseUtil.error(
                    message="您在队列中的任务已满！", 
                    code=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            # 创建会话和初始记录
            conversation, record = create_conversation_and_record(
                user=user,
                task_type='product_text_image',
                description=description,
                task_id=f"temp_{uuid.uuid4()}",
                conversation_id=conversation_id  # 传递会话ID
            )

            # 创建异步任务并立即返回任务信息
            task_info = ImageService.product_text_image(description, user, request)
            
            # 更新记录中的任务ID和任务对象
            try:
                task = ComfyUITask.objects.get(task_id=task_info['task_id'])
                record.comfyUI_task = task
                record.image_name = f"{task_info['task_id']}_pending.png"
                record.save()
                logger.info(f"已更新记录的任务ID: {task_info['task_id']}, 记录ID: {record.id}")
            except Exception as e:
                logger.error(f"更新记录任务ID失败: {str(e)}")

            # 添加会话和记录信息到返回数据
            task_info['conversation_id'] = conversation.id
            task_info['record_id'] = record.id

            return ResponseUtil.success(
                data=task_info,
                message="产品文生图任务已提交"
            )

        except Exception as e:
            logger.error(f"ProductTextImageAPIView 处理失败: {str(e)}")
            return ResponseUtil.error(
                message=f"任务创建失败: {str(e)}"
            )


@method_decorator(csrf_exempt, name='dispatch')
class TextToGenerateImagesAPIView(APIView):
    """
    家具工作流动生成文本图像并返回任务信息。
    """
    permission_classes = [IsAuthenticated]


    def _generate_random_seed(self):
        return random.SystemRandom().randint(1, 2 ** 31 - 1)

    @extend_schema(
        request=TextImageNewDTO,
        responses={200: None},
    )
    def post(self, request, *args, **kwargs):
        try:
            # 使用 DTO 类验证请求参数
            dto = TextImageNewDTO(data=request.data)
            dto.is_valid(raise_exception=True)  # 如果验证失败，会抛出 ValidationError

            # 获取验证后的数据
            description = dto.validated_data.get('description', '')
            # user_id = dto.validated_data['user_id']
            quantity = dto.validated_data['quantity']
            proportion = dto.validated_data.get('proportion', '1024X1024')
            priority = dto.validated_data.get('priority', 'medium')
            conversation_id = dto.validated_data.get('conversation_id')  # 获取会话ID
            add_new_data = dto.validated_data.get('add_new_data', '')   
            match = re.match(r'^(\d+)[xX](\d+)$', proportion)
            width = int(match.group(1))
            height = int(match.group(2))
            seed = self._generate_random_seed()
            user_id = request.user.id  # 直接获取用户 ID

            if not description:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER, data='', errors="参数不能为空")
            if not user_id:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER, data='', errors="参数不能为空")
            if not proportion:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER, data='', errors="参数不能为空")
            if not quantity:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER, data='', errors="参数不能为空")

            # 获取用户信息
            user = get_object_or_404(SysUser, id=user_id)
            
            # 检查用户任务并发限制
            if not TaskUtils.check_user_concurrent_limit(user):
                return ResponseUtil.error(
                    message="您在队列中的任务已满！", 
                    code=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            # 创建会话和初始记录
            conversation, record = create_conversation_and_record(
                user=user,
                task_type='text_to_image',
                description=description,
                task_id=f"temp_{uuid.uuid4()}",
                conversation_id=conversation_id  # 传递会话ID
            )

            # 创建异步任务并立即返回任务信息
            task_info = ImageService.text_to_generate_images(description, height, width, seed, quantity, user, priority, add_new_data)
            
            # 更新记录中的任务ID和任务对象
            try:
                task = ComfyUITask.objects.get(task_id=task_info['task_id'])
                record.comfyUI_task = task
                record.image_name = f"{task_info['task_id']}_pending.png"
                record.save()
                logger.info(f"已更新记录的任务ID: {task_info['task_id']}, 记录ID: {record.id}")
            except Exception as e:
                logger.error(f"更新记录任务ID失败: {str(e)}")
                
            # 添加会话和记录信息到返回数据
            task_info['conversation_id'] = conversation.id
            task_info['record_id'] = record.id

            return ResponseUtil.success(
                data=task_info,
                message="上线文生图任务已提交"
            )

        except Exception as e:
            logger.error(f"TextToGenerateImagesAPIView 处理失败: {str(e)}")
            return ResponseUtil.error(
                message=f"任务创建失败: {str(e)}"
            )


@method_decorator(csrf_exempt, name='dispatch')
class ImagesImageClueAPIView(APIView):
    """
    图片线索生成任务。
    """
    permission_classes = [AllowAny]

    @extend_schema(
        request=ImagesClueImageDTO,
        responses={200: None},
    )
    def post(self, request, *args, **kwargs):
        try:
            # 使用 DTO 类验证请求参数
            dto = ImagesClueImageDTO(data=request.data)
            dto.is_valid(raise_exception=True)  # 如果验证失败，会抛出 ValidationError

            # 获取验证后的数据
            url = dto.validated_data.get('url', '')  # 这里应该是文件对象
            description = dto.validated_data.get('description', '')
            # user_id = dto.validated_data['user_id']
            user_id = request.user.id  # 直接获取用户 ID
            conversation_id = dto.validated_data.get('conversation_id')  # 获取会话ID
            add_new_data = dto.validated_data.get('add_new_data', '')  # 获取新增数据

            if not url:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER.code, data='', errors="参数不能为空")
            if not description:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER.code, data='', errors="参数不能为空")
            if not user_id:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER.code, data='', errors="参数不能为空")

            # 获取用户信息
            user = get_object_or_404(SysUser, id=user_id)
            
            # 检查用户任务并发限制
            if not TaskUtils.check_user_concurrent_limit(user):
                return ResponseUtil.error(
                    message="您在队列中的任务已满！", 
                    code=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            # 创建会话和初始记录
            conversation, record = create_conversation_and_record(
                user=user,
                task_type='clue_product',
                description=description,
                task_id=f"temp_{uuid.uuid4()}",
                image_url="",
                image_list=url,
                conversation_id=conversation_id  # 传递会话ID
            )

            # 创建异步任务并立即返回任务信息
            task_info = ImageService.images_image_clue(description, url, user, request, add_new_data)
            
            # 更新记录中的任务ID和任务对象
            try:
                task = ComfyUITask.objects.get(task_id=task_info['task_id'])
                record.comfyUI_task = task
                record.image_name = f"{task_info['task_id']}_pending.png"
                record.save()
                logger.info(f"已更新记录的任务ID: {task_info['task_id']}, 记录ID: {record.id}")
            except Exception as e:
                logger.error(f"更新记录任务ID失败: {str(e)}")
                
            # 添加会话和记录信息到返回数据
            task_info['conversation_id'] = conversation.id
            task_info['record_id'] = record.id

            return ResponseUtil.success(
                data=task_info,
                message="图片线索生成任务已提交"
            )

        except Exception as e:
            logger.error(f"ImagesClueImageAPIView 处理失败: {str(e)}")
            return ResponseUtil.error(
                message=f"任务创建失败: {str(e)}"
            )


@method_decorator(csrf_exempt, name='dispatch')
class ImagesClueImageAPIView(APIView):
    """
    线索图片生成任务。
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ImagesClueImageDTO,
        responses={200: None},
    )
    def post(self, request, *args, **kwargs):
        try:

            # 使用 DTO 类验证请求参数
            dto = ImagesClueImageDTO(data=request.data)
            dto.is_valid(raise_exception=True)  # 如果验证失败，会抛出 ValidationError

            # 获取验证后的数据
            url = dto.validated_data.get('url', '')  # 这里应该是文件对象
            description = dto.validated_data.get('description', '')
            # user_id = dto.validated_data['user_id']
            user_id = request.user.id  # 直接获取用户 ID
            conversation_id = dto.validated_data.get('conversation_id')  # 获取会话ID
            add_new_data = dto.validated_data.get('add_new_data', '')  # 获取新增数据

            if not url:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER.code, data='', errors="参数不能为空")
            if not description:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER.code, data='', errors="参数不能为空")
            if not user_id:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER.code, data='', errors="参数不能为空")

            # 获取用户信息
            user = get_object_or_404(SysUser, id=user_id)
            
            # 检查用户任务并发限制
            if not TaskUtils.check_user_concurrent_limit(user):
                return ResponseUtil.error(
                    message="您在队列中的任务已满！", 
                    code=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            # 创建会话和初始记录
            conversation, record = create_conversation_and_record(
                user=user,
                task_type='clue_product',
                description=description,
                task_id=f"temp_{uuid.uuid4()}",
                image_url="",
                image_list=url,
                conversation_id=conversation_id  # 传递会话ID
            )

            # 创建异步任务并立即返回任务信息
            task_info = ImageService.images_clue_image(description, url, user, request, add_new_data)
            
            # 更新记录中的任务ID和任务对象
            try:
                task = ComfyUITask.objects.get(task_id=task_info['task_id'])
                record.comfyUI_task = task
                record.image_name = f"{task_info['task_id']}_pending.png"
                record.save()
                logger.info(f"已更新记录的任务ID: {task_info['task_id']}, 记录ID: {record.id}")
            except Exception as e:
                logger.error(f"更新记录任务ID失败: {str(e)}")
                
            # 添加会话和记录信息到返回数据
            task_info['conversation_id'] = conversation.id
            task_info['record_id'] = record.id

            return ResponseUtil.success(
                data=task_info,
                message="线索图片生成任务已提交"
            )

        except Exception as e:
            logger.error(f"ImagesClueImageAPIView 处理失败: {str(e)}")
            return ResponseUtil.error(
                message=f"任务创建失败: {str(e)}"
            )


@method_decorator(csrf_exempt, name='dispatch')
class WhiteBackgroundAPIView(APIView):
    """
    user图像生成白底图像并返回任务信息。
    """
    # permission_classes = [AllowAny]
    permission_classes = [IsAuthenticated]


    @extend_schema(
        request=WhiteBackgroundImageDTO,
        responses={200: None},
    )
    def post(self, request, *args, **kwargs):
        try:
            # 使用 DTO 类验证请求参数
            dto = WhiteBackgroundImageDTO(data=request.data)
            dto.is_valid(raise_exception=True)  # 如果验证失败，会抛出 ValidationError

            # 获取验证后的数据
            url = dto.validated_data.get('url', '')  # 这里应该是文件对象
            description = dto.validated_data.get('description', 'White')
            # user_id = dto.validated_data['user_id']
            user_id = request.user.id  # 直接获取用户 ID
            conversation_id = dto.validated_data.get('conversation_id')  # 获取会话ID
            add_new_data = dto.validated_data.get('add_new_data', '')  # 获取新增数据

            if not url:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER, data='', errors="参数不能为空")
            if not description:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER, data='', errors="参数不能为空")
            if not user_id:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER, data='', errors="参数不能为空")

            # 获取用户信息
            user = get_object_or_404(SysUser, id=user_id)
            
            # 检查用户任务并发限制
            if not TaskUtils.check_user_concurrent_limit(user):
                return ResponseUtil.error(
                    message="您在队列中的任务已满！", 
                    code=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            # 创建会话和初始记录
            conversation, record = create_conversation_and_record(
                user=user,
                task_type='white_background',
                description=description,
                task_id=f"temp_{uuid.uuid4()}",
                image_url="",
                image_list=url,
                conversation_id=conversation_id  # 传递会话ID
            )

            # 创建异步任务并立即返回任务信息
            task_info = ImageService.images_white_background(description, url, user, add_new_data)
            
            # 更新记录中的任务ID和任务对象
            try:
                task = ComfyUITask.objects.get(task_id=task_info['task_id'])
                record.comfyUI_task = task
                record.image_name = f"{task_info['task_id']}_pending.png"
                record.save()
                logger.info(f"已更新记录的任务ID: {task_info['task_id']}, 记录ID: {record.id}")
            except Exception as e:
                logger.error(f"更新记录任务ID失败: {str(e)}")
                
            # 添加会话和记录信息到返回数据
            task_info['conversation_id'] = conversation.id
            task_info['record_id'] = record.id

            return ResponseUtil.success(
                data=task_info,
                message="白底图生成任务已提交"
            )

        except Exception as e:
            logger.error(f"WhiteBackgroundAPIView 处理失败: {str(e)}")
            return ResponseUtil.error(
                message=f"任务创建失败: {str(e)}"
            )


@method_decorator(csrf_exempt, name='dispatch')
class TextToGenerateImagesModelAPIView(APIView):
    """
    模型修改类的文生图
    """
    permission_classes = [IsAuthenticated]


    def _generate_random_seed(self):
        return random.SystemRandom().randint(1, 2 ** 31 - 1)

    @extend_schema(
        request=TextImageNewModelDTO,
        responses={200: None},
    )
    def post(self, request, *args, **kwargs):
        try:
            # 使用 DTO 类验证请求参数
            dto = TextImageNewModelDTO(data=request.data)
            dto.is_valid(raise_exception=True)  # 如果验证失败，会抛出 ValidationError

            # 获取验证后的数据
            description = dto.validated_data.get('description', '')
            # user_id = dto.validated_data['user_id']
            quantity = dto.validated_data['quantity']
            model = dto.validated_data.get('model', '')
            proportion = dto.validated_data.get('proportion', '1024X1024')
            priority = dto.validated_data.get('priority', 'medium')
            conversation_id = dto.validated_data.get('conversation_id')  # 获取会话ID
            add_new_data = dto.validated_data.get('add_new_data', '')
            match = re.match(r'^(\d+)[xX](\d+)$', proportion)
            width = int(match.group(1))
            height = int(match.group(2))
            seed = self._generate_random_seed()
            user_id = request.user.id  # 直接获取用户 ID

            if not description:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER, data='', errors="参数不能为空")
            if not user_id:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER, data='', errors="参数不能为空")
            if not proportion:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER, data='', errors="参数不能为空")
            if not quantity:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER, data='', errors="参数不能为空")
            if not model:
                raise BusinessException(error_code=ErrorCode.NOT_PARAMETER, data='', errors="参数不能为空")

            # 获取用户信息
            user = get_object_or_404(SysUser, id=user_id)
            
            # 检查用户任务并发限制
            if not TaskUtils.check_user_concurrent_limit(user):
                return ResponseUtil.error(
                    message="您在队列中的任务已满！", 
                    code=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            # 创建会话和初始记录
            conversation, record = create_conversation_and_record(
                user=user,
                task_type='text_to_image',
                description=f"{description} (模型: {model})",
                task_id=f"temp_{uuid.uuid4()}",
                conversation_id=conversation_id  # 传递会话ID
            )

            # 创建异步任务并立即返回任务信息
            task_info = ImageService.text_to_generate_images_new(description, height, width, seed, quantity, model, user, priority, add_new_data)
            
            # 更新记录中的任务ID和任务对象
            try:
                task = ComfyUITask.objects.get(task_id=task_info['task_id'])
                record.comfyUI_task = task
                record.image_name = f"{task_info['task_id']}_pending.png"
                record.save()
                logger.info(f"已更新记录的任务ID: {task_info['task_id']}, 记录ID: {record.id}")
            except Exception as e:
                logger.error(f"更新记录任务ID失败: {str(e)}")
                
            # 添加会话和记录信息到返回数据
            task_info['conversation_id'] = conversation.id
            task_info['record_id'] = record.id

            return ResponseUtil.success(
                data=task_info,
                message="模型修改文生图任务已提交"
            )

        except Exception as e:
            logger.error(f"TextToGenerateImagesAPIView 处理失败: {str(e)}")
            return ResponseUtil.error(
                message=f"任务创建失败: {str(e)}"
            )


@method_decorator(csrf_exempt, name='dispatch')
class MultiImageToImageView(APIView):
    """
    多图生图API - 支持1到5张参考图片的图像生成
    根据输入图片数量自动选择不同的工作流程
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


    def _generate_random_seed(self):
        return random.SystemRandom().randint(1, 2 ** 31 - 1)
    
    @extend_schema(
        request=MultiImageToImageDTO,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'task_id': {'type': 'string'},
                    'status': {'type': 'string'},
                    'task_type': {'type': 'string'},
                    'image_count': {'type': 'integer'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'}
                }
            }
        },
        description='基于1-5张参考图片生成新图片，系统会根据参考图片数量自动选择工作流'
    )
    def post(self, request, *args, **kwargs):
        try:
            # 使用DTO类验证请求参数
            dto = MultiImageToImageDTO(data=request.data)
            dto.is_valid(raise_exception=True)
            
            # 获取验证后的数据
            validated_data = dto.validated_data
            description = validated_data.get('description')
            image_urls = validated_data.get('image_urls')
            seed = validated_data.get('seed')  # 不提供默认值，允许为None
            quantity = validated_data.get('quantity', 1)
            height = validated_data.get('height', 1024)
            width = validated_data.get('width', 1024)
            priority = validated_data.get('priority', 'medium')
            conversation_id = validated_data.get('conversation_id')  # 获取会话ID
            add_new_data = validated_data.get('add_new_data', '')  # 获取新增数据
            # 获取当前用户
            user = request.user
            
            # 检查用户任务并发限制
            if not TaskUtils.check_user_concurrent_limit(user):
                return ResponseUtil.error(
                    message="您在队列中的任务已满！", 
                    code=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            # 如果没有提供seed，生成随机种子
            if seed is None:
                seed = self._generate_random_seed()
                logger.info(f"使用自动生成的随机种子: {seed}")
            
            # 根据输入参数决定走哪个流程
            if image_urls and len(image_urls) > 0:
                # 有参考图片，走图生图流程
                logger.info(f"执行图生图流程，参考图片数量: {len(image_urls)}")
                
                # 创建会话和初始记录
                conversation, record = create_conversation_and_record(
                    user=user,
                    task_type='multi_image_to_image',
                    description=description,
                    task_id=f"temp_{uuid.uuid4()}",
                    image_url="",
                    image_list=",".join(image_urls),
                    conversation_id=conversation_id  # 传递会话ID
                )
                
                task_info = ImageService.multi_images_to_image(
                    description=description,
                    image_urls=image_urls,
                    seed=seed,
                    quantity=quantity,
                    height=height,
                    width=width,
                    user=user,
                    priority=priority,
                    add_new_data=add_new_data
                )
                generation_type = "image_to_image"
                message = f"已创建图生图任务，处理 {len(image_urls)} 张参考图片"
            else:
                # 无参考图片，走文生图流程 
                logger.info("执行文生图流程")
                
                # 创建会话和初始记录
                conversation, record = create_conversation_and_record(
                    user=user,
                    task_type='text_to_image',
                    description=description,
                    task_id=f"temp_{uuid.uuid4()}",
                    conversation_id=conversation_id  # 传递会话ID
                )
                
                task_info = ImageService.text_to_generate_images(
                    description=description,
                    height=height,
                    width=width,
                    seed=seed,
                    quantity=quantity,
                    user=user,
                    priority=priority,
                    add_new_data=add_new_data
                )
                generation_type = "text_to_image"
                message = "已创建文生图任务"
            
            # 更新记录中的任务ID和任务对象
            try:
                task = ComfyUITask.objects.get(task_id=task_info['task_id'])
                record.comfyUI_task = task
                record.image_name = f"{task_info['task_id']}_pending.png"
                record.save()
                logger.info(f"已更新记录的任务ID: {task_info['task_id']}, 记录ID: {record.id}")
            except Exception as e:
                logger.error(f"更新记录任务ID失败: {str(e)}")
            
            # 添加生成类型信息到返回结果
            task_info['generation_type'] = generation_type
            # 添加会话和记录信息到返回数据
            task_info['conversation_id'] = conversation.id
            task_info['record_id'] = record.id
            
            # 返回成功响应
            return ResponseUtil.success(
                data=task_info,
                message=message
            )
            
        except serializers.ValidationError as ve:
            # 处理验证错误
            logger.warning(f"多图生图参数验证失败: {str(ve)}")
            return ResponseUtil.error(
                message=f"参数验证失败: {str(ve)}",
                code=status.HTTP_400_BAD_REQUEST
            )
        except BusinessException as be:
            # 处理业务异常
            logger.error(f"创建多图生图任务失败，业务异常: {be.errors}")
            return ResponseUtil.error(
                message=be.errors,
                code=be.error_code if hasattr(be, 'error_code') else status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # 处理其他异常
            logger.error(f"创建多图生图任务失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                message=f"创建多图生图任务失败: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class CombinedImageGenerationView(APIView):
    """
    融合式图像生成API - 根据输入参数自动选择文生图或图生图流程
    - 当提供image_urls时走图生图流程
    - 当仅提供description时走文生图流程
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def _generate_random_seed(self):
        """生成随机种子，最大16位数"""
        return random.SystemRandom().randint(1, 9999999999999999)
    
    @extend_schema(
        request=CombinedImageGenerationDTO,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'task_id': {'type': 'string'},
                    'status_url': {'type': 'string'},
                    'cancel_url': {'type': 'string'},
                    'generation_type': {'type': 'string'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'}
                }
            }
        },
        description='智能图像生成API：当提供image_urls时执行图生图，仅提供description时执行文生图'
    )
    def post(self, request, *args, **kwargs):
        try:
            # 使用DTO类验证请求参数
            dto = CombinedImageGenerationDTO(data=request.data)
            dto.is_valid(raise_exception=True)
            
            # 获取验证后的数据
            validated_data = dto.validated_data
            description = validated_data.get('description')
            image_urls = validated_data.get('image_urls', [])
            seed = validated_data.get('seed')  # 允许为None，会自动生成随机种子
            quantity = validated_data.get('quantity', 1)
            height = validated_data.get('height', 1024)
            width = validated_data.get('width', 1024)
            priority = validated_data.get('priority', 'medium')
            conversation_id = validated_data.get('conversation_id')  # 获取会话ID
            add_new_data = validated_data.get('add_new_data', '')  # 获取新增数据
            # 获取当前用户
            user = request.user
            
            # 检查用户任务并发限制
            if not TaskUtils.check_user_concurrent_limit(user):
                return ResponseUtil.error(
                    message="您在队列中的任务已满！", 
                    code=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            # 如果没有提供seed，生成随机种子
            if seed is None:
                seed = self._generate_random_seed()
                logger.info(f"使用自动生成的随机种子: {seed}")
            
            # 根据输入参数决定走哪个流程
            if image_urls and len(image_urls) > 0:
                # 有参考图片，走图生图流程
                logger.info(f"执行图生图流程，参考图片数量: {len(image_urls)}")
                
                # 创建会话和初始记录
                conversation, record = create_conversation_and_record(
                    user=user,
                    task_type='multi_image_to_image',
                    description=description,
                    task_id=f"temp_{uuid.uuid4()}",
                    image_url="",
                    image_list=",".join(image_urls),
                    conversation_id=conversation_id  # 传递会话ID
                )
                
                task_info = ImageService.multi_images_to_image(
                    description=description,
                    image_urls=image_urls,
                    seed=seed,
                    quantity=quantity,
                    height=height,
                    width=width,
                    user=user,
                    priority=priority,
                    add_new_data=add_new_data
                )
                generation_type = "image_to_image"
                message = f"已创建图生图任务，处理 {len(image_urls)} 张参考图片"
            else:
                # 无参考图片，走文生图流程 
                logger.info("执行文生图流程")
                
                # 创建会话和初始记录
                conversation, record = create_conversation_and_record(
                    user=user,
                    task_type='text_to_image',
                    description=description,
                    task_id=f"temp_{uuid.uuid4()}",
                    conversation_id=conversation_id  # 传递会话ID
                )
                
                task_info = ImageService.text_to_generate_images(
                    description=description,
                    height=height,
                    width=width,
                    seed=seed,
                    quantity=quantity,
                    user=user,
                    priority=priority,
                    add_new_data=add_new_data
                )
                generation_type = "text_to_image"
                message = "已创建文生图任务"
            
            # 更新记录中的任务ID和任务对象
            try:
                task = ComfyUITask.objects.get(task_id=task_info['task_id'])
                record.comfyUI_task = task
                record.image_name = f"{task_info['task_id']}_pending.png"
                record.save()
                logger.info(f"已更新记录的任务ID: {task_info['task_id']}, 记录ID: {record.id}")
            except Exception as e:
                logger.error(f"更新记录任务ID失败: {str(e)}")

            
            # 添加生成类型信息到返回结果
            task_info['generation_type'] = generation_type
            # 添加会话和记录信息到返回数据
            task_info['conversation_id'] = conversation.id
            task_info['record_id'] = record.id
            
            # 返回成功响应
            return ResponseUtil.success(
                data=task_info,
                message=message
            )
            
        except serializers.ValidationError as ve:
            # 处理验证错误
            logger.warning(f"参数验证失败: {str(ve)}")
            return ResponseUtil.error(
                message=f"参数验证失败: {str(ve)}",
                code=status.HTTP_400_BAD_REQUEST
            )
        except BusinessException as be:
            # 处理业务异常
            logger.error(f"创建图像生成任务失败，业务异常: {be.errors}")
            return ResponseUtil.error(
                message=be.errors,
                code=be.error_code if hasattr(be, 'error_code') else status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # 处理其他异常
            logger.error(f"创建图像生成任务失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(
                message=f"创建图像生成任务失败: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class UserTaskListAPIView(APIView):
    """
    获取用户任务列表
    """
    permission_classes = [IsAuthenticated]
    
    class TaskPagination(PageNumberPagination):
        page_size = 10
        page_size_query_param = 'page_size'
        max_page_size = 100
    
    def get(self, request):
        try:
            user = request.user
            
            # 获取查询参数
            status_filter = request.query_params.get('status', None)
            task_type_filter = request.query_params.get('task_type', None)
            
            # 构建查询条件
            query = Q(user=user)
            if status_filter:
                query &= Q(status=status_filter)
            if task_type_filter:
                query &= Q(task_type=task_type_filter)
            
            # 获取任务列表
            tasks = ComfyUITask.objects.filter(query).order_by('-created_at')
            
            # 分页
            paginator = self.TaskPagination()
            paginated_tasks = paginator.paginate_queryset(tasks, request)
            
            # 格式化任务数据
            task_list = []
            for task in paginated_tasks:
                task_data = {
                    'task_id': task.task_id,
                    'task_type': task.task_type,
                    'status': task.status,
                    'priority': task.priority,
                    'input': task.input_data,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                    'error_message': task.error_message,
                    'progress': task.progress,
                    'queue_position': task.queue_position,
                }
                
                # 添加输出数据（如果有）
                if task.output_data and task.status != 'failed':
                    task_data['output_data'] = task.output_data
                
                task_list.append(task_data)
            
            # 返回分页结果
            return paginator.get_paginated_response({
                'tasks': task_list,
                'total_count': tasks.count(),
                'pending_count': tasks.filter(status='pending').count(),
                'processing_count': tasks.filter(status='processing').count(),
                'completed_count': tasks.filter(status='completed').count(),
                'failed_count': tasks.filter(status='failed').count(),
                'cancelled_count': tasks.filter(status='cancelled').count(),
            })
            
        except Exception as e:
            return ResponseUtil.error(message=str(e), code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class RetryTaskAPIView(APIView):
    """
    重新运行任务（将原任务输入提取出来创建新任务并排队）
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, task_id):
        try:
            user = request.user
            
            # 检查任务是否存在且属于当前用户
            task = ComfyUITask.objects.filter(task_id=task_id, user=user).first()
            if not task:
                return ResponseUtil.error(message="任务不存在或不属于当前用户", code=status.HTTP_404_NOT_FOUND)
            
            # 检查任务状态是否为失败或已完成
            if task.status not in ['failed', 'completed', 'cancelled']:
                return ResponseUtil.error(message="只能重新运行失败、已完成或已取消的任务", code=status.HTTP_400_BAD_REQUEST)
            
            # Check user concurrent task limit
            if not TaskUtils.check_user_concurrent_limit(user):
                return ResponseUtil.error(message="您在队列中的任务已满！", code=status.HTTP_429_TOO_MANY_REQUESTS)
            

            # Extract input data and task type from the original task
            input_data = task.input_data if task.input_data else {}
            task_type = task.task_type
            original_conversation_id = None
            original_image_list = "" # Variable to store image_list from original record

            # Try to find an associated record to get the conversation ID and image_list
            existing_records = ImageUploadRecord.objects.filter(comfyUI_task=task)
            if existing_records.exists():
                 original_conversation_id = existing_records[0].conversation_id
                 # Get image_list from the original record if available
                 if existing_records[0].image_list:
                     original_image_list = existing_records[0].image_list
                 logger.info(f"Found existing record {existing_records[0].id} for task {task_id}. Original conversation ID: {original_conversation_id}, Original image_list: {original_image_list})")

            # Determine the image_list for the new record: prioritize original record's image_list, then input_data
            new_record_image_list = original_image_list
            if not new_record_image_list:
                 # Fallback to checking input_data if original record didn't have image_list
                 new_record_image_list = input_data.get('image_list', input_data.get('url', input_data.get('image_urls', [])))
                 if isinstance(new_record_image_list, list):
                     new_record_image_list = ",".join(new_record_image_list)
                 logger.info(f"Original record image_list was empty, using input_data. Result: {new_record_image_list}")
            else:
                 logger.info(f"Using image_list from original record: {new_record_image_list}")


            # Generate a new temporary task ID for the initial record creation
            new_temp_task_id = f"temp_{uuid.uuid4()}"

            # Create a new conversation and initial record for the new task
            # Use the original conversation if found, otherwise a new one will be created
            conversation, record = create_conversation_and_record(
                user=user,
                task_type=task_type,
                description=input_data.get('description', f"重试任务-{task_id}"),
                task_id=new_temp_task_id, # Use a temp ID initially
                image_url="", # This will be updated after the new task completes
                image_list=new_record_image_list, # Pass the determined image_list
                conversation_id=original_conversation_id # Pass the original conversation ID
            )
            logger.info(f"为重试任务创建新会话: {conversation.id} 和新记录: {record.id} with image_list: {new_record_image_list})")


            # Call the appropriate ImageService method based on task_type
            task_info = {}
            # Common parameters passed to most workflows
            common_params = {
                'user': user,
                'priority': input_data.get('priority', 'medium'), # Use original priority or default
                'add_new_data': input_data.get('metadata', {}).get('add_new_data', '') # Pass through add_new_data from metadata
            }

            # Generate a new random seed for all retried tasks
            if hasattr(ImageService, '_generate_random_seed'):
                common_params['seed'] = ImageService._generate_random_seed()
                logger.info(f"Generated new random seed for retried task: {common_params['seed']}")
            else:
                common_params['seed'] = random.SystemRandom().randint(1, 2 ** 31 - 1)
                logger.info(f"Generated new random seed using SystemRandom: {common_params['seed']}")

            # Add seed if present in original input or generate a new one if needed by the workflow
            # Check if the ImageService has a seed generation method and if seed wasn't in the original input
            if 'seed' in input_data and input_data['seed'] is not None:
                common_params['seed'] = input_data['seed']
            # Note: ImageService._generate_random_seed is an internal method,
            # calling it directly here might break if its name changes or it becomes truly private.
            # A safer approach would be to have a public method in ImageService for seed generation or
            # handle seed generation within the specific workflow methods.
            # For now, I'll keep the original logic but note the potential fragility.


            if task_type == 'wide_picture':
                 # Extract values from prompt_updates if available
                 prompt_updates = input_data.get('prompt_updates', {})
                 node_134 = prompt_updates.get('134', {}).get('inputs', {})
                 
                 # Use values from prompt_updates if available, otherwise use defaults from input_data
                 left = node_134.get('left', input_data.get('left', 0))
                 top = node_134.get('top', input_data.get('top', 0))
                 right = node_134.get('right', input_data.get('right', 0))
                 bottom = node_134.get('bottom', input_data.get('bottom', 0))

                 # Ensure seed is handled for this specific workflow if not in input_data
                 if 'seed' not in common_params and hasattr(ImageService, '_generate_random_seed'):
                     common_params['seed'] = ImageService._generate_random_seed()
                     logger.info(f"Generated new random seed for retried wide_picture task: {common_params['seed']}")

                 task_info = ImageService.wide_picture_workflow(
                     description=input_data.get('description', ''),
                     url=input_data.get('url'),
                     left=left,
                     top=top,
                     right=right,
                     bottom=bottom,
                     seed=random.SystemRandom().randint(1, 2 ** 31 - 1), # Use new random seed
                     user=common_params['user'],
                     priority=common_params['priority'],
                     add_new_data=common_params['add_new_data']
                 )
            elif task_type == 'internal_supplementation':
                 # Ensure seed is handled for this specific workflow if not in input_data
                 if 'seed' not in common_params and hasattr(ImageService, '_generate_random_seed'):
                      common_params['seed'] = ImageService._generate_random_seed()
                      logger.info(f"Generated new random seed for retried internal_supplementation task: {common_params['seed']}")

                 task_info = ImageService.internal_supplementation_workflow(
                     description=input_data.get('description', ''),
                     url=input_data.get('url'),
                     mask_url=input_data.get('mask_url'),
                     seed=random.SystemRandom().randint(1, 2 ** 31 - 1), # Use new random seed
                     user=common_params['user'],
                     priority=common_params['priority'],
                     add_new_data=common_params['add_new_data']
                 )
            elif task_type == 'internal_supplementation_and_removal':
                 # Ensure seed is handled for this specific workflow if not in input_data
                 if 'seed' not in common_params and hasattr(ImageService, '_generate_random_seed'):
                      common_params['seed'] = ImageService._generate_random_seed()
                      logger.info(f"Generated new random seed for retried internal_supplementation_and_removal task: {common_params['seed']}")

                 task_info = ImageService.internal_supplementation_and_removal_workflow(
                     url=input_data.get('url'),
                     mask_url=input_data.get('mask_url'),
                     seed=random.SystemRandom().randint(1, 2 ** 31 - 1), # Use new random seed
                     user=common_params['user'],
                     priority=common_params['priority'],
                     add_new_data=common_params['add_new_data']
                 )
            elif task_type == 'complete_redrawing':
                 # Ensure seed is handled for this specific workflow if not in input_data
                 if 'seed' not in common_params and hasattr(ImageService, '_generate_random_seed'):
                      common_params['seed'] = ImageService._generate_random_seed()
                      logger.info(f"Generated new random seed for retried complete_redrawing task: {common_params['seed']}")

                 task_info = ImageService.xl_wholeimagefix_complete_redrawing_and_refinement_of_the_entire_image_workflow(
                     description=input_data.get('description', ''),
                     level=input_data.get('level', 0.6),
                     url=input_data.get('url'),
                     seed=random.SystemRandom().randint(1, 2 ** 31 - 1), # Use new random seed
                     user=common_params['user'],
                     priority=common_params['priority'],
                     add_new_data=common_params['add_new_data']
                 )
            elif task_type == 'image_to_image' or task_type == 'multi_image_to_image': # Both map to multi_images_to_image now
                 # Ensure seed is handled for this specific workflow if not in input_data
                 if 'seed' not in common_params and hasattr(ImageService, '_generate_random_seed'):
                      common_params['seed'] = ImageService._generate_random_seed()
                      logger.info(f"Generated new random seed for retried multi_image_to_image task: {common_params['seed']}")

                 image_urls = input_data.get('image_urls', [input_data.get('url')])
                 task_info = ImageService.multi_images_to_image(
                     description=input_data.get('description', ''),
                     image_urls=[url for url in image_urls if url], # Ensure no None or empty strings
                     quantity=input_data.get('quantity', 1),
                     height=input_data.get('height', 1024),
                     width=input_data.get('width', 1024),
                     seed=random.SystemRandom().randint(1, 2 ** 31 - 1), # Use new random seed
                     user=common_params['user'],
                     priority=common_params['priority'],
                     add_new_data=common_params['add_new_data']
                 )
            elif task_type == 'product_replace': # Maps to product_replacement_workflow
                 # Ensure seed is handled for this specific workflow if not in input_data
                 if 'seed' not in common_params and hasattr(ImageService, '_generate_random_seed'):
                      common_params['seed'] = ImageService._generate_random_seed()
                      logger.info(f"Generated new random seed for retried product_replace task: {common_params['seed']}")

                 task_info = ImageService.product_replacement_workflow(
                    description=input_data.get('description'),
                    level=input_data.get('level', 0.6),
                    seed=random.SystemRandom().randint(1, 2 ** 31 - 1), # Use new random seed
                    white_background_product_url=input_data.get('white_background_product_url', input_data.get('white_url')),
                    white_mask_url=input_data.get('white_mask_url', "https://qihuaimage.tos-cn-guangzhou.volces.com/f7bd296e-fa3c-49e7-87b8-988ce8deb33a.png"),
                    template_url=input_data.get('template_url'),
                    mask_url=input_data.get('mask_url'),
                    user=common_params['user'],
                    priority=common_params['priority'],
                    add_new_data=common_params['add_new_data']
                 )
            elif task_type == 'fine_detail':
                 # Ensure seed is handled for this specific workflow if not in input_data
                 if 'seed' not in common_params and hasattr(ImageService, '_generate_random_seed'):
                      common_params['seed'] = ImageService._generate_random_seed()
                      logger.info(f"Generated new random seed for retried fine_detail task: {common_params['seed']}")

                 task_info = ImageService.fine_detail_workflow(
                     description=input_data.get('description'),
                     level=input_data.get('level', 0.6),
                     url=input_data.get('url'),
                     mask_url=input_data.get('mask_url'),
                     seed=random.SystemRandom().randint(1, 2 ** 31 - 1), # Use new random seed
                     user=common_params['user'],
                     priority=common_params['priority'],
                     add_new_data=common_params['add_new_data']
                 )
            elif task_type == 'clue_product': # Could be images_image_clue or images_clue_image
                 # Ensure seed is handled for this specific workflow if not in input_data
                 if 'seed' not in common_params and hasattr(ImageService, '_generate_random_seed'):
                      common_params['seed'] = ImageService._generate_random_seed()
                      logger.info(f"Generated new random seed for retried clue_product task: {common_params['seed']}")
                 # Assuming images_clue_image is the more recent/standard one
                 task_info = ImageService.images_clue_image(
                     description=input_data.get('description', ''),
                     url=input_data.get('url'),
                     seed=random.SystemRandom().randint(1, 2 ** 31 - 1), # Use new random seed
                     user=common_params['user'],
                     request=request, # Pass request if needed by the service method
                     add_new_data=common_params['add_new_data']
                 )
            elif task_type == 'white_background':
                 # Ensure seed is handled for this specific workflow if not in input_data
                 # White background workflow might not use a seed, so check ImageService method signature
                 # If images_white_background doesn't take a seed, remove it here.
                 # Assuming it might use one for some underlying step, pass if available.
                 if 'seed' not in common_params and hasattr(ImageService, '_generate_random_seed'):
                      common_params['seed'] = ImageService._generate_random_seed()
                      logger.info(f"Generated new random seed for retried white_background task: {common_params['seed']}")

                 # Check the signature of images_white_background in ImageService to see if it accepts seed.
                 # If it does, pass it. If not, remove seed from the call.
                 # Based on the provided code, images_white_background takes (description, url, user, add_new_data).
                 # So, we should NOT pass seed here.
                 task_info = ImageService.images_white_background(
                     description=input_data.get('description', 'White'),
                     url=input_data.get('url'),
                     user=common_params['user'],
                     add_new_data=common_params['add_new_data']
                 )
            elif task_type == 'text_to_image': # Handled by text_to_generate_images or text_to_generate_images_new
                 # Ensure seed is handled for this specific workflow if not in input_data
                 if 'seed' not in common_params and hasattr(ImageService, '_generate_random_seed'):
                      common_params['seed'] = ImageService._generate_random_seed()
                      logger.info(f"Generated new random seed for retried text_to_image task: {common_params['seed']}")

                 # Check if 'model' is present to determine which text_to_image workflow was used
                 if 'model' in input_data and input_data['model']:
                      task_info = ImageService.text_to_generate_images_new(
                         description=input_data.get('description', ''),
                         height=input_data.get('height', 1024),
                         width=input_data.get('width', 1024),
                         seed=random.SystemRandom().randint(1, 2 ** 31 - 1), # Use new random seed
                         quantity=input_data.get('quantity', 1),
                         model=input_data.get('model'),
                         user=common_params['user'],
                         priority=common_params['priority'],
                         add_new_data=common_params['add_new_data']
                      )
                 else:
                     task_info = ImageService.text_to_generate_images(
                         description=input_data.get('description', ''),
                         height=input_data.get('height', 1024),
                         width=input_data.get('width', 1024),
                         seed=random.SystemRandom().randint(1, 2 ** 31 - 1), # Use new random seed
                         quantity=input_data.get('quantity', 1),
                         user=common_params['user'],
                         priority=common_params['priority'],
                         add_new_data=common_params['add_new_data']
                     )
            elif task_type == 'multi_image_to_image':
                 task_info = ImageService.multi_images_to_image(
                     description=input_data.get('description'),
                     image_urls=input_data.get('image_urls', []),
                     seed=random.SystemRandom().randint(1, 2 ** 31 - 1), # Use new random seed
                     quantity=input_data.get('quantity', 1),
                     height=input_data.get('height', 1024),
                     width=input_data.get('width', 1024),
                     user=common_params['user'],
                     priority=common_params['priority'],
                     add_new_data=common_params['add_new_data']
                 )
            else: # Handles unsupported task types
                return ResponseUtil.error(message=f"不支持的任务类型重试: {task_type}", code=status.HTTP_400_BAD_REQUEST)

            # Update the newly created record with the actual task ID
            if task_info and 'task_id' in task_info:
                 try:
                     new_task = ComfyUITask.objects.get(task_id=task_info['task_id'])
                     record.comfyUI_task = new_task
                     record.image_name = f"{new_task.task_id}_pending.png"
                     # Update image_list if it wasn't correctly captured from input_data initially
                     if not record.image_list and ('url' in task_info or ('image_urls' in task_info and task_info['image_urls'])):
                         record.image_list = task_info.get('url', ','.join(task_info.get('image_urls', [])))

                     record.save()
                     logger.info(f"已更新新记录 {record.id} 的任务ID为 {new_task.task_id}")
                 except ComfyUITask.DoesNotExist:
                     logger.error(f"新建任务 {task_info['task_id']} 未找到，无法更新记录 {record.id}")
                 except Exception as e:
                     logger.error(f"更新新记录 {record.id} 的任务ID失败: {str(e)}")
            else:
                logger.error(f"创建新任务失败，task_info 中没有 task_id")


            # Add conversation and record info to the response data
                task_info['conversation_id'] = conversation.id
            task_info['record_id'] = record.id
            
            return ResponseUtil.success(
                data=task_info,
                message="任务已重新提交（创建新任务）"
            )
            
        except Exception as e:
            logger.error(f"重新运行任务失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(message=f"重新运行任务失败: {str(e)}", code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TaskTypeManagementAPIView(APIView):
    """
    任务类型管理API - 提供任务类型的CRUD操作
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        获取任务类型列表
        可选查询参数:
        - active_only: 为true时只返回活跃的任务类型
        - id: 按ID筛选指定任务类型
        - name: 按名称筛选任务类型
        """
        try:
            # 获取查询参数
            active_only = request.query_params.get('active_only', 'false').lower() == 'true'
            type_id = request.query_params.get('id')
            type_name = request.query_params.get('name')
            
            # 构建查询
            query = Q()
            if active_only:
                query &= Q(is_active=True)
            if type_id:
                query &= Q(id=type_id)
            if type_name:
                query &= Q(name__icontains=type_name)
            
            # 执行查询
            task_types = TaskType.objects.filter(query).order_by('priority_order', 'name')
            
            # 转换为JSON格式
            result = []
            for task_type in task_types:
                result.append({
                    'id': task_type.id,
                    'name': task_type.name,
                    'display_name': task_type.display_name,
                    'description': task_type.description,
                    'is_active': task_type.is_active,
                    'handler_name': task_type.handler_name,
                    'config': task_type.config,
                    'priority_order': task_type.priority_order,
                    'created_at': task_type.created_at,
                    'updated_at': task_type.updated_at
                })
            
            return ResponseUtil.success(data=result)
            
        except Exception as e:
            logger.error(f"获取任务类型列表失败: {str(e)}")
            return ResponseUtil.error(message=f"获取任务类型列表失败: {str(e)}")
    
    def post(self, request):
        """
        创建新的任务类型
        请求体参数:
        - name: 任务类型代码（必填）
        - display_name: 显示名称（必填）
        - description: 描述
        - handler_name: 处理器名称，默认为'generic'
        - config: 配置信息
        - is_active: 是否激活，默认为true
        - priority_order: 排序顺序，默认为0
        """
        try:
            # 获取必填参数
            name = request.data.get('name')
            display_name = request.data.get('display_name')
            
            # 检查必填参数
            if not name or not display_name:
                return ResponseUtil.error(
                    message="缺少必填参数: name和display_name",
                    code=ErrorCode.PARAMS_ERROR,
                    httpCode=400
                )
            
            # 检查名称是否已存在
            if TaskType.objects.filter(name=name).exists():
                return ResponseUtil.error(
                    message=f"任务类型名称 '{name}' 已存在",
                    code=ErrorCode.DATA_ALREADY_EXIST,
                    httpCode=400
                )
            
            # 获取可选参数
            description = request.data.get('description')
            handler_name = request.data.get('handler_name', 'generic')
            config = request.data.get('config', {})
            is_active = request.data.get('is_active', True)
            priority_order = request.data.get('priority_order', 0)
            
            # 创建任务类型
            task_type = task_manager.create_task_type(
                name=name,
                display_name=display_name,
                description=description,
                handler_name=handler_name,
                config=config,
                is_active=is_active,
                priority_order=priority_order
            )
            
            # 刷新缓存
            task_manager.load_task_types()
            
            # 返回创建结果
            return ResponseUtil.success(data={
                'id': task_type.id,
                'name': task_type.name,
                'display_name': task_type.display_name,
                'message': '任务类型创建成功'
            })
            
        except Exception as e:
            logger.error(f"创建任务类型失败: {str(e)}")
            return ResponseUtil.error(message=f"创建任务类型失败: {str(e)}")
    
    def put(self, request, type_id=None):
        """
        更新任务类型
        路径参数:
        - type_id: 任务类型ID
        请求体参数:
        - name: 任务类型代码
        - display_name: 显示名称
        - description: 描述
        - handler_name: 处理器名称
        - config: 配置信息
        - is_active: 是否激活
        - priority_order: 排序顺序
        """
        try:
            # 检查ID参数
            if not type_id:
                type_id = request.data.get('id')
            
            if not type_id:
                return ResponseUtil.error(
                    message="缺少必填参数: id或type_id",
                    code=ErrorCode.PARAMS_ERROR,
                    httpCode=400
                )
            
            # 获取任务类型
            task_type = TaskType.objects.filter(id=type_id).first()
            if not task_type:
                return ResponseUtil.error(
                    message=f"任务类型ID {type_id} 不存在",
                    code=ErrorCode.RESOURCE_NOT_FOUND,
                    httpCode=404
                )
            
            # 更新字段
            if 'name' in request.data:
                if TaskType.objects.filter(name=request.data['name']).exclude(id=type_id).exists():
                    return ResponseUtil.error(
                        message=f"任务类型名称 '{request.data['name']}' 已存在",
                        code=ErrorCode.DATA_ALREADY_EXIST,
                        httpCode=400
                    )
                task_type.name = request.data['name']
            
            if 'display_name' in request.data:
                task_type.display_name = request.data['display_name']
            
            if 'description' in request.data:
                task_type.description = request.data['description']
            
            if 'handler_name' in request.data:
                task_type.handler_name = request.data['handler_name']
            
            if 'config' in request.data:
                task_type.config = request.data['config']
            
            if 'is_active' in request.data:
                task_type.is_active = request.data['is_active']
            
            if 'priority_order' in request.data:
                task_type.priority_order = request.data['priority_order']
            
            # 保存并刷新缓存
            task_type.save()
            task_manager.load_task_types()
            
            # 返回更新结果
            return ResponseUtil.success(data={
                'id': task_type.id,
                'name': task_type.name,
                'display_name': task_type.display_name,
                'message': '任务类型更新成功'
            })
            
        except Exception as e:
            logger.error(f"更新任务类型失败: {str(e)}")
            return ResponseUtil.error(message=f"更新任务类型失败: {str(e)}")
    
    def delete(self, request, type_id=None):
        """
        删除任务类型
        路径参数:
        - type_id: 任务类型ID
        """
        try:
            # 检查ID参数
            if not type_id:
                type_id = request.data.get('id')
            
            if not type_id:
                return ResponseUtil.error(
                    message="缺少必填参数: id或type_id",
                    code=ErrorCode.PARAMS_ERROR,
                    httpCode=400
                )
            
            # 获取任务类型
            task_type = TaskType.objects.filter(id=type_id).first()
            if not task_type:
                return ResponseUtil.error(
                    message=f"任务类型ID {type_id} 不存在",
                    code=ErrorCode.RESOURCE_NOT_FOUND,
                    httpCode=404
                )
            
            # 检查是否有关联任务
            if ComfyUITask.objects.filter(task_type=task_type.name).exists():
                return ResponseUtil.error(
                    message=f"任务类型 '{task_type.name}' 有关联任务，无法删除",
                    code=ErrorCode.OPERATION_DENIED,
                    httpCode=400
                )
            
            # 保存任务类型名称用于返回
            type_name = task_type.name
            type_display_name = task_type.display_name
            
            # 删除任务类型
            task_type.delete()
            
            # 刷新缓存
            task_manager.load_task_types()
            
            # 返回删除结果
            return ResponseUtil.success(data={
                'name': type_name,
                'display_name': type_display_name,
                'message': '任务类型删除成功'
            })
            
        except Exception as e:
            logger.error(f"删除任务类型失败: {str(e)}")
            return ResponseUtil.error(message=f"删除任务类型失败: {str(e)}")

