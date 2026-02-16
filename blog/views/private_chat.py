# blog/views/private_chat.py

import json
import base64
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count, Max
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from cryptography.fernet import InvalidToken
from ..models import PrivateChatSession, PrivateMessage
from ..forms_private_chat import UserSearchForm

logger = logging.getLogger(__name__)

# ---------- 页面视图 ----------

@login_required
def private_chat_detail_view(request, user_id):
    """私聊详情页"""
    other_user = get_object_or_404(User, pk=user_id)
    return render(request, 'blog/private_chat_detail.html', {'other_user': other_user})

@login_required
def private_chat_list_view(request):
    """私聊会话列表页"""
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

    for session in sessions:
        session.other_user = session.user1 if session.user2 == request.user else session.user2

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
    """开始私聊（重定向到详情页）"""
    other_user = get_object_or_404(User, pk=user_id)
    if other_user == request.user:
        return redirect('private_chat_list')
    return redirect('private_chat_detail', user_id=user_id)

# ---------- API 视图 ----------

@login_required
def api_private_messages(request, user_id):
    try:
        other_user = get_object_or_404(User, pk=user_id)

        # 确保会话存在（user1 < user2）
        user1, user2 = sorted([request.user, other_user], key=lambda u: u.id)
        session, _ = PrivateChatSession.objects.get_or_create(
            user1=user1,
            user2=user2,
            defaults={'is_active': True}
        )

        last_id = request.GET.get('last_id')
        messages_qs = session.messages.all()
        if last_id:
            try:
                messages_qs = messages_qs.filter(id__gt=int(last_id))
            except ValueError:
                pass

        # 标记未读（在切片前）
        unread = messages_qs.filter(receiver=request.user, is_read=False)
        for msg in unread:
            msg.mark_as_read()

        # 切片获取最近50条
        messages_qs = messages_qs.order_by('created_at')[:50]

        messages_data = []
        for msg in messages_qs:
            content = None
            if msg.destroyed_at:
                content = "[消息已销毁]"
            elif msg.encryption_type == 'system':
                try:
                    content = msg.get_system_content()
                except InvalidToken:
                    content = "[解密失败]"
                except Exception as e:
                    logger.error(f"系统解密异常: {e}, msg_id={msg.id}")
                    content = "[解密错误]"
            else:  # custom
                if msg.encrypted_content:
                    try:
                        content = base64.b64encode(msg.encrypted_content).decode('ascii')
                    except Exception as e:
                        logger.error(f"Base64编码异常: {e}, msg_id={msg.id}")
                        content = None
                else:
                    content = None

            messages_data.append({
                'id': msg.id,
                'sender_id': msg.sender.id,
                'sender_username': msg.sender.username,
                'content': content,
                'encryption_type': msg.encryption_type,
                'is_burn_after_reading': msg.is_burn_after_reading,
                'burn_at': msg.burn_at.isoformat() if msg.burn_at else None,
                'destroyed_at': msg.destroyed_at.isoformat() if msg.destroyed_at else None,
                'is_read': msg.is_read,
                'read_at': msg.read_at.isoformat() if msg.read_at else None,
                'created_at': msg.created_at.isoformat(),
            })

        total_unread = PrivateMessage.objects.filter(
            receiver=request.user,
            is_read=False
        ).count()

        return JsonResponse({'messages': messages_data, 'total_unread': total_unread})

    except Exception as e:
        logger.exception(f"获取私聊消息未预期异常: {e}, user_id={user_id}")
        return JsonResponse({'error': '服务器内部错误'}, status=500)

@csrf_exempt
@login_required
def api_send_private_message(request, user_id):
    """发送私聊消息"""
    if request.method != 'POST':
        return JsonResponse({'error': '只支持 POST 请求'}, status=405)

    other_user = get_object_or_404(User, pk=user_id)
    if other_user == request.user:
        return JsonResponse({'error': '不能给自己发送消息'}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': '无效的 JSON 数据'}, status=400)

    encryption_type = data.get('encryption_type', 'system')
    content = data.get('content', '').strip()
    is_burn = data.get('is_burn_after_reading', False)
    burn_at_str = data.get('burn_at', None)

    if not content:
        return JsonResponse({'error': '消息内容不能为空'}, status=400)

    # 明文长度限制（统一 500 字符）
    MAX_PLAIN_LENGTH = 500
    if encryption_type == 'system':
        if len(content) > MAX_PLAIN_LENGTH:
            return JsonResponse({'error': f'消息内容不能超过 {MAX_PLAIN_LENGTH} 字符'}, status=400)
    else:  # custom
        try:
            decoded = base64.b64decode(content, validate=True)
        except (base64.binascii.Error, TypeError):
            return JsonResponse({'error': '自定义加密内容必须是有效的 Base64'}, status=400)
        if len(decoded) > MAX_PLAIN_LENGTH * 4:
            return JsonResponse({'error': '加密内容过长'}, status=400)

    # 解析定时销毁时间
    burn_at = None
    if burn_at_str:
        burn_at = parse_datetime(burn_at_str)
        if burn_at is None:
            return JsonResponse({'error': '无效的定时销毁时间格式'}, status=400)
        if burn_at <= timezone.now():
            return JsonResponse({'error': '定时销毁时间必须晚于当前时间'}, status=400)

    # 获取或创建会话（确保 user1 < user2）
    user1, user2 = sorted([request.user, other_user], key=lambda u: u.id)
    session, created = PrivateChatSession.objects.get_or_create(
        user1=user1,
        user2=user2,
        defaults={'is_active': True}
    )

    # 创建消息对象
    message = PrivateMessage(
        session=session,
        sender=request.user,
        receiver=other_user,
        encryption_type=encryption_type,
        is_burn_after_reading=is_burn,
        burn_at=burn_at,
    )

    try:
        if encryption_type == 'system':
            message.set_system_content(content)
        else:
            # 使用模型方法（需确保模型中已定义 set_custom_content）
            message.set_custom_content(content)
        message.save()
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.exception("消息保存失败")
        return JsonResponse({'error': '消息保存失败'}, status=500)

    # 更新会话时间
    session.updated_at = timezone.now()
    session.save(update_fields=['updated_at'])

    return JsonResponse({
        'success': True,
        'message_id': message.id,
        'created_at': message.created_at.isoformat(),
    })

@login_required
def api_mark_all_as_read(request):
    """标记所有消息为已读"""
    if request.method != 'POST':
        return JsonResponse({'error': '只支持 POST 请求'}, status=405)

    unread = PrivateMessage.objects.filter(receiver=request.user, is_read=False)
    count = unread.count()
    for msg in unread:
        msg.mark_as_read()
    return JsonResponse({'success': True, 'updated_count': count})

@login_required
def api_private_chat_summary(request):
    """获取私聊摘要（用于导航栏）"""
    total_unread = PrivateMessage.objects.filter(
        receiver=request.user,
        is_read=False
    ).count()

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
        other_user = session.user1 if session.user2 == request.user else session.user2
        last_message = session.messages.last()
        sessions_data.append({
            'user_id': other_user.id,
            'username': other_user.username,
            'unread_count': session.unread_count,
            'last_message': last_message.get_preview() if last_message else '',
            'last_message_time': last_message.created_at.isoformat() if last_message else None,
        })

    return JsonResponse({
        'total_unread': total_unread,
        'recent_sessions': sessions_data,
    })


