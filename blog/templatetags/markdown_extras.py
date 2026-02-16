# blog/templatetags/markdown_extras.py

import markdown
from django import template
from django.utils.safestring import mark_safe
from django.template.defaultfilters import stringfilter
import re
from mdx_math import MathExtension

register = template.Library()

# 配置 Markdown 扩展
EXTENSIONS = [
    'markdown.extensions.extra',  # 表格、列表等
    'markdown.extensions.codehilite',  # 代码高亮
    'markdown.extensions.toc',  # 目录
    'markdown.extensions.nl2br',  # 换行转<br>
    'markdown.extensions.sane_lists',  # 更智能的列表
    MathExtension(),  # LaTeX 支持
]

EXTENSION_CONFIGS = {
    'markdown.extensions.codehilite': {
        'css_class': 'hljs',
        'linenums': True,
        'guess_lang': True,
    },
    'mdx_math': {
        'enable_dollar_delimiter': True,  # 启用 $...$ 语法
        'add_preview': True,  # 添加预览
    },
    'markdown.extensions.toc': {
        'title': '目录',
        'permalink': True,
        'baselevel': 2,
    }
}


@register.filter(name='markdown')
@stringfilter
def markdown_filter(value):
    """
    将 Markdown 文本转换为 HTML
    """
    if not value:
        return ''

    try:
        # 创建 Markdown 实例
        md = markdown.Markdown(
            extensions=EXTENSIONS,
            extension_configs=EXTENSION_CONFIGS,
            output_format='html5'
        )

        # 转换 Markdown 为 HTML
        html = md.convert(value)

        # 处理一些特殊情况
        html = post_process_html(html)

        return mark_safe(html)
    except Exception as e:
        # 如果转换失败，返回原始文本
        error_html = f'''
        <div class="alert alert-danger">
            <i class="fas fa-exclamation-triangle"></i>
            Markdown 渲染失败：{str(e)}
        </div>
        <pre>{value}</pre>
        '''
        return mark_safe(error_html)


@register.filter(name='markdown_summary')
@stringfilter
def markdown_summary_filter(value, length=200):
    """
    生成 Markdown 摘要（移除标签和 LaTeX 公式）
    """
    if not value:
        return ''

    # 移除 LaTeX 公式
    text = re.sub(r'\$.*?\$', '', value)  # 行内公式
    text = re.sub(r'\\\[.*?\\\]', '', text)  # 块级公式
    text = re.sub(r'\$\$.*?\$\$', '', text)  # 块级公式

    # 移除 Markdown 标签
    text = re.sub(r'\[.*?\]\(.*?\)', '', text)  # 链接
    text = re.sub(r'#+ ', '', text)  # 标题
    text = re.sub(r'[*_~`]', '', text)  # 粗体、斜体等
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)  # 图片
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)  # 代码块

    # 移除 HTML 标签（如果有）
    text = re.sub(r'<[^>]+>', '', text)

    # 截断文本
    if len(text) > length:
        text = text[:length] + '...'

    return text


@register.filter(name='has_math')
@stringfilter
def has_math_filter(value):
    """
    检查文本中是否包含数学公式
    """
    if not value:
        return False

    math_patterns = [
        r'\$.*?\$',  # 行内公式
        r'\\\(.*?\\\)',  # 行内公式
        r'\$\$.*?\$\$',  # 块级公式
        r'\\\[.*?\\\]',  # 块级公式
    ]

    for pattern in math_patterns:
        if re.search(pattern, value, re.DOTALL):
            return True

    return False


def post_process_html(html):
    """
    对生成的 HTML 进行后处理
    """
    if not html:
        return html

    # 添加表格的 Bootstrap 类
    html = re.sub(r'<table>', '<table class="table table-bordered table-hover">', html)

    # 为代码块添加行号
    html = re.sub(
        r'<div class="codehilite"><pre><span></span><code>',
        '<div class="codehilite"><pre><code>',
        html
    )

    # 为图片添加响应式类
    html = re.sub(
        r'<img src="([^"]+)" alt="([^"]*)"',
        r'<img src="\1" alt="\2" class="img-fluid rounded"',
        html
    )

    # 为数学公式添加样式类
    html = html.replace('class="math"', 'class="math katex-render"')
    html = html.replace('class="math inline"', 'class="math inline katex-render"')
    html = html.replace('class="math display"', 'class="math display katex-render"')

    return html


@register.simple_tag
def render_markdown_file(file_path):
    """
    渲染 Markdown 文件
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return markdown_filter(content)
    except Exception as e:
        return mark_safe(f'<div class="alert alert-danger">无法读取文件: {str(e)}</div>')


@register.inclusion_tag('blog/components/markdown_preview.html')
def markdown_preview(content, height='400px'):
    """
    生成 Markdown 预览区域
    """
    return {
        'content': content,
        'height': height
    }