from datetime import datetime


def static_template_context(request):
    """
    为静态模板添加上下文变量
    """
    year_str = datetime.now()
    year_str1 = year_str.strftime("%Y")
    return {
        'site_name': '我的博客',
        'current_year': year_str1,
        'STATIC_URL': '/static/',  # 确保静态模板中能正确引用静态文件
    }