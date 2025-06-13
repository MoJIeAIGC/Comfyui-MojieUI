import json
import datetime
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema, OpenApiParameter, F
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny  # 新增对 AllowAny 的导入
from rest_framework.views import APIView
from rest_framework_jwt.settings import api_settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
import uuid
from common.ErrorCode import ErrorCode
from common.response_utils import ResponseUtil
from exception.business_exception import BusinessException
from user.models import SysUser, Assets
from rest_framework import viewsets
from user.models import SysUser,UserProxy
from .dto import UserRegisterDTO, UserLoginDTO
from .serializers import UserSerializer, SysUserVOSerializer,SysuserSerializer
from .userService import UserService
import logging
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
logger = logging.getLogger(__name__)
from django.contrib.auth.hashers import make_password
import string
import random
from django.core.cache import cache
class UserViewSet(viewsets.ModelViewSet):
    queryset = SysUser.objects.all()
    serializer_class = UserSerializer
from common.email_utils import send_test_email
from rest_framework.generics import get_object_or_404
import re  # 新增对 re 模块的导入
import requests
import configparser
from django.conf import settings
from rest_framework.views import APIView
from common.response_utils import ResponseUtil
from .models import MiniProgramUser,InvitedUser
# class TestView(APIView):
from .utils import MiniProgramUserTokenObtainPairSerializer
#     def get(self, request):
#         return JsonResponse({'code': 200, 'message': "测试"})
import os
import base64
from Crypto.Cipher import AES
import json
config = configparser.ConfigParser()
config.read(os.path.join(settings.BASE_DIR, 'config', 'config.ini'))
from order.models import UserVIP, Order
from common.sms_utils import SMSUtils
from user.models import UserShare  # 假设有ShareCode模型
avatar_url = "https://qihuaimage.tos-cn-guangzhou.volces.com/static/avator.png"
from django.core.paginator import Paginator

# 创建代理用户接口
class CreateProxyUserView(APIView):
    """创建代理用户接口"""
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # 获取请求数据
            username = request.data.get('username')
            password = request.data.get('password')
            webid = request.data.get('webid')  # 网页端用户ID
            miniid = request.data.get('miniid')  # 小程序用户ID

            # 验证必要参数
            if not username or not password:
                return ResponseUtil.error(message="用户名和密码不能为空")

            # 检查用户名是否已存在
            if SysUser.objects.filter(username=username).exists():
                return ResponseUtil.error(message="用户名已存在")

            # 创建新用户
            user = SysUser.objects.create(
                username=username,
                password=make_password(password),  # 加密密码
                userRole='proxy',  # 设置用户角色为proxy
                avatar=avatar_url,  # 使用默认头像
                create_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                update_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                isDelete=0
            )
            # 如果用户没有分享记录，创建一个
            user_share = UserShare.objects.create(
                user=user,
                invite_count=0,
                earned_points=0
            )

            # 处理邀请关系
            if webid:
                web_user = get_object_or_404(SysUser, id=webid)
                # web_user_share = UserShare.objects.filter(user=web_user).first()
                # InvitedUser.objects.create(
                #         user_share=user_share,
                #         invited_user=web_user
                #     )
                UserProxy.objects.create(
                    created_at=datetime.datetime.now(),  # 代理创建时间
                    proxy=web_user,  # 网页端用户
                    way=0,  # 网页端用户
                    account=user
                )


            if miniid:
                mini_user = get_object_or_404(SysUser, id=miniid)
                # mini_user_share = UserShare.objects.filter(user=mini_user).first()
                # InvitedUser.objects.create(
                #         user_share=user_share,
                #         invited_user=mini_user
                #     )
                UserProxy.objects.create(
                    created_at=datetime.datetime.now(),  # 代理创建时间
                    proxy=mini_user,  # 网页端用户
                    way=1,  # 网页端用户
                    account=user
                )

            return ResponseUtil.success(message="用户创建成功", data={
                'user_id': user.id,
                'username': user.username
            })

        except Exception as e:
            logger.error(f"创建代理用户失败: {str(e)}")
            return ResponseUtil.error(message="创建用户失败")

# 获取近7天的用户邀请统计信息
class UserShareWeeklyStatsView(APIView):
    """获取近7天的用户邀请统计信息"""
    permission_classes = [AllowAny]

    def get(self, request):
        user_id = request.query_params.get('user_id')

        if not user_id:
            return ResponseUtil.error(message="缺少用户ID参数")

        try:
            # 查询UserShare记录
            user_share = UserShare.objects.filter(user_id=user_id).first()
            if not user_share:
                return ResponseUtil.error(message="用户分享记录不存在")
            
            # 计算7天前的日期
            today = datetime.datetime.now().date()
            seven_days_ago = today - datetime.timedelta(days=6)
            
            # 查询最近7天的邀请记录
            invited_users = InvitedUser.objects.filter(
                user_share=user_share,
                created_at__date__gte=seven_days_ago,
                created_at__date__lte=today
            ).select_related('invited_user')

            # 初始化7天的数据
            daily_stats = {}
            current_date = seven_days_ago
            while current_date <= today:
                daily_stats[current_date.strftime('%Y-%m-%d')] = {
                    'date': current_date.strftime('%Y-%m-%d'),
                    'count': 0,
                    'users': []
                }
                current_date += datetime.timedelta(days=1)

            # 统计每天的邀请用户
            for invited_user in invited_users:
                invite_date = invited_user.created_at.date().strftime('%Y-%m-%d')
                daily_stats[invite_date]['count'] += 1
                daily_stats[invite_date]['users'].append({
                    'id': invited_user.invited_user.id,
                    'username': invited_user.invited_user.username,
                    'avatar': invited_user.invited_user.avatar,
                    'invite_time': invited_user.created_at
                })

            return ResponseUtil.success(data={
                'share_code': user_share.share_code,
                'total_invite_count': user_share.invite_count,
                'daily_stats': list(daily_stats.values())
            })

        except Exception as e:
            return ResponseUtil.error(message=f"查询失败: {str(e)}")

