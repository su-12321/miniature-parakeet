"""
统计功能视图
处理访问统计和数据分析
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import json
from ..models import VisitStatistics, Post

def is_staff_user(user):
    """检查用户是否是员工"""
    return user.is_staff

@login_required
@user_passes_test(is_staff_user)
def statistics_view(request):
    """
    统计面板视图
    只有管理员可以访问
    """
    # 时间范围
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # 访问统计
    total_visits = VisitStatistics.objects.count()
    today_visits = VisitStatistics.objects.filter(
        visit_time__date=today
    ).count()
    week_visits = VisitStatistics.objects.filter(
        visit_time__date__gte=week_ago
    ).count()
    month_visits = VisitStatistics.objects.filter(
        visit_time__date__gte=month_ago
    ).count()

    # 热门页面
    popular_pages = VisitStatistics.objects.values('path')\
        .annotate(count=Count('id'))\
        .order_by('-count')[:10]

    # 文章统计
    total_posts = Post.objects.count()
    published_posts = Post.objects.filter(status='published').count()
    draft_posts = Post.objects.filter(status='draft').count()
    archived_posts = Post.objects.filter(status='archived').count()

    # 热门文章
    top_posts = Post.objects.filter(status='published')\
        .order_by('-view_count')[:10]

    # 用户统计
    from django.contrib.auth.models import User
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    staff_users = User.objects.filter(is_staff=True).count()

    context = {
        # 访问统计
        'total_visits': total_visits,
        'today_visits': today_visits,
        'week_visits': week_visits,
        'month_visits': month_visits,
        'popular_pages': popular_pages,

        # 文章统计
        'total_posts': total_posts,
        'published_posts': published_posts,
        'draft_posts': draft_posts,
        'archived_posts': archived_posts,
        'top_posts': top_posts,

        # 用户统计
        'total_users': total_users,
        'active_users': active_users,
        'staff_users': staff_users,

        # 时间范围
        'today': today,
        'week_ago': week_ago,
        'month_ago': month_ago,
    }

    return render(request, 'blog/statistics.html', context)

def api_visit_stats(request):
    """
    API: 获取访问统计数据
    返回JSON格式的统计数据，用于图表展示
    """
    if not request.user.is_staff:
        return JsonResponse({'error': '权限不足'}, status=403)

    # 过去30天的访问数据
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)

    visits_by_date = VisitStatistics.objects.filter(
        visit_time__date__range=[start_date, end_date]
    ).values('visit_time__date')\
     .annotate(count=Count('id'))\
     .order_by('visit_time__date')

    # 格式化数据
    dates = []
    counts = []

    for item in visits_by_date:
        dates.append(item['visit_time__date'].strftime('%m-%d'))
        counts.append(item['count'])

    # 热门访问路径
    popular_paths = VisitStatistics.objects.values('path')\
        .annotate(count=Count('id'))\
        .order_by('-count')[:15]

    # 浏览器统计
    browsers = {}
    for stat in VisitStatistics.objects.all()[:1000]:  # 限制样本数量
        user_agent = stat.user_agent or ''
        if 'Chrome' in user_agent:
            browsers['Chrome'] = browsers.get('Chrome', 0) + 1
        elif 'Firefox' in user_agent:
            browsers['Firefox'] = browsers.get('Firefox', 0) + 1
        elif 'Safari' in user_agent:
            browsers['Safari'] = browsers.get('Safari', 0) + 1
        elif 'Edge' in user_agent:
            browsers['Edge'] = browsers.get('Edge', 0) + 1
        else:
            browsers['其他'] = browsers.get('其他', 0) + 1

    data = {
        'dates': dates,
        'counts': counts,
        'popular_paths': list(popular_paths),
        'browsers': browsers,
        'total_visits': VisitStatistics.objects.count(),
        'unique_ips': VisitStatistics.objects.values('ip_address').distinct().count(),
    }

    return JsonResponse(data)
