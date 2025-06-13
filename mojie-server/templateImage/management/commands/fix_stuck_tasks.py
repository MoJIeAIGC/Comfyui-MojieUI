from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import logging
from django.db.models import Q

from templateImage.models import ComfyUITask, ImageUploadRecord
from templateImage.task_utils import TaskUtils

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '查找并修复卡在队列中太久的任务'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='仅检查不修复，只报告发现的问题',
        )
        parser.add_argument(
            '--minutes',
            type=int,
            default=5,
            help='检查几分钟前更新的任务，默认5分钟',
        )
        parser.add_argument(
            '--task-id',
            type=str,
            help='指定任务ID进行检查和修复',
        )
        parser.add_argument(
            '--check-incomplete',
            action='store_true',
            help='检查所有未完成的任务，无时间限制',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制更新所有匹配的任务状态，无论是否有结果',
        )
        parser.add_argument(
            '--status',
            type=str,
            default='completed',
            help='强制更新为指定状态，默认completed，配合--force使用',
        )
        parser.add_argument(
            '--sync-records',
            action='store_true',
            help='同步更新关联的ImageUploadRecord记录',
        )

    def handle(self, *args, **options):
        check_only = options['check_only']
        minutes = options['minutes']
        task_id = options['task_id']
        check_incomplete = options['check_incomplete']
        force = options['force']
        target_status = options['status']
        sync_records = options['sync_records']

        self.stdout.write(self.style.SUCCESS(f'开始检查卡住的任务...'))
        
        try:
            if task_id:
                # 如果指定了任务ID，直接检查该任务
                self.check_specific_task(task_id, check_only, force, target_status, sync_records)
            elif check_incomplete:
                # 检查所有未完成状态的任务
                self.check_incomplete_tasks(check_only, force, target_status, sync_records)
            else:
                # 常规检查：几分钟前更新过的处理中任务
                self.check_stuck_tasks(minutes, check_only, force, target_status, sync_records)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'执行过程中出错: {str(e)}'))
            logger.error(f'执行过程中出错: {str(e)}', exc_info=True)

    def check_specific_task(self, task_id, check_only, force, target_status, sync_records):
        """检查并修复特定任务ID"""
        try:
            task = ComfyUITask.objects.get(task_id=task_id)
            self.stdout.write(f'检查任务 {task_id}:')
            self.stdout.write(f'  - 状态: {task.status}')
            self.stdout.write(f'  - 更新时间: {task.updated_at}')
            self.stdout.write(f'  - 完成时间: {task.completed_at}')
            
            # 检查任务是否有结果
            has_results = False
            
            if task.output_data and isinstance(task.output_data, dict) and 'image_urls' in task.output_data:
                if task.output_data['image_urls']:
                    has_results = True
                    self.stdout.write(self.style.WARNING(f'  - 发现任务有结果但状态为 {task.status}'))
            
            # 如果任务处理时间超过30分钟还没有结果，可能是卡住了
            is_stuck = False
            if task.started_at and (timezone.now() - task.started_at).total_seconds() > 1800:
                is_stuck = True
                self.stdout.write(self.style.WARNING(f'  - 任务处理超过30分钟无结果，可能已卡住'))
                
            if (force or has_results or is_stuck) and not check_only:
                # 更新任务状态
                old_status = task.status
                if force or has_results:
                    status_to_set = target_status
                else:
                    status_to_set = 'stuck_timeout'  # 超时状态
                    
                self.stdout.write(self.style.WARNING(f'  - 将任务状态从 {old_status} 更新为 {status_to_set}'))
                TaskUtils._update_task_status(
                    task_id,
                    status_to_set,
                    force_redis_update=True,
                    output_data=task.output_data if has_results else None,
                    completed_at=timezone.now() if status_to_set in ['completed', 'failed', 'stuck_timeout'] else None,
                    error_message='任务处理超时，系统自动取消' if status_to_set == 'stuck_timeout' else None
                )
                
                # 同步更新关联记录
                if sync_records:
                    sync_result = TaskUtils.sync_record_status(task_id, force=True)
                    if sync_result['success']:
                        self.stdout.write(self.style.SUCCESS(f'  - 已同步 {sync_result["updated_count"]} 条关联记录'))
                    else:
                        self.stdout.write(self.style.ERROR(f'  - 同步记录状态失败: {sync_result.get("message")}'))
                
                self.stdout.write(self.style.SUCCESS(f'已更新任务 {task_id} 状态为 {status_to_set}'))
            elif check_only:
                if has_results:
                    self.stdout.write(self.style.WARNING(f'任务 {task_id} 需要更新（有结果但状态是 {task.status}）'))
                elif is_stuck:
                    self.stdout.write(self.style.WARNING(f'任务 {task_id} 可能已卡住（处理时间过长）'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'任务 {task_id} 状态正常'))
        except ComfyUITask.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'任务 {task_id} 不存在'))

    def check_incomplete_tasks(self, check_only, force, target_status, sync_records):
        """检查所有未完成状态的任务"""
        incomplete_tasks = ComfyUITask.objects.filter(
            status__in=['pending', 'processing', 'processing_completed']
        )
        
        self.stdout.write(f'找到 {incomplete_tasks.count()} 个未完成的任务')
        
        fixed_count = 0
        has_results_count = 0
        is_stuck_count = 0
        
        for task in incomplete_tasks:
            # 检查任务是否有结果
            has_results = False
            
            if task.output_data and isinstance(task.output_data, dict) and 'image_urls' in task.output_data:
                if task.output_data['image_urls']:
                    has_results = True
                    has_results_count += 1
            
            # 检查任务是否卡住
            is_stuck = False
            if task.started_at and (timezone.now() - task.started_at).total_seconds() > 1800:
                is_stuck = True
                is_stuck_count += 1
                
            if (force or has_results or is_stuck) and not check_only:
                # 更新任务状态
                old_status = task.status
                if force or has_results:
                    status_to_set = target_status
                else:
                    status_to_set = 'stuck_timeout'  # 超时状态
                    
                TaskUtils._update_task_status(
                    task.task_id,
                    status_to_set,
                    force_redis_update=True,
                    output_data=task.output_data if has_results else None,
                    completed_at=timezone.now() if status_to_set in ['completed', 'failed', 'stuck_timeout'] else None,
                    error_message='任务处理超时，系统自动取消' if status_to_set == 'stuck_timeout' else None
                )
                
                # 同步更新关联记录
                if sync_records:
                    TaskUtils.sync_record_status(task.task_id, force=True)
                
                fixed_count += 1
                self.stdout.write(f'已将任务 {task.task_id} 状态从 {old_status} 更新为 {status_to_set}')
        
        if check_only:
            self.stdout.write(self.style.SUCCESS(f'检查完成: 发现 {has_results_count} 个任务有结果但状态不正确，{is_stuck_count} 个任务可能已卡住'))
        else:
            self.stdout.write(self.style.SUCCESS(f'共修复了 {fixed_count} 个任务'))

    def check_stuck_tasks(self, minutes, check_only, force, target_status, sync_records):
        """检查几分钟前更新的处理中任务"""
        # 查找处理中状态可能卡住的任务
        processing_tasks = ComfyUITask.objects.filter(
            status__in=['processing', 'processing_completed'],
            updated_at__lt=timezone.now() - timedelta(minutes=minutes)
        )
        
        self.stdout.write(f'找到 {processing_tasks.count()} 个可能卡住的任务')
        
        fixed_count = 0
        has_results_count = 0
        
        for task in processing_tasks:
            # 检查任务是否有结果
            has_results = False
            
            if task.output_data and isinstance(task.output_data, dict) and 'image_urls' in task.output_data:
                if task.output_data['image_urls']:
                    has_results = True
                    has_results_count += 1
            
            if (force or has_results) and not check_only:
                # 更新任务状态
                old_status = task.status
                
                TaskUtils._update_task_status(
                    task.task_id,
                    target_status,
                    force_redis_update=True,
                    output_data=task.output_data,
                    completed_at=timezone.now()
                )
                
                # 同步更新关联记录
                if sync_records:
                    TaskUtils.sync_record_status(task.task_id, force=True)
                
                fixed_count += 1
                self.stdout.write(f'已将任务 {task.task_id} 状态从 {old_status} 更新为 {target_status}')
            elif not has_results and not check_only:
                # 如果任务处理时间超过30分钟还没有结果，标记为stuck_timeout
                if task.started_at and (timezone.now() - task.started_at).total_seconds() > 1800:
                    old_status = task.status
                    
                    TaskUtils._update_task_status(
                        task.task_id,
                        'stuck_timeout',
                        force_redis_update=True,
                        error_message='任务处理超时，系统自动取消',
                        completed_at=timezone.now()
                    )
                    
                    # 同步更新关联记录
                    if sync_records:
                        TaskUtils.sync_record_status(task.task_id, force=True)
                    
                    fixed_count += 1
                    self.stdout.write(f'已将超时任务 {task.task_id} 状态从 {old_status} 更新为 stuck_timeout')
        
        if check_only:
            self.stdout.write(self.style.SUCCESS(f'检查完成: 发现 {has_results_count} 个任务有结果但状态不正确'))
        else:
            self.stdout.write(self.style.SUCCESS(f'共修复了 {fixed_count} 个任务')) 