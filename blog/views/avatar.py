# blog/views/avatar.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from blog.models import UserProfile
from blog.forms import AvatarUploadForm


@login_required
def profile_view(request):
    """查看用户资料"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    context = {
        'profile': profile,
        'title': '我的资料'
    }
    return render(request, 'blog/avatar/profile.html', context)


@login_required
def avatar_upload(request):
    """上传头像页面"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = AvatarUploadForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, '头像上传成功！')
            return redirect('profile_view')
    else:
        form = AvatarUploadForm(instance=profile)

    context = {
        'form': form,
        'profile': profile,
        'title': '上传头像'
    }
    return render(request, 'blog/avatar/upload.html', context)


@login_required
def avatar_update(request):
    """AJAX头像上传"""
    if request.method == 'POST' and request.FILES.get('avatar'):
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        form = AvatarUploadForm(request.POST, request.FILES, instance=profile)

        if form.is_valid():
            form.save()
            return JsonResponse({
                'success': True,
                'avatar_url': profile.avatar.url,
                'message': '头像更新成功'
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })

    return JsonResponse({'success': False, 'error': '无效请求'})


@login_required
def avatar_reset(request):
    """重置为默认头像"""
    if request.method == 'POST':
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        profile.avatar = 'avatars/default.png'
        profile.save()
        messages.success(request, '已恢复默认头像')
        return redirect('profile_view')

    return redirect('profile_view')