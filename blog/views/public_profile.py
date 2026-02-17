from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from ..models import UserProfile

def public_profile_view(request, username):
    """公开的个人资料页"""
    user = get_object_or_404(User, username=username)
    profile = get_object_or_404(UserProfile, user=user)
    context = {
        'profile_user': user,
        'profile': profile,
    }
    return render(request, 'blog/public_profile.html', context)
