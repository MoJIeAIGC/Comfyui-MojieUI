from order.models import UserVIP
from user.models import SysUser
from django.db import models
from django.utils.translation import gettext_lazy as _
import logging
from django.conf import settings

logger = logging.getLogger(__name__)
 

# 假设 SysUser 模型在 user 应用中


class templateImage(models.Model):
    id = models.AutoField(primary_key=True)
    image_name = models.CharField(max_length=255, unique=True, verbose_name="图片名称")
    image_address = models.CharField(max_length=255, unique=True, verbose_name="模板图片的地址")
    description = models.TextField(verbose_name="描述")
    image_method = models.CharField(max_length=100, null=True, verbose_name="图片类别")
    method_sub = models.CharField(max_length=100, null=True, verbose_name="模板图片细分")
    # 自动设置为创建时间
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    # 自动设置为更新时间
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    isDelete = models.IntegerField(null=True, verbose_name="是否删除（0正常 1停用）")

    # 多张图片和同一个用户的一对多关系
    userImage = models.ForeignKey(SysUser, on_delete=models.CASCADE, related_name='template_images')

    # 自引用字段：关联同一张表中的另一行图片
    related_image = models.ForeignKey(
        'self',  # 引用自身
        on_delete=models.SET_NULL,  # 如果关联图片被删除，设置为 NULL
        null=True,  # 允许 NULL
        blank=True,  # 允许表单中为空
        related_name='related_images'  # 反向关系的名称
    )

    # 添加metadata字段，用于存储额外的任务信息
    metadata = models.JSONField(null=True, blank=True, verbose_name="元数据")

    def __str__(self):
        return self.image_name

    class Meta:
        ordering = ['id']
        verbose_name = "模板图片"
        verbose_name_plural = "模板图片"
        db_table = "template_image"


class RequestStatus(models.TextChoices):
    PENDING = 'pending', _('等待中')
    PROCESSING = 'processing', _('处理中')
    COMPLETED = 'completed', _('已完成')
    FAILED = 'failed', _('已失败')
    RETRY_PENDING = 'retry_pending', _('等待重试')




class ConversationList(models.Model):
    """
    会话列表，记录用户的会话信息。
    """
    name = models.TextField(verbose_name="会话名称")
    user = models.ForeignKey(SysUser, on_delete=models.CASCADE, verbose_name="用户")
    upload_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    is_delete = models.IntegerField(default=0, verbose_name='是否删除，0: 存在，1: 删除')

    class Meta:
        verbose_name = "会话列表"
        verbose_name_plural = "会话列表"

    def __str__(self):
        return f"用户 {self.user.id} 的会话列表"


