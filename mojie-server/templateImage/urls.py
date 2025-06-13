from django.urls import path

from templateImage.ai_platform_views import GeminiImageGenerationView, ChatGPTImageGenerationView, \
    ChatGPTImageGenerationNewView, VolcengineVisualAPIView, ChatGPTImageGenerationOpenAIView, \
    FluxKontextProImageFluxView, UserPointsDeductionHistoryView
from templateImage.ai_platform_views_sdk import VolcengineVisualAPIViewSDK
from templateImage.comfyui_views import ImagesImageAPIView, TextImageAPIView, ProductTextImageAPIView, \
    TextToGenerateImagesAPIView, WhiteBackgroundAPIView, ImagesClueImageAPIView, ProductReplacementWorkflowAPIView, \
    FineDetailWorkflowAPIView, WidePictureWorkflowAPIView, InternalSupplementationWorkflowAPIView, \
    InternalSupplementationAndRemovalWorkflowAPIView, CompleteRedrawingWorkflowAPIView, ImagesTextImagesImageAPIView, \
    QueueInfoAPIView, TaskStatusAPIView, TaskCancelAPIView, MultiImageToImageView, CombinedImageGenerationView, \
    TextToGenerateImagesModelAPIView, \
    UserTaskListAPIView, RetryTaskAPIView, TaskTypeManagementAPIView

from templateImage.views import ImageUploadView, \
    TemplateGetUserListImagesView, \
    get_user_conversation_images, \
    get_all_conversation_images, newConversation, deleteConversation, get_ConversationList, getCaptcha, \
    UserRequestListView, UserInputAutoSaveView, BaiduTranslate, \
    TemplateImageGetListView, \
    UserCloudImageAddView, UserCloudImageListView, UserCloudImageDeleteView, UserCloudImageImportFromComfyUIView, \
    ComfyUITaskAutoSaveSettingView, WhiteBackgroundOnlyAPIView, TemplateImageDeleteView, ColorAdjustmentImageView,ImageUploadRecordDeleteView
from templateImage.queue_admin_views import QueueAdminAPIView
from templateImage.ai_platform_views import FluxKontextProImageView

