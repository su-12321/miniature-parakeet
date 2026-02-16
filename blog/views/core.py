"""
核心视图模块
处理文章相关的所有视图
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse
from ..models import Post, Category, Tag, Comment
from ..forms import PostForm, CommentForm

def home_view(request):
    """
    首页视图
    显示文章列表，支持搜索和过滤
    """
    # 获取查询参数
    query = request.GET.get('q', '')
    category_id = request.GET.get('category')
    tag_id = request.GET.get('tag')
    featured = request.GET.get('featured')

    # 基础查询集
    posts = Post.objects.filter(status='published').order_by('-created_at')

    # 应用过滤
    if query:
        posts = posts.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(summary__icontains=query)
        )

    if category_id:
        posts = posts.filter(category_id=category_id)

    if tag_id:
        posts = posts.filter(tags__id=tag_id)

    if featured:
        posts = posts.filter(is_featured=True)

    # 分页
    paginator = Paginator(posts, 10)  # 每页10篇文章
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 获取分类和标签用于筛选
    categories = Category.objects.annotate(post_count=Count('post'))
    tags = Tag.objects.annotate(post_count=Count('post'))

    # 热门文章
    popular_posts = Post.objects.filter(status='published')\
        .order_by('-view_count')[:5]

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'tags': tags,
        'popular_posts': popular_posts,
        'query': query,
        'category_id': category_id,
        'tag_id': tag_id,
        'featured': featured,
    }

    return render(request, 'blog/home.html', context)

def post_detail_view(request, pk):
    """
    文章详情视图
    """
    post = get_object_or_404(Post, pk=pk)

    # 检查文章状态
    if post.status != 'published' and not request.user.is_staff:
        messages.error(request, '这篇文章暂时不可用。')
        return redirect('home')

    # 增加浏览数
    post.increment_view_count()

    # 处理评论提交
    if request.method == 'POST' and request.user.is_authenticated:
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            messages.success(request, '评论发布成功！')
            return redirect('post_detail', pk=post.pk)
    else:
        comment_form = CommentForm()

    # 获取评论
    comments = post.comments.filter(is_active=True).order_by('-created_at')

    # 获取相关文章
    related_posts = Post.objects.filter(
        status='published',
        tags__in=post.tags.all()
    ).exclude(pk=post.pk).distinct()[:3]

    context = {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
        'related_posts': related_posts,
    }

    return render(request, 'blog/post_detail.html', context)

@login_required
def post_create_view(request):
    """
    创建文章视图
    """
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            form.save_m2m()  # 保存多对多关系（标签）
            messages.success(request, '文章创建成功！')
            return redirect('post_detail', pk=post.pk)
    else:
        form = PostForm()

    context = {
        'form': form,
        'title': '创建文章',
    }

    return render(request, 'blog/post_form.html', context)

@login_required
def post_edit_view(request, pk):
    """
    编辑文章视图
    """
    post = get_object_or_404(Post, pk=pk)

    # 检查权限
    if post.author != request.user and not request.user.is_staff:
        messages.error(request, '您没有权限编辑这篇文章。')
        return redirect('post_detail', pk=post.pk)

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, '文章更新成功！')
            return redirect('post_detail', pk=post.pk)
    else:
        form = PostForm(instance=post)

    context = {
        'form': form,
        'title': '编辑文章',
        'post': post,
    }

    return render(request, 'blog/post_form.html', context)

@login_required
def post_delete_view(request, pk):
    """
    删除文章视图
    """
    post = get_object_or_404(Post, pk=pk)

    # 检查权限
    if post.author != request.user and not request.user.is_staff:
        messages.error(request, '您没有权限删除这篇文章。')
        return redirect('post_detail', pk=post.pk)

    if request.method == 'POST':
        post.delete()
        messages.success(request, '文章删除成功！')
        return redirect('home')

    context = {
        'post': post,
    }

    return render(request, 'blog/post_confirm_delete.html', context)

@login_required
def my_posts_view(request):
    """
    我的文章视图
    """
    posts = Post.objects.filter(author=request.user).order_by('-created_at')

    # 统计信息
    stats = {
        'total': posts.count(),
        'published': posts.filter(status='published').count(),
        'draft': posts.filter(status='draft').count(),
        'archived': posts.filter(status='archived').count(),
    }

    context = {
        'posts': posts,
        'stats': stats,
    }

    return render(request, 'blog/my_posts.html', context)

def category_posts_view(request, category_id):
    """
    分类文章列表视图
    """
    category = get_object_or_404(Category, pk=category_id)
    posts = Post.objects.filter(category=category, status='published')\
        .order_by('-created_at')

    context = {
        'category': category,
        'posts': posts,
    }

    return render(request, 'blog/category_posts.html', context)

def tag_posts_view(request, tag_id):
    """
    标签文章列表视图
    """
    tag = get_object_or_404(Tag, pk=tag_id)
    posts = Post.objects.filter(tags=tag, status='published')\
        .order_by('-created_at')

    context = {
        'tag': tag,
        'posts': posts,
    }

    return render(request, 'blog/tag_posts.html', context)


def public_posts_view(request):
    """
    显示所有已发布的公开文章（不带筛选功能）
    """
    # 获取所有已发布的文章，按创建时间倒序排列
    posts = Post.objects.filter(status='published').order_by('-created_at')

    # 分页处理（每页10篇）
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'title': '所有公开文章',
    }
    return render(request, 'blog/public_posts.html', context)
