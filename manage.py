"""Django's command-line utility for administrative tasks."""
import os
import sys

# ========== 添加这三行代码 ==========
# 获取当前目录（E:\pythonProject-1\）
current_dir = os.path.dirname(os.path.abspath(__file__))
# 将 myblog 目录添加到 Python 路径
sys.path.insert(0, os.path.join(current_dir, 'myblog'))
# ==================================

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myblog.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()