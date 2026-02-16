# blog/views/private_chat.py

import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count, Max
from django.utils import timezone
from datetime import datetime, timedelta

from ..models import PrivateChatSession, PrivateMessage
from ..forms_private_chat import PrivateMessageForm, UserSearchForm


@login_required
def private_chat_detail_view(request, user_id):
    other_user = get_object_or_404(User, pk=user_id)
    return render(request, 'blog/private_chat_detail.html', {'other_user': other_user})


@login_required
def private_chat_list_view(request):
    """私聊会话列表视图"""
    # 获取用户的私聊会话
    sessions = PrivateChatSession.objects.filter(
        Q(user1=request.user) | Q(user2=request.user),
        is_active=True
    ).annotate(
        last_message_time=Max('messages__created_at'),
        unread_count=Count('messages', filter=Q(
            messages__receiver=request.user,
            messages__is_read=False
        ))
    ).order_by('-last_message_time')

    # 为每个会话添加另一个用户的信息
    for session in sessions:
        if session.user1 == request.user:
            session.other_user = session.user2
        else:
            session.other_user = session.user1

    # 搜索表单
    search_form = UserSearchForm(request.GET or None)
    search_results = []

    if search_form.is_valid():
        username = search_form.cleaned_data['username']
        if username:
            search_results = User.objects.filter(
                username__icontains=username
            ).exclude(id=request.user.id)[:10]

    context = {
        'sessions': sessions,
        'search_form': search_form,
        'search_results': search_results,
    }
    return render(request, 'blog/private_chat_list.html', context)


@login_required
def start_private_chat_view(request, user_id):
    """开始私聊视图（重定向到私聊详情）"""
    other_user = get_object_or_404(User, pk=user_id)

    # 检查是否可以发起私聊（不能给自己发消息）
    if other_user == request.user:
        return redirect('private_chat_list')

    return redirect('private_chat_detail', user_id=user_id)


@login_required
def api_private_messages(request, user_id):
    """API: 获取私聊消息（用于实时更新）"""
    other_user = get_object_or_404(User, pk=user_id)

    # 获取会话
    try:
        session = PrivateChatSession.objects.get(
            Q(user1=request.user, user2=other_user) |
            Q(user1=other_user, user2=request.user)
        )
    except PrivateChatSession.DoesNotExist:
        return JsonResponse({'error': '会话不存在'}, status=404)

    # 获取最后消息ID（用于增量获取）
    last_id = request.GET.get('last_id')

    # 构建查询
    messages_query = session.messages.all()

    if last_id:
        try:
            messages_query = messages_query.filter(id__gt=int(last_id))
        except ValueError:
            pass

    # 限制消息数量
    messages = messages_query.order_by('created_at')

    # 标记未读消息为已读
    unread_messages = messages.filter(
        receiver=request.user,
        is_read=False
    )

    for msg in unread_messages:
        msg.mark_as_read()

    # 序列化消息
    messages_data = []
    for msg in messages:
        messages_data.append({
            'id': msg.id,
            'sender_id': msg.sender.id,
            'sender_username': msg.sender.username,
            'content': msg.get_content(),
            'created_at': msg.created_at.isoformat(),
            'is_own': msg.sender == request.user,
        })

    # 获取未读消息总数
    total_unread = PrivateMessage.objects.filter(
        receiver=request.user,
        is_read=False
    ).count()

    return JsonResponse({
        'messages': messages_data,
        'total_unread': total_unread,
        'session_id': session.id,
    })


@csrf_exempt
@login_required
def api_send_private_message(request, user_id):
    """API: 发送私聊消息"""
    if request.method != 'POST':
        return JsonResponse({'error': '只支持POST请求'}, status=400)

    other_user = get_object_or_404(User, pk=user_id)

    # 检查是否可以发送消息
    if other_user == request.user:
        return JsonResponse({'error': '不能给自己发送消息'}, status=400)

    try:
        data = json.loads(request.body)
        content = data.get('content', '').strip()

        if not content:
            return JsonResponse({'error': '消息内容不能为空'}, status=400)

        if len(content) > 1000:
            return JsonResponse({'error': '消息内容过长'}, status=400)

        # 获取或创建会话
        session, created = PrivateChatSession.objects.get_or_create(
            user1=request.user if request.user.id < other_user.id else other_user,
            user2=other_user if request.user.id < other_user.id else request.user,
            defaults={'is_active': True}
        )

        # 创建消息
        message = PrivateMessage.objects.create(
            session=session,
            sender=request.user,
            receiver=other_user,
            content=content
        )

        # 更新会话时间
        session.updated_at = timezone.now()
        session.save()

        return JsonResponse({
            'success': True,
            'message_id': message.id,
            'created_at': message.created_at.isoformat(),
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': '无效的JSON数据'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_private_chat_summary(request):
    """API: 获取私聊摘要信息（用于导航栏显示）"""
    # 获取未读消息总数
    total_unread = PrivateMessage.objects.filter(
        receiver=request.user,
        is_read=False
    ).count()

    # 获取最近活跃的会话
    recent_sessions = PrivateChatSession.objects.filter(
        Q(user1=request.user) | Q(user2=request.user),
        is_active=True
    ).annotate(
        last_message_time=Max('messages__created_at'),
        unread_count=Count('messages', filter=Q(
            messages__receiver=request.user,
            messages__is_read=False
        ))
    ).order_by('-last_message_time')[:5]

    sessions_data = []
    for session in recent_sessions:
        other_user = session.other_user(request.user)
        last_message = session.messages.last()

        sessions_data.append({
            'user_id': other_user.id,
            'username': other_user.username,
            'unread_count': session.unread_count,
            'last_message': last_message.content[:50] + '...' if last_message and len(last_message.content) > 50 else
            last_message.content if last_message else '',
            'last_message_time': last_message.created_at.isoformat() if last_message else None,
        })

    return JsonResponse({
        'total_unread': total_unread,
        'recent_sessions': sessions_data,
    })


@login_required
def api_mark_all_as_read(request):
    """API: 标记所有消息为已读"""
    if request.method != 'POST':
        return JsonResponse({'error': '只支持POST请求'}, status=400)

    # 标记当前用户的所有未读消息为已读
    unread_messages = PrivateMessage.objects.filter(
        receiver=request.user,
        is_read=False
    )

    updated_count = unread_messages.count()

    for msg in unread_messages:
        msg.mark_as_read()

    return JsonResponse({
        'success': True,
        'updated_count': updated_count,
    })
