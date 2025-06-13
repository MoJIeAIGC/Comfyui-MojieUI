import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache
from user.models import SysUser

logger = logging.getLogger(__name__)

@receiver(post_save, sender=SysUser)
def set_default_auto_save_setting(sender, instance, created, **kwargs):
    """
    当新用户创建时，设置ComfyUI任务自动保存到云空间的默认值
    """
    if created:
        try:
            # 获取全局设置作为用户默认设置
            global_setting = cache.get("comfyui_auto_save_default_global", False)
            
            # 设置用户级别的自动保存设置
            user_cache_key = f"comfyui_auto_save_default_{instance.id}"
            cache.set(user_cache_key, global_setting, timeout=None)  # 永不过期
            
            logger.info(f"已为新用户 {instance.username} (ID: {instance.id}) 设置ComfyUI任务自动保存默认值: {global_setting}")
        except Exception as e:
            logger.error(f"为用户 {instance.username} 设置ComfyUI任务自动保存默认值失败: {str(e)}") 