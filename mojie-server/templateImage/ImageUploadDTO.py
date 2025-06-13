from django.core.validators import FileExtensionValidator
from rest_framework import serializers
from django.core.files.uploadedfile import UploadedFile
from typing import Dict, Optional

import logging
import mimetypes
import re

logger = logging.getLogger(__name__)

# 添加一个自定义的图片验证器
class CustomImageValidator:
    """
    自定义图片验证器，除了检查文件扩展名外，还检查MIME类型
    """
    def __init__(self, allowed_extensions=None):
        self.allowed_extensions = allowed_extensions or [
            'bmp', 'dib', 'gif', 'jfif', 'jpe', 'jpg', 'jpeg', 'pbm', 'pgm', 'ppm', 'pnm', 'pfm', 'png', 
            'apng', 'blp', 'bufr', 'cur', 'pcx', 'dcx', 'dds', 'ps', 'eps', 'fit', 'fits', 'fli', 'flc', 
            'ftc', 'ftu', 'gbr', 'grib', 'h5', 'hdf', 'jp2', 'j2k', 'jpc', 'jpf', 'jpx', 'j2c', 'icns', 
            'ico', 'im', 'iim', 'mpg', 'mpeg', 'tif', 'tiff', 'mpo', 'msp', 'palm', 'pcd', 'pdf', 'pxr', 
            'psd', 'qoi', 'bw', 'rgb', 'rgba', 'sgi', 'ras', 'tga', 'icb', 'vda', 'vst', 'webp', 'wmf', 
            'emf', 'xbm', 'xpm'
        ]
        self.allowed_mime_types = [
            'image/bmp', 'image/gif', 'image/jpeg', 'image/png', 'image/webp', 
            'image/tiff', 'image/x-icon', 'application/pdf',
            'image/x-portable-pixmap', 'image/x-portable-graymap', 'image/x-portable-bitmap',
            'image/x-portable-anymap'
        ]
    
    def __call__(self, value):
        # 检查文件扩展名
        ext = self._get_file_extension(value)
        content_type = getattr(value, 'content_type', '')
        
        logger.info(f"正在验证文件: 扩展名={ext}, 内容类型={content_type}")
        
        # 如果有有效的扩展名，并且在允许列表中，则通过
        if ext and ext.lower() in self.allowed_extensions:
            return
        
        # 如果没有有效扩展名，但内容类型是图像，则通过
        if content_type and any(content_type.startswith(mime) for mime in self.allowed_mime_types):
            logger.info(f"文件没有有效扩展名，但内容类型 {content_type} 是允许的图像类型")
            return
            
        # 如果二进制文件开头有图像特征（魔数），也可以通过
        # 检查二进制数据的魔数来识别常见图像格式
        if hasattr(value, 'read') and hasattr(value, 'seek'):
            # 保存当前位置
            pos = value.tell()
            # 读取文件头部数据
            header = value.read(12)
            # 恢复位置
            value.seek(pos)
            
            # JPEG: FF D8 FF
            if header[:3] == b'\xFF\xD8\xFF':
                logger.info("通过魔数检测识别为JPEG图像")
                return
                
            # PNG: 89 50 4E 47 0D 0A 1A 0A
            if header[:8] == b'\x89PNG\r\n\x1a\n':
                logger.info("通过魔数检测识别为PNG图像")
                return
                
            # GIF: 47 49 46 38
            if header[:4] == b'GIF8':
                logger.info("通过魔数检测识别为GIF图像")
                return
            
            # WEBP: 52 49 46 46 ** ** ** ** 57 45 42 50
            if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
                logger.info("通过魔数检测识别为WEBP图像")
                return
        
        # 如果上述所有检查都失败，则拒绝
        extensions_str = ', '.join(self.allowed_extensions)
        mime_types_str = ', '.join(self.allowed_mime_types)
        error_msg = f'文件扩展"{ext}"是不被允许。允许的扩展为：{extensions_str}。允许的内容类型为：{mime_types_str}。'
        raise serializers.ValidationError(error_msg)
    
    def _get_file_extension(self, file):
        """获取文件扩展名"""
        if hasattr(file, 'name'):
            # 使用正则表达式提取扩展名，避免处理多个点的文件名时出错
            match = re.search(r'\.([^.]+)$', file.name)
            if match:
                return match.group(1).lower()
        return ''