# 微信小程序登录
class MiniProgramLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        code = request.data.get('code')
        encrypted_data = request.data.get('encrypted_data')
        iv = request.data.get('iv')
        share_code = request.data.get('share_code')  # 新增分享码参数
        print("是否有share_code:", share_code)

        if not code:
            return ResponseUtil.error(message='缺少 code 参数')
        # if encrypted_data and not iv:
        #     return ResponseUtil.error(message='提供了加密数据但缺少初始向量 iv')
        # if iv and not encrypted_data:
        #     return ResponseUtil.error(message='提供了初始向量 iv 但缺少加密数据')

        appid = config.get('mini_program', 'appid')
        secret = config.get('mini_program', 'secret')
        print("appid:", appid)
        print("secret:", secret)
        url = 'https://api.weixin.qq.com/sns/jscode2session'
        params = {
            'appid': appid,
            'secret': secret,
            'js_code': code,
            'grant_type': 'authorization_code'
        }


        try:
            
            response = requests.get(url, params=params)
            response_data = response.json()
            print("response_data:", response_data)
            if 'errcode' in response_data:
                return ResponseUtil.error(message=f'微信接口调用失败: {response_data.get("errmsg")}')

            openid = response_data.get('openid')
            session_key = response_data.get('session_key')

            # if encrypted_data and iv:
            #     decrypted_data = decrypt_wechat_data(session_key, encrypted_data, iv)
            #     print("decrypted_data:", decrypted_data)
            #     if decrypted_data:
            #         print("--------------------------")
            #         nick_name = decrypted_data.get('nickName')
            #         print("nick_name:", nick_name)
            #         avatar_url = decrypted_data.get('avatarUrl')     
            #         print("avatar_url:", avatar_url)       

            # openid = '666'
            # session_key = '666'
            defaults = {
                'session_key': session_key
                }
            
            avatar_url = "https://qihuaimage.tos-cn-guangzhou.volces.com/static/avator.png"

            # 先尝试获取用户
            #user = SysUser.objects.filter(openid=openid).first()
            user = SysUser.objects.filter(openid=openid).first()
            
            if not user:
                # 处理分享码逻辑
                if share_code:
                    print("分享码share_code:", share_code)
                    try:
                        # 查询分享码表
                        share_record = UserShare.objects.filter(share_code=share_code).first()
                        print("share_record:", share_record)
                        if share_record:
                            print("update")
                            # 更新邀请人数和积分
                            share_user = SysUser.objects.filter(id=share_record.user.id).first()
                            if share_user:
                                share_user.points = share_user.points + 120
                                share_user.save()
                            share_record.invite_count = share_record.invite_count + 1
                            share_record.earned_points = share_record.earned_points + 120
                            share_record.save()
                    except Exception as e:
                        logger.warning(f"处理分享码失败: {str(e)}")
                # 用户不存在，创建新用户
                import random
                import string
                characters = string.ascii_letters + string.digits
                random_str = ''.join(random.choice(characters) for i in range(5))
                nick_name = f'wx_{random_str}'
                avatar_url = "https://qihuaimage.tos-cn-guangzhou.volces.com/static/avator.png"
                
                user = SysUser.objects.create(
                    openid=openid,
                    session_key=session_key,
                    username=nick_name,
                    avatar=avatar_url,
                    userRole="user",
                    create_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    points=100,
                    isDelete=0,
                )
                usershare = UserShare.objects.create(
                    user=user,
                    invite_count=0,
                    earned_points=0
                )
                print("该新用户的分享码", usershare.share_code)
                
                created = True
                print('userid:',user.id)

                # 处理分享码逻辑
                if share_code:
                    try:
                        # 查询分享码表
                        share_record = UserShare.objects.filter(share_code=share_code).first()
                        if share_record:
                            # 更新yaor字段，添加当前用户ID
                            if share_record.yaor:
                                share_record.yaor += f",{user.id}" if user else ""
                            else:
                                share_record.yaor = str(user.id) if user else ""
                            share_record.save()
                            InvitedUser.objects.create(
                                user_share=share_record,
                                invited_user=user,
                                created_at=datetime.datetime.now()
                            )
                    except Exception as e:
                        logger.warning(f"处理分享码失败: {str(e)}")
            else:
                # 用户存在，只更新session_key
                user.session_key = session_key
                user.save()
                created = False


            

            # 生成 JWT token
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            # 查询用户的 UserVIP 信息，过滤 is_active 为 True 的数据
            user_vip = UserVIP.objects.filter(user=user, is_active=True).first()
            vip_info = {
                'level': user_vip.level if user_vip else None,
                'end_time': user_vip.end_time if user_vip else None
            }

            return ResponseUtil.success(data={
                'openid': openid,
                'is_new_user': created,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'vip_level': vip_info['level'],
                'vip_end_time': vip_info['end_time'],
                # 'nickName': nick_name,
                'avatarUrl': avatar_url
            })

        except Exception as e:
            return ResponseUtil.error(message=f'登录失败: {str(e)}')


