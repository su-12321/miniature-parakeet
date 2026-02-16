"""
博客应用的路由配置
"""
from blog import consumers
from blog.views import chat_room
from . import views
from django.urls import path, include

urlpatterns = [
    # 核心功能
    path('', views.home_view, name='home'),
    path('post/<int:pk>/', views.post_detail_view, name='post_detail'),
    path('post/create/', views.post_create_view, name='post_create'),
    path('post/<int:pk>/edit/', views.post_edit_view, name='post_edit'),
    path('post/<int:pk>/delete/', views.post_delete_view, name='post_delete'),
    path('my-posts/', views.my_posts_view, name='my_posts'),
    path('category/<int:category_id>/', views.category_posts_view, name='category_posts'),
    path('tag/<int:tag_id>/', views.tag_posts_view, name='tag_posts'),
    path('public-posts/', views.public_posts_view, name='public_posts'),

    # 认证功能
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),

    # 统计功能
    path('statistics/', views.statistics_view, name='statistics'),
    path('api/visit-stats/', views.api_visit_stats, name='api_visit_stats'),

    # 聊天功能
    path('chat/', views.chat_view, name='chat'),
    path('api/chat/messages/', views.chat_messages_api, name='chat_messages_api'),
    path('api/chat/send/', views.send_message_api, name='send_message_api'),
    path('chat/<slug:room_slug>/', chat_room.chat_room, name='chat_room'),

    path('api/weather/refresh/', views.WeatherRefreshView.as_view(), name='refresh_weather'),

    # 私聊功能
    path('private-chat/', views.private_chat_list_view, name='private_chat_list'),
    path('private-chat/start/<int:user_id>/', views.start_private_chat_view, name='start_private_chat'),
    path('private-chat/<int:user_id>/', views.private_chat_detail_view, name='private_chat_detail'),

    # 私聊API
    # TODO
    path('api/private-chat/summary/', views.api_private_chat_summary, name='api_private_chat_summary'),
    path('api/private-chat/messages/<int:user_id>/', views.api_private_messages, name='api_private_messages'),
    path('api/private-chat/send/<int:user_id>/', views.api_send_private_message, name='api_send_private_message'),
    path('api/private-chat/mark-all-read/', views.api_mark_all_as_read, name='api_mark_all_as_read'),
    path('markdown-preview/', views.markdown_preview, name='markdown_preview'),

    # 公告板URL
    path('bulletin/', views.bulletin_list, name='bulletin_list'),
    path('bulletin/<int:pk>/', views.bulletin_detail, name='bulletin_detail'),
    path('bulletin/create/', views.bulletin_create, name='bulletin_create'),
    path('bulletin/<int:pk>/edit/', views.bulletin_update, name='bulletin_update'),
    path('bulletin/<int:pk>/delete/', views.bulletin_delete, name='bulletin_delete'),

    # 头像和用户资料URL
    path('profile/', views.profile_view, name='profile_view'),
    path('profile/avatar/', views.avatar_upload, name='avatar_upload'),
    path('profile/avatar/update/', views.avatar_update, name='avatar_update'),
    path('profile/avatar/reset/', views.avatar_reset, name='avatar_reset'),
]
