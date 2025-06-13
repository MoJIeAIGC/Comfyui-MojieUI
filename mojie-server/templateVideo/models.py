from django.db import models

class templateVideo(models.Model):
    id = models.AutoField(primary_key=True)
    video_name = models.CharField(max_length=255, verbose_name="视频名称")
    video_address = models.CharField(max_length=255,  verbose_name="模板视频的地址")
    audeo_address = models.CharField(null=True,max_length=255,  verbose_name="模板音频的地址")
    task_id = models.CharField(null=True,max_length=255,  verbose_name="模板音频的地址")
    description = models.TextField(verbose_name="描述")
    video_method = models.CharField(max_length=100, null=True, verbose_name="视频类别")
    create_time = models.DateTimeField(null=True, verbose_name="创建时间")
    update_time = models.DateTimeField(null=True, verbose_name="更新时间")
    status = models.IntegerField(null=True, verbose_name="状态（0正常 1停用）")
    isDelete = models.IntegerField(null=True, verbose_name="是否删除（0正常 1停用）")
    userVideo = models.ForeignKey('user.SysUser', on_delete=models.CASCADE) 

    class Meta:
        db_table = "template_video"
        verbose_name = '视频生成记录'
        verbose_name_plural = verbose_name
