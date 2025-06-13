from django.urls import path

from user.views import user_logout, phonecode, UserLoginView, UserRegisterView, mojieLogin, mojie_logout, \
    TokenRefreshView, SysUserGetListView,ChangePasswordView,AssetsView,MiniProgramLoginView,CurrentUserInfoView
from .views import get_all_users,UserPhoneLoginView,mailcode,UserMailLoginView,UpdateUserView,ShareCodeView,LinkExampleByRealtagView,\
    UserShareInfoView,UserShareWeeklyStatsView,proxyLogin,CreateProxyUserView,forgetpassView
urlpatterns = [
    # path('test', TestView.as_view(), name='test'),  # 测试
    path('phoncode', phonecode.as_view(), name='test'),  # 手机验证码
    path('mailcode', mailcode.as_view(), name='test'),  # 邮箱验证码
    # path('list', TestViewList.as_view(), name='user-list'),  # 测试testlist
    # path('jwt_test', jwtViewTest.as_view(), name='jwt_test'),  #
    path('register', UserRegisterView.as_view(), name='register'),  # 用户简单注册
    path('refresh', TokenRefreshView.as_view(), name='register'),  # 用户简单注册
    path('login', UserLoginView.as_view(), name='login'),  
    path('aaa', LinkExampleByRealtagView.as_view(), name='login'),  
    path('phlogin', UserPhoneLoginView.as_view(), name='phlogin'),  
    path('maillogin', UserMailLoginView.as_view(), name='phlogin'),  
    path('logout', user_logout.as_view(), name='logout'),  
    path('repass', forgetpassView.as_view(), name='logout'),  
    path('userinfo', CurrentUserInfoView.as_view(), name='logout'),  
    path('cgpass', ChangePasswordView.as_view(), name='logout'),  
    path('assets', AssetsView.as_view(), name='logout'),  
    path('assets/<int:pk>/', AssetsView.as_view(), name='logout'),  
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # 后台管理系统
    path('mojie/login', mojieLogin.as_view(), name='login'),  
    path('mojie/logout', mojie_logout.as_view(), name='logout'),  
    path('mojie/list', get_all_users.as_view(), name='get_all_users'),
    path('mojie/user_seek', SysUserGetListView.as_view(), name='get_all_users'),
    path('mojie/user_update/<int:pk>/', UpdateUserView.as_view(), name='UpdateUserView'),

    # 代理系统
    path('proxy/login', proxyLogin.as_view(), name='login'),  
    path('proxy/list', UserShareInfoView.as_view(), name='get_all_users'),
    path('proxy/chart', UserShareWeeklyStatsView.as_view(), name='login'),  
    path('proxy/create-proxy/', CreateProxyUserView.as_view(), name='create-proxy-user'),



    path('wx-mini-login', MiniProgramLoginView.as_view(), name='login'),  

    # 获取分享码
    path('get_share_code', ShareCodeView.as_view(), name='get_share_code'),
    # 查询分享信息
    # path('get_share', ShareCodeView.as_view(), name='get_share_code'),


]





