from django import template
from django.template.loader import get_template
import os
from pathlib import Path
from django.conf import settings

register = template.Library()


@register.simple_tag(takes_context=True)
def render_static_template(context, template_path):
    """
    渲染静态文件目录中的模板
    用法: {% render_static_template 'pages/about.html' %}
    """
    # 将静态文件路径转换为模板路径
    static_dir = Path(settings.BASE_DIR) / 'myblog' / 'blog' / 'static'
    full_path = static_dir / template_path

    if full_path.exists():
        # 读取文件内容
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 创建临时模板
        template_obj = template.Template(content)

        # 渲染模板
        rendered = template_obj.render(context)
        return rendered

    return f"<!-- Template not found: {template_path} -->"