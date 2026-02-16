#!/usr/bin/env bash
# build.sh

echo "=== 开始构建 Django 应用 ==="

# 安装依赖
pip install -r requirements.txt

# 收集静态文件
python manage.py collectstatic --noinput

# 迁移数据库（如果需要，但注意Render在部署时会自动运行startCommand，这里也可以不迁移，放在启动命令中）
# python manage.py migrate

echo "=== 构建完成 ==="