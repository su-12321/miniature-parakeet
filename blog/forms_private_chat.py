# blog/forms_private_chat.py

from django import forms
from django.contrib.auth.models import User
from .models import PrivateMessage

class PrivateMessageForm(forms.ModelForm):
    """私聊消息表单"""
    class Meta:
        model = PrivateMessage
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '输入消息内容...',
                'maxlength': 1000,
            })
        }
        labels = {
            'content': ''
        }

class UserSearchForm(forms.Form):
    """用户搜索表单"""
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '输入用户名搜索...'
        })
    )
    