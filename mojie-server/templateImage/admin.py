from django.contrib import admin

# Register your models here.
from .models import *

class UserCloudImageStorageAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'image_name', 'image_size', 'source', 'created_at', 'is_deleted')
    list_filter = ('source', 'is_deleted', 'created_at')
    search_fields = ('image_name', 'description', 'user__username')
    date_hierarchy = 'created_at'
    readonly_fields = ('image_size', 'created_at', 'updated_at')

class TaskTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name', 'is_active', 'handler_name', 'priority_order', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'display_name', 'description')
    list_editable = ('display_name', 'is_active', 'priority_order')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'display_name', 'description', 'is_active')
        }),
        ('处理器配置', {
            'fields': ('handler_name', 'config', 'priority_order')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

admin.site.register(templateImage)
admin.site.register(UserCloudImageStorage, UserCloudImageStorageAdmin)
admin.site.register(TaskType, TaskTypeAdmin)