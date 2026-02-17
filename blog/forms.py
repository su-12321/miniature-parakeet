"""
表单定义
"""

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Post, Comment, Category, Tag
from django.utils import timezone
from .models import Bulletin, UserProfile
from PIL import Image
from io import BytesIO

class CustomUserCreationForm(UserCreationForm):
    """自定义用户注册表单"""
    email = forms.EmailField(required=True, label='邮箱')
    first_name = forms.CharField(max_length=30, required=False, label='名')
    last_name = forms.CharField(max_length=30, required=False, label='姓')

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """用户资料表单"""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        labels = {
            'first_name': '名',
            'last_name': '姓',
            'email': '邮箱',
        }


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['bio', 'website']
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        }


class PostForm(forms.ModelForm):
    """文章表单"""

    class Meta:
        model = Post
        fields = ['title', 'content', 'summary', 'category', 'tags',
                  'cover_image', 'status', 'is_featured']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 10}),
            'summary': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'tags': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'title': '标题',
            'content': '内容',
            'summary': '摘要',
            'category': '分类',
            'tags': '标签',
            'cover_image': '封面图片',
            'status': '状态',
            'is_featured': '设为推荐',
        }


class CommentForm(forms.ModelForm):
    """评论表单"""

    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '写下你的评论...'
            }),
        }
        labels = {
            'content': '评论',
        }


class CategoryForm(forms.ModelForm):
    """分类表单"""

    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class TagForm(forms.ModelForm):
    """标签表单"""

    class Meta:
        model = Tag
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# blog/forms.py (在原有文件末尾添加)




class BulletinForm(forms.ModelForm):
    """公告表单"""

    class Meta:
        model = Bulletin
        fields = ['title', 'content', 'priority', 'is_pinned', 'expires_at']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'expires_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def clean_expires_at(self):
        expires_at = self.cleaned_data.get('expires_at')
        if expires_at and expires_at < timezone.now():
            raise forms.ValidationError("过期时间不能早于当前时间")
        return expires_at


class AvatarUploadForm(forms.ModelForm):
    """头像上传表单"""

    class Meta:
        model = UserProfile
        fields = ['avatar']
        widgets = {
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')

        if not avatar:
            return avatar

        # 检查文件大小
        if avatar.size > 5 * 1024 * 1024:  # 5MB
            raise forms.ValidationError("图片大小不能超过5MB")

        # 验证图片
        try:
            avatar.seek(0)
            img = Image.open(avatar)
            img.verify()
            avatar.seek(0)
        except Exception as e:
            raise forms.ValidationError(f"无效的图片文件: {str(e)}")

        return avatar

    def save(self, commit=True):
        instance = super().save(commit=False)
        avatar = self.cleaned_data.get('avatar')

        if avatar:
            try:
                # 打开并处理图片
                avatar.seek(0)
                img = Image.open(avatar)

                # 转换为RGB
                if img.mode in ('RGBA', 'LA', 'P'):
                    if img.mode == 'P':
                        img = img.convert('RGBA')

                    # 白色背景
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[3])
                        img = background
                    else:
                        background.paste(img)
                        img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                # 调整尺寸
                max_size = (800, 800)
                if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)

                # 保存为JPEG
                output = BytesIO()
                img.save(output, format='JPEG', quality=85, optimize=True)
                output.seek(0)

                # 更新文件名
                import os
                name, ext = os.path.splitext(instance.avatar.name)
                instance.avatar.name = name + '.jpg'

            except Exception:
                # 如果转换失败，保留原始文件
                pass

        if commit:
            instance.save()

        return instance
