from django.contrib import admin

# Register your models here.
from .models import *

admin.site.site_header = '摩诘后台管理系统'  # 设置header
admin.site.site_title = '摩诘后台管理系统'   # 设置title
admin.site.index_title = '摩诘后台管理系统'

class Video_Manager(admin.ModelAdmin):
    list_display = ['id', 'video_name', 'video_address', 'description', 'video_method', 'create_time', 'update_time', 'isDelete', 'userVideo']
    # 设置每页显示的记录数量，这里设置为 10
    list_per_page = 10  

admin.site.register(templateVideo, Video_Manager)