# blog/views/bulletin.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from blog.models import Bulletin
from blog.forms import BulletinForm


def is_staff_user(user):
    return user.is_staff or user.is_superuser


def bulletin_list(request):
    """公告列表"""
    # 获取活动的、未过期的公告
    bulletins = Bulletin.objects.filter(is_active=True)

    # 排除已过期的公告
    bulletins = bulletins.exclude(
        expires_at__lt=timezone.now()
    ) if bulletins.exists() else bulletins

    # 排序
    bulletins = bulletins.order_by('-is_pinned', '-publish_at')

    # 搜索
    keyword = request.GET.get('keyword', '')
    if keyword:
        bulletins = bulletins.filter(
            Q(title__icontains=keyword) | Q(content__icontains=keyword)
        )

    # 分页
    paginator = Paginator(bulletins, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'keyword': keyword,
        'title': '公告板'
    }
    return render(request, 'blog/bulletin/list.html', context)


def bulletin_detail(request, pk):
    """公告详情"""
    bulletin = get_object_or_404(Bulletin, pk=pk, is_active=True)

    if bulletin.expires_at and bulletin.expires_at < timezone.now():
        messages.warning(request, '此公告已过期')

    context = {
        'bulletin': bulletin,
        'title': bulletin.title
    }
    return render(request, 'blog/bulletin/detail.html', context)


@login_required
@user_passes_test(is_staff_user)
def bulletin_create(request):
    """创建公告"""
    if request.method == 'POST':
        form = BulletinForm(request.POST)
        if form.is_valid():
            bulletin = form.save(commit=False)
            bulletin.author = request.user
            bulletin.save()
            messages.success(request, '公告创建成功！')
            return redirect('bulletin_detail', pk=bulletin.pk)
    else:
        form = BulletinForm()

    context = {'form': form, 'title': '创建公告'}
    return render(request, 'blog/bulletin/form.html', context)


@login_required
@user_passes_test(is_staff_user)
def bulletin_update(request, pk):
    """更新公告"""
    bulletin = get_object_or_404(Bulletin, pk=pk)

    if request.method == 'POST':
        form = BulletinForm(request.POST, instance=bulletin)
        if form.is_valid():
            form.save()
            messages.success(request, '公告更新成功！')
            return redirect('bulletin_detail', pk=bulletin.pk)
    else:
        form = BulletinForm(instance=bulletin)

    context = {'form': form, 'bulletin': bulletin, 'title': '编辑公告'}
    return render(request, 'blog/bulletin/form.html', context)


@login_required
@user_passes_test(is_staff_user)
def bulletin_delete(request, pk):
    """删除公告（软删除）"""
    bulletin = get_object_or_404(Bulletin, pk=pk)

    if request.method == 'POST':
        bulletin.is_active = False
        bulletin.save()
        messages.success(request, '公告已删除！')
        return redirect('bulletin_list')

    context = {'bulletin': bulletin, 'title': '删除公告'}
    return render(request, 'blog/bulletin/confirm_delete.html', context)

