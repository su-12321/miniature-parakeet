"""
认证相关视图
处理用户注册、登录、注销和个人资料
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from ..forms import CustomUserCreationForm, ProfileForm

def register_view(request):
    """
    用户注册视图
    """
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, '注册成功！欢迎来到我的博客。')
            return redirect('home')
    else:
        form = CustomUserCreationForm()

    context = {
        'form': form,
        'title': '注册',
    }

    return render(request, 'blog/register.html', context)

def login_view(request):
    """
    用户登录视图
    """
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'欢迎回来，{username}！')
                return redirect('home')
        else:
            messages.error(request, '用户名或密码错误。')
    else:
        form = AuthenticationForm()

    context = {
        'form': form,
        'title': '登录',
    }

    return render(request, 'blog/login.html', context)

def logout_view(request):
    """
    用户注销视图
    """
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, '您已成功注销。')

    return redirect('home')

@login_required
def profile_view(request):
    """
    用户个人资料视图
    """
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, '个人资料更新成功！')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)

    # 获取用户统计信息
    user_posts = request.user.post_set.filter(status='published')
    user_comments = request.user.comment_set.count()

    context = {
        'form': form,
        'user_posts': user_posts,
        'user_comments': user_comments,
    }

    return render(request, 'blog/profile.html', context)
