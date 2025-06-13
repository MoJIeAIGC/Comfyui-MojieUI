import logging

import requests
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from djangoProject import settings
from templateImage import models
from templateImage.models import RequestStatus, UserRequest

# from templateImage.retry_tasks import retry_failed_request_task

logger = logging.getLogger(__name__)


class RequestManager:
    """
    请求管理服务类
    """

    @classmethod
    def create_request(cls, user_id, conversation_id, request_data, service_type):
        """创建请求记录并返回完整对象"""
        try:
            request = UserRequest.objects.create(
                user_id=user_id,
                conversation_id=conversation_id,
                request_data=request_data,
                service_type=service_type,
                status=RequestStatus.PENDING
            )
            # 刷新数据库获取完整数据
            request.refresh_from_db()
            return request
        except Exception as e:
            logger.error(f"创建请求失败: {str(e)}", exc_info=True)
            raise

    @classmethod
    def get_requests(cls, user_id=None, conversation_id=None, status=None, service_type=None):
        """
        获取请求记录
        """
        queryset = UserRequest.objects.all()

        if user_id is not None:
            queryset = queryset.filter(user_id=user_id)
        if conversation_id is not None:
            queryset = queryset.filter(conversation_id=conversation_id)
        if status is not None:
            if isinstance(status, (list, tuple)):
                queryset = queryset.filter(status__in=status)
            else:
                queryset = queryset.filter(status=status)
        if service_type is not None:
            queryset = queryset.filter(service_type=service_type)

        return queryset.order_by('-created_at')

    @classmethod
    def get_retryable_requests(cls, older_than_minutes=5):
        """
        获取可重试的请求(失败且未达到最大重试次数)
        """
        time_threshold = timezone.now() - timedelta(minutes=older_than_minutes)
        return UserRequest.objects.filter(
            status=RequestStatus.FAILED,
            retry_count__lt=models.F('max_retries'),
            updated_at__lte=time_threshold
        )

    @classmethod
    def update_request_status(cls, request_id, status, **kwargs):
        """
        更新请求状态
        """
        try:
            request = UserRequest.objects.get(id=request_id)

            if status == RequestStatus.COMPLETED:
                request.mark_as_completed(kwargs.get('response_data'))
            elif status == RequestStatus.FAILED:
                request.mark_as_failed(kwargs.get('error_message'))
            elif status == RequestStatus.PROCESSING:
                request.mark_as_processing()
            elif status == RequestStatus.RETRY_PENDING:
                if not request.prepare_for_retry():
                    return False
            else:
                request.status = status
                request.save(update_fields=['status', 'updated_at'])

            return True
        except UserRequest.DoesNotExist:
            logger.error(f"请求不存在: {request_id}")
            return False
        except Exception as e:
            logger.error(f"更新请求状态失败: {str(e)}", exc_info=True)
            return False

    @classmethod
    def retry_request(cls, request_id, service_callback):
        """
        重试请求
        """
        try:
            request = UserRequest.objects.get(id=request_id)

            if request.status != RequestStatus.FAILED and request.status != RequestStatus.RETRY_PENDING:
                logger.warning(f"请求[{request_id}]状态[{request.status}]不允许重试")
                return False

            if not request.prepare_for_retry():
                logger.warning(f"请求[{request_id}]已达到最大重试次数")
                return False

            # 调用服务处理请求
            result = service_callback(request.request_data)

            if result.get('success'):
                request.mark_as_completed(result)
                return True

            request.mark_as_failed(result.get('error', 'Unknown error'))
            return False

        except Exception as e:
            logger.error(f"重试请求[{request_id}]失败: {str(e)}", exc_info=True)
            if 'request' in locals():
                request.mark_as_failed(str(e))
            return False

    # @classmethod
    # def handle_failed_request(cls, request_id, error_message):
    #     """
    #     处理失败请求并触发重试
    #     """
    #
    #     request = UserRequest.objects.get(id=request_id)
    #
    #     # 标记为失败状态
    #     request.mark_as_failed(error_message)
    #
    #     # 如果还有重试次数，触发异步重试
    #     if request.retry_count < request.max_retries:
    #         # 使用 apply_async 并设置倒计时（例如5分钟后重试）
    #         retry_failed_request_task.apply_async(
    #             args=[request_id],
    #             countdown=2  # 5分钟后重试
    #         )
