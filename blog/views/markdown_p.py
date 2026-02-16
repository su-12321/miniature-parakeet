import markdown
from django.shortcuts import render, get_object_or_404
from ..models import Post


def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)

    # 转换 Markdown 为 HTML
    if post.content_format == 'markdown':
        post.content_html = markdown.markdown(
            post.content,
            extensions=[
                'extra',  # 包括表格、脚注等
                'codehilite',  # 代码高亮
                'toc',  # 目录生成
                'fenced_code',  # 围栏式代码块
                'mdx_math'  # 数学公式支持（如果需要）
            ],
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight'
                },
                'toc': {
                    'title': '目录',
                    'permalink': True
                }
            }
        )
    else:
        post.content_html = post.content

    return render(request, 'blog/post_detail.html', {'post': post})