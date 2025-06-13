import logging
from datetime import timedelta
import json
from django.db.models import Count
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import NotFound
from rest_framework.decorators import action

from common.response_utils import ResponseUtil
from templateImage.models import ComfyUITask
from templateImage.queue_service_singleton import queue_service
from templateImage.task_utils import TaskUtils

logger = logging.getLogger(__name__)

class CustomPageNumberPagination(PageNumberPagination):
    """自定义分页类"""
    page_size = 10  # 默认每页数量
    page_size_query_param = 'page_size'  # 允许客户端通过此参数指定每页数量
    max_page_size = 100  # 每页最大数量
    
    def get_paginated_response_data(self, data):
        """返回分页的响应数据"""
        return {
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'current_page': self.page.number,
            'total_pages': self.page.paginator.num_pages,
            'page_size': self.page_size,
            'results': data
        }
    
    def get_next_link(self):
        """
        重写获取下一页链接方法，不使用request.build_absolute_uri
        """
        if not self.page.has_next():
            return None
        page_number = self.page.next_page_number()
        return page_number
    
    def get_previous_link(self):
        """
        重写获取上一页链接方法，不使用request.build_absolute_uri
        """
        if not self.page.has_previous():
            return None
        page_number = self.page.previous_page_number()
        return page_number

class SimpleObj:
    """用于创建简单的模拟请求对象"""
    def __init__(self, query_params):
        self.query_params = query_params

    def build_absolute_uri(self, url):
        """模拟实现build_absolute_uri方法"""
        return url