# 脚本接口
class LinkExampleByRealtagView(APIView):
    """
    关联Example和realtag数据
    1. 筛选is_example=True的realtag
    2. 根据name匹配Example的tag.description
    3. 建立关联关系
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # 删除用户表里面邮箱字段为""的用户将邮箱字段设置为None
        # SysUser.objects.filter(email='').update(email=None)
        # 积分清零
        whitelist_users = [
            'wx_LSgSv',
            'wx_WIVDA',
            'wx_VtPfr',
            'wx_opclM',
            'wx_ihNG6',
            'wx_el3Rj',
            'wx_XCCSW',
            'wx_ML084',

            'eggetteLuo@gmail.com',
            '13870796522',
            '351734088@qq.com',
            '1651055116@qq.com',
            'cynicbreakout@gmail.com',
            '18279761024',
            '15179064839',

        ]
        
        # 清零非白名单用户的积分
        # SysUser.objects.exclude(username__in=whitelist_users).update(points=0)

        return ResponseUtil.success(data={})

# 用户分享码接口
class ShareCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_share = UserShare.objects.filter(user=user).first()
        if not user_share:
            # 如果用户没有分享记录，创建一个
            user_share = UserShare.objects.create(
                user=user,
                invite_count=0,
                earned_points=0
            )
        yaor_users = []
        if user_share.yaor:
            user_ids = [int(id_str) for id_str in user_share.yaor.split(',') if id_str]
            users = SysUser.objects.filter(id__in=user_ids)
            yaor_users = [{
                'id': user.id,
                'nickname': user.username,
                'avatar': user.avatar
            } for user in users]

        return ResponseUtil.success(data={
            'share_code': user_share.share_code,
            'invite_count': user_share.invite_count,
            'earned_points': user_share.earned_points,
            'yaor_users': yaor_users  # 返回包含昵称和头像的用户列表
        })
        
# 代理后台获取邀请信息
class UserShareInfoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user_id = request.query_params.get('user_id')
        # 获取分页参数
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))

        if not user_id:
            return ResponseUtil.error(message="缺少用户ID参数")

        try:
            # 查询UserShare记录
            user_share = UserShare.objects.filter(user_id=user_id).first()
            if not user_share:
                return ResponseUtil.error(message="用户分享记录不存在")
            
            # 查询所有关联的InvitedUser记录
            invited_users = InvitedUser.objects.filter(user_share=user_share).select_related('invited_user')

            if invited_users.exists():
                # 对用户列表进行分页
                paginator = Paginator(invited_users, page_size)
                try:
                    page_obj = paginator.page(page)
                except Exception:
                    return ResponseUtil.error(message="请求的页码不存在")
                
                user_info_list = []
                for invited_user in page_obj.object_list:
                    user = invited_user.invited_user
                    user_info_list.append({
                        'id': user.id,
                        'invite_time': invited_user.created_at,
                        'username': user.username,
                        'avatar': user.avatar,
                    })
                
                return ResponseUtil.success(data={
                    'users': user_info_list,
                    'share_code': user_share.share_code,
                    'invite_count': user_share.invite_count,
                    'total': paginator.count,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': paginator.num_pages
                })
            
            return ResponseUtil.success(data={
                'users': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0
            })

        except ValueError:
            return ResponseUtil.error(message="分页参数必须为整数")
        except Exception as e:
            return ResponseUtil.error(message=f"查询失败: {str(e)}")



# 获取ip信息
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# 小程序解密算法
def decrypt_wechat_data(session_key, encrypted_data, iv):
    """
    解密微信小程序加密数据
    :param session_key: 会话密钥
    :param encrypted_data: 加密数据
    :param iv: 加密算法的初始向量
    :return: 解密后的数据
    """
    try:
        # 将 base64 编码的字符串解码
        session_key = base64.b64decode(session_key)
        encrypted_data = base64.b64decode(encrypted_data)
        iv = base64.b64decode(iv)

        # 创建 AES 解密器
        cipher = AES.new(session_key, AES.MODE_CBC, iv)

        # 解密数据
        decrypted_data = cipher.decrypt(encrypted_data)

        # 去除填充数据
        padding_length = decrypted_data[-1]
        decrypted_data = decrypted_data[:-padding_length]

        # 将解密后的数据转换为字典
        result = json.loads(decrypted_data)

        return result
    except Exception as e:
        print(f"解密失败: {e}")
        return None



# 手机验证码接口
class phonecode(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        phone = request.data.get('phone')
        if not phone:
            return ResponseUtil.error(message="手机号不能为空，请输入手机号！")

        if cache.get(phone) is not None:
            return ResponseUtil.error(message="获取验证码失败，验证码已存在，请稍后再试！")
        # 这里调用第三方的接口返回验证码
        sms_util = SMSUtils()
        rcode = sms_util.send_sms(phone)
        print("rcode:", rcode)
        
        if not rcode:
            return ResponseUtil.error(message="短信发送失败，请稍后再试！")
        # rcode = "666666"
        # 检查 cache 中是否已经存在 phone 这个键
        
        cache.set(phone, rcode, 120)
        return ResponseUtil.success( message="获取验证码成功")

# 邮箱验证码接口
class mailcode(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        mail = request.data.get('mail')

        if not mail:
            return ResponseUtil.error(message="邮箱不能为空，请输入邮箱！")


        if cache.get(mail) is not None:
            return ResponseUtil.error(message="验证码已存在，请稍后再试！")
        # 判断是邮箱还是手机号
        if '@' in mail:  # 邮箱逻辑
            rcode = ''.join(random.choices(string.digits, k=5))
            print("rcode:", rcode)
            # 发送邮件
            if send_test_email(mail, rcode):
                cache.set(mail, rcode, 120)
                return ResponseUtil.success(message="获取验证码成功")
            return ResponseUtil.error(message="获取验证码失败")
        else:  # 手机号逻辑
            try:
                if cache.get(mail) is not None:
                    return ResponseUtil.error(message="获取验证码失败，验证码已存在，请稍后再试！")
                sms_util = SMSUtils()
                rcode = sms_util.send_sms(mail)
                print("rcode:", rcode)
                
                if not rcode:
                    return ResponseUtil.error(message="短信发送失败，请稍后再试！")
                    
                cache.set(mail, rcode, 120)
                return ResponseUtil.success(message="获取验证码成功")
            except Exception as e:
                return ResponseUtil.error(message=f"短信发送失败: {str(e)}")

# 用户注销
class user_logout(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):

        try:
            # 从请求数据中获取 refresh_token
            refresh_token = request.data.get('refresh_token')
            # if not refresh_token:
            #     return ResponseUtil.error(message="缺少 refresh_token")
            # refresh_token = request.data["refresh_token"]
            print("refresh_token:", refresh_token)
            # # 创建 RefreshToken 对象
            token = RefreshToken(refresh_token)
            # # 将 refresh_token 加入黑名单
            token.blacklist()

            return ResponseUtil.success(message="注销成功")
        except Exception as e:
            return ResponseUtil.error("您还未登陆！")

# 用户注册接口
@method_decorator(csrf_exempt, name='dispatch')
class UserRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # user_name = request.POST.get("username")
            usermail = request.data.get("usermail")
            password = request.data.get("password")
            check_password = request.data.get("checkpassword")
            code = request.data.get("code")
            share_code = request.data.get('share_code')  # 新增分享码参数
            print("是否有share_code:", share_code)

            if not usermail:
                return ResponseUtil.error(message="邮箱不能为空，请输入手机号！")
            if not password:
                return ResponseUtil.error(message="密码不能为空，请输入密码！")
            if not check_password:
                return ResponseUtil.error(message="确认密码不能为空，请输入确认密码！")
            if not code:
                return ResponseUtil.error(message="验证码不能为空，请输入验证码！")

            # if SysUser.objects.filter(username=user_name).exists():
            #     return ResponseUtil.error(message="用户名已存在，请更换！")
            exituser = SysUser.objects.filter(username=usermail).first()
            if exituser:
                print("exituser:", exituser)
                if exituser.is_active == 0 or exituser.isDelete == 1:
                    return ResponseUtil.error(message="账号已被禁用，请联系管理员！")
                else:
                    return ResponseUtil.error(message="账号已存在，请更换！")

            # 检查验证码是否正确，这里简单假设验证码为 666666
            rcode = cache.get(usermail)
            print("rcode:", rcode)
            print("code:", code)
            if code != rcode:
                return ResponseUtil.error(message="验证码不正确，请重新输入！")


            # 检查两次输入的密码是否一致
            print("password:", password)
            print("check_password:", check_password)
            if password != check_password:
                return ResponseUtil.error( message="两次输入的密码不一致，请重新输入！")

            # 生成随机用户名
            characters = string.ascii_letters + string.digits
            user_name = ''.join(random.choice(characters) for i in range(8))
            # 处理分享码逻辑
            if share_code:
                print("分享码share_code:", share_code)
                try:
                    # 查询分享码表
                    share_record = UserShare.objects.filter(share_code=share_code).first()
                    print("share_record:", share_record)
                    if share_record:
                        print("update")
                        # 更新邀请人数和积分
                        share_user = SysUser.objects.filter(id=share_record.user.id).first()
                        if share_user:
                            share_user.points = share_user.points + 120
                            share_user.save()
                        share_record.invite_count = share_record.invite_count + 1
                        share_record.earned_points = share_record.earned_points + 120
                        share_record.save()
                except Exception as e:
                    logger.warning(f"处理分享码失败: {str(e)}")
                # 用户不存在，创建新用户
            # 4. 创建用户
            user = SysUser.objects.create(
                avatar=avatar_url,
                username=usermail,
                password=make_password(password),
                userRole="user",
                email=usermail if '@' in usermail else None,
                phone=usermail if '@' not in usermail else None,
                create_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                points=100,
                userAITime="30s",
                isDelete=0
            )
            usershare = UserShare.objects.create(
                    user=user,
                    invite_count=0,
                    earned_points=0
                )
            print("该新用户的分享码", usershare.share_code)
            # 处理分享码逻辑
            if share_code:
                try:
                    # 查询分享码表
                    share_record = UserShare.objects.filter(share_code=share_code).first()
                    if share_record:
                        # 更新yaor字段，添加当前用户ID
                        if share_record.yaor:
                            share_record.yaor += f",{user.id}" if user else ""
                        else:
                            share_record.yaor = str(user.id) if user else ""
                        share_record.save()
                        InvitedUser.objects.create(
                                user_share=share_record,
                                invited_user=user,
                                created_at=datetime.datetime.now()
                            )
                except Exception as e:
                    logger.warning(f"处理分享码失败: {str(e)}")
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            # 返回成功响应
            return ResponseUtil.success(
                data={
                    "userId": user.id,
                    "username": user.username,
                    "userRole": user.userRole,
                    "access_token": access_token,  # 返回 JWT 访问令牌
                    "refresh_token": refresh_token  # 返回 JWT 刷新令牌
                },
                message="登录成功"
            )
            

        
        except Exception as e:
            logger.error(f'用户登录失败，服务器内部错误: {e}')
            return ResponseUtil.error(
                message=f'用户登录失败，服务器内部错误: {e}'
            )


# 忘记密码接口
# 用户注册接口
@method_decorator(csrf_exempt, name='dispatch')
class forgetpassView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # user_name = request.POST.get("username")
            usermail = request.data.get("usermail")
            password = request.data.get("password")
            check_password = request.data.get("checkpassword")
            code = request.data.get("code")
            

            if not usermail:
                return ResponseUtil.error(message="邮箱不能为空，请输入手机号！")
            if not password:
                return ResponseUtil.error(message="密码不能为空，请输入密码！")
            if not check_password:
                return ResponseUtil.error(message="确认密码不能为空，请输入确认密码！")
            if not code:
                return ResponseUtil.error(message="验证码不能为空，请输入验证码！")

            # if SysUser.objects.filter(username=user_name).exists():
            #     return ResponseUtil.error(message="用户名已存在，请更换！")
            exituser = SysUser.objects.filter(username=usermail).first()
            if exituser:
                print("exituser:", exituser)
                if exituser.is_active == 0 or exituser.isDelete == 1:
                    return ResponseUtil.error(message="账号已被禁用，请联系管理员！")
                
            else:
                return ResponseUtil.error(message="账号不存在，请重新输入！")

            # 检查验证码是否正确，这里简单假设验证码为 666666
            rcode = cache.get(usermail)
            print("rcode:", rcode)
            print("code:", code)
            if code != rcode:
                return ResponseUtil.error(message="验证码不正确，请重新输入！")


            # 检查两次输入的密码是否一致
            print("password:", password)
            print("check_password:", check_password)
            if password != check_password:
                return ResponseUtil.error( message="两次输入的密码不一致，请重新输入！")

            
            # 4. 创建用户
            exituser.password=make_password(password)
            exituser.save()
            # 返回成功响应
            return ResponseUtil.success(
                message="密码重置成功"
            )
        except Exception as e:
            logger.error(f'密码重置失败，服务器内部错误: {e}')
            return ResponseUtil.error(
                message=f'密码重置失败，服务器内部错误: {e}'
            )



# 用户登录接口
@method_decorator(csrf_exempt, name='dispatch')
class UserLoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        """
        用户登录接口
        """
        try:
            # session_id = request.session.session_key
            # print("session_id:", session_id)

            # user_name = request.POST.get("user_name")
            usermail = request.data.get("usermail")
            password = request.data.get("password")
            code = request.data.get("code")


            client_ip = get_client_ip(request)
            print(f"客户端 IP 地址: {client_ip}")

            rcode = cache.get(client_ip)
            print("rcode:",rcode)
            print("rcode:",cache.get(client_ip+'errorlogin'))

             # 非空判断
            if not usermail:
                return ResponseUtil.error(message="邮箱不能为空，请输入邮箱！")
            if not password:
                return ResponseUtil.error(message="密码不能为空，请输入密码！")

            if not code and cache.get(client_ip+'errorlogin'):
                return ResponseUtil.error(message="验证码不能为空，请输入验证码！")
            print("-------------------")

            if cache.get(client_ip+'errorlogin'):
                if not re.match(r'^[a-zA-Z0-9]+$', code) :
                    return ResponseUtil.error(message="验证码格式错误，请重新输入！")

            
            
            print("rcode:", rcode)
            print("code:", code)
            print("-------------------")

            if cache.get(client_ip+'errorlogin'):
                if rcode is None:
                    return ResponseUtil.error(message="验证码失效")
                if code.lower() != rcode.lower():
                    return ResponseUtil.error(message="验证码不正确，请重新输入！")
            print("-------------------")

            print("usermail:", usermail)
            print("password:", password)

            try:
                user = authenticate(username=usermail, password=password)
                if not user:
                    cache.set(client_ip+'errorlogin', 1, 120)
                    print(f"用户登录失败，",cache.get(client_ip+'errorlogin'))
                    return ResponseUtil.error(message="用户名或密码错误")

            
                # user = authenticate(email=usermail, password=password)
                print("user:", user)  # 打印验证结果
                if user:
                    if user.openid is not None:
                        return ResponseUtil.error(message="小程序用户，禁止登录")
                    if user.is_active == 0 or user.isDelete == 1:
                        return ResponseUtil.error(message="账号已被禁用，请联系管理员！")
                    # token, created = Token.objects.get_or_create(user=user)
                    refresh = RefreshToken.for_user(user)
                    access_token = str(refresh.access_token)
                    refresh_token = str(refresh)
                    # 返回成功响应
                    cache.delete(client_ip+'errorlogin')  # 删除redis中的值
                    return ResponseUtil.success(
                        data={
                            "userId": user.id,
                            "username": user.username,
                            "userRole": user.userRole,
                            "access_token": access_token,  # 返回 JWT 访问令牌
                            "refresh_token": refresh_token  # 返回 JWT 刷新令牌
                        },
                        message="登录成功"
                    )
            except Exception as e:
                cache.set(client_ip+'errorlogin', 1, 120)
                print(f"用户登录失败，",cache.get(client_ip+'errorlogin'))
                print(f"用户登录失败，服务器内部错误: {e}")
                return ResponseUtil.error(message="用户登录失败，服务器内部错误")

        
        except Exception as e:
            # 捕获其他异常并返回服务器内部错误
            logger.error(f'用户登录失败，服务器内部错误: {e}')
            return ResponseUtil.error(message=f'用户登录失败，服务器内部错误: {e}')

# 用户手机号登录
@method_decorator(csrf_exempt, name='dispatch')
class UserPhoneLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # 获取手机号和验证码
            phone = request.data.get('phone')
            code = request.data.get('code')
            # imgcode = request.data.get('imgcode')
            if not phone:
                return ResponseUtil.error(message="手机号不能为空，请输入手机号！")
            if not code:
                return ResponseUtil.error(message="验证码不能为空，请输入验证码！")
            if not re.match(r'^[a-zA-Z0-9]+$', code):
                return ResponseUtil.error(message="验证码格式错误，请重新输入！")
            # if not imgcode:
            #     return ResponseUtil.error(message="图形验证码不能为空，请输入验证码！")
            # if not re.match(r'^[a-zA-Z0-9]+$', imgcode):
            #     return ResponseUtil.error(message="图形验证码格式错误，请重新输入！")

            # 检查验证码是否正确，这里简单假设验证码为 666666
            rcode = cache.get(phone)
            print("rcode:", rcode)
            print("code:", code)
            if code != rcode:
                return ResponseUtil.error(message="验证码不正确，请重新输入！")

            client_ip = get_client_ip(request)
            print(f"客户端 IP 地址: {client_ip}")

            # icode = cache.get(client_ip)
            
            # print("icode:", icode)
            # print("imgcode:", imgcode)
            # if icode is None:
            #     return ResponseUtil.error(message="验证码失效")
            # if icode.lower() != imgcode.lower():
            #     return ResponseUtil.error(message="验证码不正确，请重新输入！")

            # 在数据库中查询用户
            user = SysUser.objects.filter(username=phone).first()


            if user:
                if user.openid is not None:
                    return ResponseUtil.error(message="小程序用户，禁止登录")
                # 用户已存在
                if user.is_active == 0 or user.isDelete == 1:
                    return ResponseUtil.error(message="账号已被禁用，请联系管理员！")
                # user.is_active = 1
                # user.isDelete = 0
                # user.save()
                data = {
                    "userId": user.id,
                    "username": user.username,
                    "phone": user.phone
                }
            else:
                # 用户不存在，创建新用户
                # 生成随机的 8 位用户名
                characters = string.ascii_letters + string.digits
                username = ''.join(random.choice(characters) for i in range(8))

                user = SysUser.objects.create(
                    avatar=avatar_url,
                    username=phone,
                    password=0,  # 这里可以设置默认密码，或者后续让用户重置
                    phone=phone,
                    userRole="user",
                    create_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    points=100,
                    userAITime="30s",
                    isDelete=0
                )

                data = {
                    "userId": user.id,
                    "username": user.username,
                    "phone": user.phone
                }
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            data["access_token"] = access_token
            data["refresh_token"] = refresh_token
            cache.delete('phone')
            return ResponseUtil.success(data=data, message="手机号登录成功")

        except Exception as e:
            logger.error(f'用户手机号登录失败，服务器内部错误: {e}')
            return ResponseUtil.error(
                message='服务器内部错误',
            )


# 邮箱登录
@method_decorator(csrf_exempt, name='dispatch')
class UserMailLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # 获取手机号和验证码
            mail = request.data.get('mail')
            code = request.data.get('code')

            # 检查验证码是否正确，这里简单假设验证码为 666666
            rcode = cache.get(mail)
            if not mail:
                return ResponseUtil.error(message="邮箱不能为空，请输入邮箱！")
            if not code:
                return ResponseUtil.error(message="验证码不能为空，请输入验证码！")
            if not code.isdigit():
                return ResponseUtil.error(message="验证码必须为数字，请重新输入！")

            print("rcode:", rcode)
            print("code:", code)
            if code != rcode:
                return ResponseUtil.error(message="验证码不正确，请重新输入！")

            # 在数据库中查询用户
            user = SysUser.objects.filter(username=mail).first()


            if user:
                if user.openid is not None:
                    return ResponseUtil.error(message="小程序用户，禁止登录")
                # 用户已存在
                if user.is_active == 0 or user.isDelete == 1:
                    return ResponseUtil.error(message="账号已被禁用，请联系管理员！")
                print("用户已存在user:", user)
                
                data = {
                    "userId": user.id,
                    "username": user.username,
                    "phone": user.phone,
                    "email": user.email
                }
            else:
                # return ResponseUtil.error(message='用户不存在',)
                # 用户不存在，创建新用户
                # 生成随机的 8 位用户名
                characters = string.ascii_letters + string.digits
                username = ''.join(random.choice(characters) for i in range(8))

                user = SysUser.objects.create(
                    avatar=avatar_url,
                    username=mail,
                    password=0,  # 这里可以设置默认密码，或者后续让用户重置
                    email=mail,
                    userRole="user",
                    create_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    points=100,
                    userAITime="30s",
                    isDelete=0
                )

                data = {
                    "userId": user.id,
                    "username": user.username,
                    "phone": user.phone,
                    "email": user.email
                }
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            data["access_token"] = access_token
            data["refresh_token"] = refresh_token
            cache.delete('phone')
            return ResponseUtil.success(data=data, message="邮箱登录成功")

        except Exception as e:
            logger.error(f'用户手机号登录失败，服务器内部错误: {e}')
            return ResponseUtil.error(
                message='服务器内部错误',
            )



# 刷新 Token
class TokenRefreshView(APIView):
    # permission_classes = [AllowAny]
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if not refresh_token:
                return ResponseUtil.error(message="缺少 refresh_token")

            token = RefreshToken(refresh_token)
            new_access_token = str(token.access_token)
            new_refresh_token = str(token)

            return ResponseUtil.success(
                data={
                    "access_token": new_access_token,
                    "refresh_token": new_refresh_token
                },
                message="Token 刷新成功"
            )
        except Exception as e:
            return ResponseUtil.error(message="Token 刷新失败")



# 后台管理系统登录接口
class mojieLogin(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        """
        用户登录接口
        """
        try:
            user_name = request.data.get("user_name")
            password = request.data.get("password")
            print("user_name:", user_name)
            print("password:", password)

            user = authenticate(username=user_name, password=password)
            print("user:", user)  # 打印验证结果
            if user and user.userRole == 'admin':
                # token, created = Token.objects.get_or_create(user=user)
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                refresh_token = str(refresh)
                # 返回成功响应
                return ResponseUtil.success(
                    data={
                        "userId": user.id,
                        "username": user.username,
                        "userRole": user.userRole,
                        "access_token": access_token,  # 返回 JWT 访问令牌
                        "refresh_token": refresh_token  # 返回 JWT 刷新令牌
                    },
                    message="登录成功"
                )
                return ResponseUtil.error()
        
        except Exception as e:
            # 捕获其他异常并返回服务器内部错误
            logger.error(f'用户登录失败，服务器内部错误: {e}')
            return ResponseUtil.error()


# 代理系统登录接口
class proxyLogin(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        """
        用户登录接口
        """
        try:
            user_name = request.data.get("user_name")
            password = request.data.get("password")
            print("user_name:", user_name)
            print("password:", password)

            user = authenticate(username=user_name, password=password)
            print("user:", user)  # 打印验证结果
            if user and user.userRole == 'proxy':
                # 查询UserProxy表中proxy字段等于当前用户的记录
                proxy_relations = UserProxy.objects.filter(account=user)
                # 按way字段分类关联用户
                web_accounts = 0
                mini_accounts = 0
                for relation in proxy_relations:
                    if relation.way == 0:
                        web_accounts = relation.proxy.id
                    elif relation.way == 1:
                        mini_accounts = relation.proxy.id
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                refresh_token = str(refresh)
                # 返回成功响应
                return ResponseUtil.success(
                    data={
                        "userId": user.id,
                        "avatar": user.avatar,
                        "username": user.username,
                        "phone": user.phone,
                        "email": user.email,
                        "userRole": user.userRole,
                        "access_token": access_token,  # 返回 JWT 访问令牌
                        "refresh_token": refresh_token,  # 返回 JWT 刷新令牌
                        "web_accounts": web_accounts,  # way=0的关联用户
                        "mini_accounts": mini_accounts  # way=1的关联用户
                    },
                    message="登录成功"
                )
            return ResponseUtil.error(message="用户名或密码错误")
        
        except Exception as e:
            # 捕获其他异常并返回服务器内部错误
            logger.error(f'用户登录失败，服务器内部错误: {e}')
            return ResponseUtil.error()


# 后台管理系统登出
class mojie_logout(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh_token"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return ResponseUtil.success(message="注销成功")
        except Exception as e:
            return ResponseUtil.error(message="注销失败，请检查刷新令牌")


# 查询所有用户的视图函数
class get_all_users(APIView):
    # permission_classes = [AllowAny]
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    """
    获取所有用户的视图函数
    :param request: 请求对象
    :return: JSON 响应，包含所有用户的信息
    """
    def get(self, request):
        try:
            # 查询所有用户
            users = SysUser.objects.filter(isDelete=0)
            user_list = []
            for user in users:
                user_data = {
                    'id': user.id,
                    'username': user.username,
                    'phone': user.phone,
                    'email': user.email,
                    'userRole': user.userRole,
                    'userAITime': user.userAITime,
                    'points': user.points,
                    'create_time': str(user.create_time) if user.create_time else None,
                    'remark': user.remark
                }
                user_list.append(user_data)
            # 使用 responseutill 返回成功响应
            return ResponseUtil.success(data=user_list, message="获取所有用户成功")
        except Exception as e:
            # 处理异常情况
            return ResponseUtil.error(message="获取所有用户失败")

# 删除用户的视图函数


# 条件查询获取用户信息
class SysUserPagination(PageNumberPagination):
    page_size = 10  # 每页显示 10 条数据
    page_size_query_param = 'page_size'  # 允许客户端自定义每页大小
    max_page_size = 100  # 每页最大显示 100 条数据


# 后台修改用户信息
class UpdateUserView(APIView):
    """修改Product模型的接口"""
    # permission_classes = [AllowAny]  # 根据需求设置权限

    def put(self, request, pk):
        """更新Product对象"""
        try:
            # 获取要更新的Product对象
            user = get_object_or_404(SysUser, pk=pk)
            # 初始化序列化器
            serializer = SysuserSerializer(user, data=request.data, partial=True)
            print(serializer)
            if serializer.is_valid():
                # 保存更新后的对象
                serializer.save()
                return ResponseUtil.success(data=serializer.data)
            # return ResponseUtil.error()
        except Exception as e:
            logger.error(f"更新Product对象失败: {str(e)}")
            return ResponseUtil.error(description = "修改失败")


# 修改用户密码
class ChangePasswordView(APIView):
    """
    修改用户密码的视图类
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = request.user
        password = request.data.get("password")
        check_password = request.data.get("checkpassword")
        old_password = request.data.get("oldpassword")  # 假设这里是旧密码字段名

        if not password:
            return ResponseUtil.error(message="密码不能为空，请输入密码！")
        if not check_password:
            return ResponseUtil.error(message="确认密码不能为空，请输入确认密码！")
        if not old_password:
            return ResponseUtil.error(message="旧密码不能为空，请输入旧密码！")

        try:
            # 验证旧密码是否正确
            if not user.check_password(old_password):
                return ResponseUtil.error(message="旧密码不正确，请重新输入！")

            # 验证两次输入的新密码是否一致
            if password != check_password:
                return ResponseUtil.error(message="两次输入的密码不一致，请重新输入！")

            # 修改用户密码
            user.set_password(password)
            user.save()

            return ResponseUtil.success(message="密码修改成功！")

        except Exception as e:
            logger.error(f"修改用户密码失败: {str(e)}")
            return ResponseUtil.error(message="修改用户密码失败，请稍后再试！")
        




