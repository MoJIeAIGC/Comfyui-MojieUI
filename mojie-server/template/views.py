from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny,IsAuthenticated
from .models import Example, Template, Tag, realtag, UserLike, UserFavorite, ExampleLike
from common.response_utils import ResponseUtil
from common.volcengine_tos_utils import VolcengineTOSUtils
import string
import random
from django.core.paginator import Paginator
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.shortcuts import redirect, get_object_or_404
from .serializer import TemplateSerializer
from django.core.cache import cache  # 新增导入cache模块
# 初始化工具类
tos_utils = VolcengineTOSUtils()
from django.db.models import Case, When
import redis
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
def flush_redis_database():

    redis_url ='redis://localhost:6379/6'
    
    # 连接到Redis
    r = redis.from_url(redis_url)
    
    # 执行FLUSHDB命令（删除当前数据库）
    r.flushdb()
    return True


class LinkExampleByRealtagView(APIView):
    """
    关联Example和realtag数据
    1. 筛选is_example=True的realtag
    2. 根据name匹配Example的tag.description
    3. 建立关联关系
    """
    permission_classes = [AllowAny]

    def get(self, request):
        
        

        return ResponseUtil.success(data={
        })



# 范例查询
class ExampleListView(APIView):
    """查询 Example 表的所有数据的接口"""
    permission_classes = [AllowAny]

    def get(self, request):
        # 生成缓存键，包含所有查询参数
        cache_key = f"example_list_{request.GET.urlencode()}"
        # 尝试从缓存获取数据
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            print('从缓存获取范例列表数据')
            # 从缓存获取基础数据
            result = cached_data
            # 如果有userid参数，查询点赞状态
            userid = request.GET.get('userid')
            if userid:
                try:
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    user = User.objects.get(id=userid)
                    data = result['data']
                    for item in data:
                        example_id = item['id']
                        example = Example.objects.get(id=example_id)
                        is_liked = ExampleLike.objects.filter(user=user, example_id=example_id).exists()
                        item['is_liked'] = 1 if is_liked else 0
                        item['like_count'] = example.like_count
                except User.DoesNotExist:
                    pass
            return ResponseUtil.success(data=result)

        # 获取 tagid 和 cateid 参数，默认为 0
        tagid = request.GET.get('cateid', 0)
        cateid = request.GET.get('tagid', 0)
        # 获取 title 参数
        title = request.GET.get('title')
        modeluse = request.GET.get('model')

        # 获取分页参数
        page = request.GET.get('page', 1)
        page_size = request.GET.get('page_size', 10)

        try:
            tagid = int(tagid)
            cateid = int(cateid)
            page = int(page)
            page_size = int(page_size)
            query_filter = {'is_deleted': False}
            if tagid != 0:
                query_filter['tag'] = tagid
            if cateid != 0:
                query_filter['realtag'] = cateid
            if title:
                query_filter['title__icontains'] = title
            if modeluse:
                query_filter['generation_method'] = modeluse

            examples = Example.objects.filter(**query_filter).order_by('-created_date')
        except ValueError:
            return ResponseUtil.error(message="tagid、cateid、page 和 page_size 参数必须为整数")

        paginator = Paginator(examples, page_size)
        try:
            page_obj = paginator.page(page)
        except Exception:
            return ResponseUtil.error(message="请求的页码不存在")

        data = list(page_obj.object_list.values())
        # 如果有userid参数，查询点赞状态
        userid = request.GET.get('userid')
        if userid:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(id=userid)
                for index, example in enumerate(page_obj.object_list):
                    is_liked = ExampleLike.objects.filter(user=user, example=example).exists()
                    data[index]['is_liked'] = 1 if is_liked else 0
            except User.DoesNotExist:
                pass

        # 添加标签信息
        for index, example in enumerate(page_obj.object_list):
            tags = list(example.tag.values_list('id', flat=True))
            data[index]['tags'] = tags
            realtags = list(example.realtag.values_list('name', flat=True))
            data[index]['realtagsname'] = realtags
            realtags = list(example.realtag.values_list('id', flat=True))
            data[index]['realtags'] = realtags

        result = {
            'data': data,
            'total': paginator.count,
            'page': page,
            'page_size': page_size
        }

        # 将结果存入缓存，设置过期时间为1小时
        cache.set(cache_key, result, timeout=120)

        return ResponseUtil.success(data=result)


