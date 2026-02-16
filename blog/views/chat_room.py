from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from ..models import ChatRoom


@login_required
def chat_room(request, room_slug):
    room = get_object_or_404(ChatRoom, slug=room_slug)
    return render(request, 'blog/chat_room.html', {'room': room})
