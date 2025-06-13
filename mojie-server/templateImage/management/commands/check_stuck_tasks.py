from django.core.management.base import BaseCommand
import logging
from templateImage.task_utils import TaskUtils

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '检查和修复卡住的任务状态'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('开始检查卡住的任务...'))
        
        try:
            # 调用TaskUtils的方法检查并修复卡住的任务
            TaskUtils.check_and_update_stuck_tasks()
            self.stdout.write(self.style.SUCCESS('检查完成'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'检查过程中出错: {str(e)}'))
            logger.error(f"check_stuck_tasks命令执行错误: {str(e)}") 