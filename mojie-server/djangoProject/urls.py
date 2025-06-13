"""
URL configuration for djangoProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from djangoProject import settings
from templateImage.views import ImageViewSet
from user.views import UserViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'templateImage', ImageViewSet)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/user/', include('user.urls')), # 用户模块
    path('api/image/', include('templateImage.urls')), #模板图片模块
    path('api/video/', include('templateVideo.urls')), # 模板视频模块
    path('api/temp/', include('template.urls')), # 模板视频模块
    path('api/pay/', include('order.urls')),  # 支付相关路由
    # openAPI文档
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    # path('order/', include('order.urls')),  # 订单模块（初始功能）
    # path('templateImage/', include('templateImage.urls')),
]

# 开发环境下提供媒体文件的访问
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
