"""
数据库模型
"""
from cryptography.fernet import Fernet
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver
import hashlib
import os
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
from django.conf import settings


class HashedFilenameStorage(FileSystemStorage):
    """自定义存储类，使用文件内容哈希作为文件名"""

    def get_valid_name(self, name):
        """清理文件名，移除特殊字符"""
        import re
        # 只保留字母、数字、下划线、点、连字符
        name = re.sub(r'[^a-zA-Z0-9_.-]', '', name)
        return super().get_valid_name(name)

    def _save(self, name, content):
        """重写保存方法，使用哈希文件名"""
        # 1. 读取文件内容并计算哈希
        content.seek(0)
        file_content = content.read()

        # 计算哈希（使用SHA256更安全）
        file_hash = hashlib.sha256(file_content).hexdigest()

        # 2. 获取文件扩展名
        _, ext = os.path.splitext(name)
        if not ext:  # 如果没有扩展名，根据内容猜测
            from PIL import Image
            import io
            try:
                img = Image.open(io.BytesIO(file_content))
                if img.format:
                    ext = f'.{img.format.lower()}'
                else:
                    ext = '.jpg'
            except:
                ext = '.jpg'

        # 统一扩展名为小写
        ext = ext.lower()

        # 3. 创建目录结构：哈希前2位/哈希次2位/
        dir1 = file_hash[:2]
        dir2 = file_hash[2:4]

        # 4. 构建新文件名和路径
        new_filename = f'{file_hash}{ext}'
        new_path = os.path.join('hashed', dir1, dir2, new_filename)

        # 5. 检查是否已存在相同文件
        if not self.exists(new_path):
            # 创建目录
            full_path = self.path(new_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            # 写入文件
            content.seek(0)
            super()._save(new_path, content)

        # 6. 返回存储路径（相对路径）
        return new_path

    def delete(self, name):
        """删除文件时，如果是hashed存储的，检查是否有其他引用"""
        try:
            # 对于hashed文件，不立即删除（可能有其他引用）
            if name.startswith('hashed/'):
                # 可以在这里实现引用计数或垃圾回收
                print(f"警告: hashed文件 {name} 被标记删除，但可能被其他引用")
                # 可以在这里记录到日志，由后台任务定期清理
                return
        except:
            pass

        # 非hashed文件正常删除
        super().delete(name)

class Category(models.Model):
    """文章分类"""
    name = models.CharField('分类名称', max_length=100)
    description = models.TextField('描述', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '分类'
        verbose_name_plural = '分类'
        ordering = ['name']

    def __str__(self):
        return self.name


class Tag(models.Model):
    """文章标签"""
    name = models.CharField('标签名称', max_length=50)
    description = models.TextField('描述', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '标签'
        verbose_name_plural = '标签'
        ordering = ['name']

    def __str__(self):
        return self.name


class Post(models.Model):
    """博客文章"""
    STATUS_CHOICES = (
        ('draft', '草稿'),
        ('published', '已发布'),
        ('archived', '已归档'),
    )

    title = models.CharField('标题', max_length=200)
    content = models.TextField('内容')
    summary = models.TextField('摘要', max_length=500, blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='作者')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL,
                                 null=True, blank=True, verbose_name='分类')
    tags = models.ManyToManyField(Tag, blank=True, verbose_name='标签')
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='draft')
    cover_image = models.ImageField('封面图片', upload_to='post_covers/', blank=True)
    is_featured = models.BooleanField('是否推荐', default=False)
    view_count = models.PositiveIntegerField('浏览数', default=0)
    created_at = models.DateTimeField('创建时间', default=timezone.now)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '文章'
        verbose_name_plural = '文章'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('post_detail', args=[str(self.id)])

    def increment_view_count(self):
        """增加浏览数"""
        self.view_count += 1
        self.save(update_fields=['view_count'])

    @property
    def short_content(self):
        """内容预览"""
        return self.content[:200] + '...' if len(self.content) > 200 else self.content


class Comment(models.Model):
    """文章评论"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name='文章')
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='评论者')
    content = models.TextField('评论内容')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                               related_name='replies', verbose_name='父评论')
    is_active = models.BooleanField('是否显示', default=True)
    created_at = models.DateTimeField('创建时间', default=timezone.now)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '评论'
        verbose_name_plural = '评论'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.author.username} 评论了 {self.post.title}'


class VisitStatistics(models.Model):
    """访问统计"""
    ip_address = models.GenericIPAddressField('IP地址')
    user_agent = models.TextField('用户代理', blank=True)
    path = models.CharField('访问路径', max_length=500)
    method = models.CharField('请求方法', max_length=10)
    status_code = models.IntegerField('状态码')
    visit_time = models.DateTimeField('访问时间', auto_now_add=True)

    class Meta:
        verbose_name = '访问统计'
        verbose_name_plural = '访问统计'
        ordering = ['-visit_time']

    def __str__(self):
        return f'{self.ip_address} - {self.path}'


# 在 blog/models.py 文件中添加以下模型

class PrivateChatSession(models.Model):
    """私聊会话"""
    user1 = models.ForeignKey(User, on_delete=models.CASCADE,
                              related_name='chat_sessions_as_user1',
                              verbose_name='用户1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE,
                              related_name='chat_sessions_as_user2',
                              verbose_name='用户2')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('最后更新时间', auto_now=True)
    is_active = models.BooleanField('是否活跃', default=True)

    class Meta:
        verbose_name = '私聊会话'
        verbose_name_plural = '私聊会话'
        unique_together = ['user1', 'user2']
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user1.username} 和 {self.user2.username} 的聊天"

    def other_user(self, current_user):
        """获取会话中的另一个用户"""
        return self.user2 if current_user == self.user1 else self.user1

    def unread_count_for_user(self, user):
        """获取用户未读消息数"""
        return self.messages.filter(
            receiver=user,
            is_read=False
        ).count()


class PrivateMessage(models.Model):
    ENCRYPTION_CHOICES = [
        ('system', '系统加密'),
        ('custom', '用户自定义加密'),
    ]

    session = models.ForeignKey(PrivateChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_private_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_private_messages')

    # 加密内容（存储密文，二进制或文本均可，建议使用 BinaryField 或 TextField 配合 base64）
    encrypted_content = models.BinaryField('加密内容', null=True, blank=True)

    # 加密类型
    encryption_type = models.CharField('加密类型', max_length=10, choices=ENCRYPTION_CHOICES, default='system')

    # 自毁相关
    is_burn_after_reading = models.BooleanField('阅后即焚', default=False)
    burn_at = models.DateTimeField('定时销毁时间', null=True, blank=True)
    destroyed_at = models.DateTimeField('实际销毁时间', null=True, blank=True)

    is_read = models.BooleanField('是否已读', default=False)
    read_at = models.DateTimeField('阅读时间', null=True, blank=True)
    created_at = models.DateTimeField('发送时间', auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
            models.Index(fields=['burn_at']),  # 用于定时销毁查询
            models.Index(fields=['receiver', 'is_read']),
        ]

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username}: {self.get_preview()}"

    def get_preview(self):
        """返回消息预览（截取前50字符）"""
        if self.destroyed_at:
            return "[消息已销毁]"
        if not self.encrypted_content:
            return ""
        try:
            # 仅对系统加密消息尝试解密预览，自定义加密无法预览
            if self.encryption_type == 'system':
                return self._decrypt_system()[:50] + "..."
        except:
            pass
        return "[加密消息]"

    # ---------- 系统加密方法 ----------
    def _encrypt_system(self, plaintext):
        from django.conf import settings
        from cryptography.fernet import Fernet
        cipher = Fernet(settings.CHAT_ENCRYPTION_KEY.encode())
        return cipher.encrypt(plaintext.encode())

    def _decrypt_system(self):
        from django.conf import settings
        from cryptography.fernet import Fernet
        cipher = Fernet(settings.CHAT_ENCRYPTION_KEY.encode())
        return cipher.decrypt(self.encrypted_content).decode()

    def set_system_content(self, plaintext):
        """设置系统加密内容"""
        self.encryption_type = 'system'
        self.encrypted_content = self._encrypt_system(plaintext)

    def get_system_content(self):
        """获取系统解密内容（仅当类型为system时有效）"""
        if self.encryption_type != 'system':
            raise ValueError("Message is not system-encrypted")
        if self.destroyed_at:
            return None
        return self._decrypt_system()

    # ---------- 销毁方法 ----------
    def destroy(self):
        """销毁消息内容（阅后即焚或定时销毁调用）"""
        self.encrypted_content = None
        self.destroyed_at = timezone.now()
        self.save(update_fields=['encrypted_content', 'destroyed_at'])

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
            if self.is_burn_after_reading:
                self.destroy()




# 公告板模型
class Bulletin(models.Model):
    """公告板模型"""
    PRIORITY_CHOICES = [
        ('normal', '普通'),
        ('important', '重要'),
        ('urgent', '紧急'),
    ]

    title = models.CharField('标题', max_length=200)
    content = models.TextField('内容')
    author = models.ForeignKey('auth.User', on_delete=models.CASCADE, verbose_name='作者')
    priority = models.CharField('优先级', max_length=20, choices=PRIORITY_CHOICES, default='normal')
    is_pinned = models.BooleanField('置顶', default=False)
    is_active = models.BooleanField('是否显示', default=True)

    # 时间相关
    publish_at = models.DateTimeField('发布时间', default=timezone.now)
    expires_at = models.DateTimeField('过期时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-publish_at', '-priority']
        verbose_name = '公告'
        verbose_name_plural = '公告管理'

    def __str__(self):
        return self.title


# 用户资料扩展模型
class UserProfile(models.Model):
    """用户扩展资料"""
    user = models.OneToOneField(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='用户'
    )

    avatar = models.ImageField(
        '头像',
        upload_to='avatars/',
        default='avatars/default.png',
        max_length=255
    )

    bio = models.TextField('个人简介', max_length=500, blank=True)
    website = models.URLField('个人网站', max_length=200, blank=True)
    avatar_updated_at = models.DateTimeField('头像更新时间', auto_now=True)

    class Meta:
        verbose_name = '用户资料'
        verbose_name_plural = '用户资料管理'

    def __str__(self):
        return f"{self.user.username}的资料"


# 信号：用户创建时自动创建UserProfile


@receiver(post_save, sender='auth.User')
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender='auth.User')
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


cipher = Fernet(settings.CHAT_ENCRYPTION_KEY.encode())

class ChatRoom(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    encrypted_content = models.BinaryField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def set_content(self, plaintext):
        self.encrypted_content = cipher.encrypt(plaintext.encode())

    def get_content(self):
        return cipher.decrypt(self.encrypted_content).decode()
