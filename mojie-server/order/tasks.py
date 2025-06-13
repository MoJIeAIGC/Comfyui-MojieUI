# tasks.py
from datetime import timedelta

from celery import shared_task
from django.utils import timezone
import logging

from order.models import Order

logger = logging.getLogger(__name__)

@shared_task
def check_vip_expiration():
    """每天检查VIP过期情况"""
    from .models import UserVIP

    expired_count = UserVIP.objects.filter(
        end_time__lte=timezone.now(),
        is_active=True
    ).update(is_active=False)

    logger.info(f"VIP过期检查完成，共处理{expired_count}个过期会员")

@shared_task
def cancel_timeout_orders():
    """
    取消超时未支付的订单
    默认30分钟未支付则取消订单
    """
    try:
        # 获取30分钟前的时间点
        timeout_threshold = timezone.now() - timedelta(minutes=30)
        
        # 查找所有待支付且创建时间超过30分钟的订单
        timeout_orders = Order.objects.filter(
            status=0,  # 待支付状态
            create_time__lt=timeout_threshold,
            is_delete=False
        )
        
        # 更新订单状态
        for order in timeout_orders:
            order.status = 4  # 已取消
            order.remark = "超时未支付，系统自动取消"
            order.save()
            logger.info(f"订单 {order.order_no} 因超时未支付已自动取消")
            
        return f"成功取消 {timeout_orders.count()} 个超时订单"
        
    except Exception as e:
        logger.error(f"取消超时订单时发生错误: {str(e)}")
        raise