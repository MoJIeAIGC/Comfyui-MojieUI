from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.
class SysUser(AbstractUser):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=100, unique=True, verbose_name="用户名")
    password = models.CharField(max_length=100, verbose_name="密码")
    avatar = models.CharField(max_length=255, null=True, verbose_name="用户头像")
    email = models.CharField(max_length=100, null=True, verbose_name="用户邮箱")
    phone = models.CharField(max_length=11,null=True,  verbose_name="手机号码")
    userRole = models.CharField(max_length=255, null=True, verbose_name="用户角色")
    role = models.CharField(max_length=255, null=True, verbose_name="月卡状态")
    points = models.PositiveIntegerField(default=0, verbose_name="普通积分")
    vip_points = models.PositiveIntegerField(default=0, verbose_name="VIP积分")
    userAITime = models.CharField(max_length=255, verbose_name="时间")
    isDelete = models.IntegerField(null=True, verbose_name="是否删除（0正常 1停用）")
    create_time = models.DateTimeField(null=True, verbose_name="创建时间", )
    update_time = models.DateTimeField(null=True, verbose_name="更新时间")
    remark = models.CharField(max_length=500, null=True, verbose_name="备注")
    openid = models.CharField(max_length=128,null=True,  verbose_name='用户唯一标识')
    session_key = models.CharField(max_length=128, null=True, verbose_name='会话密钥')
    USERNAME_FIELD = 'username'

    # 定义 REQUIRED_FIELDS
    REQUIRED_FIELDS = [phone]  # 根据实际需求添加字段

    class Meta:
        db_table = "sys_user"

    @property
    def is_vip(self):
        """检查用户是否为有效VIP"""
        if hasattr(self, 'vip_info'):  # 检查是否存在关联的UserVIP记录
            return self.vip_info.check_status()
        return False

    @property
    def vip_expire_date(self):
        """获取VIP过期时间（不存在则返回None）"""
        return getattr(self.vip_info, 'end_time', None)

    @property
    def vip_level(self):
        """获取VIP等级"""
        return getattr(self.vip_info, 'level', None)



class Assets(models.Model):
    name = models.CharField(max_length=255, verbose_name="名称")
    text = models.TextField(verbose_name="文本内容")

    class Meta:
        verbose_name = "资产"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


from django.db import models

class MiniProgramUser(models.Model):
    openid = models.CharField(max_length=128, unique=True, verbose_name='用户唯一标识')
    session_key = models.CharField(max_length=128, verbose_name='会话密钥')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '小程序用户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.openid


class UserShare(models.Model):
    """用户分享模型"""
    user = models.OneToOneField(
        SysUser, 
        on_delete=models.CASCADE,
        related_name='share_info',
        verbose_name="关联用户"
    )
    share_code = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="分享码"
    )
    invite_count = models.PositiveIntegerField(
        default=0,
        verbose_name="邀请人数"
    )
    earned_points = models.PositiveIntegerField(
        default=0,
        verbose_name="获得积分"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间"
    )
    yaor = models.CharField(max_length=100, verbose_name="邀请的用户",default="")

    class Meta:
        verbose_name = "用户分享"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user.username}的分享信息"

    def save(self, *args, **kwargs):
        """保存时自动生成分享码"""
        if not self.share_code:
            self.share_code = self.generate_share_code()
        super().save(*args, **kwargs)

    def generate_share_code(self):
        """生成8位随机分享码"""
        import random
        import string
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


class PointsRecord(models.Model):
    """积分记录模型，用于跟踪用户积分的变动"""
    user = models.ForeignKey(
        SysUser,
        on_delete=models.CASCADE,
        related_name='points_records',
        verbose_name="用户"
    )
    points_change = models.IntegerField(
        verbose_name="积分变动",
        help_text="正数表示增加，负数表示扣除"
    )
    balance = models.PositiveIntegerField(
        verbose_name="变动后余额"
    )
    transaction_type = models.CharField(
        max_length=50,
        verbose_name="交易类型",
        help_text="例如：消费、奖励、退款等"
    )
    reason = models.CharField(
        max_length=255,
        verbose_name="变动原因"
    )
    notes = models.TextField(
        null=True,
        blank=True,
        verbose_name="详细说明"
    )
    related_task_id = models.CharField(
        max_length=255, 
        null=True,
        blank=True,
        verbose_name="相关任务ID"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间"
    )

    class Meta:
        verbose_name = "积分记录"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']  # 按创建时间降序排序

    def __str__(self):
        change_type = "增加" if self.points_change > 0 else "扣除"
        return f"{self.user.username} {change_type} {abs(self.points_change)} 积分 ({self.transaction_type})"


class UserProxy(models.Model):
    """
    用户代理关系模型
    """
    proxy = models.ForeignKey(
        SysUser, 
        on_delete=models.CASCADE,
        related_name='proxy_relations',
        verbose_name="代理用户"
    )
    account = models.ForeignKey(
        SysUser,
        on_delete=models.CASCADE,
        related_name='account_relations', 
        verbose_name="被代理账户"
    )
    way = models.SmallIntegerField(
        choices=((0, '方式0'), (1, '方式1')),
        default=0,
        verbose_name="代理方式"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间"
    )

    class Meta:
        verbose_name = "用户代理关系"
        verbose_name_plural = verbose_name
        unique_together = ('proxy', 'account')  # 确保唯一关系

    def __str__(self):
        return f"{self.proxy.username} 代理 {self.account.username}"


class InvitedUser(models.Model):
    """被邀请用户关联模型"""
    user_share = models.ForeignKey(
        UserShare,
        on_delete=models.CASCADE,
        related_name='invited_users',
        verbose_name="分享记录"
    )
    invited_user = models.ForeignKey(
        SysUser,
        on_delete=models.CASCADE,
        related_name='inviter_records',
        verbose_name="被邀请用户"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间"
    )

    class Meta:
        verbose_name = "被邀请用户记录"
        verbose_name_plural = verbose_name
        unique_together = ('user_share', 'invited_user')  # 确保同一个用户不会被同一个分享记录邀请多次

    def __str__(self):
        return f"{self.user_share.user.username} 邀请了 {self.invited_user.username}"