# 网页查模板
class webTemplateListView(APIView):
    """查询 Template 表的所有数据的接口"""
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    permission_classes = [AllowAny]
    # authentication_classes = [JWTAuthentication]  # 添加认证类以获取用户信息

    def get(self, request):
        # 生成缓存键，包含所有查询参数
        cache_key = f"template_list_{request.GET.urlencode()}"
        # 尝试从缓存获取数据
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            print('从缓存获取模板列表数据'+cache_key)
            # return ResponseUtil.success(data=cached_data)
        # 获取用户信息，假设用户信息在 request.user 中，且有 userRole 属性
        userid = request.GET.get('userid')
        # user = request.user
        # try:
        #     user_role = user.userRole
        # except AttributeError:
        #     return ResponseUtil.error(message="无法获取用户角色信息")
        user = None
        if userid:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(id=userid)
                try:
                    user_role = user.userRole
                except AttributeError:
                    return ResponseUtil.error(message="无法获取用户角色信息")
            except User.DoesNotExist:
                return ResponseUtil.error(message="指定的用户不存在")
        else:
            user_role = None

        # 获取 tagid 和 realtagid 参数，默认为 0
        tagid = request.GET.get('cateid', 0)
        realtagid = request.GET.get('tagid', 0)
        # 获取 title 参数
        title = request.GET.get('title')  # 新增获取 title 参数

        # 获取分页参数
        page = request.GET.get('page', 1)
        page_size = request.GET.get('page_size', 10)

        try:
            tagid = int(tagid)
            realtagid = int(realtagid)
            page = int(page)
            page_size = int(page_size)
            query_filter = {'is_deleted': False}

            if tagid != 0:
                query_filter['tag'] = tagid
            if realtagid != 0:
                query_filter['realtag'] = realtagid
            # 如果 title 存在，添加 title 过滤条件
            if title:
                query_filter['title__icontains'] = title  # 新增 title 过滤条件

            templates = Template.objects.filter(**query_filter)
        except ValueError:
            return ResponseUtil.error(message="tagid、realtagid、page 和 page_size 参数必须为整数")

        if user_role == 'admin':
            # 管理员角色，不分页查询
            data = list(templates.values())
            # 为每条数据添加对应的 realtag 信息、islike 和 isfavor 参数
            for index, template in enumerate(templates):
                realtags = list(template.realtag.values_list('id', flat=True))
                data[index]['realtags'] = realtags
                realtagsname = list(template.realtag.values_list('name', flat=True))
                data[index]['realtagsname'] = realtagsname

                # 检查用户是否点赞
                from .models import UserLike  # 假设 UserLike 模型在当前应用的 models.py 中
                if user:
                    is_liked = UserLike.objects.filter(user=user, template=template).exists()
                    data[index]['islike'] = 1 if is_liked else 0


                # 检查用户是否收藏
                # from .models import UserFavorite  # 假设 UserFavorite 模型在当前应用的 models.py 中
                # is_favorited = UserFavorite.objects.filter(user=user, template=template).exists()
                # data[index]['isfavor'] = 1 if is_favorited else 0

            result = {
                'data': data,
                'total': len(data),
                'page': 1,
                'page_size': len(data)
            }
        else:
            # 非管理员角色，进行分页
            paginator = Paginator(templates, page_size)
            try:
                page_obj = paginator.page(page)
            except Exception:
                return ResponseUtil.error(message="请求的页码不存在")

            data = list(page_obj.object_list.values())
            # 为每条数据添加对应的 realtag 信息、islike 和 isfavor 参数
            for index, template in enumerate(page_obj.object_list):
                realtags = list(template.realtag.values_list('id', flat=True))
                data[index]['realtags'] = realtags
                data[index]['text'] = template.text

                # 检查用户是否点赞
                from .models import UserLike  # 假设 UserLike 模型在当前应用的 models.py 中
                if user:
                    is_liked = UserLike.objects.filter(user=user, template=template).exists()
                    data[index]['islike'] = 1 if is_liked else 0
                
                # # 检查用户是否收藏
                # from .models import UserFavorite  # 假设 UserFavorite 模型在当前应用的 models.py 中
                # is_favorited = UserFavorite.objects.filter(user=user, template=template).exists()
                # data[index]['isfavor'] = 1 if is_favorited else 0

            # 返回分页信息
            result = {
                'data': data,
                'total': paginator.count,
                'page': page,
                'page_size': page_size
            }
        # 将结果存入缓存，设置过期时间为1小时
        # cache.set(cache_key, result, timeout=120)

        return ResponseUtil.success(data=result)


# 根据分类查询标签
class RealtagByTagView(APIView):
    """
    根据分类ID筛选关联的realtag数据
    """
    permission_classes = [AllowAny]

    def get(self, request):
        tag_id = request.GET.get('cate_id')
        if not tag_id:
            return ResponseUtil.error(message="请提供分类ID")
        
        try:
            tag_id = int(tag_id)
        except ValueError:
            return ResponseUtil.error(message="分类ID必须为整数")

        # 筛选关联指定tag的realtag数据
        realtags = realtag.objects.filter(tag__id=tag_id, is_deleted=False,is_example=False)
        data = list(realtags.values())

        return ResponseUtil.success(data=data)


