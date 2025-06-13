from django.db import transaction
from django.db.models import F
from .models import ComfyUITask
import logging
from prometheus_client import Counter

logger = logging.getLogger(__name__)

TASK_UPDATE_COUNTER = Counter(
    'app_task_updates_total',
    'Total task status updates',
    ['status']
)

class TaskRepository:
    @staticmethod
    def get_pending_tasks():
        """获取待恢复任务（线程安全）"""
        try:
            return list(ComfyUITask.objects.filter(
                status__in=['pending', 'processing']
            ).order_by('created_at').using('default').select_for_update())
        except Exception as e:
            logger.error(f"获取待恢复任务失败: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def reset_processing_tasks():
        """重置卡住的任务状态"""
        try:
            return ComfyUITask.objects.filter(
                status='processing'
            ).update(status='pending', started_at=None)
        except Exception as e:
            logger.error(f"重置任务状态失败: {str(e)}")
            return 0

    @staticmethod
    @transaction.atomic
    def create_task(task_id, task_type, task_data, user):
        """原子化创建任务"""
        try:
            return ComfyUITask.objects.create(
                task_id=task_id,
                task_type=task_type,
                status='pending',
                input_data=task_data,
                user=user
            )
        except Exception as e:
            logger.error(f"创建任务失败: {str(e)}")
            raise

    @staticmethod
    def update_task_status(task_id, status, **kwargs):
        """批量更新任务状态"""
        try:
            update_fields = {'status': status, **kwargs}
            rows = ComfyUITask.objects.filter(task_id=task_id).update(**update_fields)
            TASK_UPDATE_COUNTER.labels(status=status).inc()
            return rows
        except Exception as e:
            logger.error(f"更新任务状态失败: {str(e)}")
            return 0

    @staticmethod
    def get_task_status(task_id):
        """获取任务状态"""
        try:
            task = ComfyUITask.objects.filter(task_id=task_id).first()
            return task.status if task else None
        except Exception as e:
            logger.error(f"查询任务状态失败: {str(e)}")
            return None