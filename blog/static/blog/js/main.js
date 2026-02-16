// 主JavaScript文件

// DOM加载完成后执行
document.addEventListener('DOMContentLoaded', function() {

    // 自动关闭警告框
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000); // 5秒后自动关闭
    });

    // 表单验证增强
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 处理中...';
            }
        });
    });

    // 滚动到顶部按钮
    const scrollTopBtn = document.createElement('button');
    scrollTopBtn.innerHTML = '<i class="fas fa-chevron-up"></i>';
    scrollTopBtn.className = 'btn btn-primary btn-scroll-top';
    scrollTopBtn.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        display: none;
        z-index: 1000;
        width: 50px;
        height: 50px;
        border-radius: 50%;
        padding: 0;
    `;
    document.body.appendChild(scrollTopBtn);

    window.addEventListener('scroll', function() {
        if (window.pageYOffset > 300) {
            scrollTopBtn.style.display = 'block';
        } else {
            scrollTopBtn.style.display = 'none';
        }
    });

    scrollTopBtn.addEventListener('click', function() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });

    // 图片懒加载
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
                observer.unobserve(img);
            }
        });
    });

    images.forEach(img => imageObserver.observe(img));

    // 文章内容字数统计
    const contentTextarea = document.querySelector('#id_content');
    if (contentTextarea) {
        const charCount = document.createElement('div');
        charCount.className = 'form-text text-end';
        charCount.innerHTML = '字数: <span class="char-count">0</span>';
        contentTextarea.parentNode.appendChild(charCount);

        function updateCharCount() {
            const count = contentTextarea.value.length;
            charCount.querySelector('.char-count').textContent = count;
            if (count > 10000) {
                charCount.style.color = '#dc3545';
            } else if (count > 5000) {
                charCount.style.color = '#ffc107';
            } else {
                charCount.style.color = '#28a745';
            }
        }

        contentTextarea.addEventListener('input', updateCharCount);
        updateCharCount(); // 初始统计
    }

    // 搜索框自动聚焦
    const searchInput = document.querySelector('input[name="q"]');
    if (searchInput) {
        searchInput.addEventListener('focus', function() {
            this.select();
        });
    }

    // 标签选择增强
    const tagSelect = document.querySelector('#id_tags');
    if (tagSelect) {
        tagSelect.classList.add('form-select');
    }

    // 响应式表格
    const tables = document.querySelectorAll('table');
    tables.forEach(table => {
        table.classList.add('table-responsive');
    });
});

// 工具函数
const BlogUtils = {
    // 显示通知
    showNotification: function(message, type = 'info') {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
        `;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(alert);

        setTimeout(() => {
            alert.remove();
        }, 5000);
    },

    // 复制到剪贴板
    copyToClipboard: function(text) {
        navigator.clipboard.writeText(text).then(() => {
            this.showNotification('已复制到剪贴板', 'success');
        }).catch(err => {
            console.error('复制失败:', err);
            this.showNotification('复制失败', 'danger');
        });
    },

    // 格式化日期
    formatDate: function(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = Math.floor((now - date) / 1000);

        if (diff < 60) return '刚刚';
        if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`;
        if (diff < 2592000) return `${Math.floor(diff / 86400)}天前`;

        return date.toLocaleDateString('zh-CN');
    },

    // 防抖函数
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

// 在 main.js 末尾添加以下代码

// 私聊功能 - 更新未读消息计数
// 在 main.js 中修改 updatePrivateChatUnreadCount 函数
function updatePrivateChatUnreadCount() {
    fetch('/api/private-chat/summary/')
        .then(response => {
            if (!response.ok) throw new Error('网络响应错误');
            return response.json();
        })
        .then(data => {
            const unreadBadge = document.querySelector('.private-chat-unread');
            if (unreadBadge) {
                if (data.total_unread > 0) {
                    unreadBadge.textContent = data.total_unread;
                    unreadBadge.style.display = 'inline';
                } else {
                    unreadBadge.style.display = 'none';
                }
            }
        })
        .catch(error => console.error('获取私聊摘要失败:', error));
}

// 用户在线状态（简化版）
const userOnlineStatus = {};

// 在聊天页面显示在线状态
if (window.location.pathname.includes('/private-chat/')) {
    // 这里可以添加WebSocket连接来实时获取在线状态
    // 目前使用轮询方式
    function updateOnlineStatus() {
        // 在实际应用中，这里应该通过API获取在线用户列表
        // 这里只是示例
        console.log('更新在线状态...');
    }

    // 每30秒更新一次在线状态
    setInterval(updateOnlineStatus, 30000);
}
/*
// 聊天功能
if (window.location.pathname.includes('/chat')) {
    class ChatManager {
        constructor() {
            this.messageContainer = document.querySelector('.chat-messages');
            this.messageInput = document.querySelector('.message-input');
            this.sendButton = document.querySelector('.send-button');
            this.pollingInterval = null;

            this.init();
        }

        init() {
            this.loadMessages();
            this.setupEventListeners();
            this.startPolling();
        }

        setupEventListeners() {
            this.sendButton?.addEventListener('click', () => this.sendMessage());
            this.messageInput?.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        async loadMessages() {
            try {
                const response = await fetch('/api/chat/messages/');
                const data = await response.json();
                this.renderMessages(data.messages);
            } catch (error) {
                console.error('加载消息失败:', error);
            }
        }

        async sendMessage() {
            const content = this.messageInput?.value.trim();
            if (!content) return;

            try {
                const response = await fetch('/api/chat/send/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken(),
                    },
                    body: JSON.stringify({ message: content }),
                });

                const data = await response.json();
                if (data.success) {
                    this.messageInput.value = '';
                    this.loadMessages(); // 重新加载所有消息
                }
            } catch (error) {
                console.error('发送消息失败:', error);
                BlogUtils.showNotification('发送失败，请重试', 'danger');
            }
        }

        renderMessages(messages) {
            if (!this.messageContainer) return;

            this.messageContainer.innerHTML = '';
            messages.forEach(msg => {
                const messageEl = this.createMessageElement(msg);
                this.messageContainer.appendChild(messageEl);
            });

            // 滚动到底部
            this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
        }

        createMessageElement(message) {
            const div = document.createElement('div');
            div.className = `message ${message.user_id === currentUserId ? 'message-self' : 'message-other'}`;

            const time = new Date(message.timestamp).toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit',
            });

            div.innerHTML = `
                <div class="message-header">
                    <strong>${message.username}</strong>
                    <small class="text-muted">${time}</small>
                </div>
                <div class="message-content">${this.escapeHtml(message.content)}</div>
            `;

            return div;
        }

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        getCsrfToken() {
            const cookieValue = document.cookie
                .split('; ')
                .find(row => row.startsWith('csrftoken='))
                ?.split('=')[1];
            return cookieValue || '';
        }

        startPolling() {
            this.pollingInterval = setInterval(() => {
                this.loadMessages();
            }, 3000); // 每3秒轮询一次
        }

        stopPolling() {
            if (this.pollingInterval) {
                clearInterval(this.pollingInterval);
            }
        }
    }

    // 假设从全局变量获取当前用户ID
    const currentUserId = window.currentUserId || 0;

    // 初始化聊天管理器
    window.chatManager = new ChatManager();
}
*/
// 天气组件交互
document.addEventListener('DOMContentLoaded', function() {
    // 初始化Bootstrap工具提示
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // 天气刷新按钮
    const refreshButtons = document.querySelectorAll('.refresh-weather');

    refreshButtons.forEach(button => {
        button.addEventListener('click', function() {
            const weatherCard = this.closest('.card');
            const weatherInfo = weatherCard.querySelector('.weather-info');
            const weatherError = weatherCard.querySelector('.weather-error');

            // 添加旋转动画
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            this.disabled = true;

            // 发送刷新请求
            fetch('/api/weather/refresh/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json',
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 重新加载页面或更新天气数据
                    setTimeout(() => {
                        location.reload();
                    }, 1000);
                } else {
                    showNotification('刷新失败，请稍后重试', 'error');
                }
            })
            .catch(error => {
                console.error('刷新天气失败:', error);
                showNotification('网络错误，请稍后重试', 'error');
            })
            .finally(() => {
                setTimeout(() => {
                    this.innerHTML = '<i class="fas fa-redo"></i>';
                    this.disabled = false;
                }, 2000);
            });
        });
    });

    // 获取CSRF令牌
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // 显示通知
    function showNotification(message, type = 'info') {
        // 这里可以使用你现有的通知系统
        // 或者创建一个简单的通知
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alert.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 300px;
        `;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(alert);

        setTimeout(() => {
            alert.remove();
        }, 5000);
    }
});