# 小程序查模板
class TemplateListView(APIView):
    
    """查询 Template 表的所有数据的接口"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 生成缓存键，包含所有查询参数
        cache_key = f"template_list_{request.GET.urlencode()}"
        # 尝试从缓存获取基础数据
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            print('从缓存获取模板基础数据'+cache_key)
            # 从缓存获取基础数据后，再添加用户相关信息
            result = cached_data
            user = request.user
            data = result['data']
            
            # 为每条数据添加用户相关状态
            for index, item in enumerate(data):
                template_id = item['id']
                template = Template.objects.get(id=template_id)
                
                # 检查用户是否点赞
                is_liked = UserLike.objects.filter(user=user, template=template).exists()
                print("是否点赞",is_liked)
                data[index]['islike'] = 1 if is_liked else 0
                
                # 检查用户是否收藏
                is_favorited = UserFavorite.objects.filter(user=user, template=template).exists()
                data[index]['isfavor'] = 1 if is_favorited else 0

                data[index]['like_count'] = template.like_count
            
            return ResponseUtil.success(data=result)

        # 获取用户信息
        user = request.user
        try:
            user_role = user.userRole
        except AttributeError:
            return ResponseUtil.error(message="无法获取用户角色信息")

        # 获取查询参数
        tagid = request.GET.get('cateid', 0)
        realtagid = request.GET.get('tagid', 0)
        title = request.GET.get('title')
        page = request.GET.get('page', 1)
        page_size = request.GET.get('page_size', 10)

        try:
            tagid = int(tagid)
            realtagid = int(realtagid)
            page = int(page)
            page_size = int(page_size)
            query_filter = {'is_deleted': False}

            if tagid != 0:
                realtags = realtag.objects.filter(tag__id=tagid, is_deleted=False,is_example=False)
                realtag_ids = list(realtags.values_list('id', flat=True))
                query_filter['realtag__id__in'] = realtag_ids
            if realtagid != 0:
                query_filter['realtag'] = realtagid
            if title:
                query_filter['title__icontains'] = title

            templates = Template.objects.filter(**query_filter).order_by('-created_date')
        except ValueError:
            return ResponseUtil.error(message="参数必须为整数")

        # 分页处理
        paginator = Paginator(templates, page_size)
        try:
            page_obj = paginator.page(page)
        except Exception:
            return ResponseUtil.error(message="请求的页码不存在")

        # 准备基础数据（不包含用户信息）
        data = list(page_obj.object_list.values())
        for index, template in enumerate(page_obj.object_list):
            realtags = list(template.realtag.values_list('id', flat=True))
            realtagsname = list(template.realtag.values_list('name', flat=True))
            data[index]['realtags'] = realtags
            data[index]['realtagsname'] = realtagsname
            data[index]['text'] = template.text
            # 不在此处添加islike和isfavor字段

        # 准备缓存数据（不包含用户信息）
        result = {
            'data': data,
            'total': paginator.count,
            'page': page,
            'page_size': page_size
        }
        
        # 将基础数据存入缓存
        cache.set(cache_key, result, timeout=120)

        # 为返回数据添加用户相关信息
        for index, item in enumerate(data):
            template = page_obj.object_list[index]
            is_liked = UserLike.objects.filter(user=user, template=template).exists()
            data[index]['islike'] = 1 if is_liked else 0
            is_favorited = UserFavorite.objects.filter(user=user, template=template).exists()
            data[index]['isfavor'] = 1 if is_favorited else 0

        return ResponseUtil.success(data=result)




class PublicTemplateListView(APIView):
    """公开查询Template表数据的接口，不校验token，不返回用户信息"""
    permission_classes = [AllowAny]

    def get(self, request):
        # 生成缓存键，包含所有查询参数
        cache_key = f"public_template_list_{request.GET.urlencode()}"
        # 尝试从缓存获取数据
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            print('从缓存获取公开模板列表数据')
            return ResponseUtil.success(data=cached_data)

        # 获取tagid和realtagid参数，默认为0
        tagid = request.GET.get('cateid', 0)
        realtagid = request.GET.get('tagid', 0)
        title = request.GET.get('title')

        # 获取分页参数
        page = request.GET.get('page', 1)
        page_size = request.GET.get('page_size', 10)

        try:
            tagid = int(tagid)
            realtagid = int(realtagid)
            page = int(page)
            page_size = int(page_size)
            query_filter = {'is_deleted': False}

            if tagid != 0:
                realtags = realtag.objects.filter(tag__id=tagid, is_deleted=False, is_example=False)
                realtag_ids = list(realtags.values_list('id', flat=True))
                query_filter['realtag__id__in'] = realtag_ids
            if realtagid != 0:
                query_filter['realtag'] = realtagid
            if title:
                query_filter['title__icontains'] = title

            templates = Template.objects.filter(**query_filter).order_by('-created_date')
        except ValueError:
            return ResponseUtil.error(message="参数必须为整数")

        # 分页处理
        paginator = Paginator(templates, page_size)
        try:
            page_obj = paginator.page(page)
        except Exception:
            return ResponseUtil.error(message="请求的页码不存在")

        data = list(page_obj.object_list.values())
        # 添加标签信息
        for index, template in enumerate(page_obj.object_list):
            realtags = list(template.realtag.values_list('id', flat=True))
            realtagsname = list(template.realtag.values_list('name', flat=True))
            data[index]['realtags'] = realtags
            data[index]['realtagsname'] = realtagsname
            data[index]['text'] = template.text
            data[index]['islike'] = False

        result = {
            'data': data,
            'total': paginator.count,
            'page': page,
            'page_size': page_size
        }

        # 将结果存入缓存
        cache.set(cache_key, result, timeout=120)
        return ResponseUtil.success(data=result)




# 查询分类
class TagListView(APIView):
    """查询 Template 表的所有数据的接口"""
    permission_classes = [AllowAny]

    def get(self, request):
        # 设置缓存键
        cache_key = 'tag_list'
        # 尝试从缓存获取数据
        cached_data = cache.get(cache_key)

        temp = request.GET.get('temp', 0)
        if temp == '0':
            temp = False
            print('temp',temp)
        else:
            temp = True
            print('temp',temp)

        
        if cached_data is not None:
            print('从缓存获取数据')
            # return ResponseUtil.success(data=cached_data)

        templates = Tag.objects.filter(is_deleted=False,is_temp=temp)
        data = list(templates.values())

        # 将数据存入缓存，设置过期时间为1小时(3600秒)
        cache.set(cache_key, data, timeout=120)



        return ResponseUtil.success(data=data)

# 点赞模板接口
class like_template(APIView):
    """
    处理模板点赞和取消点赞的接口。
    如果用户未点赞过该模板，则进行点赞操作，模板点赞数加 1；
    如果用户已经点赞过该模板，则取消点赞，模板点赞数减 1。
    """
    # permission_classes = [AllowAny]
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        template_id = request.GET.get('template_id')  # 获取模板 ID
        if not template_id:
            return ResponseUtil.error(message="未提供模板 ID")
        try:
            template_id = int(template_id)
        except ValueError:
            return ResponseUtil.error(message="模板 ID 必须为整数")

        template = get_object_or_404(Template, id=template_id)
        user = request.user

        try:
            # 尝试查找用户的点赞记录
            like_record = UserLike.objects.get(user=user, template=template)
            # 如果记录存在，取消点赞
            like_record.delete()
            template.like_count -= 1
            message = "取消点赞成功"
        except UserLike.DoesNotExist:
            # 如果记录不存在，创建点赞记录
            UserLike.objects.create(user=user, template=template)
            template.like_count += 1
            message = "点赞成功"
        # if flush_redis_database():
        #     print('redis 清空成功')
        template.save()
        return ResponseUtil.success(message=message)

# 点赞范例
class like_example(APIView):
    """
    处理范例点赞和取消点赞的接口。
    如果用户未点赞过该范例，则进行点赞操作，范例点赞数加 1；
    如果用户已经点赞过该范例，则取消点赞，范例点赞数减 1。
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        example_id = request.GET.get('example_id')  # 获取范例 ID
        if not example_id:
            return ResponseUtil.error(message="未提供范例 ID")
        try:
            example_id = int(example_id)
        except ValueError:
            return ResponseUtil.error(message="范例 ID 必须为整数")

        example = get_object_or_404(Example, id=example_id)
        user = request.user

        try:
            # 尝试查找用户的点赞记录
            like_record = ExampleLike.objects.get(user=user, example=example)
            # 如果记录存在，取消点赞
            like_record.delete()
            example.like_count -= 1
            message = "取消点赞成功"
        except ExampleLike.DoesNotExist:
            # 如果记录不存在，创建点赞记录
            ExampleLike.objects.create(user=user, example=example)
            example.like_count += 1
            message = "点赞成功"
        # if flush_redis_database():
        #     print('redis 清空成功')
        example.save()
        return ResponseUtil.success(message=message)



