# views.py 或 api/views.py

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
from datetime import datetime, timedelta
from ...utils import get_weather_data, get_client_ip


# @require_GET
@csrf_exempt
def refresh_weather(request):
    """
    API端点：刷新天气数据

    参数（可选）:
    - city: 城市名称（如'北京'或'beijing'）
    - use_ip: 是否使用IP定位（true/false）
    - force: 是否强制刷新（忽略缓存）
    """
    try:
        # 获取查询参数
        city = request.GET.get('city')
        use_ip = request.GET.get('use_ip', 'true').lower() == 'true'
        force_refresh = request.GET.get('force', 'false').lower() == 'true'

        # 检查是否需要强制刷新或缓存过期
        should_refresh = force_refresh

        if not should_refresh:
            # 检查session中是否有缓存数据
            if 'weather_data' in request.session:
                weather_data = request.session.get('weather_data')
                last_update_str = request.session.get('weather_last_update')

                if last_update_str:
                    try:
                        last_update = datetime.fromisoformat(last_update_str)
                        # 检查是否过期（30分钟过期）
                        if datetime.now() - last_update < timedelta(minutes=30):
                            # 未过期，返回缓存数据
                            return JsonResponse({
                                'success': True,
                                'cached': True,
                                'data': weather_data,
                                'message': '使用缓存的天气数据'
                            })
                    except (ValueError, TypeError):
                        pass  # 日期格式错误，继续获取新数据

        # 获取新的天气数据
        if city:
            # 使用指定的城市
            weather_data = get_weather_data(location=city, use_ip=False)
        else:
            # 根据参数决定是否使用IP定位
            if use_ip:
                weather_data = get_weather_data(location=None, use_ip=True)
            else:
                # 使用默认城市
                from django.conf import settings
                default_city = getattr(settings, 'WEATHER_CITY', 'beijing')
                weather_data = get_weather_data(location=default_city, use_ip=False)

        if weather_data:
            # 保存到session中
            request.session['weather_data'] = weather_data
            request.session['weather_last_update'] = datetime.now().isoformat()

            return JsonResponse({
                'success': True,
                'cached': False,
                'data': weather_data,
                'timestamp': datetime.now().isoformat(),
                'message': '天气数据已刷新'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': '获取天气数据失败'
            }, status=500)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# 如果你想要一个基于类的视图版本
@method_decorator(csrf_exempt, name='dispatch')
class WeatherRefreshView(View):
    """天气刷新API（基于类的视图）"""

    def get(self, request):
        return refresh_weather(request)

    def post(self, request):
        """
        POST方式刷新天气（可以传递JSON参数）
        """
        try:
            # 尝试解析JSON数据
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except json.JSONDecodeError:
            data = {}

        # 从POST数据中获取参数，或使用查询参数
        city = data.get('city') or request.GET.get('city')
        use_ip = data.get('use_ip', True)
        force_refresh = data.get('force', False)

        # 修改request.GET以传递参数
        from django.http import QueryDict
        params = QueryDict(mutable=True)
        if city:
            params['city'] = city
        params['use_ip'] = str(use_ip).lower()
        params['force'] = str(force_refresh).lower()

        request.GET = params
        return refresh_weather(request)