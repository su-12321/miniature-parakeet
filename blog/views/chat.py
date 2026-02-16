"""
聊天功能视图
处理实时聊天功能
"""

import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from ..models import ChatMessage  # 导入模型

# 内存存储已不再需要，可以删除或保留（但不使用）
# chat_messages = []
# MAX_MESSAGES = 60

@login_required
def chat_view(request):
    """
    聊天室视图
    """
    # 已重定向到新版聊天室
    return redirect('chat_room', room_slug='general')

@login_required
def chat_messages_api(request):
    """
    API: 获取聊天消息（从数据库读取）
    """
    # 获取最近50条消息，按时间正序返回
    messages = ChatMessage.objects.all().order_by('-timestamp')[:50]
    messages = list(reversed(messages))  # 转为正序

    messages_data = []
    for msg in messages:
        messages_data.append({
            'id': msg.id,
            'user_id': msg.user.id,
            'username': msg.user.username,
            'content': msg.get_content(),  # 解密内容
            'timestamp': timezone.localtime(msg.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
        })

    return JsonResponse({
        'messages': messages_data,
        'count': len(messages_data),
    })

@csrf_exempt
@login_required
def send_message_api(request):
    """
    API: 发送聊天消息（此功能已由 WebSocket 接管，可保留为空或返回提示）
    """
    return JsonResponse({'error': '请使用新版聊天室发送消息'}, status=400)