# 查询标签
class realTagListView(APIView):
    """查询 Template 表的所有数据的接口"""
    permission_classes = [AllowAny]

    def get(self, request):
        # 设置缓存键
        cache_key = 'realtag_list'
        # 尝试从缓存获取数据
        cached_data = cache.get(cache_key)
        temp = request.GET.get('temp', 0)
        if temp == '0':
            temp = False
            print('temp',temp)
        else:
            temp = True
            print('temp',temp)
        
        if cached_data is not None:
            print('从缓存获取数据')
            # return ResponseUtil.success(data=cached_data)
        print('从数据库获取数据')
        templates = realtag.objects.filter(is_deleted=False,is_example=temp)
        data = list(templates.values())

        # 将数据存入缓存，设置过期时间为1小时(3600秒)
        # cache.set(cache_key, data, timeout=120)

        # Example.objects.filter(=24).delete()
        # print('删除成功')
        # Example.objects.filter(text__in=["error!", ""]).delete()
        # Template.objects.all().delete()
        # print('删除成功')







        return ResponseUtil.success(data=data)

# 创建范例
class ExampleCreateView(APIView):
    """
    新增 Example 数据的接口，处理 POST 请求。
    接收标题、英文文本、标签、生成方法和多个图片流，将图片上传到火山对象存储并保存访问路径。
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # 获取表单数据
            text = request.POST.get('text')
            title = request.POST.get('title')  # 新增获取 title 参数
            en_text = request.POST.get('en_text')  # 新增获取英文文本参数
            category = request.POST.get('category')
            remarks = request.POST.get('remarks')
            realtag_str = request.data.get('realtag')
            print(realtag_str)
            if realtag_str:
                try:
                    realtag_id = [int(id_str) for id_str in realtag_str.split(',')]
                except ValueError:
                    return ResponseUtil.error(message="标签参数必须是用逗号分隔的整数列表")
            else:
                realtag_id = []
            # 修改获取 tag_id 的逻辑
            tag_str = request.POST.get('tag')
            if tag_str:
                try:
                    tag_id = [int(id_str) for id_str in tag_str.split(',')]
                except ValueError:
                    return ResponseUtil.error(message="标签参数必须是用逗号分隔的整数列表")
            else:
                tag_id = []

            generation_method = request.POST.get('generation_method')
            image_streams = request.FILES.getlist('image')  # 获取多个 image 图片流
            image_streams2 = request.FILES.getlist('image_stream2')  # 获取多个 image_stream2 图片流

            # if not all([title, text, tag_id, generation_method, image_streams or image_streams2]):
            #     return ResponseUtil.error(message="标题、英文文本、文本、标签、生成方法和图片流均为必填项")

            # 检查所有标签是否存在
            tags = []
            for tid in tag_id:
                try:
                    tag = Tag.objects.get(id=tid)
                    tags.append(tag)
                except Tag.DoesNotExist:
                    return ResponseUtil.error(message=f"指定的标签 {tid} 不存在")

            realtags = []
            for tid in realtag_id:
                try:
                    tag = realtag.objects.get(id=tid)
                    realtags.append(tag)
                except realtag.DoesNotExist:
                    return ResponseUtil.error(message=f"指定的标签 {tid} 不存在")

            image_paths = []
            image_paths_res = []

            # 遍历 image_streams 并上传
            folder_name = 'example'  # 定义文件夹名称
            for image_stream in image_streams:
                characters = string.ascii_letters + string.digits
                object_name1 = ''.join(random.choice(characters) for i in range(6)) + ".png"
                # 拼接文件夹名称和对象名称
                full_object_name = f"{folder_name}/{object_name1}"
                image_path = tos_utils.upload_image(full_object_name, file_data=image_stream)
                if not image_path:
                    return ResponseUtil.error(message="图片上传失败")
                image_paths.append(image_path)

            # 遍历 image_streams2 并上传
            for image_stream in image_streams2:
                characters = string.ascii_letters + string.digits
                object_name1 = ''.join(random.choice(characters) for i in range(6)) + ".png"
                # 拼接文件夹名称和对象名称
                full_object_name = f"{folder_name}/{object_name1}"
                image_path = tos_utils.upload_image(full_object_name, file_data=image_stream)
                if not image_path:
                    return ResponseUtil.error(message="图片上传失败")
                image_paths_res.append(image_path)

            # 拼接图片路径
            combined_image_paths = ','.join(image_paths)
            combined_image_paths_res = ','.join(image_paths_res)

            # 创建 Example 实例，先不设置多对多字段
            example = Example.objects.create(
                text=text,
                title=title,  # 新增保存 title 到数据库
                remarks=remarks,  # 新增保存 title 到数据库
                category=category,  # 新增保存 title 到数据库
                english_prompt=en_text,  # 新增保存英文文本到数据库
                generation_method=generation_method,
                image_path=combined_image_paths,
                image_path_res=combined_image_paths_res  # 新增保存 image_path_res 到数据库
            )

            # 使用 set 方法设置多对多字段
            example.tag.set(tags)
            example.realtag.set(realtags)
            if flush_redis_database():
                print('redis 清空成功')

            return ResponseUtil.success(data={'id': example.id, 'image_path': combined_image_paths, 'image_path_res': combined_image_paths_res})
        except Exception as e:
            return ResponseUtil.error(message=f"新增 Example 数据失败: {str(e)}")

# 创建模板
class TemplateCreateView(APIView):
    """
    新增 Template 数据的接口，处理 POST 请求。
    接收文本、标签、生成方法和图片流，将图片上传到火山对象存储并保存访问路径。
    """
    # permission_classes = [AllowAny]

    def post(self, request):
        try:
            # 获取表单数据
            tag_id = request.POST.get('tag')
            image = request.FILES.get('image')
            realtag_str = request.data.get('realtag')
            title = request.data.get('title')
            folder_name = 'template'  # 定义文件夹名称
            image_paths = []
            mask = request.FILES.getlist('mask')
            if mask:
                for image_stream in mask:
                    characters = string.ascii_letters + string.digits
                    object_name1 = ''.join(random.choice(characters) for i in range(6)) + ".png"
                    full_object_name = f"{folder_name}/{object_name1}"
                    image_path = tos_utils.upload_image(full_object_name, file_data=image_stream)
                    if not image_path:
                        return ResponseUtil.error(message="图片上传失败")
                    image_paths.append(image_path)
                combined_image_paths = ','.join(image_paths)
                # template.mask = combined_image_paths

            print(realtag_str)
            if realtag_str:
                try:
                    realtag_id = [int(id_str) for id_str in realtag_str.split(',')]
                except ValueError:
                    return ResponseUtil.error(message="标签参数必须是用逗号分隔的整数列表")
            else:
                realtag_id = []
            realtags = []
            for tid in realtag_id:
                try:
                    tag = realtag.objects.get(id=tid)
                    realtags.append(tag)
                except realtag.DoesNotExist:
                    return ResponseUtil.error(message=f"指定的标签 {tid} 不存在")



            try:
                tag_id = int(tag_id)
            except ValueError:
                return ResponseUtil.error(message="标签参数必须为整数")

            try:
                tag = Tag.objects.get(id=tag_id)
            except Tag.DoesNotExist:
                return ResponseUtil.error(message="指定的标签不存在")

            # 调用火山对象存储的上传方法
            # 生成包含所有字母和数字的字符集
            characters = string.ascii_letters + string.digits
            # 生成六位随机字符串
            object_name1 = ''.join(random.choice(characters) for i in range(6)) + ".png"
            full_object_name = f"{folder_name}/{object_name1}"
            image_path1 = tos_utils.upload_image(object_name1,file_data=image)

            if not image_path1:
                return ResponseUtil.error(message="图片上传失败")

            # 创建 Example 实例
            example = Template.objects.create(
                tag=tag,
                title=title,  # 新增保存 title 到数据库
                image_path=image_path1,
                mask=combined_image_paths
            )
            example.realtag.set(realtags)
            if flush_redis_database():
                print('redis 清空成功')


            return ResponseUtil.success(data={'id': example.id, 'image_path': image_path})
        except Exception as e:
            return ResponseUtil.error(message=f"新增 Template 数据失败: {str(e)}")

# 范例删除
class ExampleSoftDeleteView(APIView):
    # permission_classes = [AllowAny]

    """
    软删除 Example 实例的视图，通过修改 is_deleted 字段实现
    """
    def delete(self, request, pk):
        try:
            # 尝试获取指定主键的 Example 实例
            example = Example.objects.get(pk=pk, is_deleted=False)
            # 将 is_deleted 字段设置为 True
            example.is_deleted = True
            example.save()
            if flush_redis_database():
                print('redis 清空成功')
            return ResponseUtil.success()

        except Example.DoesNotExist:
            return ResponseUtil.error()

# 模板删除
class templateSoftDeleteView(APIView):
    # permission_classes = [AllowAny]

    """
    软删除 Example 实例的视图，通过修改 is_deleted 字段实现
    """
    def delete(self, request, pk):
        try:
            # 尝试获取指定主键的 Example 实例
            example = Template.objects.get(pk=pk, is_deleted=False)
            # 将 is_deleted 字段设置为 True
            example.is_deleted = True
            example.save()
            if flush_redis_database():
                print('redis 清空成功')
            return ResponseUtil.success()

        except Example.DoesNotExist:
            return ResponseUtil.error()

# 范例更新
class ExampleUpdateView(APIView):
    """
    修改 Example 数据的接口，处理 PUT 和 PATCH 请求。
    PUT 请求需要提供完整的更新数据，PATCH 请求可以只提供部分更新数据。
    """
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    permission_classes = [AllowAny]


    def put(self, request, pk):
        return self._update_example(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update_example(request, pk, partial=True)

    def _update_example(self, request, pk, partial=False):
        try:
            example = Example.objects.get(pk=pk, is_deleted=False)
        except Example.DoesNotExist:
            return ResponseUtil.error(message="要修改的 Example 实例不存在")
        folder_name = 'example'  # 定义文件夹名称


        # 获取表单数据
        print(request.data)
        text = request.data.get('text', example.text)
        title = request.data.get('title', example.title)
        en_text = request.data.get('en_text', example.english_prompt)
        realtag_str = request.data.get('realtag')
        print(realtag_str)
        if realtag_str:
            print('realtag_str',realtag_str)
            try:
                realtag_id = [int(id_str) for id_str in realtag_str.split(',')]
            except ValueError:
                return ResponseUtil.error(message="标签参数必须是用逗号分隔的整数列表")
        else:
            realtag_id = None
        remarks = request.data.get('remarks', example.remarks)
        tag_str = request.data.get('tag')
        if tag_str:
            try:
                tag_id = [int(id_str) for id_str in tag_str.split(',')]
            except ValueError:
                return ResponseUtil.error(message="标签参数必须是用逗号分隔的整数列表")
        else:
            tag_id = None
        generation_method = request.data.get('generation_method', example.generation_method)
        image_streams = request.FILES.getlist('image')
        image_streams2 = request.FILES.getlist('image_stream2')

        # 更新标签
        if realtag_id is not None:
            realtags = []
            for tid in realtag_id:
                try:
                    tag = realtag.objects.get(id=tid)
                    realtags.append(tag)
                except realtag.DoesNotExist:
                    return ResponseUtil.error(message=f"指定的标签 {tid} 不存在")
            example.realtag.set(realtags)

        # 更新标签
        if tag_id is not None:
            tags = []
            for tid in tag_id:
                try:
                    tag = Tag.objects.get(id=tid)
                    tags.append(tag)
                except Tag.DoesNotExist:
                    return ResponseUtil.error(message=f"指定的标签 {tid} 不存在")
            example.tag.set(tags)

        # 处理图片上传
        image_paths = []
        image_paths_res = []
        if image_streams:
            example.image_path = ""
            for image_stream in image_streams:
                characters = string.ascii_letters + string.digits
                object_name1 = ''.join(random.choice(characters) for i in range(6)) + ".png"
                full_object_name = f"{folder_name}/{object_name1}"
                image_path = tos_utils.upload_image(full_object_name, file_data=image_stream)
                if not image_path:
                    return ResponseUtil.error(message="图片上传失败")
                image_paths.append(image_path)
            combined_image_paths = ','.join(image_paths)
            example.image_path = combined_image_paths

        if image_streams2:
            example.image_path_res = ""
            for image_stream in image_streams2:
                characters = string.ascii_letters + string.digits
                object_name1 = ''.join(random.choice(characters) for i in range(6)) + ".png"
                full_object_name = f"{folder_name}/{object_name1}"
                image_path = tos_utils.upload_image(full_object_name, file_data=image_stream)
                if not image_path:
                    return ResponseUtil.error(message="图片上传失败")
                image_paths_res.append(image_path)
            combined_image_paths_res = ','.join(image_paths_res)
            example.image_path_res = combined_image_paths_res

        # 更新其他字段
        example.text = text
        example.title = title
        example.english_prompt = en_text
        # example.realtag = realtag
        example.remarks = remarks
        example.generation_method = generation_method

        example.save()
        if flush_redis_database():
            print('redis 清空成功')

        return ResponseUtil.success(data={'id': example.id})

# 模板更新
class TemplateUpdateView(APIView):
    """
    修改 Template 数据的接口，处理 PUT 和 PATCH 请求。
    PUT 请求需要提供完整的更新数据，PATCH 请求可以只提供部分更新数据。
    """
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    permission_classes = [AllowAny]


    def put(self, request, pk):
        return self._update_template(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update_template(request, pk, partial=True)

    def _update_template(self, request, pk, partial=False):
        try:
            template = Template.objects.get(pk=pk)
        except Template.DoesNotExist:
            return ResponseUtil.error(message="要修改的 Template 实例不存在")

        # 获取表单数据
        title = request.data.get('title', template.title)
        folder_name = 'template'  # 定义文件夹名称
        image_paths = []
        # 处理 mask 图片
        mask = request.FILES.getlist('mask')
        if mask:
            # 清空原有 mask 数据
            template.mask = ""
            image_paths = []
            for image_stream in mask:
                characters = string.ascii_letters + string.digits
                object_name1 = ''.join(random.choice(characters) for i in range(6)) + ".png"
                full_object_name = f"{folder_name}/{object_name1}"
                image_path = tos_utils.upload_image(full_object_name, file_data=image_stream)
                if not image_path:
                    return ResponseUtil.error(message="图片上传失败")
                image_paths.append(image_path)
            combined_image_paths = ','.join(image_paths)
            template.mask = combined_image_paths
        realtag_str = request.data.get('realtag')
        print(realtag_str)
        if realtag_str:
            try:
                realtag_id = [int(id_str) for id_str in realtag_str.split(',')]
            except ValueError:
                return ResponseUtil.error(message="标签参数必须是用逗号分隔的整数列表")
        else:
            realtag_id = None
        # 更新标签
        if realtag_id is not None:
            realtags = []
            for tid in realtag_id:
                try:
                    tag = realtag.objects.get(id=tid)
                    realtags.append(tag)
                except realtag.DoesNotExist:
                    return ResponseUtil.error(message=f"指定的标签 {tid} 不存在")
            template.realtag.set(realtags)
        tag_str = request.data.get('tag')
        if tag_str:
            try:
                tag_id = int(tag_str)
            except ValueError:
                return ResponseUtil.error(message="标签参数必须为整数")
        else:
            tag_id = None

        # 更新标签
        if tag_id is not None:
            try:
                tag = Tag.objects.get(id=tag_id)
                template.tag = tag
            except Tag.DoesNotExist:
                return ResponseUtil.error(message=f"指定的标签 {tag_id} 不存在")

        # 处理图片上传
        # 处理 image 图片
        image_stream = request.FILES.get('image')
        if image_stream:
            # 清空原有 image_path 数据
            template.image_path = ""
            characters = string.ascii_letters + string.digits
            object_name1 = ''.join(random.choice(characters) for i in range(6)) + ".png"
            full_object_name = f"{folder_name}/{object_name1}"
            image_path = tos_utils.upload_image(full_object_name, file_data=image_stream)
            if not image_path:
                return ResponseUtil.error(message="图片上传失败")
            template.image_path = image_path
        template.title = title
        

        template.save()
        if flush_redis_database():
                print('redis 清空成功')

        return ResponseUtil.success(data={'id': template.id})

# 模板收藏
class FavoriteTemplateView(APIView):
    """
    处理模板收藏和取消收藏的接口。
    如果用户未收藏过该模板，则进行收藏操作，往收藏表添加一条数据；
    如果用户已经收藏过该模板，则取消收藏，删除收藏表中的对应数据。
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        template_id = request.GET.get('template_id')  # 获取模板 ID
        if not template_id:
            return ResponseUtil.error(message="未提供模板 ID")
        try:
            template_id = int(template_id)
        except ValueError:
            return ResponseUtil.error(message="模板 ID 必须为整数")

        template = get_object_or_404(Template, id=template_id)
        user = request.user

        try:
            # 尝试查找用户的收藏记录
            favorite_record = UserFavorite.objects.get(user=user, template=template)
            # 如果记录存在，取消收藏
            favorite_record.delete()
            message = "取消收藏成功"
        except UserFavorite.DoesNotExist:
            # 如果记录不存在，创建收藏记录
            UserFavorite.objects.create(user=user, template=template)
            message = "收藏成功"

        return ResponseUtil.success(message=message)


