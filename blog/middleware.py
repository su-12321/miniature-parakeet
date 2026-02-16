"""
自定义中间件
包含访问统计中间件
"""

import time
from django.utils.deprecation import MiddlewareMixin
from .models import VisitStatistics
from .utils import get_client_ip

# middleware/public_ip_middleware.py
import json
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache


class ClientPublicIPMiddleware(MiddlewareMixin):
    """
    获取客户端公网IP的中间件
    优先级：前端上报 > HTTP头 > 真实IP
    """

    def process_request(self, request):
        # 方法1: 从前端上报的header中获取
        client_ip = request.headers.get('X-Client-Public-IP')

        # 方法2: 从cookie中获取（前端设置的）
        if not client_ip:
            client_ip = request.COOKIES.get('client_public_ip')

        # 方法3: 从POST数据中获取（前端ajax上报）
        if not client_ip and request.method == 'POST':
            try:
                if request.content_type == 'application/json':
                    body = json.loads(request.body.decode('utf-8'))
                    client_ip = body.get('client_public_ip')
                else:
                    client_ip = request.POST.get('client_public_ip')
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        # 方法4: 从代理头获取（如果配置了反向代理）
        if not client_ip:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                # 取第一个IP（客户端真实IP）
                client_ip = x_forwarded_for.split(',')[0].strip()

        # 方法5: 获取真实IP
        if not client_ip:
            client_ip = request.META.get('REMOTE_ADDR')

        # 如果是内网地址，尝试从缓存中获取之前上报的公网IP
        if self._is_private_ip(client_ip):
            session_key = request.session.session_key
            if session_key:
                cache_key = f'client_public_ip_{session_key}'
                cached_ip = cache.get(cache_key, None)
                if cached_ip:
                    client_ip = cached_ip
            else:
                # 尝试从用户代理字符串中提取session信息
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                # 这里可以添加更多逻辑来关联用户

        # 存储到request对象中
        request.client_public_ip = client_ip

        # 如果是前端上报的IP，缓存起来
        if request.method == 'POST' and 'report_ip' in request.path:
            # 这个会在view中处理
            pass

        return None

    def _is_private_ip(self, ip):
        """检查是否为私有IP地址"""
        if not ip:
            return False

        # IPv4私有地址范围
        private_ranges = [
            ('10.0.0.0', '10.255.255.255'),
            ('172.16.0.0', '172.31.255.255'),
            ('192.168.0.0', '192.168.255.255'),
            ('127.0.0.0', '127.255.255.255'),
            ('169.254.0.0', '169.254.255.255'),  # 链路本地
        ]

        # IPv6私有地址
        if ':' in ip:
            return ip.lower().startswith(('fc', 'fd', 'fe80::', '::1'))

        # 检查IPv4
        from ipaddress import ip_address, IPv4Address
        try:
            ip_obj = ip_address(ip)
            if isinstance(ip_obj, IPv4Address):
                ip_num = int(ip_obj)
                for start, end in private_ranges:
                    start_num = int(ip_address(start))
                    end_num = int(ip_address(end))
                    if start_num <= ip_num <= end_num:
                        return True
        except ValueError:
            pass

        return False


# 工具函数，可以在任何地方调用
def get_client_public_ip(request):
    """获取客户端公网IP的辅助函数"""
    if hasattr(request, 'client_public_ip'):
        return request.client_public_ip

    # 如果没有中间件，尝试直接获取
    ip = request.META.get('HTTP_X_CLIENT_PUBLIC_IP') or \
         request.COOKIES.get('client_public_ip') or \
         request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or \
         request.META.get('REMOTE_ADDR')

    return ip

class VisitStatisticsMiddleware(MiddlewareMixin):
    """
    访问统计中间件
    记录每个请求的访问信息
    """

    def process_request(self, request):
        """在请求开始时记录时间"""
        request.start_time = time.time()

    def process_response(self, request, response):
        """在响应时记录访问统计"""
        # 排除管理后台和静态文件
        if request.path.startswith('/admin/') or request.path.startswith('/static/'):
            return response

        # 排除API请求（可选）
        if request.path.startswith('/api/'):
            return response

        try:
            # 计算响应时间
            response_time = 0
            if hasattr(request, 'start_time'):
                response_time = time.time() - request.start_time

            # 获取客户端信息
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')

            # 记录访问统计
            VisitStatistics.objects.create(
                ip_address=ip_address,
                user_agent=user_agent[:500],  # 限制长度
                path=request.path[:500],
                method=request.method,
                status_code=response.status_code,
            )

        except Exception as e:
            # 记录日志但不影响正常请求
            print(f"记录访问统计失败: {e}")

        return response

    def process_exception(self, request, exception):
        """处理异常请求"""
        try:
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')

            VisitStatistics.objects.create(
                ip_address=ip_address,
                user_agent=user_agent[:500],
                path=request.path[:500],
                method=request.method,
                status_code=500,  # 服务器错误
            )
        except:
            pass

        return None
