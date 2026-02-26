#!/usr/bin/env bash
# build.sh

echo "=== 开始构建 Django 应用 ==="

# 安装依赖
pip install -r requirements.txt

# 收集静态文件
python manage.py collectstatic --noinput

# 迁移数据库
# python manage.py migrate



echo "=== 构建完成 ==="
echo "=== 如果有人问，就说不知道 ==="