# 用户收藏过的模板列表
class UserFavoriteTemplateListView(APIView):
    """
    查询用户收藏过的模板列表的接口。
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # 获取 tagid 参数，默认为 0
        tagid = request.GET.get('tagid', 0)
        try:
            tagid = int(tagid)
        except ValueError:
            return ResponseUtil.error(message="tagid 参数必须为整数")

        # 查询用户收藏过的模板，按创建时间升序排序
        favorite_templates = UserLike.objects.filter(user=user).order_by('-like_time')
        # 提取模板 ID 列表
        template_ids = [favorite.template.id for favorite in favorite_templates]

        # 获取分页参数
        page = request.GET.get('page', 1)
        page_size = request.GET.get('page_size', 10)
        try:
            page = int(page)
            page_size = int(page_size)
        except ValueError:
            return ResponseUtil.error(message="page 和 page_size 参数必须为整数")

        if tagid != 0:
            # 筛选模板的 tagid 包含 tagid 的数据
            templates = Template.objects.filter(id__in=template_ids, tag=tagid)
        else:
            # tagid 没传或者是 0，返回所有收藏模板
            templates = Template.objects.filter(id__in=template_ids)

        # 按照模板ID列表的顺序排序
        
        preserved_order = Case(*[When(id=id, then=pos) for pos, id in enumerate(template_ids)])
        templates = templates.order_by(preserved_order)

        # 分页处理
        from django.core.paginator import Paginator
        paginator = Paginator(templates, page_size)
        try:
            page_obj = paginator.page(page)
        except Exception:
            return ResponseUtil.error(message="请求的页码不存在")

        # 序列化模板信息
        serializer = TemplateSerializer(page_obj.object_list, many=True)

        result = {
            'data': serializer.data,
            'total': paginator.count,
            'page': page,
            'page_size': page_size
        }
        return ResponseUtil.success(data=result)

# 模板详情
class TemplateDetailView(APIView):
    """
    查询模板详情的接口。
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            template_id = request.GET.get('template_id')  # 获取模板 ID
            if not template_id:
                return ResponseUtil.error(message="未提供模板 ID")
                
            # 设置缓存键
            cache_key = f'template_detail_{template_id}'
            # 尝试从缓存获取数据
            cached_data = cache.get(cache_key)
            
            if cached_data is not None:
                print("从缓存中获取模板详情")
                return ResponseUtil.success(data=cached_data)

            print("从数据库中获取模板详情")
            template = Template.objects.get(id=template_id, is_deleted=False)
            serializer = TemplateSerializer(template)
            data = serializer.data
            
            # 将数据存入缓存，设置过期时间为1小时(3600秒)
            cache.set(cache_key, data, timeout=3600)

            # 检查用户是否点赞
            from .models import UserLike  # 假设 UserLike 模型在当前应用的 models.py 中
            is_liked = UserLike.objects.filter(user=request.user, template=template).exists()
            data['is_liked'] = is_liked
            data['text'] = template.text

            # 检查用户是否收藏
            from .models import UserFavorite  # 假设 UserFavorite 模型在当前应用的 models.py 中
            is_favorited = UserFavorite.objects.filter(user=request.user, template=template).exists()
            data['is_favorited'] = is_favorited

            return ResponseUtil.success(data=data)
        except Template.DoesNotExist:
            return ResponseUtil.error(message="模板不存在")



