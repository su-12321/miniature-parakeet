from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from myblog.blog.models import UserProfile
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = '管理用户状态（封禁/解封/警告）'

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='command', required=True, help='子命令')

        # 封禁用户
        ban_parser = subparsers.add_parser('ban', help='封禁用户')
        ban_parser.add_argument('username', help='用户名')
        ban_parser.add_argument('--days', type=int, default=7, help='封禁天数，默认7天')
        ban_parser.add_argument('--reason', default='违反社区规则', help='封禁原因')
        ban_parser.add_argument('--permanent', action='store_true', help='永久封禁')

        # 解封用户
        unban_parser = subparsers.add_parser('unban', help='解封用户')
        unban_parser.add_argument('username', help='用户名')

        # 禁言用户
        mute_parser = subparsers.add_parser('mute', help='禁言用户')
        mute_parser.add_argument('username', help='用户名')
        mute_parser.add_argument('--hours', type=int, default=24, help='禁言小时数，默认24小时')
        mute_parser.add_argument('--reason', default='发布不当内容', help='禁言原因')

        # 警告用户
        warn_parser = subparsers.add_parser('warn', help='警告用户')
        warn_parser.add_argument('username', help='用户名')
        warn_parser.add_argument('--reason', required=True, help='警告原因')

        # 查看用户状态
        status_parser = subparsers.add_parser('status', help='查看用户状态')
        status_parser.add_argument('username', help='用户名')

        # 查看被封禁用户列表
        banned_parser = subparsers.add_parser('list-banned', help='查看所有被封禁用户')
        banned_parser.add_argument('--all', action='store_true', help='显示所有用户状态')

        # 查看被禁言用户列表
        muted_parser = subparsers.add_parser('list-muted', help='查看所有被禁言用户')

    def handle(self, *args, **options):
        command = options['command']

        if command == 'ban':
            self.ban_user(options)
        elif command == 'unban':
            self.unban_user(options)
        elif command == 'mute':
            self.mute_user(options)
        elif command == 'warn':
            self.warn_user(options)
        elif command == 'status':
            self.show_status(options)
        elif command == 'list-banned':
            self.list_banned_users(options)
        elif command == 'list-muted':
            self.list_muted_users(options)

    def get_user_profile(self, username):
        """获取用户和对应的UserProfile"""
        try:
            user = User.objects.get(username=username)
            profile, created = UserProfile.objects.get_or_create(user=user)
            return user, profile, created
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'用户 {username} 不存在'))
            return None, None, None

    def ban_user(self, options):
        user, profile, created = self.get_user_profile(options['username'])
        if not user:
            return

        if options['permanent']:
            profile.ban_until = None
            self.stdout.write(self.style.WARNING(f'永久封禁用户: {user.username}'))
        else:
            profile.ban_until = timezone.now() + timedelta(days=options['days'])
            self.stdout.write(self.style.SUCCESS(
                f"封禁用户 {user.username} {options['days']} 天，直到 {profile.ban_until.strftime('%Y-%m-%d %H:%M:%S')}"
            ))

        profile.is_banned = True
        profile.ban_reason = options['reason']
        profile.last_warning = f"被封禁：{options['reason']} - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        profile.save()

        # 禁言状态也解除（如果存在）
        if hasattr(profile, 'is_muted'):
            profile.is_muted = False
            profile.mute_until = None
            profile.save()

    def unban_user(self, options):
        user, profile, created = self.get_user_profile(options['username'])
        if not user:
            return

        if not profile.is_banned:
            self.stdout.write(self.style.WARNING(f'用户 {user.username} 未被封禁'))
            return

        profile.is_banned = False
        profile.ban_until = None
        profile.ban_reason = ''
        profile.save()

        self.stdout.write(self.style.SUCCESS(f'已解封用户: {user.username}'))

    def mute_user(self, options):
        user, profile, created = self.get_user_profile(options['username'])
        if not user:
            return

        # 检查用户是否已经被封禁
        if profile.is_banned:
            self.stdout.write(self.style.WARNING(f'用户 {user.username} 已被封禁，无法禁言'))
            return

        # 确保UserProfile有mute相关字段
        if not hasattr(profile, 'is_muted'):
            self.stdout.write(self.style.ERROR('UserProfile 模型没有禁言相关字段'))
            return

        profile.is_muted = True
        profile.mute_until = timezone.now() + timedelta(hours=options['hours'])
        profile.mute_reason = options['reason']
        profile.last_warning = f"被禁言：{options['reason']} - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        profile.save()

        self.stdout.write(self.style.SUCCESS(
            f"禁言用户 {user.username} {options['hours']} 小时，直到 {profile.mute_until.strftime('%Y-%m-%d %H:%M:%S')}"
        ))

    def warn_user(self, options):
        user, profile, created = self.get_user_profile(options['username'])
        if not user:
            return

        # 记录警告
        warning_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        if hasattr(profile, 'warnings'):
            # 如果UserProfile有warnings字段（假设是JSONField或TextField）
            warnings = profile.warnings if profile.warnings else []
            warnings.append({
                'reason': options['reason'],
                'time': warning_time
            })
            profile.warnings = warnings
        else:
            # 使用last_warning字段
            profile.last_warning = f"警告：{options['reason']} - {warning_time}"

        profile.save()

        # 检查警告次数，达到3次自动封禁
        warning_count = self.get_warning_count(profile)
        if warning_count >= 3:
            profile.is_banned = True
            profile.ban_reason = f'收到{warning_count}次警告，自动封禁'
            profile.ban_until = timezone.now() + timedelta(days=7)
            profile.save()
            self.stdout.write(self.style.WARNING(
                f'用户 {user.username} 已收到{warning_count}次警告，自动封禁7天'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'已警告用户 {user.username}，原因：{options["reason"]}，总警告次数：{warning_count}'
            ))

    def get_warning_count(self, profile):
        """获取用户警告次数"""
        if hasattr(profile, 'warnings') and profile.warnings:
            return len(profile.warnings)
        elif hasattr(profile, 'warning_count'):
            return profile.warning_count or 0
        return 0

    def show_status(self, options):
        user, profile, created = self.get_user_profile(options['username'])
        if not user:
            return

        self.stdout.write(self.style.SUCCESS(f'=== 用户状态: {user.username} ==='))
        self.stdout.write(f'用户ID: {user.id}')
        self.stdout.write(f'邮箱: {user.email}')
        self.stdout.write(f'注册时间: {user.date_joined.strftime("%Y-%m-%d %H:%M:%S")}')
        self.stdout.write(
            f'最后登录: {user.last_login.strftime("%Y-%m-%d %H:%M:%S") if user.last_login else "从未登录"}')

        self.stdout.write(f'\n--- 封禁状态 ---')
        if profile.is_banned:
            if profile.ban_until:
                if profile.ban_until > timezone.now():
                    self.stdout.write(
                        self.style.ERROR(f'封禁中，直到: {profile.ban_until.strftime("%Y-%m-%d %H:%M:%S")}'))
                else:
                    self.stdout.write(
                        self.style.WARNING(f'封禁已过期: {profile.ban_until.strftime("%Y-%m-%d %H:%M:%S")}'))
            else:
                self.stdout.write(self.style.ERROR('永久封禁'))
            self.stdout.write(f'封禁原因: {profile.ban_reason}')
        else:
            self.stdout.write(self.style.SUCCESS('正常'))

        if hasattr(profile, 'is_muted'):
            self.stdout.write(f'\n--- 禁言状态 ---')
            if profile.is_muted and profile.mute_until:
                if profile.mute_until > timezone.now():
                    self.stdout.write(
                        self.style.WARNING(f'禁言中，直到: {profile.mute_until.strftime("%Y-%m-%d %H:%M:%S")}'))
                else:
                    self.stdout.write(self.style.SUCCESS('禁言已过期'))
            else:
                self.stdout.write(self.style.SUCCESS('正常'))

        self.stdout.write(f'\n--- 警告信息 ---')
        if hasattr(profile, 'last_warning') and profile.last_warning:
            self.stdout.write(f'最后警告: {profile.last_warning}')

        warning_count = self.get_warning_count(profile)
        self.stdout.write(f'总警告次数: {warning_count}')

    def list_banned_users(self, options):
        if options.get('all'):
            profiles = UserProfile.objects.all().select_related('user')
            title = '所有用户状态'
        else:
            profiles = UserProfile.objects.filter(is_banned=True).select_related('user')
            title = '被封禁用户列表'

        self.stdout.write(self.style.SUCCESS(f'=== {title} ==='))

        for profile in profiles:
            status = "封禁" if profile.is_banned else "正常"
            if profile.is_banned:
                if profile.ban_until:
                    status += f" ({profile.ban_until.strftime('%Y-%m-%d %H:%M')})"
                else:
                    status += " (永久)"

            self.stdout.write(f'{profile.user.username:20} | {status:20} | {profile.ban_reason or "无"}')

    def list_muted_users(self, options):
        if not hasattr(UserProfile, 'is_muted'):
            self.stdout.write(self.style.ERROR('UserProfile 模型没有禁言相关字段'))
            return

        profiles = UserProfile.objects.filter(is_muted=True, mute_until__gt=timezone.now()).select_related('user')

        self.stdout.write(self.style.SUCCESS('=== 被禁言用户列表 ==='))

        for profile in profiles:
            remaining = profile.mute_until - timezone.now()
            hours_remaining = int(remaining.total_seconds() / 3600)
            minutes_remaining = int((remaining.total_seconds() % 3600) / 60)

            self.stdout.write(
                f'{profile.user.username:20} | 直到: {profile.mute_until.strftime("%Y-%m-%d %H:%M")} | 剩余: {hours_remaining}小时{minutes_remaining}分钟 | 原因: {getattr(profile, "mute_reason", "无")}')
