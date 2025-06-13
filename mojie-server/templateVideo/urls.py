from django.urls import path
from templateVideo.views import RunningHubVideoAPIView,FileUploadAPIView,TemplateVideoStatusAPIView,TemplateVideoListAPIView\
    ,TemplateVideoDeleteAPIView,RunningHubCallbackAPIView

urlpatterns = [
    path('runninghub/', RunningHubVideoAPIView.as_view(), name='runninghub-video'),
    # path('webhook/', ComfyUIWebhookView.as_view(), name='runninghub-webhook'),
    path('upload/', FileUploadAPIView.as_view(), name='runninghub-webhook'),
    path('getvideos/', TemplateVideoListAPIView.as_view(), name='runninghub-webhook'),
    path('delvideos/', TemplateVideoDeleteAPIView.as_view(), name='runninghub-webhook'),
    path('status/<int:videoid>/', TemplateVideoStatusAPIView.as_view(), name='template-video-status'),
    path('callback/', RunningHubCallbackAPIView.as_view(), name='runninghub-callback'),
]