# 新增标签
class TagCreateView(APIView):
    """
    新增 Tag 数据的接口，处理 POST 请求。
    接收标签名称和标签类型，将标签信息保存到数据库。
    """
    # permission_classes = [AllowAny]

    def post(self, request):
        try:
            # 获取表单数据
            tag_name = request.data.get('description')
            temp1 = request.data.get('temp', 0)
            if temp1 == 0:
                temp1 = False
                print('temp',temp1)
            else:
                temp1 = True
                print('temp',temp1)
            
            if not tag_name:
                return ResponseUtil.error(message="标签名称不能为空")
            # 检查标签是否已存在
            existing_tag = Tag.objects.filter(description=tag_name).first()
            if existing_tag:
                return ResponseUtil.error(message="标签已存在")
            # 创建新标签
            new_tag = Tag.objects.create(description=tag_name,is_temp=temp1)
            print('new_tag',new_tag)
            if flush_redis_database():
                print('redis 清空成功')
            return ResponseUtil.success(data={'id': new_tag.id})
        except Exception as e:
            return ResponseUtil.error(message=f"新增标签失败: {str(e)}")


# 编辑标签
class TagUpdateView(APIView):
    """
    修改 Tag 数据的接口，处理 PUT 和 PATCH 请求。
    PUT 请求需要提供完整的更新数据，PATCH 请求可以只提供部分更新数据。
    """
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    permission_classes = [AllowAny]

    def put(self, request, pk):
        return self._update_tag(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update_tag(request, pk, partial=True)

    def _update_tag(self, request, pk, partial=False):
        try:
            tag = Tag.objects.get(pk=pk)
        except Tag.DoesNotExist:
            return ResponseUtil.error(message="要修改的 Tag 实例不存在")
        # 获取表单数据
        tag_name = request.data.get('description', tag.description)
        # 更新标签信息
        tag.description = tag_name
        tag.save()
        if flush_redis_database():
            print('redis 清空成功')
        return ResponseUtil.success(data={'id': tag.id})



# 新增真实标签
class realTagCreateView(APIView):
    """
    新增 Tag 数据的接口，处理 POST 请求。
    接收标签名称和标签类型，将标签信息保存到数据库。
    """
    # permission_classes = [AllowAny]

    def post(self, request):
        try:
            # 获取表单数据
            tag_name = request.data.get('name')
            temp = request.data.get('temp', 0)
            cateid = request.data.get('cateid')  # 新增获取cateid参数

            if not tag_name:
                return ResponseUtil.error(message="标签名称不能为空")
            # 检查标签是否已存在
            existing_tag = realtag.objects.filter(name=tag_name).first()
            if existing_tag:
                return ResponseUtil.error(message="标签已存在")
                
            

            if temp == 0:
                temp = False
                print('temp',temp)
            else:
                temp = True
                print('temp',temp)

            # 创建realtag记录
            realtag_data = {
                'name': tag_name,
                'is_deleted': False,
                'is_example':temp
            }
            # 如果传入了cateid，则赋值给tag_id
            if cateid:
                try:
                    realtag_data['tag_id'] = int(cateid)
                except ValueError:
                    return ResponseUtil.error(message="分类ID必须为整数")
            
            
            # 创建新标签
            print(temp)
            new_tag = realtag.objects.create(**realtag_data)
            print(new_tag)
            if flush_redis_database():
                print('redis 清空成功')
            return ResponseUtil.success(data={'id': new_tag.id})
        except Exception as e:
            return ResponseUtil.error(message=f"新增标签失败: {str(e)}")


# 编辑真实标签
class realTagUpdateView(APIView):
    """
    修改 Tag 数据的接口，处理 PUT 和 PATCH 请求。
    PUT 请求需要提供完整的更新数据，PATCH 请求可以只提供部分更新数据。
    """
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    permission_classes = [AllowAny]

    def put(self, request, pk):
        return self._update_tag(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update_tag(request, pk, partial=True)

    def _update_tag(self, request, pk, partial=False):
        try:
            tag = realtag.objects.get(pk=pk)
        except Tag.DoesNotExist:
            return ResponseUtil.error(message="要修改的 Tag 实例不存在")
        # 获取表单数据
        tag_name = request.data.get('name', tag.name)
        # 更新标签信息
        tag.name = tag_name
        tag.save()
        if flush_redis_database():
            print('redis 清空成功')
        return ResponseUtil.success(data={'id': tag.id})


from common.volcengine_imagex_utils import upload_image_data_to_volcengine



# 删除分类
class tagSoftDeleteView(APIView):
    # permission_classes = [AllowAny]

    """
    软删除 Example 实例的视图，通过修改 is_deleted 字段实现
    """
    def delete(self, request, pk):
        try:
            # 先检查标签是否存在
            tag = Tag.objects.get(pk=pk)
            if tag.is_deleted:
                return ResponseUtil.error(message="标签已被删除")
                
            # 执行软删除
            tag.is_deleted = True
            tag.save()
            if flush_redis_database():
                print('redis 清空成功')
            return ResponseUtil.success()
        except Example.DoesNotExist:
            return ResponseUtil.error()
    
# 删除标签
class realtagSoftDeleteView(APIView):
    # permission_classes = [AllowAny]

    """
    软删除 Example 实例的视图，通过修改 is_deleted 字段实现
    """
    def delete(self, request, pk):
        try:
            tag_obj = realtag.objects.get(pk=pk)
            if tag_obj.is_deleted:
                return ResponseUtil.error(message="标签已被删除")
                
            # 执行软删除
            tag_obj.is_deleted = True
            tag_obj.save()

            if flush_redis_database():
                print('redis 清空成功')
            return ResponseUtil.success()
        except Example.DoesNotExist:
            return ResponseUtil.error()
    

# 用户记录转范例
class TemplateuserView(APIView):
    """
    新增 Template 数据的接口，处理 POST 请求。
    接收文本、标签、生成方法和图片流，将图片上传到火山对象存储并保存访问路径。
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # 获取表单数据
            tag_str = request.data.get('tag')
            image = request.data.get('image')
            image_list = request.data.get('image_list')
            realtag_str = request.data.get('realtag')
            title = request.data.get('title')
            method1 = request.data.get('method')

            # 调用工具方法
            result = upload_image_data_to_volcengine(image)
            print(result)
            if not result:
                return ResponseUtil.error(message="图片审核失败")

            

            print(realtag_str)
            if realtag_str:
                try:
                    realtag_id = [int(id_str) for id_str in realtag_str.split(',')]
                except ValueError:
                    return ResponseUtil.error(message="标签参数必须是用逗号分隔的整数列表")
            else:
                realtag_id = []
            realtags = []
            for tid in realtag_id:
                try:
                    tag = realtag.objects.get(id=tid)
                    realtags.append(tag)
                except realtag.DoesNotExist:
                    return ResponseUtil.error(message=f"指定的标签 {tid} 不存在")



            if tag_str:
                try:
                    tag_id = [int(id_str) for id_str in tag_str.split(',')]
                except ValueError:
                    return ResponseUtil.error(message="标签参数必须是用逗号分隔的整数列表")
            else:
                tag_id = []
            tags = []
            for tid1 in tag_id:
                try:
                    tag1 = Tag.objects.get(id=tid1)
                    tags.append(tag1)
                except realtag.DoesNotExist:
                    return ResponseUtil.error(message=f"指定的标签 {tid1} 不存在")

            

            # 创建 Example 实例

            example = Example.objects.create(
                title=title,
                text=title,
                fromuser=True,
                is_deleted=False,
                created_date=timezone.now(),
                image_path_res=image,
                image_path=image_list,
                generation_method=method1,
            )
            example.tag.set(tags)
            example.realtag.set(realtags)

            print(example)

            return ResponseUtil.success(data={'id': example.id, 'image_path': image})
        except Exception as e:
            print(str(e))
            return ResponseUtil.error(message=f"新增 Template 数据失败: {str(e)}")