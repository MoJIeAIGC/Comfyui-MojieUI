import logging
from django.db import transaction
from .models import ImageUploadRecord, RequestStatus
import time
from common.db_utils import with_db_retry, ensure_connection

logger = logging.getLogger(__name__)


class ImageUploadManager:
    """
    图片上传记录管理服务类
    提供完整的图片上传记录创建和状态管理功能
    """

    @classmethod
    def create_upload_record(
            cls,
            user_id: int,
            conversation_id: int,
            image_list: str,
            prompt: str,
            model_used: str,
            image_url: str = "",
            image_name: str = "",
            seed_used: str = "",
            status: str = RequestStatus.PENDING,
            **extra_fields
    ) -> ImageUploadRecord:
        """
        创建图片上传记录（完整参数版）

        参数:
            user_id: 用户ID (必填)
            conversation_id: 会话ID (必填)
            image_list: 图片列表JSON字符串 (必填)
            prompt: 生成提示词 (必填)
            model_used: 使用的模型名称 (必填)
            image_url: 图片结果URL (可选)
            image_name: 图片文件名 (可选)
            seed_used: 使用的随机种子 (可选)
            status: 初始状态 (默认PENDING)
            extra_fields: 其他模型字段

        返回:
            ImageUploadRecord: 创建的记录对象

        异常:
            ValueError: 当必填参数缺失时
            Exception: 数据库操作失败时
        """
        try:
            # 参数校验
            if not all([user_id, conversation_id, prompt, model_used]):
                raise ValueError("缺少必填参数")
            
            # 创建记录
            record = ImageUploadRecord.objects.create(
                user_id=user_id,
                conversation_id=conversation_id,
                image_list=image_list,
                prompt=prompt,
                model_used=model_used,
                image_url=image_url,
                image_name=image_name,
                seed_used=seed_used,
                status=status,
                **extra_fields
            )
            
            logger.info(f"创建图片上传记录成功，ID: {record.id}")
            return record

        except Exception as e:
            logger.error(f"创建图片上传记录失败: {str(e)}", exc_info=True)
            raise

    @classmethod
    def update_record_status(cls, record_id, status, **kwargs):
        """
        更新记录状态及相关字段
        :param record_id: 记录ID
        :param status: 新状态 (RequestStatus枚举值)
        :param kwargs: 状态相关字段
                      COMPLETED需传 image_url, [image_name]
                      FAILED需传 error_message
        :return: bool 是否更新成功
        """
        try:
            # 确保连接可用
            ensure_connection()
            
            record = ImageUploadRecord.objects.get(id=record_id)

            # 状态校验
            if status not in dict(RequestStatus.choices):
                raise ValueError(f"无效状态: {status}")

            # 状态特定字段处理
            if status == RequestStatus.COMPLETED:
                if 'image_url' not in kwargs:
                    raise ValueError("COMPLETED状态必须提供image_url")
                record.image_url = kwargs['image_url']
                if 'image_name' in kwargs:
                    record.image_name = kwargs['image_name']

            elif status == RequestStatus.FAILED:
                if 'error_message' not in kwargs:
                    raise ValueError("FAILED状态必须提供error_message")
                record.image_url = f"Error: {kwargs['error_message']}"

            # 更新状态和修改时间
            record.status = status
            update_fields = ['status', 'upload_time']

            # 动态添加其他需要更新的字段
            for field in ['image_url', 'image_name']:
                if field in kwargs:
                    update_fields.append(field)

            record.save(update_fields=update_fields)
            return True

        except ImageUploadRecord.DoesNotExist:
            logger.error(f"记录不存在: {record_id}")
            return False
        except ValueError as e:
            logger.warning(f"参数错误: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"状态更新失败: {str(e)}")
            return False

    @classmethod
    @with_db_retry(max_retries=3, retry_delay=1)
    def update_record_by_id(cls, record_id, **update_fields):
        """
        根据ID更新图片上传记录
        :param record_id: 记录ID
        :param update_fields: 需要更新的字段键值对
        :return: 更新后的记录对象
        """
        try:
            # 确保连接可用
            ensure_connection()
            
            record = ImageUploadRecord.objects.get(id=record_id)
            for field, value in update_fields.items():
                if hasattr(record, field):
                    setattr(record, field, value)
            record.save()
            return record
        except ImageUploadRecord.DoesNotExist:
            logger.error(f"图片上传记录不存在，ID: {record_id}")
            raise
        except Exception as e:
            logger.error(f"更新记录失败: {str(e)}")
            raise

    # 状态快捷方法 --------------------------------------------------

    @classmethod
    def mark_as_processing(cls, record_id: int) -> bool:
        """标记为处理中状态"""
        return cls.update_upload_status(
            record_id=record_id,
            status=RequestStatus.PROCESSING
        )

    @classmethod
    @with_db_retry(max_retries=3, retry_delay=1)
    def mark_as_completed(cls, record_id, image_url, image_name=None):
        """标记为已完成"""
        try:
            # 确保连接可用
            ensure_connection()
            
            return cls.update_record_status(
                record_id=record_id,
                status=RequestStatus.COMPLETED,
                image_url=image_url,
                image_name=image_name
            )
        except Exception as e:
            logger.error(f"标记完成状态失败: {str(e)}")
            raise

    @classmethod
    @with_db_retry(max_retries=3, retry_delay=1)
    def mark_as_failed(cls, record_id, error_message):
        """标记为已失败"""
        try:
            # 确保连接可用
            ensure_connection()
            
            return cls.update_record_status(
                record_id=record_id,
                status=RequestStatus.FAILED,
                error_message=error_message
            )
        except Exception as e:
            logger.error(f"标记失败状态时出错: {str(e)}")
            # 尝试直接更新数据库
            try:
                record = ImageUploadRecord.objects.get(id=record_id)
                record.status = RequestStatus.FAILED
                record.image_url = f"Error: {error_message}"
                record.save(update_fields=['status', 'image_url', 'upload_time'])
                return True
            except Exception as db_error:
                logger.error(f"直接更新数据库失败: {str(db_error)}")
                return False

    @classmethod
    def get_record(cls, record_id: int) -> ImageUploadRecord:
        """获取记录对象"""
        try:
            return ImageUploadRecord.objects.get(id=record_id)
        except ImageUploadRecord.DoesNotExist:
            logger.error(f"记录不存在: {record_id}")
            raise

    @classmethod
    def mark_as_processed(cls, record_id, result_url, seed_used=None):
        """标记为已处理（处理完成后的状态）
        
        Args:
            record_id: 记录ID
            result_url: 结果图片URL
            seed_used: 使用的随机种子
            
        Returns:
            bool: 操作是否成功
        """
        try:
            record = ImageUploadRecord.objects.get(id=record_id)
            record.status = RequestStatus.COMPLETED
            record.image_url = result_url
            
            # 更新种子值（如果提供）
            if seed_used is not None:
                record.seed_used = str(seed_used)
                
            record.save(update_fields=['status', 'image_url', 'seed_used', 'upload_time'])
            logger.info(f"标记记录为已处理状态成功，ID: {record_id}")
            return True
        except ImageUploadRecord.DoesNotExist:
            logger.error(f"记录不存在: {record_id}")
            return False
        except Exception as e:
            logger.error(f"标记为已处理状态失败: {str(e)}")
            return False
            
    @classmethod
    @with_db_retry(max_retries=3, retry_delay=1)
    def update_oss_info(cls, record_id, oss_url):
        """更新OSS信息
        
        Args:
            record_id: 记录ID
            oss_url: OSS存储URL
            
        Returns:
            bool: 操作是否成功
        """
        ensure_connection()
        try:
            with transaction.atomic():
                record = ImageUploadRecord.objects.get(id=record_id)
                record.image_url = oss_url
                record.save(update_fields=['image_url', 'upload_time'])
                logger.info(f"更新OSS信息成功，ID: {record_id}")
                return True
        except ImageUploadRecord.DoesNotExist:
            logger.error(f"记录不存在: {record_id}")
            return False
        except Exception as e:
            logger.error(f"更新OSS信息失败: {str(e)}")
            # 尝试直接更新数据库
            try:
                with transaction.atomic():
                    record = ImageUploadRecord.objects.get(id=record_id)
                    record.image_url = oss_url
                    record.save(update_fields=['image_url', 'upload_time'])
                    return True
            except Exception as db_error:
                logger.error(f"直接更新数据库失败: {str(db_error)}")
                return False