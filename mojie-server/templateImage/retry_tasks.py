import logging
from celery import shared_task
from djangoProject import settings
from templateImage.ChatGPTImageService import ChatGPTImageService
from templateImage.GeminiService import GeminiImageService
from templateImage.RequestService import RequestService
from templateImage.models import UserRequest
# tasks.py
from celery.signals import task_failure
logger = logging.getLogger(__name__)
@shared_task(bind=True, max_retries=3)
def retry_failed_request_task(self, request_id):
    """
    异步重试单个失败请求的任务
    """
    try:
        request = UserRequest.objects.get(id=request_id)

        # 根据服务类型选择不同的回调
        if request.service_type == 'chatgpt_image':
            service = ChatGPTImageService()
            callback = lambda data: service.generate_image(
                prompt=data['prompt'],
                image_urls=data.get('image_urls', []),
                api_key=settings.CHATGPT_CONFIG_NEW['API_KEY'],
                api_url=settings.CHATGPT_CONFIG_NEW['API_URL'],
                model=settings.CHATGPT_CONFIG_NEW['MODEL'],
                user_id=data['user_id'],
                conversation_id=data['conversation_id'],
                seed=data.get('seed')
            )
        elif request.service_type == 'gemini_image':
            service = GeminiImageService()
            callback = lambda data: service.generate_image(
                prompt=data['prompt'],
                api_key=settings.GEMINI_CONFIG['API_KEY'],
                model=data.get('model', settings.GEMINI_CONFIG['DEFAULT_MODEL']),
                image_urls=data.get('image_urls', []),
                aspect_ratio=data.get('aspect_ratio', 'Free (自由比例)'),
                temperature=data.get('temperature', 1.0),
                seed=data.get('seed'),
                user_id=data['user_id'],
                conversation_id=data.get('conversation_id'),
                enable_long_context=data.get('enable_long_context', True)
            )

        return RequestService.retry_request(request_id, callback)

    except Exception as e:
        # 如果重试失败，使用 exponential backoff 策略
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

@task_failure.connect
def handle_task_failure(sender=None, task_id=None, exception=None, args=None, **kwargs):
    from django.core.mail import mail_admins

    # 发送管理员邮件
    mail_admins(
        subject=f"Celery Task Failed: {sender.name}",
        message=f"Task {task_id} failed with {exception}\nArgs: {args}"
    )

    # 也可以记录到数据库或日志系统
    logger.critical(f"Task failed: {task_id}, Error: {exception}")