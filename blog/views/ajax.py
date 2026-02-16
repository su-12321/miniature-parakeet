# blog/views.py

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from ..templatetags.markdown_extras import markdown_filter


@csrf_exempt
def markdown_preview(request):
    """
    AJAX 预览 Markdown
    """
    if request.method == 'POST':
        content = request.POST.get('content', '')

        try:
            # 使用过滤器渲染
            html = markdown_filter(content)

            return JsonResponse({
                'success': True,
                'html': html
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

    return JsonResponse({'success': False, 'error': 'Invalid request'})