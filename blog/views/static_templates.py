import os
from django.conf import settings
from pathlib import Path
from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.template import Template, Context
from django.conf import settings
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET


@require_GET
@cache_page(60 * 15)  # 缓存15分钟
def static_template_view(request, template_path):
    """
    将静态文件作为模板渲染的视图
    """
    # 定义允许的静态模板路径（白名单）
    ALLOWED_PATHS = [
        'pages/about.html',
        'pages/contact.html',
        'pages/privacy.html',
        'pages/terms.html',
        'components/header.html',
        'components/footer.html',
        'layouts/base.html',
        'about_develop/developer_note.html',
        'about_develop/Developer.html',
    ]

    # 安全检查
    if template_path not in settings.ALLOWED_STATIC_TEMPLATES:
        raise Http404("Template not allowed")

    # 构建文件路径
    static_dir = Path(settings.BASE_DIR) / 'myblog' / 'blog' / 'static'
    file_path = static_dir / template_path

    # 防止目录遍历攻击
    try:
        file_path.resolve().relative_to(static_dir.resolve())
    except ValueError:
        raise Http404("Invalid path")

    # 检查文件是否存在
    if not file_path.exists():
        raise Http404("Template not found")

    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

    # 创建 Django 模板
    template_obj = Template(template_content)

    # 准备上下文
    context = {
        'request': request,
        'user': request.user,
        # 添加其他默认上下文变量
        'STATIC_URL': settings.STATIC_URL,
        'MEDIA_URL': settings.MEDIA_URL,
    }

    # 渲染模板
    rendered = template_obj.render(Context(context))

    return HttpResponse(rendered, content_type='text/html; charset=utf-8')