class SensitiveContentValidator:
    """
    敏感内容验证器，用于检查文本中是否包含不良内容
    """
    def __init__(self):
        # 定义敏感词列表
        self.sensitive_words = [
            # 色情相关
            '色情', '情色', '成人', '性', '露骨', '暴露', '裸体', 'sexy', 'porn', 'sex',
            # 暴力相关
            '暴力', '血腥', '残忍', '虐待', '伤害', '杀人', '死亡', 'blood', 'violence', 'kill',
            # 赌博相关
            '赌博', '博彩', '赌场', '赌钱', '赌注', 'gambling', 'casino', 'bet',
            # 政治敏感
            '政治', '政府', '领导人', '敏感', '政治敏感',
            # 其他不良内容
            '毒品', '吸毒', '贩毒', 'drug', 'narcotic',
            '歧视', '种族歧视', '性别歧视', 'discrimination',
            '恐怖', '恐怖主义', 'terrorism', 'terrorist'
        ]
        
        # 构建正则表达式模式
        self.pattern = '|'.join(self.sensitive_words)
        self.regex = re.compile(self.pattern, re.IGNORECASE)
    
    def __call__(self, value):
        if not value:
            return value
            
        # 检查是否包含敏感词
        matches = self.regex.findall(value)
        if matches:
            raise serializers.ValidationError(
                f"描述文本包含不良内容，请修改后重试。"
            )
        return value

class TextImageDTO(serializers.Serializer):
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        help_text="图片描述",
        validators=[SensitiveContentValidator()]
    )
    user_id = serializers.IntegerField(required=True, help_text="用户ID")
    conversation_id = serializers.IntegerField(required=False, allow_null=True, help_text="会话ID，可选，不提供则自动创建")
    add_new_data = serializers.CharField(required=False, allow_blank=True, help_text="额外数据参数，会被传递到metadata中")

class TextImageNewDTO(serializers.Serializer):
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        help_text="图片描述",
        validators=[SensitiveContentValidator()]
    )
    quantity = serializers.IntegerField(required=True, help_text="图片数量")
    proportion = serializers.CharField(required=False, allow_blank=True, help_text="图片比例；示例（1024X1024）")
    priority = serializers.CharField(required=False, allow_blank=True, help_text="priority")
    conversation_id = serializers.IntegerField(required=False, allow_null=True, help_text="会话ID，可选，不提供则自动创建")
    add_new_data = serializers.CharField(required=False, allow_blank=True, help_text="额外数据参数，会被传递到metadata中")

class TextImageNewModelDTO(serializers.Serializer):
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        help_text="图片描述",
        validators=[SensitiveContentValidator()]
    )
    quantity = serializers.IntegerField(required=True, help_text="图片数量")
    model = serializers.CharField(required=False, allow_blank=True, help_text="模型选择")
    proportion = serializers.CharField(required=False, allow_blank=True, help_text="图片比例；示例（1024X1024）")
    priority = serializers.CharField(required=False, allow_blank=True, help_text="priority")
    conversation_id = serializers.IntegerField(required=False, allow_null=True, help_text="会话ID，可选，不提供则自动创建")
    add_new_data = serializers.CharField(required=False, allow_blank=True, help_text="额外数据参数，会被传递到metadata中")


class ImagesImageDTO(serializers.Serializer):
    url = serializers.CharField(required=False, allow_blank=True, help_text="url")
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        help_text="图片描述",
        validators=[SensitiveContentValidator()]
    )
    user_id = serializers.IntegerField(required=True, help_text="用户ID")
    conversation_id = serializers.IntegerField(required=False, allow_null=True, help_text="会话ID，可选，不提供则自动创建")
    add_new_data = serializers.CharField(required=False, allow_blank=True, help_text="额外数据参数，会被传递到metadata中")

class ImageUploadDTO(serializers.Serializer):
    image = serializers.ImageField(
        required=True, 
        help_text="上传的图片文件",
        validators=[CustomImageValidator()]
    )
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        help_text="图片描述",
        validators=[SensitiveContentValidator()]
    )
    method = serializers.CharField(required=False, allow_blank=True, help_text="图片类别")
    method_su = serializers.CharField(required=False, allow_blank=True, help_text="图片细分")
    related_id = serializers.IntegerField(required=False, help_text="对应图片ID")
    add_new_data = serializers.CharField(required=False, allow_blank=True, help_text="额外数据参数，会被传递到metadata中")


class ImageListDTO(serializers.Serializer):
    method = serializers.CharField(required=False, allow_blank=True, help_text="图片类别（可以传递空参）")
    user_id = serializers.IntegerField(required=True, help_text="用户ID（可以传递空参）")
    page = serializers.IntegerField(required=True, help_text="页码")
    page_size = serializers.IntegerField(required=True, help_text="每页大小")