urlpatterns=[
    path('img_upload', ImageUploadView.as_view(), name='上传图片'),
    path('text_img', TextImageAPIView.as_view(), name='文生图'),
    path('image_img', ImagesImageAPIView.as_view(), name='图生图'),

    path('image_list_admin', TemplateImageGetListView.as_view(), name='图像列表分页'),
    path('image_list_user', TemplateGetUserListImagesView.as_view(), name='前台列表分页'),

    path('image_product', ImagesTextImagesImageAPIView.as_view(), name='演示版家具产品替换图'),
    path('text_image_product', ProductTextImageAPIView.as_view(), name='家具产品文生图'),
    path('text_to_generate_images', TextToGenerateImagesAPIView.as_view(), name='家具产品文生图'),
    path('text_to_generate_model_images', TextToGenerateImagesModelAPIView.as_view(), name='可以更换模型的文生图'),
    path('white_image_product', WhiteBackgroundAPIView.as_view(), name='测试白底产品图'),
    path('image_clue_product', ImagesClueImageAPIView.as_view(), name='线稿生成产品图'),
    path('image_workflow_product', ProductReplacementWorkflowAPIView.as_view(), name='线上家具产品替换图'),
    path('image_fine_detail_product', FineDetailWorkflowAPIView.as_view(), name='细节精修产品图'),
    path('image_wide_picture', WidePictureWorkflowAPIView.as_view(), name='阔图处理'),
    path('image_internal_supplement', InternalSupplementationWorkflowAPIView.as_view(), name='内补功能'),
    path('image_internal_supplement_removal', InternalSupplementationAndRemovalWorkflowAPIView.as_view(), name='内补去除功能'),
    path('image_complete_redrawing', CompleteRedrawingWorkflowAPIView.as_view(), name='重绘精修功能'),
    path('white_image_product_only', WhiteBackgroundOnlyAPIView.as_view(), name='白底产品图'),
    path('multi_image_to_image', MultiImageToImageView.as_view(), name='多图生图'),
    path('combined_image_generation', CombinedImageGenerationView.as_view(), name='结合文身图和图生图的接口'),
    path('color_adjustment', ColorAdjustmentImageView.as_view(), name='色彩调节'),

    # AI API
    path('image_Gemini_API_product', GeminiImageGenerationView.as_view(), name='谷歌生图'),
    path('image_ChatGPT_API_product', ChatGPTImageGenerationView.as_view(), name='ChatGPT生图'),
    path('image_ChatGPT_NEW_API_product', ChatGPTImageGenerationNewView.as_view(), name='ChatGPT生图新的链接'),
    path('image_Volcengine_API_product', VolcengineVisualAPIView.as_view(), name='火山引擎生图'),
    path('image_Volcengine_SDK_API_product', VolcengineVisualAPIViewSDK.as_view(), name='火山引擎SDK生图'),
    path('image_ChatGPT_OPENAI_API_product', ChatGPTImageGenerationOpenAIView.as_view(), name='openai-image-generation'),
    path('flux-kontext-pro/image/generation/', FluxKontextProImageView.as_view(), name='flux-kontext-pro-image-generation_1'),
    path('flux-kontext-pro/image/flux/generation/', FluxKontextProImageFluxView.as_view(), name='flux-kontext-pro-image-generation_2'),

    path('get_user_images', get_user_conversation_images.as_view(), name='获取用户的图像列表'),
    path('get_all_images', get_all_conversation_images.as_view(), name='后台获取所有用户的图像列表'),
    path('del_rec', ImageUploadRecordDeleteView.as_view(), name='后台获取所有用户的图像列表'),
    path('newConver', newConversation.as_view(), name='新建会话列表'),
    path('delConver', deleteConversation.as_view(), name='删除会话列表'),
    path('getConver', get_ConversationList.as_view(), name='查询会话列表'),
    path('getCaptcha', getCaptcha.as_view(), name='图形验证码'),
    path('user-requests', UserRequestListView.as_view(), name='user-requests-list'),
    path('requests-input', UserInputAutoSaveView.as_view(), name='user-requests-list'),
    path('tasks/<str:task_id>/status', TaskStatusAPIView.as_view(), name='task_status'),
    path('tasks/<str:task_id>/cancel', TaskCancelAPIView.as_view(), name='task_cancel'),
    path('queue/comfyui/info', QueueInfoAPIView.as_view(), name='comfyui_queue_info'),
    path('queue/info/', QueueInfoAPIView.as_view(), name='queue_info'),

    # 队列管理API
    path('queue/admin/', QueueAdminAPIView.as_view(), name='queue_admin'),
    path('queue/admin/<str:task_id>/', QueueAdminAPIView.as_view(), name='queue_admin_task_detail'),

    # 用户云空间图片管理
    path('cloud/images/add', UserCloudImageAddView.as_view(), name='添加云空间图片'),
    path('cloud/images/list', UserCloudImageListView.as_view(), name='查询云空间图片'),
    path('cloud/images/manage', UserCloudImageDeleteView.as_view(), name='管理云空间图片'),
    path('cloud/images/import-from-comfyui', UserCloudImageImportFromComfyUIView.as_view(), name='从ComfyUI导入图片'),
    path('images/delete/', TemplateImageDeleteView.as_view(), name='template-image-delete'),
    
    # ComfyUI自动保存设置
    path('cloud/auto-save-setting', ComfyUITaskAutoSaveSettingView.as_view(), name='自动保存到云空间设置'),

    path('translate', BaiduTranslate.as_view(), name='翻译接口'),

    # 新增路由
    path('tasks/', UserTaskListAPIView.as_view(), name='user_tasks'),
    path('tasks/<str:task_id>/retry', RetryTaskAPIView.as_view(), name='retry_task'),
    
    # 任务类型管理API
    path('task-types/', TaskTypeManagementAPIView.as_view(), name='task_types_list_create'),
    path('task-types/<int:type_id>/', TaskTypeManagementAPIView.as_view(), name='task_type_detail'),

    # 积分扣除历史记录
    path('points-deduction-history/', UserPointsDeductionHistoryView.as_view(), name='points-deduction-history'),
]