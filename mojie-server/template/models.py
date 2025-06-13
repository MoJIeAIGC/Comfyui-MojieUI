from django.db import models
from django.utils import timezone
from django.conf import settings



class realtag(models.Model):
    """
    标签表模型
    包含标签的基本信息，如标签名称和描述
    """
    id = models.AutoField(primary_key=True)  # 自增主键
    name = models.CharField(max_length=100, verbose_name="标签名称")  # 标签名称
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除")  # 是否删除标志
    is_example = models.BooleanField(default=False, verbose_name="默认是给模板用的")  # 是否删除标志
    is_one = models.BooleanField(default=False, verbose_name="一级分类")  # 是否删除标志
    tag = models.ForeignKey('Tag', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="标签")  # 标签名称


    class Meta:
        verbose_name = "真标签"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name



class Tag(models.Model):
    """
    标签表模型
    包含标签的基本信息，如标签名称和描述
    """
    id = models.AutoField(primary_key=True)  # 自增主键
    description = models.TextField(verbose_name="标签描述", blank=True, null=True)  # 标签描述
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除")  # 是否删除标志
    is_temp = models.BooleanField(default=False, verbose_name="默认是范例分类")  # 是否删除标志
    


    class Meta:
        verbose_name = "标签"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.description

class Example(models.Model):
    """
    范例表模型
    包含范例相关的信息，如标题、文字、图片路径、标签等
    """
    id = models.AutoField(primary_key=True)  # 自增主键
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除")  # 是否删除标志
    # 新增标题字段
    fromuser = models.BooleanField(default=False, verbose_name="是否删除")  # 是否删除标志
    title = models.TextField( verbose_name="标题", blank=True, null=True)
    text = models.TextField(verbose_name="文字")  # 文字内容
    image_path = models.CharField(max_length=255, verbose_name="图片路径")  # 图片路径
    image_path_res = models.CharField(max_length=255, verbose_name="图片路径", blank=True, null=True)  # 图片路径
    created_date = models.DateTimeField(default=timezone.now, verbose_name="创建日期")  # 创建日期
    # 修改 tag 字段为多对多关联 Tag 模型
    tag = models.ManyToManyField(Tag, verbose_name="标签")
    realtag = models.ManyToManyField(realtag, verbose_name="真标签")
    # 新增类别字段
    category = models.CharField(max_length=100, verbose_name="类别", blank=True, null=True)
    # 新增英文提示词字段
    english_prompt = models.TextField(verbose_name="英文提示词", blank=True, null=True)
    # 新增备注字段
    remarks = models.TextField(verbose_name="备注", blank=True, null=True)
    generation_method = models.CharField(max_length=100, verbose_name="生成方法")  # 生成方法
    like_count = models.IntegerField(default=0, verbose_name="点赞数量")  # 新增点赞数量字段

    class Meta:
        verbose_name = "范例"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title

class ExampleLike(models.Model):
    """
    用户点赞范例表模型
    记录各个用户对范例的点赞情况
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="用户")
    example = models.ForeignKey(Example, on_delete=models.CASCADE, verbose_name="范例")
    like_time = models.DateTimeField(auto_now_add=True, verbose_name="点赞时间")

    class Meta:
        verbose_name = "用户点赞范例"
        verbose_name_plural = verbose_name
        unique_together = ('user', 'example')  # 确保一个用户对一个范例只能点赞一次


class Template(models.Model):
    """
    模版表模型
    包含模版相关的信息，如图片路径、标签等
    """
    id = models.AutoField(primary_key=True)  # 自增主键
    title = models.CharField(max_length=255, verbose_name="标题", blank=True, null=True)
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除")  # 是否删除标志
    fromuser = models.BooleanField(default=False, verbose_name="是否删除")  # 是否删除标志
    text = models.TextField(verbose_name="文字", blank=True, null=True)  # 文字内容
    image_path = models.CharField(max_length=255, verbose_name="图片路径")  # 图片路径
    mask = models.CharField(max_length=255, verbose_name="遮罩", blank=True, null=True)  # 图片路径
    created_date = models.DateTimeField(default=timezone.now, verbose_name="创建日期")  # 创建日期
    # 修改 tag 字段为外键关联 Tag 模型
    tag = models.ForeignKey(Tag, on_delete=models.SET_NULL, verbose_name="标签", null=True)
    like_count = models.IntegerField(default=0, verbose_name="点赞数量")
    realtag = models.ManyToManyField(realtag, verbose_name="真标签")


    class Meta:
        verbose_name = "模版"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.image_path


class UserLike(models.Model):
    """
    用户点赞表模型
    记录各个用户对模版的点赞情况
    """
    # 修改关联模型
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="用户")
    template = models.ForeignKey(Template, on_delete=models.CASCADE, verbose_name="模版")
    like_time = models.DateTimeField(auto_now_add=True, verbose_name="点赞时间")

    class Meta:
        verbose_name = "用户点赞"
        verbose_name_plural = verbose_name
        unique_together = ('user', 'template')  # 确保一个用户对一个模版只能点赞一次


class UserFavorite(models.Model):
    """
    用户收藏表模型
    记录用户对模板的收藏情况
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="用户")
    template = models.ForeignKey(Template, on_delete=models.CASCADE, verbose_name="模板")
    favorite_time = models.DateTimeField(auto_now_add=True, verbose_name="收藏时间")

    class Meta:
        verbose_name = "用户收藏"
        verbose_name_plural = verbose_name
        unique_together = ('user', 'template')  # 确保一个用户对一个模板只能收藏一次