@method_decorator(csrf_exempt, name='dispatch')
class SysUserGetListView(APIView):
    """
    用户列表查询视图，支持分页和多种条件过滤
    """
    pagination_class = SysUserPagination

    @extend_schema(
        parameters=[
            OpenApiParameter(name='user_id', description='用户ID', type=int, required=False),
            OpenApiParameter(name='username', description='用户名(模糊)', type=str, required=False),
            OpenApiParameter(name='phone', description='手机号(精确)', type=str, required=False),
            OpenApiParameter(name='email', description='邮箱(模糊)', type=str, required=False),
            OpenApiParameter(name='userRole', description='用户角色', type=str, required=False),
            OpenApiParameter(name='isDelete', description='删除状态(0正常 1停用)', type=int, required=False),
        ],
        responses={200: SysUserVOSerializer(many=True)},
    )
    def get(self, request):
        """
        获取用户列表，支持分页和多种条件过滤
        """
        # 获取查询参数
        params = request.query_params
        user_id = params.get('user_id')
        username = params.get('username')
        phone = params.get('phone')
        email = params.get('email')
        user_role = params.get('userRole')
        is_delete = params.get('isDelete')

        # 构建查询条件
        queryset = SysUser.objects.all()

        if user_id:
            queryset = queryset.filter(id=user_id)
        if username:
            queryset = queryset.filter(username__icontains=username)
        if phone:
            queryset = queryset.filter(phone=phone)
        if email:
            queryset = queryset.filter(email__icontains=email)
        if user_role:
            queryset = queryset.filter(userRole=user_role)
        if is_delete is not None:
            queryset = queryset.filter(isDelete=int(is_delete))

        # 分页处理
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        # 序列化数据
        serializer = SysUserVOSerializer(page, many=True)
        response_data = {
            'results': serializer.data,  # 当前页的数据
            'pagination': {
                'total': paginator.page.paginator.count,  # 总记录数
                'page': paginator.page.number,  # 当前页码
                'page_size': paginator.get_page_size(request),  # 每页大小
                'next': paginator.get_next_link(),  # 下一页的链接
                'previous': paginator.get_previous_link(),  # 上一页的链接
            }
        }

        # 返回分页结果
        return ResponseUtil.success(data=response_data, message="Users retrieved successfully")



