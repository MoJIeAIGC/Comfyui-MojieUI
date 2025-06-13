from datetime import timezone

from django.db import models
from django.core.validators import MinValueValidator

from user.models import SysUser
# Create your models here.
class Product(models.Model):
    """
    订单模型，包含价格、种子和描述信息。

    Attributes:
        price (int): 订单的价格。
        seed (int): 种子值，用于特定的业务逻辑。
        description (str): 订单的描述信息。
    """
    price = models.DecimalField(
        verbose_name="价格",
        max_digits=10,  # 最大位数（包含小数位）
        decimal_places=2,  # 小数位数
        default=0.00  # 默认值
    )
    points = models.IntegerField(verbose_name="种子值")
    description = models.CharField(max_length=255, verbose_name="描述信息")
    about = models.TextField(verbose_name="产品描述", blank=True, null=True)
    gift_points = models.IntegerField(default=0, verbose_name="赠送种子值")
    way = models.IntegerField(default=0, verbose_name="平台")
    method = models.CharField(default="", max_length=255, verbose_name="描述信息")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    is_delete = models.BooleanField(default=False, verbose_name="是否删除")
    exchange_min_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1.00,
        verbose_name="最小兑换金额"
    )

    @property
    def exchange_unit(self):
        """返回最小兑换单位（如0.1元）"""
        return 1 / float(self.points) if self.points else 0
    class Meta:
        verbose_name = "订单信息"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"Order: {self.description}"


class Order(models.Model):
    # 订单状态选项
    STATUS_CHOICES = (
        (0, '待支付'),
        (1, '已支付'),
        (2, '已发货'),
        (3, '已完成'),
        (4, '已取消'),
        (5, '已退款'),
    )

    # 支付方式选项
    PAYMENT_CHOICES = (
        (1, '支付宝'),
        (2, '微信支付'),
        (3, '银行卡'),
        (4, '现金'),
    )

    id = models.AutoField(primary_key=True, verbose_name="订单ID")
    order_no = models.CharField(max_length=64, unique=True, verbose_name="订单编号")
    user = models.ForeignKey(SysUser, on_delete=models.SET_NULL, null=True, verbose_name="关联用户")

    # 订单基本信息
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)],
                                       verbose_name="订单总金额")
    actual_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)],
                                        verbose_name="实付金额")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, verbose_name="商品信息")
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="优惠金额")
    freight = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="运费")

    # 订单状态
    status = models.IntegerField(choices=STATUS_CHOICES, default=0, verbose_name="订单状态")
    payment_method = models.IntegerField(choices=PAYMENT_CHOICES, null=True, blank=True, verbose_name="支付方式")
    payment_time = models.DateTimeField(null=True, blank=True, verbose_name="支付时间")

    # 收货信息
    receiver_name = models.CharField(max_length=50, verbose_name="收货人姓名")
    receiver_phone = models.CharField(max_length=20, verbose_name="收货人电话")
    receiver_address = models.CharField(max_length=255, verbose_name="收货地址")
    receiver_postcode = models.CharField(max_length=20, null=True, blank=True, verbose_name="邮政编码")

    # 时间信息
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    complete_time = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")

    # 其他信息
    remark = models.CharField(max_length=500, null=True, blank=True, verbose_name="订单备注")
    is_delete = models.BooleanField(default=False, verbose_name="是否删除")

    class Meta:
        db_table = "order"
        verbose_name = "订单"
        verbose_name_plural = "订单"
        ordering = ['-create_time']

    def __str__(self):
        return f"订单{self.order_no}({self.get_status_display()})"

class Payment(models.Model):
    """支付记录模型"""
    STATUS_CHOICES = (
        (0, '待支付'),
        (1, '已支付'),
        (2, '支付失败'),
        (3, '已退款'),
        (4, '已取消'),
    )

    PAYMENT_METHODS = (
        (1, '支付宝'),
        (2, '微信支付'),
        (3, '银行卡'),
    )

    id = models.AutoField(primary_key=True, verbose_name="支付ID")
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, related_name='payments', verbose_name="关联订单")
    user = models.ForeignKey(SysUser, on_delete=models.SET_NULL, null=True, verbose_name="支付用户")

    # 支付信息
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="支付金额")
    currency = models.CharField(max_length=3, default='CNY', verbose_name="货币类型")
    status = models.IntegerField(choices=STATUS_CHOICES, default=0, verbose_name="支付状态")
    payment_method = models.IntegerField(choices=PAYMENT_METHODS, verbose_name="支付方式")

    # 时间信息
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    pay_time = models.DateTimeField(null=True, blank=True, verbose_name="支付时间")

    # 第三方支付平台信息
    transaction_id = models.CharField(max_length=100, null=True, blank=True, verbose_name="交易流水号")
    raw_response = models.JSONField(default=dict, blank=True, verbose_name="原始响应数据")

    # 其他信息
    description = models.CharField(max_length=500, null=True, blank=True, verbose_name="支付描述")
    is_delete = models.BooleanField(default=False, verbose_name="是否删除")

    class Meta:
        db_table = "payment"
        verbose_name = "支付记录"
        verbose_name_plural = "支付记录"
        ordering = ['-create_time']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['status']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"支付记录{self.id}({self.get_status_display()})"

class Refund(models.Model):
    """退款记录模型"""
    STATUS_CHOICES = (
        (0, '处理中'),
        (1, '成功'),
        (2, '失败'),
    )

    id = models.AutoField(primary_key=True, verbose_name="退款ID")
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name='refunds', verbose_name="关联支付")

    # 退款信息
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="退款金额")
    reason = models.CharField(max_length=500, null=True, blank=True, verbose_name="退款原因")
    status = models.IntegerField(choices=STATUS_CHOICES, default=0, verbose_name="退款状态")

    # 时间信息
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    refund_time = models.DateTimeField(null=True, blank=True, verbose_name="退款时间")

    # 第三方支付平台信息
    transaction_id = models.CharField(max_length=100, null=True, blank=True, verbose_name="退款流水号")
    raw_response = models.JSONField(default=dict, blank=True, verbose_name="原始响应数据")

    # 其他信息
    is_delete = models.BooleanField(default=False, verbose_name="是否删除")

    class Meta:
        db_table = "refund"
        verbose_name = "退款记录"
        verbose_name_plural = "退款记录"
        ordering = ['-create_time']

    def __str__(self):
        return f"退款记录{self.id}({self.get_status_display()})"


class UserVIP(models.Model):
    VIP_LEVELS = (
        ('vip_basic', '月度VIP'),
        ('vip_premium', '季度VIP'),
        ('vip_platinum', '年度VIP'),
    )

    user = models.ForeignKey(SysUser, on_delete=models.CASCADE, related_name='vip_info')
    level = models.CharField(max_length=20, choices=VIP_LEVELS, default='vip_basic')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    last_payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True)

    class Meta:
        indexes = [models.Index(fields=['end_time', 'is_active'])]
        verbose_name = 'VIP会员信息'
        verbose_name_plural = verbose_name

    @property
    def remaining_days(self):
        """剩余天数"""
        delta = self.end_time - timezone.now()
        return delta.days if delta.days > 0 else 0

    def check_status(self):
        """检查并更新VIP状态"""
        now = timezone.now()
        if now > self.end_time and self.is_active:
            self.is_active = False
            self.save()
        return self.is_active