class QueueAdminAPIView(APIView):
    """
    队列系统后台管理接口
    """
    permission_classes = [IsAuthenticated]  # 需要认证才能访问

    @extend_schema(
        parameters=[
            {
                'name': 'task_type',
                'in': 'query',
                'required': False,
                'type': 'string',
                'description': '按任务类型筛选'
            },
            {
                'name': 'page_size',
                'in': 'query',
                'required': False,
                'type': 'integer',
                'description': '每页显示数量，默认为10'
            },
            {
                'name': 'pending_page',
                'in': 'query',
                'required': False,
                'type': 'integer',
                'description': '待处理任务的页码，默认为1'
            },
            {
                'name': 'processing_page',
                'in': 'query',
                'required': False,
                'type': 'integer',
                'description': '处理中任务的页码，默认为1'
            },
            {
                'name': 'completed_page',
                'in': 'query',
                'required': False,
                'type': 'integer',
                'description': '已完成任务的页码，默认为1'
            }
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'status_stats': {'type': 'array'},
                            'priority_stats': {'type': 'array'},
                            'recent_stats': {'type': 'array'},
                            'queue_tasks': {
                                'type': 'object',
                                'properties': {
                                    'count': {'type': 'integer'},
                                    'next': {'type': 'string', 'nullable': True},
                                    'previous': {'type': 'string', 'nullable': True},
                                    'current_page': {'type': 'integer'},
                                    'total_pages': {'type': 'integer'},
                                    'page_size': {'type': 'integer'},
                                    'results': {'type': 'array'}
                                }
                            },
                            'processing_tasks': {
                                'type': 'object',
                                'properties': {
                                    'count': {'type': 'integer'},
                                    'next': {'type': 'string', 'nullable': True},
                                    'previous': {'type': 'string', 'nullable': True},
                                    'current_page': {'type': 'integer'},
                                    'total_pages': {'type': 'integer'},
                                    'page_size': {'type': 'integer'},
                                    'results': {'type': 'array'}
                                }
                            },
                            'completed_tasks': {
                                'type': 'object',
                                'properties': {
                                    'count': {'type': 'integer'},
                                    'next': {'type': 'string', 'nullable': True},
                                    'previous': {'type': 'string', 'nullable': True},
                                    'current_page': {'type': 'integer'},
                                    'total_pages': {'type': 'integer'},
                                    'page_size': {'type': 'integer'},
                                    'results': {'type': 'array'}
                                }
                            },
                            'system_metrics': {'type': 'object'},
                            'query_params': {'type': 'object'}
                        }
                    }
                }
            }
        },
        description="获取队列系统详细信息，支持分页和按任务类型筛选"
    )
    def get(self, request, task_id=None):
        """
        GET 请求处理
        如果提供了task_id，则获取特定任务的详细信息
        否则获取队列系统的概览信息
        """
        if task_id:
            return self.get_task_detail(request, task_id)
        else:
            return self.get_queue_overview(request)
        
    @extend_schema(
        parameters=[
            {
                'name': 'task_id',
                'in': 'query',
                'required': True,
                'type': 'string',
                'description': '要查询的任务ID'
            }
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string'},
                    'data': {'type': 'object'},
                    'message': {'type': 'string'}
                }
            }
        },
        description="获取特定任务的详细信息"
    )
    def get_task_detail(self, request, task_id):
        """
        获取特定任务的详细信息
        """
        try:
            task = ComfyUITask.objects.filter(task_id=task_id).first()
            if not task:
                return ResponseUtil.error(message=f"任务 {task_id} 不存在", status_code=404)

            # 将任务对象转换为字典
            task_data = {
                'task_id': task.task_id,
                'task_type': task.task_type,
                'status': task.status,
                'priority': task.priority,
                'queue_position': task.queue_position,
                'progress': task.progress,
                'user_id': task.user_id if task.user else None,
                'input_data': task.input_data,
                'output_data': task.output_data,
                'error_message': task.error_message,
                'processing_time': task.processing_time,
                'created_at': task.created_at,
                'started_at': task.started_at,
                'completed_at': task.completed_at,
                'updated_at': task.updated_at,
                'saved_to_cloud': task.saved_to_cloud,
                'auto_save_to_cloud': task.auto_save_to_cloud,
            }

            # 获取任务在Redis队列中的状态（如果可用）
            redis_status = None
            if queue_service.is_redis_available:
                redis_status = TaskUtils.get_task_status(task_id)

            # 构建响应
            response_data = {
                'task': task_data,
                'redis_status': redis_status
            }

            return ResponseUtil.success(data=response_data, message="任务详情获取成功")
        except Exception as e:
            return ResponseUtil.error(message=str(e))

    def get_queue_overview(self, request):
        """
        获取队列系统详细信息
        """
        try:
            # 获取所有任务的状态统计
            status_stats = ComfyUITask.objects.values('status').annotate(
                count=Count('task_id')
            )

            # 获取各优先级的任务数量
            priority_stats = ComfyUITask.objects.filter(
                status='pending'
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

            # 获取当前队列中的任务（按优先级和创建时间排序）
            pending_tasks_query = ComfyUITask.objects.filter(
                status='pending'
            ).order_by(
                'priority',
                'created_at'
            )
            
            # 获取正在处理的任务
            processing_tasks_query = ComfyUITask.objects.filter(
                status='processing'
            ).order_by('-started_at')
            
            # 获取所有已完成的任务
            completed_tasks_query = ComfyUITask.objects.filter(
                status__in=['completed', 'failed', 'cancelled']
            ).order_by('-completed_at')
            
            # 应用分页
            paginator = CustomPageNumberPagination()
            
            # 分页参数
            task_type = request.query_params.get('task_type')
            pending_page = request.query_params.get('pending_page', 1)
            processing_page = request.query_params.get('processing_page', 1)
            completed_page = request.query_params.get('completed_page', 1)
            page_size = request.query_params.get('page_size', paginator.page_size)
            
            # 应用过滤条件
            if task_type:
                pending_tasks_query = pending_tasks_query.filter(task_type=task_type)
                processing_tasks_query = processing_tasks_query.filter(task_type=task_type)
                completed_tasks_query = completed_tasks_query.filter(task_type=task_type)
            
            # 对各个查询进行分页处理
            paginator.page_size = int(page_size)
            
            # 待处理任务分页
            pending_values = pending_tasks_query.values(
                'task_id', 'priority', 'queue_position', 'created_at', 'task_type',
                'user_id', 'input_data', 'progress', 'error_message', 'processing_time',
                'updated_at', 'saved_to_cloud', 'auto_save_to_cloud'
            )
            pending_request = SimpleObj({'page': pending_page, 'page_size': page_size})
            pending_page_result = paginator.paginate_queryset(list(pending_values), pending_request)
            pending_page_data = paginator.get_paginated_response_data(pending_page_result)
            
            # 处理中任务分页
            processing_values = processing_tasks_query.values(
                'task_id', 'priority', 'progress', 'started_at', 'task_type',
                'user_id', 'input_data', 'error_message', 'processing_time',
                'created_at', 'updated_at', 'saved_to_cloud', 'auto_save_to_cloud'
            )
            processing_request = SimpleObj({'page': processing_page, 'page_size': page_size})
            processing_page_result = paginator.paginate_queryset(list(processing_values), processing_request)
            processing_page_data = paginator.get_paginated_response_data(processing_page_result)
            
            # 已完成任务分页
            completed_values = completed_tasks_query.values(
                'task_id', 'status', 'priority', 'progress', 'task_type',
                'user_id', 'input_data', 'output_data', 'error_message',
                'processing_time', 'created_at', 'started_at', 'completed_at',
                'updated_at', 'saved_to_cloud', 'auto_save_to_cloud'
            )
            completed_request = SimpleObj({'page': completed_page, 'page_size': page_size})
            completed_page_result = paginator.paginate_queryset(list(completed_values), completed_request)
            completed_page_data = paginator.get_paginated_response_data(completed_page_result)

            # 获取系统性能指标
            system_metrics = {
                'queue_size': queue_service.get_queue_size(),
                'active_consumers': 1 if queue_service.get_consumer() else 0,
                'redis_available': queue_service.is_redis_available
            }

            # 添加查询参数信息
            query_params = {
                'task_type': task_type,
                'page_size': int(page_size),
            }

            return ResponseUtil.success(data={
                'status_stats': list(status_stats),
                'priority_stats': list(priority_stats),
                'recent_stats': list(recent_stats),
                'queue_tasks': pending_page_data,
                'processing_tasks': processing_page_data,
                'completed_tasks': completed_page_data,
                'system_metrics': system_metrics,
                'query_params': query_params
            }, message="队列信息获取成功！")
        except Exception as e:
            return ResponseUtil.error(message=str(e))

    @extend_schema(
        request={
            'type': 'object',
            'properties': {
                'action': {
                    'type': 'string',
                    'enum': ['cancel_task', 'pause_queue', 'resume_queue', 'clear_queue', 'retry_task'],
                    'description': '要执行的操作'
                },
                'task_id': {
                    'type': 'string',
                    'description': '任务ID（某些操作需要）'
                }
            },
            'required': ['action']
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string'},
                    'message': {'type': 'string'}
                }
            }
        },
        description="执行队列管理操作"
    )
    def post(self, request):
        """
        执行队列管理操作
        """
        try:
            action = request.data.get('action')
            task_id = request.data.get('task_id')

            if not action:
                return Response({
                    'status': 'error',
                    'message': '缺少action参数'
                }, status=400)

            if action == 'cancel_task' and task_id:
                # 取消指定任务
                success = TaskUtils.cancel_task(task_id)
                if success:
                    return Response({
                        'status': 'success',
                        'message': f'任务 {task_id} 已取消'
                    })
                else:
                    return Response({
                        'status': 'error',
                        'message': f'取消任务 {task_id} 失败'
                    }, status=400)

            elif action == 'pause_queue':
                # 暂停队列处理
                queue_service.running = False
                return Response({
                    'status': 'success',
                    'message': '队列已暂停'
                })

            elif action == 'resume_queue':
                # 恢复队列处理
                queue_service.running = True
                if not queue_service.consumer_thread or not queue_service.consumer_thread.is_alive():
                    queue_service.start_consumer()
                return Response({
                    'status': 'success',
                    'message': '队列已恢复'
                })

            elif action == 'clear_queue':
                # 清空等待中的任务
                ComfyUITask.objects.filter(status='pending').update(
                    status='cancelled',
                    completed_at=timezone.now()
                )
                return Response({
                    'status': 'success',
                    'message': '等待中的任务已清空'
                })

            elif action == 'retry_task' and task_id:
                # 重试失败的任务
                task = ComfyUITask.objects.filter(task_id=task_id).first()
                if not task:
                    return Response({
                        'status': 'error',
                        'message': f'任务 {task_id} 不存在'
                    }, status=404)

                if task.status not in ['failed', 'cancelled']:
                    return Response({
                        'status': 'error',
                        'message': '只能重试失败或已取消的任务'
                    }, status=400)

                # 重置任务状态
                task.status = 'pending'
                task.error_message = None
                task.progress = 0
                task.queue_position = None
                task.started_at = None
                task.completed_at = None
                task.save()

                # 重新加入队列
                queue_service.add_task(
                    task_id=task.task_id,
                    task_type=task.task_type,
                    task_data=task.input_data
                )

                return Response({
                    'status': 'success',
                    'message': f'任务 {task_id} 已重新加入队列'
                })

            else:
                return Response({
                    'status': 'error',
                    'message': '无效的操作'
                }, status=400)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=500)

    @extend_schema(
        request={
            'type': 'object',
            'properties': {
                'task_id': {'type': 'string', 'required': True},
                'priority': {
                    'type': 'string',
                    'enum': ['low', 'medium', 'high'],
                    'description': '新的优先级'
                },
                'status': {
                    'type': 'string',
                    'enum': ['pending', 'processing', 'completed', 'failed', 'cancelled'],
                    'description': '新的状态'
                }
            },
            'required': ['task_id']
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string'},
                    'message': {'type': 'string'}
                }
            }
        },
        description="更新任务优先级或状态"
    )
    def put(self, request):
        """
        更新任务优先级或状态
        """
        try:
            task_id = request.data.get('task_id')
            new_priority = request.data.get('priority')
            new_status = request.data.get('status')

            if not task_id:
                return Response({
                    'status': 'error',
                    'message': '缺少task_id参数'
                }, status=400)

            task = ComfyUITask.objects.filter(task_id=task_id).first()
            if not task:
                return Response({
                    'status': 'error',
                    'message': f'任务 {task_id} 不存在'
                }, status=404)

            if new_priority:
                if new_priority not in [ComfyUITask.PRIORITY_LOW, ComfyUITask.PRIORITY_MEDIUM, ComfyUITask.PRIORITY_HIGH]:
                    return Response({
                        'status': 'error',
                        'message': '无效的优先级值'
                    }, status=400)
                task.priority = new_priority

            if new_status:
                if new_status not in [status[0] for status in ComfyUITask.STATUS_CHOICES]:
                    return Response({
                        'status': 'error',
                        'message': '无效的状态值'
                    }, status=400)
                task.status = new_status

            task.save()

            # 如果任务状态改变为pending，重新加入队列
            if new_status == 'pending':
                queue_service.add_task(
                    task_id=task.task_id,
                    task_type=task.task_type,
                    task_data=task.input_data
                )

            return Response({
                'status': 'success',
                'message': f'任务 {task_id} 已更新'
            })

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=500)