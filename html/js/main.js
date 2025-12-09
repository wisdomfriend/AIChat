// 计数器功能
let counter = 0;

function increment() {
    counter++;
    updateCounter();
}

function decrement() {
    counter--;
    updateCounter();
}

function reset() {
    counter = 0;
    updateCounter();
}

function updateCounter() {
    const counterElement = document.getElementById('counter');
    if (counterElement) {
        counterElement.textContent = counter;
        // 添加动画效果
        counterElement.style.transform = 'scale(1.2)';
        setTimeout(() => {
            counterElement.style.transform = 'scale(1)';
        }, 200);
    }
}

// 时间显示功能
function updateCurrentTime() {
    const timeElement = document.getElementById('currentTime');
    if (timeElement) {
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        timeElement.textContent = `${hours}:${minutes}:${seconds}`;
    }
}

// 每秒更新当前时间
setInterval(updateCurrentTime, 1000);
updateCurrentTime();

// 获取服务器时间
async function fetchServerTime() {
    const serverTimeElement = document.getElementById('serverTime');
    if (serverTimeElement) {
        serverTimeElement.textContent = '获取中...';
        try {
            // 通过 HTTP 头获取服务器时间
            const response = await fetch('/api/time', {
                method: 'HEAD'
            });
            const serverDate = new Date(response.headers.get('Date'));
            const hours = String(serverDate.getHours()).padStart(2, '0');
            const minutes = String(serverDate.getMinutes()).padStart(2, '0');
            const seconds = String(serverDate.getSeconds()).padStart(2, '0');
            serverTimeElement.textContent = `${hours}:${minutes}:${seconds}`;
        } catch (error) {
            // 如果 API 不存在，使用客户端时间
            const now = new Date();
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            serverTimeElement.textContent = `${hours}:${minutes}:${seconds} (客户端时间)`;
            console.log('无法获取服务器时间，使用客户端时间:', error);
        }
    }
}

// 页面加载时获取一次服务器时间
window.addEventListener('load', () => {
    fetchServerTime();
});

// 模态框功能
function showInfo() {
    const modal = document.getElementById('infoModal');
    const nginxInfo = document.getElementById('nginxInfo');
    
    if (modal && nginxInfo) {
        modal.style.display = 'block';
        
        // 获取浏览器信息
        const userAgent = navigator.userAgent;
        const language = navigator.language;
        const platform = navigator.platform;
        const screenWidth = window.screen.width;
        const screenHeight = window.screen.height;
        
        // 尝试获取服务器信息
        fetch('/api/info')
            .then(response => {
                if (response.ok) {
                    return response.json();
                }
                throw new Error('API 不可用');
            })
            .then(data => {
                nginxInfo.innerHTML = `
                    <h3>服务器信息</h3>
                    <p><strong>Nginx 版本:</strong> ${data.nginx_version || '未知'}</p>
                    <p><strong>服务器时间:</strong> ${data.server_time || '未知'}</p>
                    <hr>
                    <h3>客户端信息</h3>
                    <p><strong>用户代理:</strong> ${userAgent}</p>
                    <p><strong>语言:</strong> ${language}</p>
                    <p><strong>平台:</strong> ${platform}</p>
                    <p><strong>屏幕分辨率:</strong> ${screenWidth} x ${screenHeight}</p>
                `;
            })
            .catch(error => {
                nginxInfo.innerHTML = `
                    <h3>客户端信息</h3>
                    <p><strong>用户代理:</strong> ${userAgent}</p>
                    <p><strong>语言:</strong> ${language}</p>
                    <p><strong>平台:</strong> ${platform}</p>
                    <p><strong>屏幕分辨率:</strong> ${screenWidth} x ${screenHeight}</p>
                    <p style="color: #999; margin-top: 1rem;">注: 服务器 API 不可用，仅显示客户端信息</p>
                `;
            });
    }
}

function closeModal() {
    const modal = document.getElementById('infoModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// 点击模态框外部关闭
window.addEventListener('click', (event) => {
    const modal = document.getElementById('infoModal');
    if (event.target === modal) {
        closeModal();
    }
});

// 平滑滚动
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