class ImagesProductDTO(serializers.Serializer):
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        help_text="图片描述",
        validators=[SensitiveContentValidator()]
    )
    level = serializers.FloatField(required=False, help_text="程度")
    white_url = serializers.CharField(required=False, allow_blank=True, help_text="white_background_product_url")
    template_url = serializers.CharField(required=False, allow_blank=True, help_text="template_url")
    mask_url = serializers.CharField(required=False, allow_blank=True, help_text="mask_url")
    user_id = serializers.IntegerField(required=True, help_text="用户ID")
    priority = serializers.CharField(required=False, allow_blank=True, help_text="priority")
    conversation_id = serializers.IntegerField(required=False, allow_null=True, help_text="会话ID，可选，不提供则自动创建")
    add_new_data = serializers.CharField(required=False, allow_blank=True, help_text="额外数据参数，会被传递到metadata中")


class ImagesProductWorkflowDTO(serializers.Serializer):
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        help_text="图片描述",
        validators=[SensitiveContentValidator()]
    )
    level = serializers.FloatField(required=False, help_text="程度")
    white_url = serializers.CharField(required=False, allow_blank=True, help_text="white_background_product_url")
    white_mask_url = serializers.CharField(required=False, allow_blank=True, default="https://qihuaimage.tos-cn-guangzhou.volces.com/f7bd296e-fa3c-49e7-87b8-988ce8deb33a.png", help_text="white_mask_url")
    template_url = serializers.CharField(required=False, allow_blank=True, help_text="template_url")
    mask_url = serializers.CharField(required=False, allow_blank=True, help_text="mask_url")
    priority = serializers.CharField(required=False, allow_blank=True, help_text="priority")
    conversation_id = serializers.IntegerField(required=False, allow_null=True, help_text="会话ID，可选，不提供则自动创建")
    add_new_data = serializers.CharField(required=False, allow_blank=True, help_text="额外数据参数，会被传递到metadata中")


class ImagesFineDetailWorkflowDTO(serializers.Serializer):
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        help_text="图片描述",
        validators=[SensitiveContentValidator()]
    )
    level = serializers.FloatField(required=False, help_text="程度")
    url = serializers.CharField(required=False, allow_blank=True, help_text="url")
    mask_url = serializers.CharField(required=True, allow_blank=True, help_text="mask_url")
    priority = serializers.CharField(required=False, allow_blank=True, help_text="priority")
    conversation_id = serializers.IntegerField(required=False, allow_null=True, help_text="会话ID，可选，不提供则自动创建")
    add_new_data = serializers.CharField(required=False, allow_blank=True, help_text="额外数据参数，会被传递到metadata中")


class WhiteBackgroundImageDTO(serializers.Serializer):
    url = serializers.CharField(required=False, allow_blank=True, help_text="url")
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        help_text="图片描述",
        validators=[SensitiveContentValidator()]
    )
    conversation_id = serializers.IntegerField(required=False, allow_null=True, help_text="会话ID，可选，不提供则自动创建")
    add_new_data = serializers.CharField(required=False, allow_blank=True, help_text="额外数据参数，会被传递到metadata中")

class WhiteBackgroundImageOnlyDTO(serializers.Serializer):
    image = serializers.ImageField(
        required=True, 
        help_text="上传的图片文件",
        validators=[CustomImageValidator()]
    )
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        help_text="图片描述",
        validators=[SensitiveContentValidator()]
    )
    add_new_data = serializers.CharField(required=False, allow_blank=True, help_text="额外数据参数，会被传递到metadata中")
class ImagesClueImageDTO(serializers.Serializer):
    url = serializers.CharField(required=False, allow_blank=True, help_text="url")
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        help_text="图片描述",
        validators=[SensitiveContentValidator()]
    )
    user_id = serializers.IntegerField(required=True, help_text="用户ID")
    conversation_id = serializers.IntegerField(required=False, allow_null=True, help_text="会话ID，可选，不提供则自动创建")
    add_new_data = serializers.CharField(required=False, allow_blank=True, help_text="额外数据参数，会被传递到metadata中")