class UserCloudImageStorage(models.Model):
    """
    用户云空间图片存储表，记录用户在ComfyUI中生成的图片
    """
    user = models.ForeignKey(SysUser, on_delete=models.CASCADE, verbose_name="用户")
    image_name = models.CharField(max_length=255, verbose_name="图片名称")
    image_url = models.TextField(verbose_name="图片URL")
    image_size = models.PositiveIntegerField(verbose_name="图片大小(字节)")
    image_type = models.CharField(max_length=20, default="image/png", verbose_name="图片类型")
    description = models.TextField(blank=True, null=True, verbose_name="图片描述")
    source = models.CharField(max_length=50, default="comfyui", verbose_name="图片来源")
    
    # 时间相关字段
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    # 逻辑删除
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="删除时间")
    
    # 元数据，可以存储额外信息
    metadata = models.JSONField(null=True, blank=True, verbose_name="元数据")
    
    class Meta:
        verbose_name = "用户云空间图片"
        verbose_name_plural = "用户云空间图片"
        db_table = "user_cloud_image_storage"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_deleted']),
        ]
    
    def __str__(self):
        return f"{self.user.username}的图片: {self.image_name}"
    
    @staticmethod
    def get_image_size_from_url(image_url):
        """
        从URL获取图片大小
        """
        import requests
        from urllib.parse import urlparse
        
        try:
            # 检查URL是否有效
            parsed_url = urlparse(image_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return 0
                
            # 发送HEAD请求获取Content-Length
            response = requests.head(image_url, timeout=5)
            if response.status_code == 200 and 'content-length' in response.headers:
                return int(response.headers['content-length'])
                
            # 如果HEAD请求无法获取大小，尝试下载部分内容
            response = requests.get(image_url, stream=True, timeout=5)
            if response.status_code == 200:
                # 下载整个内容并计算大小
                size = 0
                for chunk in response.iter_content(chunk_size=8192):
                    size += len(chunk)
                return size
                
            return 0
        except Exception as e:
            logger.error(f"获取图片大小失败: {str(e)}")
            return 0


class UserRequest(models.Model):
    user = models.ForeignKey(SysUser, on_delete=models.CASCADE, verbose_name="用户")
    conversation_id = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name=_('会话ID')
    )
    request_data = models.JSONField(verbose_name=_('请求数据'))
    response_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('响应数据')
    )
    status = models.CharField(
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING,
        verbose_name=_('状态')
    )
    service_type = models.CharField(
        max_length=50,
        choices=[
            ('chatgpt_image', 'ChatGPT图像生成'),
            ('gemini_image', 'Gemini图像生成')
        ],
        verbose_name=_('服务类型')
    )
    retry_count = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_('重试次数')
    )
    max_retries = models.PositiveSmallIntegerField(
        default=3,
        verbose_name=_('最大重试次数')
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('错误信息')
    )
    session_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    client_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('创建时间')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('更新时间')
    )
    is_delete = models.IntegerField(default=0, verbose_name='是否删除，0: 存在，1: 删除')

    class Meta:
        verbose_name = _('用户请求')
        verbose_name_plural = _('用户请求')
        indexes = [
            models.Index(fields=['user', 'conversation_id']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user_id}-{self.service_type}-{self.status}"

    def mark_as_processing(self):
        self.status = RequestStatus.PROCESSING
        self.save(update_fields=['status', 'updated_at'])

    def mark_as_completed(self, response_data):
        self.status = RequestStatus.COMPLETED
        self.response_data = response_data
        self.save(update_fields=['status', 'response_data', 'updated_at'])

    def mark_as_failed(self, error_message):
        self.status = RequestStatus.FAILED
        self.error_message = str(error_message)[:2000]
        self.save(update_fields=['status', 'error_message', 'updated_at'])

    def prepare_for_retry(self):
        if self.retry_count < self.max_retries:
            self.status = RequestStatus.RETRY_PENDING
            self.retry_count += 1
            self.save(update_fields=['status', 'retry_count', 'updated_at'])
            return True
        return False

    class Meta:
        indexes = [
            models.Index(fields=['user', 'conversation_id', 'session_id']),
            models.Index(fields=['user', 'client_id']),
        ]
        unique_together = [['user', 'conversation_id', 'session_id', 'client_id']]


class ComfyUITask(models.Model):
    """
    ComfyUI异步任务模型
    """
    # 优先级选项
    PRIORITY_LOW = "low"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_HIGH = "high"
    
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, "低"),
        (PRIORITY_MEDIUM, "中"),
        (PRIORITY_HIGH, "高"),
    ]
    
    # 状态选项
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    
    STATUS_CHOICES = [
        (STATUS_PENDING, "等待中"),
        (STATUS_PROCESSING, "处理中"),
        (STATUS_COMPLETED, "已完成"),
        (STATUS_FAILED, "失败"),
        (STATUS_CANCELLED, "已取消"),
    ]
    
    task_id = models.CharField(max_length=100, primary_key=True, verbose_name="任务ID")
    task_type = models.CharField(max_length=50, verbose_name="任务类型")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name="任务状态")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM, verbose_name="优先级")
    queue_position = models.IntegerField(null=True, blank=True, verbose_name="队列位置")
    progress = models.FloatField(default=0, verbose_name="进度")
    user = models.ForeignKey(SysUser, on_delete=models.CASCADE, null=True, verbose_name="用户")
    input_data = models.JSONField(default=dict, verbose_name="输入数据")
    output_data = models.JSONField(null=True, blank=True, verbose_name="输出数据")
    error_message = models.TextField(null=True, blank=True, verbose_name="错误信息")
    processing_time = models.FloatField(null=True, blank=True, verbose_name="处理时间(秒)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")
    updated_at = models.DateTimeField(auto_now=True, null=True, verbose_name="更新时间")
    # 是否已保存到云空间
    saved_to_cloud = models.BooleanField(default=False, verbose_name="是否已保存到云空间")
    # 是否自动保存到云空间的开关
    auto_save_to_cloud = models.BooleanField(default=False, verbose_name="自动保存到云空间")
    
    class Meta:
        verbose_name = "ComfyUI任务"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.task_id} - {self.task_type} - {self.status}"

    def deduct_points(self):
        """扣除用户积分（优先扣除VIP积分）"""
        try:
            user = self.user
            
            # 检查用户是否为VIP
            is_vip = UserVIP.objects.filter(user=user, is_active=True).exists()
            
            # 从settings中获取对应的扣分规则
            points_rules = settings.POINT_DEDUCTION_RULES['vip_user' if is_vip else 'regular_user']
            
            # 获取需要扣除的积分数量
            points_to_deduct = points_rules.get(self.task_type, 1)
            
            logger.info(f"用户 {user.username} {'是VIP用户' if is_vip else '是普通用户'}，任务类型 {self.task_type} 需要扣除 {points_to_deduct} 点积分")

            # 优先扣除VIP积分
            if user.vip_points >= points_to_deduct:
                user.vip_points -= points_to_deduct
                user.save(update_fields=['vip_points'])
                logger.info(f"已扣除用户 {user.username} 的VIP积分 {points_to_deduct} 点")
                
                # 创建VIP积分扣除记录
                PointsDeductionHistory.objects.create(
                    user=user,
                    points_deducted=points_to_deduct,
                    deduction_type='VIP',
                    task_type=self.task_type,
                    task_id=getattr(self, 'id', None),
                    image_upload_record=getattr(self, 'image_upload_record', None)
                )
                return True
            
            # 如果VIP积分不足，扣除普通积分
            if user.points >= points_to_deduct:
                user.points -= points_to_deduct
                user.save(update_fields=['points'])
                logger.info(f"已扣除用户 {user.username} 的普通积分 {points_to_deduct} 点")
                
                # 创建普通积分扣除记录
                PointsDeductionHistory.objects.create(
                    user=user,
                    points_deducted=points_to_deduct,
                    deduction_type='REGULAR',
                    task_type=self.task_type,
                    task_id=getattr(self, 'id', None),
                    image_upload_record=getattr(self, 'image_upload_record', None)
                )
                return True
            
            # 如果两种积分都不足
            logger.warning(f"用户 {user.username} 积分不足，无法扣除 {points_to_deduct} 点积分")
            return False

        except Exception as e:
            logger.error(f"扣除用户积分时发生错误: {str(e)}")
            return False
    
    def save_to_user_cloud(self, force=False):
        """将任务输出的图片保存到用户云空间
        
        Args:
            force (bool): 是否强制保存，无视auto_save_to_cloud开关
        
        Returns:
            bool: 保存成功返回True，否则返回False
        """
        try:
            # 确保已完成且有输出数据
            if self.status != self.STATUS_COMPLETED or not self.output_data:
                return False
                
            # 如果不是强制保存模式，则检查auto_save_to_cloud开关
            if not force and not self.auto_save_to_cloud:
                logger.info(f"任务 {self.task_id} 的自动保存开关已关闭，跳过保存到云空间")
                return False
                
            # 已经保存过则跳过
            if self.saved_to_cloud:
                return True
                
            # 从输出数据中提取图片URL
            image_urls = []
            
            # 通常ComfyUI的输出数据包含images字段
            if 'images' in self.output_data:
                images = self.output_data.get('images', [])
                # 处理可能的不同格式
                if isinstance(images, list):
                    for img in images:
                        if isinstance(img, dict) and 'url' in img:
                            image_urls.append(img['url'])
                        elif isinstance(img, str):
                            image_urls.append(img)
            
            # 检查其他可能包含图片URL的字段
            for key, value in self.output_data.items():
                if 'image' in key.lower() or 'url' in key.lower():
                    if isinstance(value, str) and (value.startswith('http') or value.startswith('/')):
                        image_urls.append(value)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str) and (item.startswith('http') or item.startswith('/')):
                                image_urls.append(item)
                            elif isinstance(item, dict) and 'url' in item:
                                image_urls.append(item['url'])
            
            # 如果没有找到图片URL则返回
            if not image_urls:
                logger.warning(f"任务 {self.task_id} 未找到图片URL")
                return False
                
            # 批量保存图片到云空间
            saved_count = 0
            for i, url in enumerate(image_urls):
                try:
                    # 计算图片大小
                    image_size = UserCloudImageStorage.get_image_size_from_url(url)
                    if image_size == 0:
                        image_size = 102400  # 默认100KB
                        
                    # 创建云空间记录
                    UserCloudImageStorage.objects.create(
                        user=self.user,
                        image_url=url,
                        image_name=f"comfyui_{self.task_id}_{i+1}",
                        image_size=image_size,
                        description=f"ComfyUI任务 {self.task_id} 生成的图片",
                        source="comfyui",
                        metadata={
                            "task_id": self.task_id,
                            "task_type": self.task_type,
                            "input_data": self.input_data
                        }
                    )
                    saved_count += 1
                except Exception as e:
                    logger.error(f"保存图片到云空间失败: {url}, 错误: {str(e)}")
            
            # 标记为已保存到云空间
            if saved_count > 0:
                self.saved_to_cloud = True
                # 只更新saved_to_cloud字段，避免触发save()方法的其他逻辑
                ComfyUITask.objects.filter(pk=self.pk).update(saved_to_cloud=True)
                logger.info(f"已将任务 {self.task_id} 的 {saved_count} 张图片保存到云空间")
                return True
                
            return False
                
        except Exception as e:
            logger.error(f"保存图片到云空间失败: {str(e)}")
            return False

    def save(self, *args, **kwargs):
        """重写save方法，在任务成功完成时扣除积分并保存图片到云空间"""
        is_new = self._state.adding
        old_status = None
        if not is_new:
            old_status = ComfyUITask.objects.get(pk=self.pk).status

        super().save(*args, **kwargs)

        # 只在任务从未完成变为完成时处理
        if not is_new and old_status != 'completed' and self.status == 'completed':
            # 任务状态变为完成，无论是否有错误信息都扣除积分
            # 扣除积分
            self.deduct_points()
            logger.info(f"任务 {self.task_id} 成功完成，已扣除用户积分")
            
            # 根据开关决定是否保存图片到云空间
            if self.auto_save_to_cloud:
                self.save_to_user_cloud()
                logger.info(f"任务 {self.task_id} 自动保存到云空间功能已开启，正在保存图片")
            else:
                logger.info(f"任务 {self.task_id} 自动保存到云空间功能已关闭，不自动保存图片")


