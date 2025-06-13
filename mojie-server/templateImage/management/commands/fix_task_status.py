"""
修复任务状态命令
此命令用于修复任何卡在processing_completed状态的任务，并将其更改为正确的状态
"""
import logging
import json
from django.core.management.base import BaseCommand
from django.utils import timezone
from templateImage.models import ComfyUITask, ImageUploadRecord
from templateImage.queue_service_singleton import queue_service
from templateImage.task_utils import TaskUtils

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '修复任务状态，确保没有任务卡在processing_completed状态'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='检查最近多少天的任务，默认7天'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制更新所有任务状态，不管当前状态是什么'
        )
        parser.add_argument(
            '--task-id',
            type=str,
            help='指定要修复的任务ID'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅检查任务状态，不实际更新'
        )

    def handle(self, *args, **options):
        days = options['days']
        force = options['force']
        task_id = options['task_id']
        dry_run = options['dry_run']

        self.stdout.write(f"开始检查任务状态...")
        
        # 查询条件
        if task_id:
            tasks = ComfyUITask.objects.filter(task_id=task_id)
            self.stdout.write(f"正在检查指定的任务: {task_id}")
        else:
            # 获取指定时间范围内的任务
            end_date = timezone.now()
            start_date = end_date - timezone.timedelta(days=days)
            
            # 查询条件
            query = ComfyUITask.objects.filter(created_at__gte=start_date)
            
            if not force:
                # 只查找processing或processing_completed状态的任务
                query = query.filter(status__in=['processing', 'processing_completed'])
            
            tasks = query.order_by('-created_at')
            self.stdout.write(f"正在检查最近{days}天内的任务，总共找到 {tasks.count()} 个任务")

        fixed_count = 0
        redis_fixed_count = 0
        
        # 处理每个任务
        for task in tasks:
            self.stdout.write(f"检查任务 {task.task_id}, 当前状态: {task.status}")
            
            # 1. 检查Redis中的状态
            redis_status = None
            redis_has_results = False
            
            try:
                redis_task_data = TaskUtils.get_task_status(task.task_id)
                if redis_task_data:
                    redis_status = redis_task_data.get('status')
                    self.stdout.write(f"  Redis中的状态: {redis_status}")
                    
                    # 检查是否有图片结果
                    if redis_task_data.get('image_urls'):
                        redis_has_results = True
                        self.stdout.write(f"  Redis中有图片URLs")
                    elif 'output_data' in redis_task_data and redis_task_data['output_data']:
                        output_data = redis_task_data['output_data']
                        if isinstance(output_data, dict) and 'image_urls' in output_data and output_data['image_urls']:
                            redis_has_results = True
                            self.stdout.write(f"  Redis中的output_data有图片URLs")
                else:
                    self.stdout.write(f"  Redis中没有此任务的数据")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  检查Redis状态失败: {str(e)}"))
            
            # 2. 检查MySQL中是否有结果
            mysql_has_results = False
            if task.output_data:
                try:
                    if isinstance(task.output_data, dict) and 'image_urls' in task.output_data:
                        mysql_has_results = True
                        self.stdout.write(f"  MySQL中有图片URLs")
                except Exception:
                    pass
            
            # 3. 检查关联记录中是否有图片URL
            record_has_results = False
            records = ImageUploadRecord.objects.filter(comfyUI_task=task)
            if records.exists():
                for record in records:
                    if record.image_url:
                        record_has_results = True
                        self.stdout.write(f"  关联记录中有图片URL")
                        break
            
            # 4. 判断是否需要修复
            need_fix = False
            new_status = None
            
            # 处理卡在processing状态的任务
            if task.status == 'processing' or redis_status == 'processing_completed':
                if mysql_has_results or redis_has_results or record_has_results:
                    need_fix = True
                    new_status = 'completed'
                    self.stdout.write(f"  任务 {task.task_id} 需要修复: 状态为processing但已有结果")
                elif task.created_at < timezone.now() - timezone.timedelta(hours=24):
                    # 如果任务已经处理了24小时都没有结果，可能是挂起的任务
                    need_fix = True
                    new_status = 'failed'
                    self.stdout.write(f"  任务 {task.task_id} 需要修复: 处理超过24小时无结果，可能挂起")
            
            # 强制修复模式下，如果状态不一致则修复
            if force and redis_status and redis_status != task.status:
                need_fix = True
                # 以Redis状态为准，但如果有结果，优先设为completed
                if mysql_has_results or redis_has_results or record_has_results:
                    new_status = 'completed'
                else:
                    new_status = redis_status
                self.stdout.write(f"  任务 {task.task_id} 需要修复: Redis状态({redis_status})与MySQL状态({task.status})不一致")
            
            # 5. 执行修复
            if need_fix and not dry_run:
                try:
                    # 更新MySQL状态
                    old_status = task.status
                    task.status = new_status
                    if new_status == 'completed' and not task.completed_at:
                        task.completed_at = timezone.now()
                    task.save()
                    fixed_count += 1
                    self.stdout.write(self.style.SUCCESS(f"  已修复MySQL中任务 {task.task_id} 状态: {old_status} -> {new_status}"))
                    
                    # 更新Redis状态
                    if hasattr(queue_service, '_update_task_status'):
                        try:
                            # 强制更新Redis中的状态
                            kwargs = {}
                            if new_status == 'completed':
                                kwargs['completed_at'] = task.completed_at or timezone.now()
                                if task.output_data:
                                    kwargs['output_data'] = task.output_data
                                
                            queue_service._update_task_status(
                                task.task_id, 
                                new_status,
                                force_redis_update=True,
                                **kwargs
                            )
                            redis_fixed_count += 1
                            self.stdout.write(self.style.SUCCESS(f"  已修复Redis中任务 {task.task_id} 状态为 {new_status}"))
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"  更新Redis状态失败: {str(e)}"))
                    
                    # 同步关联记录状态
                    if records.exists():
                        updated = records.update(status=new_status)
                        self.stdout.write(self.style.SUCCESS(f"  已更新 {updated} 条关联记录状态为 {new_status}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  修复任务状态失败: {str(e)}"))
            elif need_fix and dry_run:
                self.stdout.write(self.style.WARNING(f"  [DRY RUN] 将修复任务 {task.task_id} 状态: {task.status} -> {new_status}"))
            else:
                self.stdout.write(f"  任务 {task.task_id} 状态正常，无需修复")
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"[DRY RUN] 检查完成，发现 {fixed_count} 个需要修复的任务"))
        else:
            self.stdout.write(self.style.SUCCESS(f"修复完成，共修复 {fixed_count} 个MySQL任务状态和 {redis_fixed_count} 个Redis任务状态")) 