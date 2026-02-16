# MyBlog - Django 博客系统

一个功能完整的 Django 博客系统，包含文章管理、用户认证、统计功能和聊天功能。

## 功能特性

- 📝 文章发布与管理
- 👤 用户注册与登录
- 📊 访问统计
- 💬 实时聊天
- 🌤️ 天气信息展示
- 📱 响应式设计

## 快速开始

1. 克隆项目
2. 安装依赖：`pip install -r requirements.txt`
3. 配置环境变量：复制 `.env.example` 到 `.env`
4. 运行迁移：`python manage.py migrate`
5. 创建超级用户：`python manage.py createsuperuser`
6. 启动开发服务器：`python manage.py runserver`

## 项目结构

```

myblog/
├──myblog/          # Django 项目配置
├──blog/            # 博客应用
│├── views/       # 视图模块化
│├── templates/   # 模板文件
│└── static/      # 静态文件
└──...

```