class TextDTO(serializers.Serializer):
    """
        图片文本输入参数验证
        """
    text = serializers.CharField(required=True,
        help_text="生成文案的提示文本")
    image_url = serializers.URLField(required=False,
        help_text="生成文案的提示图片")
    stream = serializers.BooleanField(default=False)
    add_new_data = serializers.CharField(required=False, allow_blank=True, help_text="额外数据参数，会被传递到metadata中")
    def validate_text(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("输入文本不能少于3个字符")
        return value

class TextOnlyDTO(serializers.Serializer):
    """
    纯文本输入参数验证
    """
    text = serializers.CharField(
        required=True,
        help_text="生成文案的提示文本"
    )
    stream = serializers.BooleanField(
        default=True,
        help_text="是否启用流式输出"
    )
    add_new_data = serializers.CharField(required=False, allow_blank=True, help_text="额外数据参数，会被传递到metadata中")
    def validate_text(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("输入文本不能少于3个字符")
        return value


class GeminiImageGenerationRequestDTO(serializers.Serializer):
    """
    Gemini图像生成请求参数DTO
    """
    prompt = serializers.CharField(
        required=True,
        min_length=5,
        help_text="图片生成提示词，至少5个字符"
    )
    image_urls = serializers.ListField(
        required=False,
        max_length=3,
        help_text="参考图片URL列表，至少包含1个有效URL"
    )
    aspect_ratio = serializers.ChoiceField(
        choices=["Free", "Landscape", "Portrait", "Square"],
        default="Free",
        help_text="生成图片的宽高比"
    )
    temperature = serializers.FloatField(
        min_value=0.0,
        max_value=2.0,
        default=1.0,
        help_text="生成温度(0.0-2.0)"
    )
    user_id = serializers.IntegerField(required=True, help_text="用户ID")
    stream = serializers.BooleanField(
        default=False,
        help_text="是否使用流式响应"
    )

    conversation_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        help_text="会话ID (使用数据库自增ID)"
    )

    enable_long_context = serializers.BooleanField(
        default=True,
        help_text="是否启用长上下文支持"
    )


class ChatGPTImageRequestDTO(serializers.Serializer):
    prompt = serializers.CharField(
        max_length=4000,
        help_text="图像生成描述文本"
    )
    image_urls = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        max_length=3,
        help_text="参考图像URL列表（最多3张）"
    )
    model = serializers.CharField(
        required=False,
        default='gpt-4o-image',
        help_text="使用的模型"
    )
    stream = serializers.BooleanField(
        default=False,
        help_text="是否使用流式响应"
    )

    conversation_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        help_text="会话ID (使用数据库自增ID)"
    )


class WidePictureWorkflowDTO(serializers.Serializer):
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        help_text="图片描述",
        validators=[SensitiveContentValidator()]
    )
    url = serializers.CharField(required=True, allow_blank=False, help_text="原始图片URL")
    left = serializers.IntegerField(required=True, help_text="左侧扩展像素")
    top = serializers.IntegerField(required=True, help_text="顶部扩展像素")
    right = serializers.IntegerField(required=True, help_text="右侧扩展像素")
    bottom = serializers.IntegerField(required=True, help_text="底部扩展像素")
    priority = serializers.CharField(required=False, allow_blank=True, help_text="优先级")
    conversation_id = serializers.IntegerField(required=False, allow_null=True, help_text="会话ID，可选，不提供则自动创建")
    add_new_data = serializers.CharField(required=False, allow_blank=True, help_text="额外数据参数，会被传递到metadata中")

class InternalSupplementationWorkflowDTO(serializers.Serializer):
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        help_text="图片描述",
        validators=[SensitiveContentValidator()]
    )
    url = serializers.CharField(required=True, allow_blank=False, help_text="原始图片URL")
    mask_url = serializers.CharField(required=True, allow_blank=False, help_text="蒙版图片URL")
    priority = serializers.CharField(required=False, allow_blank=True, help_text="优先级")
    conversation_id = serializers.IntegerField(required=False, allow_null=True, help_text="会话ID，可选，不提供则自动创建")
    add_new_data = serializers.CharField(required=False, allow_blank=True, help_text="额外数据参数，会被传递到metadata中")

class InternalSupplementationAndRemovalWorkflowDTO(serializers.Serializer):
    url = serializers.CharField(required=True, allow_blank=False, help_text="原始图片URL")
    mask_url = serializers.CharField(required=True, allow_blank=False, help_text="蒙版图片URL")
    priority = serializers.CharField(required=False, allow_blank=True, help_text="优先级")
    conversation_id = serializers.IntegerField(required=False, allow_null=True, help_text="会话ID，可选，不提供则自动创建")
    add_new_data = serializers.CharField(required=False, allow_blank=True, help_text="额外数据参数，会被传递到metadata中")

