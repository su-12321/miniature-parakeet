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
def api_private_messages(request, user_id):
    """获取私聊消息（支持分页和增量获取）"""
    other_user = get_object_or_404(User, pk=user_id)

    # 获取会话
    try:
        session = PrivateChatSession.objects.get(
            (Q(user1=request.user) & Q(user2=other_user)) |
            (Q(user1=other_user) & Q(user2=request.user))
        )
    except PrivateChatSession.DoesNotExist:
        return JsonResponse({'messages': []})

    # 获取最后消息ID（增量）
    last_id = request.GET.get('last_id')
    messages_qs = session.messages.all()
    if last_id:
        try:
            messages_qs = messages_qs.filter(id__gt=int(last_id))
        except ValueError:
            pass

    # 限制返回数量（例如50条）
    messages_qs = messages_qs.order_by('created_at')[:50]

    # 标记未读为已读（并处理阅后即焚）
    unread_messages = messages_qs.filter(receiver=request.user, is_read=False)
    for msg in unread_messages:
        msg.mark_as_read()  # 内部会触发阅后即焚销毁

    # 构造返回数据
    messages_data = []
    for msg in messages_qs:
        msg_data = {
            'id': msg.id,
            'sender_id': msg.sender.id,
            'sender_username': msg.sender.username,
            'encryption_type': msg.encryption_type,
            'is_burn_after_reading': msg.is_burn_after_reading,
            'burn_at': msg.burn_at.isoformat() if msg.burn_at else None,
            'destroyed_at': msg.destroyed_at.isoformat() if msg.destroyed_at else None,
            'is_read': msg.is_read,
            'read_at': msg.read_at.isoformat() if msg.read_at else None,
            'created_at': msg.created_at.isoformat(),
        }

        # 根据加密类型返回内容字段
        if msg.destroyed_at:
            msg_data['content'] = None  # 已销毁，无内容
        elif msg.encryption_type == 'system':
            # 系统加密：解密后返回明文
            try:
                msg_data['content'] = msg.get_system_content()
            except:
                msg_data['content'] = None
        else:
            # 自定义加密：返回base64编码的密文
            if msg.encrypted_content:
                import base64
                msg_data['content'] = base64.b64encode(msg.encrypted_content).decode('ascii')
            else:
                msg_data['content'] = None

        messages_data.append(msg_data)

    # 获取未读总数
    total_unread = PrivateMessage.objects.filter(
        receiver=request.user,
        is_read=False
    ).count()

    return JsonResponse({
        'messages': messages_data,
        'total_unread': total_unread,
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

from django.utils.dateparse import parse_datetime

@csrf_exempt
@login_required
def api_send_private_message(request, user_id):
    if request.method != 'POST':
        return JsonResponse({'error': '只支持POST请求'}, status=400)

    other_user = get_object_or_404(User, pk=user_id)
    if other_user == request.user:
        return JsonResponse({'error': '不能给自己发送消息'}, status=400)

    try:
        data = json.loads(request.body)
        encryption_type = data.get('encryption_type', 'system')
        content = data.get('content', '').strip()
        is_burn = data.get('is_burn_after_reading', False)
        burn_at_str = data.get('burn_at', None)

        if not content:
            return JsonResponse({'error': '消息内容不能为空'}, status=400)

        if encryption_type not in ['system', 'custom']:
            return JsonResponse({'error': '无效的加密类型'}, status=400)

        # 解析定时销毁时间
        burn_at = None
        if burn_at_str:
            burn_at = parse_datetime(burn_at_str)
            if burn_at is None:
                return JsonResponse({'error': '无效的定时销毁时间格式'}, status=400)
            if burn_at <= timezone.now():
                return JsonResponse({'error': '定时销毁时间必须晚于当前时间'}, status=400)

        # 获取或创建会话
        session, created = PrivateChatSession.objects.get_or_create(
            user1=request.user if request.user.id < other_user.id else other_user,
            user2=other_user if request.user.id < other_user.id else request.user,
            defaults={'is_active': True}
        )

        message = PrivateMessage(
            session=session,
            sender=request.user,
            receiver=other_user,
            encryption_type=encryption_type,
            is_burn_after_reading=is_burn,
            burn_at=burn_at,
        )

        if encryption_type == 'system':
            message.set_system_content(content)
        else:
            import base64
            try:
                message.encrypted_content = base64.b64decode(content)
            except:
                return JsonResponse({'error': '自定义加密内容必须是有效的Base64'}, status=400)

        message.save()
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