class AssetsView(APIView):
    """查询 Template 表的所有数据的接口"""
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            examples = Assets.objects.all()
        except ValueError:
            return ResponseUtil.error(message="tagid 参数必须为整数")
        data = list(examples.values())
        return ResponseUtil.success(data=data)

    def put(self, request, pk):
        try:
            asset = Assets.objects.get(pk=pk)
            name = request.data.get('name')
            text = request.data.get('text')

            if name:
                asset.name = name
            if text:
                asset.text = text

            asset.save()
            data = {
                'id': asset.id,
                'name': asset.name,
                'text': asset.text
            }
            return ResponseUtil.success(data=data)
        except Exception as e:
            return ResponseUtil.error(message=(e))


# 每日添加积分
class DailyPointsView(APIView):
    """用户每日签到领取积分"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            # Redis key格式：daily_points_{user_id}_{date}
            today = datetime.now().strftime('%Y-%m-%d')
            cache_key = f'daily_points_{user.id}_{today}'
            
            # 检查是否已经领取过
            if cache.get(cache_key):
                return ResponseUtil.success(message='今日已领取')
            
            # 增加积分
            points_change = 30
            user.points += points_change
            user.save()
            
            # 设置Redis标记，24小时后自动过期
            # 设置过期时间为第二天0点
            tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            expire_seconds = int((tomorrow - datetime.now()).total_seconds())
            cache.set(cache_key, 1, expire_seconds)
            
            return ResponseUtil.success(message='积分领取成功', data={
                'points_added': points_change,
                'current_points': user.points
            })
            
        except Exception as e:
            return ResponseUtil.error(message=str(e))


# 获取当前用户信息的视图
class CurrentUserInfoView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # 获取当前用户
            user = request.user

            # 查询用户关联的 UserVIP 信息，过滤 is_active 为 True 的数据
            user_vip = UserVIP.objects.filter(user=user, is_active=True).first()
            print(user.points)
            print(user.vip_points)
            # 构建返回数据
            user_data = {
                'id': user.id,
                'username': user.username,
                'avatar': user.avatar,
                'points': user.points+user.vip_points,
                'email': user.email,
                'phone': user.phone,
                'userRole': user.userRole,
                'vip_info': {
                    'level': user_vip.level if user_vip else None,
                    'end_time': user_vip.end_time if user_vip else None
                }
            }

            return ResponseUtil.success(data=user_data, message="当前用户信息获取成功")
        except Exception as e:
            logger.error(f'获取当前用户信息失败: {e}')
            return ResponseUtil.error(message="获取当前用户信息失败")


# 新增用户