class CompleteRedrawingWorkflowDTO(serializers.Serializer):
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        help_text="图片描述",
        validators=[SensitiveContentValidator()]
    )
    level = serializers.FloatField(required=False, help_text="调整级别")
    url = serializers.CharField(required=True, allow_blank=False, help_text="原始图片URL")
    priority = serializers.CharField(required=False, allow_blank=True, help_text="优先级")
    conversation_id = serializers.IntegerField(required=False, allow_null=True, help_text="会话ID，可选，不提供则自动创建")
    add_new_data = serializers.CharField(required=False, allow_blank=True, help_text="额外数据参数，会被传递到metadata中")

class OpenAIImageRequestDTO(serializers.Serializer):
    prompt = serializers.CharField(
        max_length=4000,
        help_text="图像生成描述文本"
    )
    image_paths = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        max_length=5,
        help_text="编辑图片路径列表（最多5张图片）"
    )
    mask_path = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="遮罩图片路径"
    )
    operation_type = serializers.ChoiceField(
        choices=['generate', 'edit'],
        help_text="操作类型：generate-生成图像，edit-编辑图像(图生图)"
    )
    conversation_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        help_text="会话ID (使用数据库自增ID)"
    )
    stream = serializers.BooleanField(
        default=False,
        help_text="是否使用流式响应"
    )
    size = serializers.CharField(
        required=False,
        default="1024x1024",
        help_text="生成图片的尺寸，格式为'宽x高'，例如'1024x1024'"
    )

    def validate_image_paths(self, value):
        """验证图片路径列表"""
        if value and len(value) > 5:
            raise serializers.ValidationError("最多只能上传5张图片")
        return value

    def validate_size(self, value):
        """验证尺寸格式"""
        if not value:
            return "1024x1024"
            
        try:
            width, height = map(int, value.split('x'))
            if width < 256 or width > 2048 or height < 256 or height > 2048:
                raise ValueError("尺寸必须在256x256到2048x2048之间")
            if width % 64 != 0 or height % 64 != 0:
                raise ValueError("尺寸必须是64的倍数")
            return f"{width}x{height}"
        except ValueError as e:
            raise serializers.ValidationError(str(e))
        except Exception:
            raise serializers.ValidationError("尺寸格式无效，请使用'宽x高'格式，例如'1024x1024'")