class TaskType(models.Model):
    """
    任务类型模型，用于动态配置支持的任务类型
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True, verbose_name="任务类型代码")
    display_name = models.CharField(max_length=100, verbose_name="显示名称")
    description = models.TextField(blank=True, null=True, verbose_name="描述")
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    handler_name = models.CharField(max_length=100, verbose_name="处理器名称", 
                                   help_text="处理方法名称或'generic'表示使用通用处理器")
    
    # 元数据，可以存储任务类型特定的配置
    config = models.JSONField(null=True, blank=True, verbose_name="配置")
    
    # 任务排序
    priority_order = models.IntegerField(default=0, verbose_name="排序优先级")
    
    # 时间字段
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        verbose_name = "任务类型"
        verbose_name_plural = "任务类型"
        ordering = ['priority_order', 'name']
    
    def __str__(self):
        return f"{self.display_name} ({self.name})"


class ImageUploadRecord(models.Model):
    """
    图片上传记录表，记录用户上传的图片信息。
    """
    user = models.ForeignKey(SysUser, on_delete=models.CASCADE, verbose_name="用户")
    image_list = models.TextField(verbose_name="图片列表字符串")
    image_url = models.TextField(verbose_name="图片结果", default='图片结果')
    image_name = models.TextField(verbose_name="图片名称", default='图片名称')
    prompt = models.TextField(verbose_name="描述语句", default='描述语句')
    seed_used = models.TextField(verbose_name="消耗", default='消耗')
    model_used = models.TextField(verbose_name="模型", default='模型')
    comfyUI_task = models.ForeignKey(ComfyUITask, on_delete=models.CASCADE, verbose_name="对应的任务信息", null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.COMPLETED,
        verbose_name=_('状态')
    )
    conversation = models.ForeignKey('ConversationList', on_delete=models.CASCADE, verbose_name="关联会话列表的 ID")
    upload_time = models.DateTimeField(auto_now_add=True, verbose_name="上传时间")

    class Meta:
        verbose_name = "图片上传记录"
        verbose_name_plural = "图片上传记录"

    def __str__(self):
        return f"用户 {self.user.id} 的图片上传记录"


class PointsDeductionHistory(models.Model):
    """用户积分扣除历史记录"""
    user = models.ForeignKey(SysUser, on_delete=models.CASCADE, verbose_name='用户')
    deduction_time = models.DateTimeField(auto_now_add=True, verbose_name='扣除时间')
    points_deducted = models.IntegerField(verbose_name='扣除积分数量')
    deduction_type = models.CharField(
        max_length=20,
        choices=[
            ('VIP', 'VIP积分'),
            ('REGULAR', '普通积分')
        ],
        verbose_name='扣除积分类型'
    )
    task_type = models.CharField(max_length=50, verbose_name='任务类型')
    task_id = models.IntegerField(null=True, blank=True, verbose_name='任务ID')
    image_upload_record = models.ForeignKey(
        ImageUploadRecord,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name='图片上传记录'
    )
    
    class Meta:
        verbose_name = '积分扣除历史'
        verbose_name_plural = verbose_name
        ordering = ['-deduction_time']
        db_table = 'points_deduction_history'
        
    def __str__(self):
        return f"{self.user.username} - {self.deduction_time} - {self.points_deducted}点{self.deduction_type}"