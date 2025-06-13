import configparser
import logging
import time
from datetime import timezone
from pathlib import Path
from typing import Dict, List

from django.core.files.uploadedfile import InMemoryUploadedFile
import uuid
from concurrent.futures import ThreadPoolExecutor

from django_redis import cache

from common.ConfigUtils import ConfigUtils
from common.ErrorCode import ErrorCode
from common.volcengine_tos_utils import VolcengineTOSUtils
from user.models import SysUser
from . import queue_service
from .models import templateImage, ComfyUITask
from templateImage.utils import Utils  # 假设这是你处理图片的工具模块
from exception.business_exception import BusinessException  # 导入自定义异常
from .task_utils import TaskUtils
from .workflow import Workflow
from .ConfigPathManager import ConfigPathManager

logger = logging.getLogger(__name__)


class ImageService:

    @staticmethod
    def get_template_images_by_method_and_related(image_method, related_image):
        """
        根据 image_method 和 related_image 查询 templateImage 对象
        :param image_method: 图片类别（必填）
        :param related_image: 关联图片 ID（必填）
        :return: 查询到的 templateImage 对象列表
        :raises ValidationError: 如果参数缺失或查询结果为空
        """
        if not image_method:
            raise BusinessException(error_code=ErrorCode.NOT_PARAMETER.code, data='', errors="image_method 和 related_image 参数缺一不可")

        if not related_image:  # related_id 为空时直接返回 None
            return None
        # 查询条件
        queryset = templateImage.objects.filter(
            image_method=image_method,
            related_image=related_image
        )

        if not queryset.exists():
            return None

        return queryset

    @staticmethod
    def upload_image(image: InMemoryUploadedFile, description: str, image_method: str, method_su: str, related_img: templateImage, user: SysUser, request=None) -> str:
        """
        上传图片并返回图片的完整 URL
        :param image: 图片对象（必填）
        :param description: 图片描述（必填）
        :param image_method: 图片类别
        :param method_su: 模板图片细分
        :param related_img: 关联图片
        :param user: 用户对象
        :param request: 请求对象
        :return: 图片的完整 URL 和 ID
        """
        try:
            # 检查参数有效性
            if not image:
                raise BusinessException(error_code=ErrorCode.INVALID_REQUEST, data='', errors='图片不能为空！')
            if not description:
                raise BusinessException(error_code=ErrorCode.INVALID_REQUEST, data='', errors='描述不能为空！')
            if not user:
                raise BusinessException(error_code=ErrorCode.INVALID_REQUEST, data='', errors='用户不能为空！')

            folder_name = 'upload'

            # 1. 读取图片数据
            img_data = image.read()

            # 2. 将图片上传到OSS存储
            # 生成不重复的图片名称
            img_name = str(uuid.uuid4()) + '.png'

            # 调用 aliyunOSS_utills 中的 upload_file 函数上传图片
            # img_url = upload_file(bucket, img_name, img_data)
            full_object_name = f"{folder_name}/{img_name}"
            tos_utils = VolcengineTOSUtils()
            img_url = tos_utils.upload_image(full_object_name, file_data=img_data)
            if not img_url:
                raise BusinessException(error_code=ErrorCode.INTERNAL_ERROR, data='', errors='图片上传到 OSS 失败！')


            # 3. 将图片信息保存到数据库
            image_instance = templateImage.objects.create(
                image_name=img_name,
                image_address=img_url,
                description=description,
                image_method=image_method,
                method_sub=method_su,
                userImage=user,
                related_image=related_img,
                isDelete=0
            )

            # 4. 返回包含图片 URL 和图片 ID 的字典
            return {
                "image_url": img_url,
                "image_id": image_instance.id  # 返回图片的 ID
            }
        except BusinessException as e:
            # 捕获业务异常并重新抛出
            logger.error(f'图片上传失败，业务异常: {e.errors}')
            raise e
        except Exception as error:
            # 记录错误日志并抛出异常
            logger.error(f'图片上传失败，服务器内部错误: {error}')
            raise BusinessException(error_code=ErrorCode.INTERNAL_ERROR, data='', errors='图片上传失败！服务器内部错误')

    """
    文生图业务
    :param description: 图片描述（必填）
    :param SysUser: 用户信息（必填）
    :return: 图片的完整 URL
    """
    # 文生图（使用标准工作流）
    @staticmethod
    def text_to_image(description: str, user, priority: str = "medium") -> Dict:
        """
        文本生成图像并返回任务信息
        :param description: 图像描述
        :param user: 用户对象
        :param priority: 任务优先级 (low, medium, high)
        :param kwargs: 其他参数
        :return: 任务信息
        """
        try:
            # 使用ConfigPathManager获取工作流文件路径
            workflow_file = ConfigPathManager.get_workflow_file_path("comfyuiTextImage")

            # 获取服务器连接信息
            server_address = ConfigUtils.get("comfyuiTextImage", "server_address")
            username = ConfigUtils.get("comfyuiTextImage", "username")
            password = ConfigUtils.get("comfyuiTextImage", "password")

            # 准备任务数据
            task_data = {
                'workflow_file': workflow_file,
                'prompt_updates': {
                    "6": {"inputs": {"text": description}}
                },
                'description': description,
                'user_id': user.id if user else None,
                'priority': priority,
                'server_address': server_address,
                'username': username,
                'password': password
            }

            # 创建异步任务
            task_info = TaskUtils.create_async_task(
                task_type='text_to_image',
                task_data=task_data,
                user=user,
                priority=priority
            )

            return task_info

        except Exception as e:
            logger.error(f"创建文生图任务失败: {str(e)}")
            raise BusinessException(
                error_code=ErrorCode.SYSTEM_ERROR,
                data=None,
                errors=str(e)
            )

    @staticmethod
    def text_to_generate_images(description: str, height: int, width: int, seed, quantity, user, priority: str = "medium", add_new_data: str = "") -> Dict:
        """
        线上文生图
        """
        try:
            # 使用ConfigPathManager获取工作流文件路径
            workflow_file = ConfigPathManager.get_workflow_file_path("comfyuiTextToGenerateImages")
            server_address = ConfigUtils.get("comfyuiTextToGenerateImages", "server_address")
            username = ConfigUtils.get("comfyuiTextToGenerateImages", "username")
            password = ConfigUtils.get("comfyuiTextToGenerateImages", "password")
            # 准备任务数据
            task_data = {
                'workflow_file': workflow_file,
                'server_address': server_address,
                'username': username,
                'password': password,
                'prompt_updates': {
                    "6": {"inputs": {"text": description}},
                    "25": {"inputs": {"noise_seed": seed}},
                    "27": {"inputs": {"batch_size": quantity}},
                    "66": {"inputs": {"value": width}},
                    "67": {"inputs": {"value": height}}
                },
                'target_node_id': "49",
                'description': description,
                'height': height,
                'width': width,
                "batch_size": quantity,
                'noise_seed': seed,
                'user_id': user.id,
                'metadata': {
                    'description': description,
                    'height': height,
                    'width': width,
                    "batch_size": quantity,
                    'noise_seed': seed,
                    'add_new_data': add_new_data
                }
            }

            # 创建异步任务
            task_info = TaskUtils.create_async_task(
                task_type='text_to_image',
                task_data=task_data,
                user=user,
                priority=priority
            )

            return task_info

        except Exception as e:
            logger.error(f"创建上线文生图任务失败: {str(e)}")
            raise BusinessException(
                error_code=ErrorCode.SYSTEM_ERROR,
                data=None,
                errors=str(e)
            )

    @staticmethod
    def text_to_generate_images_new(description: str, height: int, width: int, seed, quantity, model_used, user,
                                priority: str = "medium", add_new_data: str = "") -> Dict:
        """
        线上文生图
        """
        try:
            # 使用ConfigPathManager获取工作流文件路径
            workflow_file = ConfigPathManager.get_workflow_file_path("comfyuiTextToGenerateImages")
            server_address = ConfigUtils.get("comfyuiTextToGenerateImages", "server_address")
            username = ConfigUtils.get("comfyuiTextToGenerateImages", "username")
            password = ConfigUtils.get("comfyuiTextToGenerateImages", "password")

            # 准备任务数据
            task_data = {
                'workflow_file': workflow_file,
                'server_address': server_address,
                'username': username,
                'password': password,
                'prompt_updates': {
                    "6": {"inputs": {"text": description}},
                    "25": {"inputs": {"noise_seed": seed}},
                    "27": {"inputs": {"batch_size": quantity}},
                    "47": {"inputs": {"lora_name": model_used}},
                    "66": {"inputs": {"value": width}},
                    "67": {"inputs": {"value": height}}
                },
                'target_node_id': "49",
                'description': description,
                'height': height,
                'width': width,
                "batch_size": quantity,
                'noise_seed': seed,
                'user_id': user.id,
                'metadata': {
                    'description': description,
                    'height': height,
                    'width': width,
                    "batch_size": quantity,
                    'noise_seed': seed,
                    'add_new_data': add_new_data
                }
            }

            # 创建异步任务
            task_info = TaskUtils.create_async_task(
                task_type='text_to_image',
                task_data=task_data,
                user=user,
                priority=priority
            )

            return task_info

        except Exception as e:
            logger.error(f"创建上线文生图任务失败: {str(e)}")
            raise BusinessException(
                error_code=ErrorCode.SYSTEM_ERROR,
                data=None,
                errors=str(e)
            )


    # 图生图任务
    @staticmethod
    def images_image(description: str, url: str, user: SysUser, priority: str = "medium", add_new_data: str = "") -> Dict:
        """
        图像替换并返回任务信息
        :param description: 图像描述
        :param url: 输入图像URL
        :param user: 用户对象
        :param priority: 任务优先级 (low, medium, high)
        :param request: 请求对象
        :return: 任务信息
        """
        workflow_file = ConfigUtils.get_path("comfyuiImageImages", "workflow_file")
        server_address = ConfigUtils.get("comfyuiImageImages", "server_address")
        username = ConfigUtils.get("comfyuiImageImages", "username")
        password = ConfigUtils.get("comfyuiImageImages", "password")
        try:
            # 准备任务数据
            task_data = {
                'workflow_file': workflow_file,
                'prompt_updates': {
                    "6": {"inputs": {"text": description}},
                    "7": {"inputs": {"url": url}}
                },
                'description': description,
                'url': url,
                'user_id': user.id if user else None,
                'priority': priority,
                'server_address': server_address,
                'username': username,
                'password': password,
                'add_new_data': add_new_data
            }

            # 创建异步任务
            task_info = TaskUtils.create_async_task(
                task_type='images_image',
                task_data=task_data,
                user=user,
                priority=priority
            )

            return task_info

        except Exception as e:
            logger.error(f"创建图像生成任务失败: {str(e)}")
            raise BusinessException(
                error_code=ErrorCode.SYSTEM_ERROR,
                data=None,
                errors=str(e)
            )

    @staticmethod
    def images_image_image_text(
            description: str,
            level: float,
            white_background_product_url: str,
            template_url: str,
            mask_url: str,
            user: SysUser,
            priority: str = "medium",
            add_new_data: str = ""
    ) -> Dict:
        """
        产品图放入模板并返回任务信息
        :param description: 图像描述
        :param level: 调整级别
        :param white_background_product_url: 白底产品图URL
        :param template_url: 模板URL
        :param mask_url: 蒙版URL
        :param user: 用户对象
        :param priority: 任务优先级 (low, medium, high)
        :param request: 请求对象 (不再使用)
        :return: 任务信息
        """
        workflow_file = ConfigUtils.get_path("comfyuiProductImageInTemplate", "workflow_file")
        server_address = ConfigUtils.get("comfyuiProductImageInTemplate", "server_address")
        username = ConfigUtils.get("comfyuiProductImageInTemplate", "username")
        password = ConfigUtils.get("comfyuiProductImageInTemplate", "password")         
        try:
            # 准备任务数据
            task_data = {
                'workflow_file': workflow_file,
                'server_address': server_address,
                'username': username,
                'password': password,
                'prompt_updates': {
                    "64": {"inputs": {"text": description}},
                    "279": {"inputs": {"float": level}},
                    "296": {"inputs": {"url": white_background_product_url}},
                    "297": {"inputs": {"url": template_url}},
                    "298": {"inputs": {"url": mask_url}}
                },
                'target_node_id': "203",
                'description': description,
                'priority': priority,
                'level': level,
                'white_background_product_url': white_background_product_url,
                'template_url': template_url,
                'mask_url': mask_url,
                'user_id': user.id,
                'metadata': {
                    'level': level,
                    'product_url': white_background_product_url,
                    'template_url': template_url,
                    'mask_url': mask_url,
                    'add_new_data': add_new_data
                }
            }

            # 创建异步任务
            task_info = TaskUtils.create_async_task(
                task_type='product_replace',
                task_data=task_data,
                user=user,
                priority=priority
            )

            return task_info

        except Exception as e:
            logger.error(f"创建产品替换任务失败: {str(e)}")
            raise BusinessException(
                error_code=ErrorCode.SYSTEM_ERROR,
                data=None,
                errors=str(e)
            )

    @staticmethod
    def product_replacement_workflow(
            description: str,
            level: float,
            seed: int,
            white_background_product_url: str,
            white_mask_url: str,
            template_url: str,
            mask_url: str,
            user: SysUser,
            priority: str = "medium",
            add_new_data: str = ""
    ) -> Dict:
        """
        产品图放入模板并返回任务信息-上线版本工作流任务
        :param description: 图像描述
        :param level: 调整级别
        :param white_background_product_url: 白底产品图URL
        :param template_url: 模板URL
        :param mask_url: 蒙版URL
        :param user: 用户对象
        :param priority: 任务优先级 (low, medium, high)
        :param request: 请求对象 (不再使用)
        :return: 任务信息
        """
        workflow_file = ConfigUtils.get_path("comfyuiProductImageInTemplateReplace", "workflow_file")               
        server_address = ConfigUtils.get("comfyuiProductImageInTemplateReplace", "server_address")
        username = ConfigUtils.get("comfyuiProductImageInTemplateReplace", "username")
        password = ConfigUtils.get("comfyuiProductImageInTemplateReplace", "password")
        try:
            # 准备任务数据
            task_data = {
                'workflow_file': workflow_file,
                'server_address': server_address,
                'username': username,
                'password': password,
                'prompt_updates': {
                    "64": {"inputs": {"text": description}},
                    "92": {"inputs": {"noise_seed": seed}},
                    "181": {"inputs": {"reference_influence": level}},
                    "311": {"inputs": {"url": mask_url}},
                    "312": {"inputs": {"url": template_url}},
                    "313": {"inputs": {"url": white_mask_url}},
                    "314": {"inputs": {"url": white_background_product_url}},
                },
                'target_node_id': "276",
                'description': description,
                'priority': priority,
                'level': level,
                'seed': seed,
                'white_background_product_url': white_background_product_url,
                'white_mask_url': white_mask_url,
                'template_url': template_url,
                'mask_url': mask_url,
                'user_id': user.id,
                'metadata': {
                    'description': description,
                    'priority': priority,
                    'level': level,
                    'seed': seed,
                    'white_background_product_url': white_background_product_url,
                    'white_mask_url': white_mask_url,
                    'template_url': template_url,
                    'mask_url': mask_url,
                    'add_new_data': add_new_data
                }
            }

            # 创建异步任务
            task_info = TaskUtils.create_async_task(
                task_type='product_replace',
                task_data=task_data,
                user=user,
                priority=priority
            )

            return task_info

        except Exception as e:
            logger.error(f"创建新产品替换任务失败: {str(e)}")
            raise BusinessException(
                error_code=ErrorCode.SYSTEM_ERROR,
                data=None,
                errors=str(e)
            )

    @staticmethod
    def fine_detail_workflow(
            description: str,
            level: float,
            url: str,
            mask_url: str,
            seed,
            user: SysUser,
            priority: str = "medium" ,
            add_new_data: str = ""
    ) -> Dict:
        """
        细节精修-上线版本工作流任务
        """
        workflow_file = ConfigUtils.get_path("comfyuiFineDetailWorkflow", "workflow_file")
        server_address = ConfigUtils.get("comfyuiFineDetailWorkflow", "server_address")
        username = ConfigUtils.get("comfyuiFineDetailWorkflow", "username")
        password = ConfigUtils.get("comfyuiFineDetailWorkflow", "password")
        try:
            # 准备任务数据
            task_data = {
                'workflow_file': workflow_file,
                'server_address': server_address,
                'username': username,
                'password': password,
                'prompt_updates': {
                    "6": {"inputs": {"text": description}},
                    "103": {"inputs": {"denoise": level}},
                    "105": {"inputs": {"noise_seed": seed}},
                    "143": {"inputs": {"url": url}},
                    "144": {"inputs": {"url": mask_url}}
                },
                'target_node_id': "129",
                'description': description,
                'priority': priority,
                'level': level,
                'url': url,
                'mask_url': mask_url,
                'noise_seed': seed,
                'user_id': user.id,
                'metadata': {
                    'description': description,
                    'priority': priority,
                    'level': level,
                    'url': url,
                    'mask_url': mask_url,
                    'noise_seed': seed,
                    'add_new_data': add_new_data
                }
            }

            # 创建异步任务
            task_info = TaskUtils.create_async_task(
                task_type='fine_detail',
                task_data=task_data,
                user=user,
                priority=priority
            )

            return task_info

        except Exception as e:
            logger.error(f"创建细节精修任务失败: {str(e)}")
            raise BusinessException(
                error_code=ErrorCode.SYSTEM_ERROR,
                data=None,
                errors=str(e)
            )

    @staticmethod
    def wide_picture_workflow(
            description: str,
            url: str,
            left,
            top,
            right,
            bottom,
            seed,
            user: SysUser,
            priority: str = "medium",
            add_new_data: str = ""
    ) -> Dict:
        """
        阔图-上线版本工作流任务
        """
        try:
            # 使用ConfigPathManager获取工作流文件路径
            workflow_file = ConfigPathManager.get_workflow_file_path("comfyuiWidePictureWorkflow")
            server_address = ConfigUtils.get("comfyuiWidePictureWorkflow", "server_address")
            username = ConfigUtils.get("comfyuiWidePictureWorkflow", "username")
            password = ConfigUtils.get("comfyuiWidePictureWorkflow", "password")
            logger.info(f"阔图工作流使用文件: {workflow_file}")
            
            # 准备任务数据
            task_data = {
                'workflow_file': workflow_file,
                'server_address': server_address,
                'username': username,
                'password': password,
                'prompt_updates': {
                    "64": {"inputs": {"text": description}},
                    "92": {"inputs": {"noise_seed": seed}},
                    "134": {"inputs": {"left": left, "top": top, "right": right, "bottom": bottom}},
                    "149": {"inputs": {"url": url}}
                },
                'target_node_id': "143",
                'description': description,
                'priority': priority,
                'url': url,
                'noise_seed': seed,
                'user_id': user.id,
                'metadata': {
                    'description': description,
                    'priority': priority,
                    'url': url,
                    'noise_seed': seed,
                    'add_new_data': add_new_data
                }
            }

            # 创建异步任务
            task_info = TaskUtils.create_async_task(
                task_type='wide_picture',
                task_data=task_data,
                user=user,
                priority=priority
            )

            return task_info

        except Exception as e:
            logger.error(f"创建阔图任务失败: {str(e)}")
            raise BusinessException(
                error_code=ErrorCode.SYSTEM_ERROR,
                data=None,
                errors=str(e)
            )

    @staticmethod
    def internal_supplementation_workflow(
            description: str,
            url: str,
            mask_url: str,
            seed,
            user: SysUser,
            priority: str = "medium",
            add_new_data: str = ""
    ) -> Dict:
        """
        内补-上线版本工作流任务
        """
        try:
            # 使用ConfigPathManager获取工作流文件路径
            workflow_file = ConfigPathManager.get_workflow_file_path("comfyuiInternalSupplementationWorkflow")
            server_address = ConfigUtils.get("comfyuiInternalSupplementationWorkflow", "server_address")
            username = ConfigUtils.get("comfyuiInternalSupplementationWorkflow", "username")
            password = ConfigUtils.get("comfyuiInternalSupplementationWorkflow", "password")
            logger.info(f"内补工作流使用文件: {workflow_file}")
            
            # 准备任务数据
            task_data = {
                'workflow_file': workflow_file,
                'server_address': server_address,
                'username': username,
                'password': password,
                'prompt_updates': {
                    "23": {"inputs": {"text": description}},
                    "3": {"inputs": {"seed": seed}},
                    "80": {"inputs": {"url": url}},
                    "81": {"inputs": {"url": mask_url}}
                },
                'target_node_id': "63",
                'description': description,
                'priority': priority,
                'url': url,
                'mask_url': mask_url,
                'noise_seed': seed,
                'user_id': user.id,
                'metadata': {
                    'description': description,
                    'priority': priority,
                    'url': url,
                    'mask_url': mask_url,
                    'noise_seed': seed,
                    'add_new_data': add_new_data
                }
            }

            # 创建异步任务
            task_info = TaskUtils.create_async_task(
                task_type='internal_supplementation',
                task_data=task_data,
                user=user,
                priority=priority
            )

            return task_info

        except Exception as e:
            logger.error(f"创建内补任务失败: {str(e)}")
            raise BusinessException(
                error_code=ErrorCode.SYSTEM_ERROR,
                data=None,
                errors=str(e)
            )

    @staticmethod
    def internal_supplementation_and_removal_workflow(
            url: str,
            mask_url: str,
            seed,
            user: SysUser,
            priority: str = "medium",
            add_new_data: str = ""
    ) -> Dict:
        """
        内补去除-上线版本工作流任务
        """
        try:
            # 使用ConfigPathManager获取工作流文件路径
            workflow_file = ConfigPathManager.get_workflow_file_path("comfyuiInternalSupplementationAndRemovalWorkflow")
            server_address = ConfigUtils.get("comfyuiInternalSupplementationAndRemovalWorkflow", "server_address")
            username = ConfigUtils.get("comfyuiInternalSupplementationAndRemovalWorkflow", "username")
            password = ConfigUtils.get("comfyuiInternalSupplementationAndRemovalWorkflow", "password")
            logger.info(f"内补去除工作流使用文件: {workflow_file}")
            
            # 准备任务数据
            task_data = {
                'workflow_file': workflow_file,
                'server_address': server_address,
                'username': username,
                'password': password,
                'prompt_updates': {
                    "3": {"inputs": {"seed": seed}},
                    "83": {"inputs": {"url": url}},
                    "84": {"inputs": {"url": mask_url}}
                },
                'target_node_id': "63",
                'priority': priority,
                'url': url,
                'mask_url': mask_url,
                'noise_seed': seed,
                'user_id': user.id,
                'metadata': {
                    'priority': priority,
                    'url': url,
                    'mask_url': mask_url,
                    'noise_seed': seed,
                    'add_new_data': add_new_data
                }
            }

            # 创建异步任务
            task_info = TaskUtils.create_async_task(
                task_type='internal_supplementation_and_removal',
                task_data=task_data,
                user=user,
                priority=priority
            )

            return task_info

        except Exception as e:
            logger.error(f"创建内补去除任务失败: {str(e)}")
            raise BusinessException(
                error_code=ErrorCode.SYSTEM_ERROR,
                data=None,
                errors=str(e)
            )

    @staticmethod
    def xl_wholeimagefix_complete_redrawing_and_refinement_of_the_entire_image_workflow(
            description: str,
            level: float,
            url: str,
            seed,
            user: SysUser,
            priority: str = "medium",
            add_new_data: str = ""
    ) -> Dict:
        """
        重绘精修-上线版本工作流任务
        """
        try:
            # 使用ConfigPathManager获取工作流文件路径
            workflow_file = ConfigPathManager.get_workflow_file_path("comfyuiCompleteRedrawingAndRefinementOfTheEntireImageWorkflow")
            server_address = ConfigUtils.get("comfyuiCompleteRedrawingAndRefinementOfTheEntireImageWorkflow", "server_address")
            username = ConfigUtils.get("comfyuiCompleteRedrawingAndRefinementOfTheEntireImageWorkflow", "username")
            password = ConfigUtils.get("comfyuiCompleteRedrawingAndRefinementOfTheEntireImageWorkflow", "password")
            logger.info(f"重绘精修工作流使用文件: {workflow_file}")
            
            # 准备任务数据
            task_data = {
                'workflow_file': workflow_file,
                'server_address': server_address,
                'username': username,
                'password': password,
                'prompt_updates': {
                    "6": {"inputs": {"text": description}},
                    "3": {"inputs": {"seed": seed, "denoise": level}},
                    "49": {"inputs": {"url": url}},
                },
                'target_node_id': "29",
                'description': description,
                'priority': priority,
                'level': level,
                'url': url,
                'noise_seed': seed,
                'user_id': user.id,
                'metadata': {
                    'description': description,
                    'priority': priority,
                    'level': level,
                    'url': url,
                    'noise_seed': seed,
                    'add_new_data': add_new_data
                }
            }

            # 创建异步任务
            task_info = TaskUtils.create_async_task(
                task_type='complete_redrawing',
                task_data=task_data,
                user=user,
                priority=priority
            )

            return task_info

        except Exception as e:
            logger.error(f"创建重绘精修任务失败: {str(e)}")
            raise BusinessException(
                error_code=ErrorCode.SYSTEM_ERROR,
                data=None,
                errors=str(e)
            )

    @staticmethod
    def product_text_image(description: str, url: str, user: SysUser, priority: str = "medium", add_new_data: str = "") -> Dict:
        """
        产品图替换并返回任务信息
        :param description: 图像描述
        :param url: 输入图像URL
        :param user: 用户对象
        :param priority: 任务优先级 (low, medium, high)
        :param request: 请求对象
        :return: 任务信息
        """
        workflow_file = ConfigUtils.get_path("comfyuiProductTextImage", "workflow_file")    
        server_address = ConfigUtils.get("comfyuiProductTextImage", "server_address")
        username = ConfigUtils.get("comfyuiProductTextImage", "username")
        password = ConfigUtils.get("comfyuiProductTextImage", "password")   
        try:
            # 准备任务数据
            task_data = {
                'workflow_file': workflow_file,
                'server_address': server_address,
                'username': username,
                'password': password,
                'prompt_updates': {
                    "6": {"inputs": {"text": description}},
                    "7": {"inputs": {"url": url}}
                },
                'description': description,
                'url': url,
                'user_id': user.id if user else None,
                'priority': priority,
                'add_new_data': add_new_data
            }

            # 创建异步任务
            task_info = TaskUtils.create_async_task(
                task_type='product_text_image',
                task_data=task_data,
                user=user,
                priority=priority
            )

            return task_info

        except Exception as e:
            logger.error(f"创建产品替换任务失败: {str(e)}")
            raise BusinessException(
                error_code=ErrorCode.SYSTEM_ERROR,
                data=None,
                errors=str(e)
            )

    @staticmethod
    def images_white_background(description: str, url: str, user: SysUser, priority: str = "medium", add_new_data: str = "") -> Dict:
        """
        生成白底图像并返回任务信息
        :param description: 图像描述
        :param url: 输入图像URL
        :param product_image: 产品图像对象
        :param user: 用户对象
        :param priority: 任务优先级 (low, medium, high)
        :param request: 请求对象 (不再使用)
        :return: 任务信息
        """
        workflow_file = ConfigUtils.get_path("comfyuiWhiteImage", "workflow_file")
        server_address = ConfigUtils.get("comfyuiWhiteImage", "server_address")
        username = ConfigUtils.get("comfyuiWhiteImage", "username")
        password = ConfigUtils.get("comfyuiWhiteImage", "password")

        try:
            # 准备任务数据
            task_data = {
                 "workflow_file": workflow_file,
                 "server_address": server_address,
                 "username": username,
                 "password": password,
                 "prompt_updates": {
                     "60": {"inputs": {"url": url, "timeout": 60, "proxy": ""}}
                 },
                 "description": description,
                 "url": url,
                 "user_id": user.id,
                 "metadata": {
                     "description": description,
                     "url": url,
                     "add_new_data": add_new_data
                 }
            }

            # 创建异步任务
            task_info = TaskUtils.create_async_task(
                task_type='white_background',
                task_data=task_data,
                user=user,
                priority=priority
            )

            return task_info

        except Exception as e:
            logger.error(f"创建白底图生成任务失败: {str(e)}")
            raise BusinessException(
                error_code=ErrorCode.SYSTEM_ERROR,
                data=None,
                errors=str(e)
            )

    @staticmethod
    def images_image_clue(description: str, url: str, user: SysUser, priority: str = "medium", add_new_data: str = "") -> Dict:
        """
        图片线索生成 - 使用队列系统
        :param description: 图像描述
        :param url: 输入图像URL
        :param user: 用户对象
        :param priority: 任务优先级 (low, medium, high)
        :param request: 请求对象 (不再使用)
        :return: 任务信息
        """
        workflow_file = ConfigUtils.get_path("comfyuiImagesImageClue", "workflow_file")
        server_address = ConfigUtils.get("comfyuiImagesImageClue", "server_address")
        username = ConfigUtils.get("comfyuiImagesImageClue", "username")
        password = ConfigUtils.get("comfyuiImagesImageClue", "password")
        try:
            # 准备任务数据
            task_data = {
                'workflow_file': workflow_file,
                'server_address': server_address,
                'username': username,
                'password': password,
                'prompt_updates': {
                    "17": {"inputs": {"string": description}},  # 正例文本
                    "32": {"inputs": {"url": url}}  # 反例文本
                },
                'description': description,
                'priority': priority,
                'metadata': {
                    'source_image_url': url,
                    'add_new_data': add_new_data
                }
            }

            # 创建异步任务
            task_info = TaskUtils.create_async_task(
                task_type='product_clue',
                task_data=task_data,
                user=user,
                priority=priority
            )

            return task_info

        except Exception as e:
            logger.error(f"创建图片线索生成任务失败: {str(e)}")
            raise BusinessException(
                error_code=ErrorCode.SYSTEM_ERROR,
                data=None,
                errors=str(e)
            )

    @staticmethod
    def images_clue_image(description: str, url: str, user: SysUser, priority: str = "medium", add_new_data: str = "") -> Dict:
        """
        线索图片生成 - 使用队列系统
        :param description: 图像描述
        :param url: 输入图像URL
        :param user: 用户对象
        :param priority: 任务优先级 (low, medium, high)
        :param request: 请求对象 (不再使用)
        :return: 任务信息
        """
        workflow_file = ConfigUtils.get_path("comfyuiImagesClueImage", "workflow_file")
        server_address = ConfigUtils.get("comfyuiImagesClueImage", "server_address")
        username = ConfigUtils.get("comfyuiImagesClueImage", "username")
        password = ConfigUtils.get("comfyuiImagesClueImage", "password")
        try:
            # 准备任务数据
            task_data = {
                'workflow_file': workflow_file,
                'server_address': server_address,
                'username': username,
                'password': password,
                'prompt_updates': {
                    "17": {"inputs": {"string": description}},  # 正例文本
                    "32": {"inputs": {"url": url}}  # 反例文本
                },
                'description': description,
                'priority': priority,
                'metadata': {
                    'source_image_url': url,
                    'add_new_data': add_new_data
                }
            }

            # 创建异步任务
            task_info = TaskUtils.create_async_task(
                task_type='clue_product',
                task_data=task_data,
                user=user,
                priority=priority
            )

            return task_info

        except Exception as e:
            logger.error(f"创建线索图片生成任务失败: {str(e)}")
            raise BusinessException(
                error_code=ErrorCode.SYSTEM_ERROR,
                data=None,
                errors=str(e)
            )

    # 状态查询和任务取消方法
    get_task_status = TaskUtils.get_task_status
    cancel_task = TaskUtils.cancel_task

    @staticmethod
    def delete_image(image_id: int, user: SysUser = None) -> Dict:
        """
        根据图片ID删除数据库中的记录和对象存储中的对象
        :param image_id: 图片ID
        :param user: 用户对象（可选，用于权限校验）
        :return: 包含删除状态信息的字典
        """
        try:
            # 获取templateImage记录
            image = templateImage.objects.filter(id=image_id).first()
            
            if not image:
                raise BusinessException(
                    error_code=ErrorCode.NOT_FOUND.code,
                    data='',
                    errors=f"未找到ID为{image_id}的图片记录"
                )
            
            # 可选的权限校验
            if user and image.userImage and image.userImage.id != user.id:
                raise BusinessException(
                    error_code=ErrorCode.PERMISSION_DENIED.code,
                    data='',
                    errors="您没有权限删除此图片"
                )
            
            # 从图片地址中提取对象名称
            image_url = image.image_address
            object_name = None
            
            try:
                # 解析图片URL获取对象名称
                # 处理URL格式: https://qihuaimage.tos-cn-guangzhou.volces.com/upload/9877623a-2857-41a5-b1f9-7d3727861992.png
                if '//' in image_url:
                    # 分离域名和路径
                    domain_path = image_url.split('//', 1)[1]
                    # 找到域名后的第一个斜杠
                    if '/' in domain_path:
                        object_name = domain_path.split('/', 1)[1]
                        logger.info(f"从URL提取的对象名称: {object_name}")
                
                # 如果无法从URL中提取对象名称，尝试使用存储的文件名构建路径
                if not object_name and image.image_name:
                    # 假设存储在默认的上传文件夹
                    object_name = f"upload/{image.image_name}"
                    logger.info(f"使用image_name构建的对象名称: {object_name}")
            except Exception as e:
                logger.error(f"解析图片URL失败: {e}")
            
            result = {
                "image_id": image_id,
                "db_deleted": False,
                "object_deleted": False,
                "object_name": object_name
            }
            
            # 删除对象存储中的对象
            if object_name:
                try:
                    tos_utils = VolcengineTOSUtils()
                    object_deleted = tos_utils.delete_object(object_name)
                    result["object_deleted"] = object_deleted
                    logger.info(f"删除对象存储中的对象 {object_name}: {'成功' if object_deleted else '失败'}")
                except Exception as e:
                    logger.error(f"删除对象存储中的对象失败: {e}")
            else:
                logger.warning(f"无法从URL {image_url} 或image_name {image.image_name} 构建有效的对象名称，跳过删除对象存储")
            
            # 从数据库中删除记录（或标记为已删除）
            try:
                # 根据实际情况选择物理删除或逻辑删除
                if hasattr(image, 'isDelete') and image.isDelete == 0:
                    # 逻辑删除
                    image.isDelete = 1
                    image.save()
                    result["db_deleted"] = True
                    logger.info(f"已将图片记录ID {image_id} 标记为已删除")
                else:
                    # 物理删除
                    image.delete()
                    result["db_deleted"] = True
                    logger.info(f"已从数据库中删除图片记录ID {image_id}")
            except Exception as e:
                logger.error(f"从数据库中删除记录失败: {e}")
                raise BusinessException(
                    error_code=ErrorCode.INTERNAL_ERROR.code,
                    data='',
                    errors=f"从数据库中删除记录失败: {str(e)}"
                )
            
            return result
            
        except BusinessException as e:
            # 捕获业务异常并重新抛出
            logger.error(f'删除图片失败，业务异常: {e.errors}')
            raise e
        except Exception as e:
            # 记录错误日志并抛出异常
            logger.error(f'删除图片失败，服务器内部错误: {e}')
            raise BusinessException(
                error_code=ErrorCode.INTERNAL_ERROR.code,
                data='',
                errors=f"删除图片失败，服务器内部错误: {str(e)}"
            )

    @staticmethod
    def multi_images_to_image(description: str, image_urls: list, seed: int = None, quantity: int = 1, 
                             height: int = 1024, width: int = 1024, user: SysUser = None, 
                             priority: str = "medium", add_new_data: str = "") -> Dict:
        """
        多图生图任务 - 根据提供的图片URL数量选择不同的工作流
        
        :param description: 图像描述
        :param image_urls: 输入图像URL列表(支持1-5张图片)
        :param seed: 随机种子值(如不提供则随机生成)
        :param quantity: 生成图片数量
        :param height: 生成图片高度(默认1024)
        :param width: 生成图片宽度(默认1024)
        :param user: 用户对象
        :param priority: 任务优先级 (low, medium, high)
        :return: 任务信息
        """
        try:
            # 验证图片URL数量
            if not image_urls or len(image_urls) == 0:
                raise BusinessException(
                    error_code=ErrorCode.INVALID_REQUEST,
                    data=None,
                    errors="至少需要提供一个图片URL"
                )
            
            if len(image_urls) > 5:
                raise BusinessException(
                    error_code=ErrorCode.INVALID_REQUEST,
                    data=None,
                    errors="最多支持5个图片URL"
                )
            
            # 如果没有提供seed，则随机生成一个
            if seed is None:
                import random
                # 生成不超过16位数的随机整数（与示例seed值相似范围）
                seed = random.randint(1, 9999999999999999)
                logger.info(f"未提供种子值，随机生成: {seed}")
                
            # 根据URL数量选择不同的工作流配置
            url_count = len(image_urls)
            workflow_key = f"comfyuiImageImages{ImageService._get_number_text(url_count)}"
            
            logger.info(f"正在使用 {workflow_key} 工作流，处理 {url_count} 张参考图片")
            
            # 获取对应的工作流文件路径
            workflow_file = ConfigUtils.get_path(workflow_key, "workflow_file")
            server_address = ConfigUtils.get(workflow_key, "server_address")
            username = ConfigUtils.get(workflow_key, "username")
            password = ConfigUtils.get(workflow_key, "password")
            
            if not workflow_file:
                logger.error(f"找不到工作流配置: {workflow_key}")
                raise BusinessException(
                    error_code=ErrorCode.CONFIGURATION_ERROR,
                    data=None,
                    errors=f"系统配置错误: 找不到工作流 {workflow_key}"
                )
            
            # 针对不同数量的图片URL，配置不同的参数和节点ID
            # 配置表 - 根据URL数量映射到相应的节点配置
            workflow_configs = {
                1: {
                    "text_node_id": "6",
                    "seed_node_id": "25",
                    "batch_node_id": "27", 
                    "width_node_id": "92",
                    "height_node_id": "93",
                    "image_node_ids": ["95"],
                    "target_node_id": "52"
                },
                2: {
                    "text_node_id": "119",
                    "seed_node_id": "97", 
                    "batch_node_id": "93",
                    "width_node_id": "126",
                    "height_node_id": "127",
                    "image_node_ids": ["128", "129"],
                    "target_node_id": "92"
                },
                3: {
                    "text_node_id": "6",
                    "seed_node_id": "97",
                    "batch_node_id": "111",
                    "width_node_id": "129", 
                    "height_node_id": "130",
                    "image_node_ids": ["131", "132", "133"],
                    "target_node_id": "92"
                },
                4: {
                    "text_node_id": "119",
                    "seed_node_id": "97",
                    "batch_node_id": "111",
                    "width_node_id": "132",
                    "height_node_id": "133",
                    "image_node_ids": ["134", "135", "136", "137"],
                    "target_node_id": "92"
                },
                5: {
                    "text_node_id": "119",
                    "seed_node_id": "97",
                    "batch_node_id": "111",
                    "width_node_id": "134",
                    "height_node_id": "135", 
                    "image_node_ids": ["136", "137", "138", "139", "140"],
                    "target_node_id": "92"
                }
            }
            
            # 获取当前URL数量对应的配置
            config = workflow_configs.get(url_count)
            if not config:
                raise BusinessException(
                    error_code=ErrorCode.CONFIGURATION_ERROR,
                    data=None,
                    errors=f"未找到 {url_count} 张图片的处理配置"
                )
            
            # 构建提示更新参数
            prompt_updates = {}
            
            # 添加基础参数
            prompt_updates[config["text_node_id"]] = {"inputs": {"text": description}}
            prompt_updates[config["seed_node_id"]] = {"inputs": {"noise_seed": seed}}
            prompt_updates[config["batch_node_id"]] = {"inputs": {"batch_size": quantity}}
            prompt_updates[config["width_node_id"]] = {"inputs": {"value": width}}
            prompt_updates[config["height_node_id"]] = {"inputs": {"value": height}}
            
            # 添加图片URL参数 - 确保每个URL都映射到正确的节点ID
            for i, url in enumerate(image_urls):
                if i < len(config["image_node_ids"]):
                    node_id = config["image_node_ids"][i]
                    prompt_updates[node_id] = {"inputs": {"url": url, "timeout": 60, "proxy": ""}}
            
            # 准备任务数据
            task_data = {
                "workflow_file": workflow_file,
                "server_address": server_address,
                "username": username,
                "password": password,
                "prompt_updates": prompt_updates,
                "target_node_id": config["target_node_id"],
                "description": description,
                "noise_seed": seed,
                "batch_size": quantity,
                "height": height,
                "width": width,
                "image_urls": image_urls,
                "user_id": user.id if user else None,
                "metadata": {
                    "description": description,
                    "noise_seed": seed,
                    "batch_size": quantity,
                    "height": height,
                    "width": width,
                    "image_count": url_count,
                    "image_urls": image_urls,
                    "workflow_key": workflow_key,
                    "add_new_data": add_new_data
                }
            }
            
            # 创建异步任务
            task_info = TaskUtils.create_async_task(
                task_type='multi_image_to_image',
                task_data=task_data,
                user=user,
                priority=priority
            )
            
            # 添加额外信息到返回结果
            task_info["workflow_used"] = workflow_key
            task_info["image_count"] = url_count
            
            return task_info
            
        except BusinessException as be:
            # 重新抛出业务异常
            logger.error(f"创建多图生图任务失败，业务异常: {be.errors}")
            raise be
        except Exception as e:
            # 处理其他异常
            logger.error(f"创建多图生图任务失败: {str(e)}", exc_info=True)
            raise BusinessException(
                error_code=ErrorCode.SYSTEM_ERROR,
                data=None,
                errors=f"创建多图生图任务失败: {str(e)}"
            )
    
    @staticmethod
    def _get_number_text(num):
        """将数字转换为英文单词 (1->One, 2->Two, ...)"""
        number_texts = {
            1: "One",
            2: "Two",
            3: "Three",
            4: "Four",
            5: "Five"
        }
        return number_texts.get(num, "One")  # 默认返回"One"



