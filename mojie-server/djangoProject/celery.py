# your_project/celery.py
from celery import Celery
from celery.schedules import crontab

app = Celery('djangoProject')

# 添加重试配置
app.conf.update(
    beat_schedule = {
        'check-vip-expiration': {
            'task': 'order.tasks.check_vip_expiration',
            'schedule': crontab(hour=0, minute=0),  # 每天凌晨执行
        },
        'cancel-timeout-orders': {
            'task': 'order.tasks.cancel_timeout_orders',
            'schedule': crontab(minute='*/5'),  # 每5分钟执行一次
        },
        'retry_failed_request_task': {
            'default_retry_delay': 200,  # 默认5分钟
            'max_retries': 3,
            'retry_backoff': True,  # 启用指数退避
            'retry_backoff_max': 3600,  # 最大延迟1小时
            'retry_jitter': True,  # 添加随机抖动
        }
    }
)