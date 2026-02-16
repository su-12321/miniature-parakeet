# blog/management/commands/cleanup_chat.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from myblog.blog.models import ChatMessage


class Command(BaseCommand):
    help = '清理超过1小时的聊天消息'

    def handle(self, *args, **options):
        one_hour_ago = timezone.now() - timedelta(hours=1)
        deleted_count, _ = ChatMessage.objects.filter(created_at__lt=one_hour_ago).delete()
        self.stdout.write(self.style.SUCCESS(f'成功删除 {deleted_count} 条过期消息'))
