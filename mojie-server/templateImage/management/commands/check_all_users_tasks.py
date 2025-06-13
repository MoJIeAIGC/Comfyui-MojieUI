from django.core.management.base import BaseCommand
import logging
from django.utils import timezone
from datetime import timedelta
from templateImage.task_utils import TaskUtils
from templateImage.models import ComfyUITask
from user.models import SysUser

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '检查所有用户的任务状态，修复卡住的任务'

    def add_arguments(self, parser):
        parser.add_argument(
            '--age',
            type=int,
            default=5,
            help='检查过去多少分钟内更新的任务（默认5分钟）'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='每个用户最多检查多少个任务（默认100个）'
        )

    def handle(self, *args, **options):
        age_minutes = options['age']
        limit_per_user = options['limit']
        
        self.stdout.write(self.style.SUCCESS(f'开始检查所有用户在过去{age_minutes}分钟内的任务...'))
        
        try:
            # 获取所有有任务的用户
            users_with_tasks = SysUser.objects.filter(
                comfyuitask__updated_at__gte=timezone.now() - timedelta(minutes=age_minutes)
            ).distinct()
            
            user_count = users_with_tasks.count()
            self.stdout.write(self.style.SUCCESS(f'找到{user_count}个用户有任务需要检查'))
            
            total_fixed = 0
            
            # 对每个用户检查任务
            for i, user in enumerate(users_with_tasks):
                try:
                    self.stdout.write(f'正在检查用户 {user.username} ({i+1}/{user_count})...')
                    
                    # 获取该用户最近更新的任务
                    tasks = ComfyUITask.objects.filter(
                        user=user,
                        status__in=['processing', 'processing_completed'],
                        updated_at__gte=timezone.now() - timedelta(minutes=age_minutes)
                    ).order_by('-updated_at')[:limit_per_user]
                    
                    task_count = tasks.count()
                    if task_count == 0:
                        self.stdout.write(f'  用户 {user.username} 没有需要检查的任务')
                        continue
                    
                    self.stdout.write(f'  用户 {user.username} 有 {task_count} 个任务需要检查')
                    
                    fixed_count = 0
                    for task in tasks:
                        try:
                            # 检查任务是否有结果
                            task_status = TaskUtils.get_task_status(task.task_id)
                            has_results = False
                            
                            # 检查任务是否有结果
                            if task.output_data and isinstance(task.output_data, dict) and 'image_urls' in task.output_data:
                                if task.output_data['image_urls']:
                                    has_results = True
                            
                            # 从Redis检查
                            if not has_results and task_status:
                                if 'image_urls' in task_status and task_status['image_urls']:
                                    has_results = True
                                elif 'output_data' in task_status and task_status['output_data']:
                                    output_data = task_status['output_data']
                                    if isinstance(output_data, dict) and 'image_urls' in output_data and output_data['image_urls']:
                                        has_results = True
                            
                            # 如果任务已有结果但状态不正确，修复
                            if has_results and task.status != 'completed':
                                # 准备output_data
                                output_data = None
                                if task.output_data and isinstance(task.output_data, dict) and 'image_urls' in task.output_data:
                                    output_data = task.output_data
                                
                                # 更新任务状态
                                TaskUtils._update_task_status(
                                    task.task_id,
                                    'completed',
                                    force_redis_update=True,
                                    output_data=output_data,
                                    completed_at=timezone.now()
                                )
                                fixed_count += 1
                                
                            # 如果任务处于处理状态超过10分钟且没有结果，可能已经卡住，标记为失败
                            elif not has_results and task.status == 'processing' and task.started_at and (timezone.now() - task.started_at).total_seconds() > 600:
                                TaskUtils._update_task_status(
                                    task.task_id,
                                    'failed',
                                    force_redis_update=True,
                                    error_message='任务处理超时，系统自动取消',
                                    completed_at=timezone.now()
                                )
                                fixed_count += 1
                                
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'  检查任务 {task.task_id} 时出错: {str(e)}'))
                            logger.error(f"检查任务 {task.task_id} 时出错: {str(e)}")
                    
                    total_fixed += fixed_count
                    self.stdout.write(self.style.SUCCESS(f'  用户 {user.username} 修复了 {fixed_count} 个任务状态'))
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'检查用户 {user.username} 任务时出错: {str(e)}'))
                    logger.error(f"检查用户 {user.id} 任务时出错: {str(e)}")
            
            self.stdout.write(self.style.SUCCESS(f'任务检查完成，共修复了 {total_fixed} 个任务状态'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'检查过程中出错: {str(e)}'))
            logger.error(f"check_all_users_tasks命令执行错误: {str(e)}") 