class TextVolcengineDTO(serializers.Serializer):
    """
    纯文本输入参数验证
    """
    text = serializers.CharField(
        required=True,
        help_text="生成文案的提示文本"
    )
    conversation_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        help_text="会话ID (使用数据库自增ID)"
    )
    stream = serializers.BooleanField(
        default=True,
        help_text="是否启用流式输出"
    )

    def validate_text(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("输入文本不能少于3个字符")
        return value

class VolcengineImageGenerationDTO(serializers.Serializer):
    """
    火山引擎图像生成参数验证
    """
    text = serializers.CharField(
        required=True,
        max_length=4000,
        help_text="生成图像的提示文本"
    )
    conversation_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        help_text="会话ID (可选)"
    )
    image_urls = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        allow_empty=True,
        max_length=5,
        help_text="参考图片URL列表（最多5张，可选）"
    )
    req_key = serializers.CharField(
        required=False,
        allow_null=True,
        default="high_aes_general_v30l_zt2i",
        help_text="API请求键，默认为'high_aes_general_v30l_zt2i'"
    )
    scale = serializers.FloatField(
        required=False,
        allow_null=True,
        min_value=1.0,
        max_value=10.0,
        default=2.5,
        help_text="缩放比例，默认为2.5，范围1.0-10.0"
    )
    width = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=512,
        max_value=2048,
        default=1328,
        help_text="图片宽度，默认为1328，最小512，最大2048"
    )
    height = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=512,
        max_value=2048,
        default=1328,
        help_text="图片高度，默认为1328，最小512，最大2048"
    )
    add_logo = serializers.BooleanField(
        required=False,
        default=False,
        help_text="是否添加logo，默认为False"
    )
    logo_position = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        max_value=3,
        default=0,
        help_text="logo位置，0:左上角, 1:左下角, 2:右下角, 3:右上角"
    )
    logo_language = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        max_value=2,
        default=0,
        help_text="logo语言，0:英文, 1:中文, 2:日文"
    )
    logo_opacity = serializers.FloatField(
        required=False,
        allow_null=True,
        min_value=0.1,
        max_value=1.0,
        default=0.3,
        help_text="logo透明度，默认为0.3，范围0.1-1.0"
    )
    logo_text = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=100,
        default="",
        help_text="logo文本内容，默认为空"
    )
    stream = serializers.BooleanField(
        default=False,
        help_text="是否启用流式输出"
    )

    def validate_text(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("提示文本不能少于3个字符")
        return value

    def validate_image_urls(self, value):
        if len(value) > 5:
            raise serializers.ValidationError("最多只能上传5张参考图片")
        return value

class MultiImageToImageDTO(serializers.Serializer):
    """
    多图生图请求参数验证
    """
    description = serializers.CharField(
        required=True, 
        min_length=3,
        max_length=1000,
        help_text="图像生成描述文本",
        validators=[SensitiveContentValidator()]
    )
    image_urls = serializers.ListField(
        child=serializers.URLField(),
        required=True,
        min_length=1,
        max_length=5,
        help_text="图片URL列表（1-5张图片）"
    )
    seed = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="随机种子值，不提供则自动生成"
    )
    quantity = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=8,
        default=1,
        help_text="生成图片数量，默认为1，最大8"
    )
    height = serializers.IntegerField(
        required=False,
        min_value=512,
        max_value=2048,
        default=1024,
        help_text="图片高度，默认为1024"
    )
    width = serializers.IntegerField(
        required=False,
        min_value=512,
        max_value=2048,
        default=1024,
        help_text="图片宽度，默认为1024"
    )
    priority = serializers.CharField(
        required=False,
        default="medium",
        help_text="任务优先级 (low, medium, high)"
    )
    conversation_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="会话ID，可选，不提供则自动创建"
    )
    
    def validate_description(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("描述文本不能少于3个字符")
        return value
    
    def validate_image_urls(self, value):
        if not value or len(value) == 0:
            raise serializers.ValidationError("至少需要提供一个图片URL")
        if len(value) > 5:
            raise serializers.ValidationError("最多支持5个图片URL")
        return value

class CombinedImageGenerationDTO(serializers.Serializer):
    """
    结合文生图和图生图的请求参数验证
    - 当提供image_urls时走图生图流程
    - 当仅提供description时走文生图流程
    """
    description = serializers.CharField(
        required=True, 
        min_length=3,
        max_length=1000,
        help_text="图像生成描述文本",
        validators=[SensitiveContentValidator()]
    )
    image_urls = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        allow_empty=True,
        max_length=5,
        help_text="可选的参考图片URL列表（最多5张）"
    )
    seed = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="随机种子值，不提供则自动生成"
    )
    quantity = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=8,
        default=1,
        help_text="生成图片数量，默认为1，最大8"
    )
    height = serializers.IntegerField(
        required=False,
        min_value=512,
        max_value=2048,
        default=1024,
        help_text="图片高度，默认为1024"
    )
    width = serializers.IntegerField(
        required=False,
        min_value=512,
        max_value=2048,
        default=1024,
        help_text="图片宽度，默认为1024"
    )
    priority = serializers.CharField(
        required=False,
        default="medium",
        help_text="任务优先级 (low, medium, high)"
    )
    conversation_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="会话ID，可选，不提供则自动创建"
    )
    add_new_data = serializers.CharField(required=False, allow_blank=True, help_text="额外数据参数，会被传递到metadata中")
    
    def validate_description(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("描述文本不能少于3个字符")
        return value

class FluxKontextProRequestDTO(serializers.Serializer):
    """Flux Kontext Pro API 请求DTO"""
    prompt = serializers.CharField(required=True, help_text="生成提示词")
    image_paths = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        help_text="输入图片URL列表（可选）"
    )
    conversation_id = serializers.CharField(required=False, allow_blank=True, help_text="会话ID")
    seed = serializers.IntegerField(required=False, help_text="随机种子")
    aspect_ratio = serializers.CharField(required=False, help_text="图片比例（可选）21:9和9:21之间的图像比例")
    output_format = serializers.ChoiceField(
        choices=['png', 'jpeg'],
        default='png',
        help_text="输出格式（png/jpeg）"
    )
    prompt_upsampling = serializers.BooleanField(
        default=False,
        help_text="是否进行提示词上采样"
    )
    safety_tolerance = serializers.IntegerField(
        default=2,
        min_value=0,
        max_value=6,
        help_text="安全容忍度（0-6）"
    )
    stream = serializers.BooleanField(
        default=False,
        help_text="是否使用流式响应"
    )