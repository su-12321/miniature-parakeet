"""
工具函数
包含天气API等功能
"""

import requests
import os
from django.conf import settings
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()


def get_weather_data(location=None, ip="", use_ip=True):
    """
    获取天气数据
    使用心知天气API（Seniverse）

    参数:
    - location: 城市名，如'beijing'或'北京'
    - use_ip: 是否使用IP定位，如果为True且location为空，则使用IP定位
    """
    api_key = os.getenv('WEATHER_API_KEY')  # 需要修改环境变量名
    if not api_key:
        return None

    try:
        # 构建API参数
        params = {
            'key': api_key,
            'language': 'zh-Hans',
            'unit': 'c',
            'start': 0,
            'days': 1  # 获取1天的天气预报
        }

        # 确定位置参数
        if location:
            params['location'] = location
        elif use_ip:
            params['location'] = ip  # 'ip'  # 使用IP自动定位
        else:
            params['location'] = os.getenv('WEATHER_CITY', 'beijing')

        url = 'https://api.seniverse.com/v3/weather/daily.json'

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if 'results' not in data or not data['results']:
            return None

        result = data['results'][0]
        location_info = result['location']
        daily_weather = result['daily'][0]

        # 获取天气代码对应的描述
        weather_code = daily_weather['code_day']
        weather_descriptions = {
            '0': '晴', '1': '多云', '2': '阴', '3': '阵雨', '4': '雷阵雨',
            '5': '雷阵雨伴有冰雹', '6': '雨夹雪', '7': '小雨', '8': '中雨',
            '9': '大雨', '10': '暴雨', '11': '大暴雨', '12': '特大暴雨',
            '13': '阵雪', '14': '小雪', '15': '中雪', '16': '大雪',
            '17': '暴雪', '18': '雾', '19': '冻雨', '20': '沙尘暴',
            '21': '小到中雨', '22': '中到大雨', '23': '大到暴雨',
            '24': '暴雨到大暴雨', '25': '大暴雨到特大暴雨', '26': '小到中雪',
            '27': '中到大雪', '28': '大到暴雪', '29': '浮尘', '30': '扬沙',
            '31': '强沙尘暴', '32': '浓雾', '33': '强浓雾', '34': '霾',
            '35': '中度霾', '36': '重度霾', '37': '严重霾', '38': '大雾',
            '39': '特强浓雾', '53': '霾', '54': '中度霾', '55': '重度霾',
            '56': '严重霾', '57': '大雾', '58': '特强浓雾'
        }

        # 解析天气数据
        weather_info = {
            'city': location_info['name'],
            'temperature': daily_weather['high'],  # 最高温度
            'low_temperature': daily_weather['low'],  # 最低温度
            'description': weather_descriptions.get(weather_code, daily_weather['text_day']),
            'icon': weather_code,  # 使用心知天气的天气代码
            'wind_speed': daily_weather['wind_speed'],
            'wind_direction': daily_weather['wind_direction'],
            'humidity': daily_weather['humidity'],
            'precipitation': float(daily_weather.get('precip', 0)) * 100,  # 转换为百分比
            'rainfall': daily_weather.get('rainfall', '0.00'),  # 降雨量
            'date': daily_weather['date'],
            'text_day': daily_weather['text_day'],  # 白天天气文字描述
            'text_night': daily_weather['text_night'],  # 夜间天气文字描述
            'updated_at': result['last_update'],  # API更新时间
            'local_time': datetime.now().strftime('%H:%M'),  # 本地获取时间
        }

        return weather_info
    except (requests.RequestException, KeyError, ValueError) as e:
        print(f"获取天气数据失败: {e}")
        return None


def get_client_weather(request):
    """
    根据客户端信息获取天气
    优先使用IP定位，失败则使用默认城市
    """
    # 尝试从客户端IP获取位置
    client_ip = get_client_ip(request)

    # 这里可以添加IP定位服务，例如使用心知天气的IP定位API
    # 但需要另外的API密钥，这里简化处理

    # 尝试使用IP自动定位
    weather_data = get_weather_data(location=None, ip=client_ip, use_ip=True)
    print(client_ip)

    # 如果IP定位失败，使用默认城市
    if not weather_data:
        default_city = os.getenv('WEATHER_CITY', 'beijing')
        weather_data = get_weather_data(location=default_city, use_ip=False)

    return weather_data


def weather_context(request):
    """
    天气上下文处理器
    将天气数据添加到所有模板上下文中
    """
    # 使用缓存避免频繁调用API
    cache_key = f'weather_data_{get_client_ip(request)}'
    weather_data = None

    # 检查是否已有缓存的天气数据（这里简化，实际应使用Django缓存）
    # 我们可以使用session来存储天气数据
    if 'weather_data' in request.session:
        weather_data = request.session['weather_data']
        last_update = request.session.get('weather_last_update')

        # 检查是否过期（1小时过期）
        if last_update:
            last_update_time = datetime.fromisoformat(last_update)
            if datetime.now() - last_update_time < timedelta(hours=1):
                return {'weather': weather_data}

    # 获取新的天气数据
    weather_data = get_client_weather(request)

    if weather_data:
        # 保存到session
        request.session['weather_data'] = weather_data
        request.session['weather_last_update'] = datetime.now().isoformat()

    return {
        'weather': weather_data,
    }


def format_date(value, format_string='Y年m月d日 H:i'):
    """
    日期格式化工具函数
    """
    if hasattr(value, 'strftime'):
        return value.strftime(format_string.replace('Y', '%Y').replace('m', '%m')
                              .replace('d', '%d').replace('H', '%H')
                              .replace('i', '%M').replace('s', '%S'))
    return value


def calculate_read_time(content, words_per_minute=200):
    """
    计算阅读时间
    """
    if not content:
        return 0

    # 简单估算：中文按字符数，英文按单词数
    chinese_chars = sum(1 for char in content if '\u4e00' <= char <= '\u9fff')
    english_words = len(content.split()) - chinese_chars

    # 估算总单词数（假设每个中文字符相当于一个单词）
    total_words = chinese_chars + english_words
    minutes = total_words / words_per_minute

    return max(1, int(minutes))  # 最少1分钟


def get_client_ip(request):
    """
    获取客户端IP地址
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
