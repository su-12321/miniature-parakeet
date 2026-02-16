"""
管理后台配置
"""
from .models import PrivateChatSession, PrivateMessage
from django.contrib import admin
from django.utils.html import format_html
from .models import Post, Comment, Category, Tag

class PostAdmin(admin.ModelAdmin):
    """文章管理"""
    list_display = ('title', 'author', 'category', 'status', 'created_at', 'view_count')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('title', 'content', 'author__username')
    readonly_fields = ('view_count', 'created_at', 'updated_at')

    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'author', 'category', 'tags', 'summary')
        }),
        ('内容', {
            'fields': ('content', 'cover_image')
        }),
        ('状态', {
            'fields': ('status', 'is_featured', 'view_count')
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)

class CommentAdmin(admin.ModelAdmin):
    """评论管理"""
    list_display = ('post', 'author', 'content_preview', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('content', 'author__username', 'post__title')

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = '内容预览'

class CategoryAdmin(admin.ModelAdmin):
    """分类管理"""
    list_display = ('name', 'description', 'post_count')

    def post_count(self, obj):
        return obj.post_set.count()
    post_count.short_description = '文章数'

class TagAdmin(admin.ModelAdmin):
    """标签管理"""
    list_display = ('name', 'description', 'post_count')

    def post_count(self, obj):
        return obj.post_set.count()
    post_count.short_description = '文章数'

# 注册模型
admin.site.register(Post, PostAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Tag, TagAdmin)

# 在 blog/admin.py 文件中添加




class PrivateMessageInline(admin.TabularInline):
    """私聊消息内联显示"""
    model = PrivateMessage
    fields = ('sender', 'receiver', 'content_preview', 'created_at', 'is_read')
    readonly_fields = ('content_preview', 'created_at')
    extra = 0

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content

    content_preview.short_description = '内容预览'


class PrivateChatSessionAdmin(admin.ModelAdmin):
    """私聊会话管理"""
    list_display = ('user1', 'user2', 'message_count', 'last_message_time', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('user1__username', 'user2__username')
    inlines = [PrivateMessageInline]

    def message_count(self, obj):
        return obj.messages.count()

    message_count.short_description = '消息数'

    def last_message_time(self, obj):
        last_msg = obj.messages.last()
        return last_msg.created_at if last_msg else None

    last_message_time.short_description = '最后消息时间'


class PrivateMessageAdmin(admin.ModelAdmin):
    """私聊消息管理"""
    list_display = ('sender', 'receiver', 'content_preview', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at', 'sender')
    search_fields = ('content', 'sender__username', 'receiver__username')
    readonly_fields = ('created_at', 'read_at')

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content

    content_preview.short_description = '内容预览'


# 注册模型
admin.site.register(PrivateChatSession, PrivateChatSessionAdmin)
admin.site.register(PrivateMessage, PrivateMessageAdmin)
