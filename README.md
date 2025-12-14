# Nginx + Flask AI 聊天应用

这是一个基于 Docker 和 Docker Compose 部署的全栈 Web 应用，集成了 AI 聊天功能。项目使用 Nginx 作为反向代理和 Web 服务器，Flask 作为后端框架，MySQL 作为数据库，并集成了 DeepSeek API 提供 AI 聊天服务。本项目部署地址:https://guopengfei.top 

## 技术栈

### 后端
- **Flask 3.0.0**: Python Web 框架
- **SQLAlchemy 2.0.32**: ORM 数据库操作
- **PyMySQL 1.1.1**: MySQL 数据库驱动
- **Gunicorn 21.2.0**: WSGI HTTP 服务器

### 前端
- **HTML/CSS/JavaScript**: 前端技术
- **响应式设计**: 适配不同屏幕尺寸

### 基础设施
- **Nginx**: 反向代理和 Web 服务器
- **MySQL 8.0**: 关系型数据库
- **Docker & Docker Compose**: 容器化部署
- **SSL/HTTPS**: 支持 HTTPS 加密访问

### 第三方服务
- **DeepSeek API**: AI 聊天服务提供商

## 项目结构

```
nginx-shop/
├── docker-compose.yml          # Docker Compose 配置文件
├── Dockerfile                  # Flask 应用镜像构建文件
├── requirements.txt            # Python 依赖包
├── run.py                      # Flask 应用启动脚本（开发环境）
├── wsgi.py                     # WSGI 入口文件（生产环境）
├── flask_app/                  # Flask 应用目录（模块化架构）
│   ├── __init__.py            # 应用工厂
│   ├── config.py              # 配置管理
│   ├── database.py            # 数据库连接管理
│   ├── models.py              # 数据库模型定义
│   ├── utils.py               # 辅助工具函数
│   ├── routes/                # 路由模块（Blueprint）
│   │   ├── __init__.py
│   │   ├── auth.py            # 认证路由（登录/登出）
│   │   ├── chat.py            # 聊天页面路由
│   │   ├── dashboard.py       # 仪表板路由
│   │   ├── admin.py           # 管理后台路由
│   │   └── api.py             # API 路由
│   ├── services/              # 业务逻辑服务层
│   │   ├── __init__.py
│   │   ├── auth_service.py    # 认证服务
│   │   ├── chat_service.py    # 聊天服务
│   │   └── stats_service.py   # 统计服务
│   ├── templates/             # HTML 模板
│   │   ├── login.html         # 登录页面
│   │   ├── chat.html          # 聊天页面
│   │   ├── dashboard.html     # 用户仪表板
│   │   └── admin.html         # 管理后台
│   └── static/                # 静态资源
│       └── css/               # 样式文件
├── nginx/
│   └── nginx.conf            # Nginx 配置文件
├── mysql/
│   └── init.sql              # 数据库初始化脚本
├── ssl/                      # SSL 证书目录
│   └── guopengfei.top/       # 域名证书文件
├── docs/                     # 文档目录
│   ├── 部署指南.md
│   ├── SSL证书使用指南.md
│   └── ...
└── scripts/                   # 部署脚本
    ├── install.sh
    └── configure-firewall.sh
```

### 架构说明

项目采用**模块化架构设计**，遵循 Flask 最佳实践：

- **应用工厂模式**: 使用 `create_app()` 函数创建应用实例，便于测试和扩展
- **Blueprint 路由模块化**: 按功能将路由拆分到不同模块（auth、chat、dashboard、admin、api）
- **服务层分离**: 业务逻辑封装在 `services/` 目录，实现关注点分离
- **配置管理**: 集中管理配置，支持开发/生产环境切换
- **数据库抽象**: 统一的数据库连接和会话管理

## 功能特性

### 核心功能
1. **用户认证系统**
   - 用户登录/登出
   - Session 管理
   - 用户状态跟踪

2. **AI 聊天功能**
   - 集成 DeepSeek API
   - 实时对话交互
   - Token 使用统计

3. **用户仪表板**
   - Token 使用统计（今日/本周/本月/总计）
   - 使用记录查看

4. **管理后台**
   - API Key 管理
   - 全局 Token 使用统计
   - 使用记录查询

### 技术特性
1. **Nginx 反向代理**
   - HTTPS/SSL 支持
   - HTTP 自动重定向到 HTTPS
   - 静态文件缓存
   - Gzip 压缩
   - 安全响应头

2. **数据库设计**
   - 用户表（users）
   - API 密钥表（api_keys）
   - Token 使用记录表（token_usage）
   - 代理访问日志表（proxy_logs）

3. **容器化部署**
   - 多容器架构（Nginx + Flask + MySQL）
   - 容器间网络通信
   - 数据持久化

## 快速开始

### 前置要求

- Docker (版本 20.10+)
- Docker Compose (版本 1.29+)
- Python 3.9+ (本地开发需要)

### 国内网络优化配置

如果你在中国大陆，建议配置国内镜像源以加速下载：

#### 1. 配置 Docker 镜像加速器

创建或编辑 `/etc/docker/daemon.json`：

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
EOF

# 重启 Docker 服务使配置生效
sudo systemctl daemon-reload
sudo systemctl restart docker

# 验证配置
docker info | grep -A 10 "Registry Mirrors"
```

**常用国内镜像源：**
- 中科大：`https://docker.mirrors.ustc.edu.cn`
- 网易：`https://hub-mirror.c.163.com`
- 百度云：`https://mirror.baidubce.com`
- 阿里云：需要登录阿里云控制台获取专属加速地址

### 启动服务

```bash
# 构建并启动所有容器
docker-compose up -d

# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f flask-app
docker-compose logs -f nginx
docker-compose logs -f mysql

# 停止服务
docker-compose down

# 停止并删除数据卷（谨慎使用）
docker-compose down -v
```

#### 访问服务

启动容器后，可以通过以下方式访问：

- **Flask 应用直接访问**: `http://localhost:5000`
- **MySQL**: `localhost:3306`


## 开发说明

### 本地开发

#### 前置要求

- Python 3.9+ （推荐 Python 3.12+）
- pip（Python 包管理器）

#### 设置 Python 虚拟环境

**推荐使用 venv（Python 内置虚拟环境）**

1. **创建虚拟环境**

```bash
# Windows PowerShell
python -m venv venv
```

2. **激活虚拟环境**

```bash
# Windows PowerShell
.\venv\Scripts\Activate.ps1

# 如果遇到执行策略错误，运行以下命令：
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Windows CMD
venv\Scripts\activate.bat
```

激活成功后，命令行提示符前会显示 `(venv)`。

4. **安装 Python 依赖**

```bash
# 确保已激活虚拟环境（命令行前显示 (venv)）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
```

**常见问题：**

- 如果遇到 `ModuleNotFoundError`，检查是否已激活虚拟环境
- 在 PyCharm 中运行，确保已配置使用 venv 解释器
- 在终端中运行，确保先执行激活命令

### 修改代码后重新部署

```bash
# 重新构建并启动
docker-compose up -d --build

# 仅重新构建特定服务
docker-compose build flask-app
docker-compose up -d flask-app
```

### 修改 Nginx 配置

修改 `nginx/nginx.conf` 后：
```bash
# Nginx 使用官方镜像，配置通过 volumes 挂载，直接重启即可生效
docker-compose restart nginx
```

### 代码结构说明

项目采用模块化架构，主要模块说明：

- **`config.py`**: 配置管理，支持开发/生产环境切换
- **`models.py`**: 数据库模型定义（User, ApiKey, TokenUsage）
- **`database.py`**: 数据库连接和会话管理
- **`utils.py`**: 辅助函数（如 `get_current_user()`, `require_login` 装饰器）
- **`routes/`**: 路由模块，使用 Blueprint 组织
  - `auth.py`: 登录/登出
  - `chat.py`: 聊天页面
  - `dashboard.py`: 用户仪表板
  - `admin.py`: 管理后台
  - `api.py`: API 接口
- **`services/`**: 业务逻辑服务层
  - `auth_service.py`: 认证业务逻辑
  - `chat_service.py`: 聊天业务逻辑（API 调用、Token 记录）
  - `stats_service.py`: 统计业务逻辑

### 数据库操作

```bash
# 进入 MySQL 容器
docker-compose exec mysql mysql -u guopengfei_learning -pGpf_learning nginx_shop

# 备份数据库
docker-compose exec mysql mysqldump -u guopengfei_learning -pGpf_learning nginx_shop > backup.sql

# 恢复数据库
docker-compose exec -T mysql mysql -u guopengfei_learning -pGpf_learning nginx_shop < backup.sql
```


## 配置说明

### Nginx 配置

主要配置项：
- **镜像**: nginx:alpine（官方镜像，无需构建）
- **配置挂载**: `nginx/nginx.conf` 通过 volumes 挂载，修改后重启即可生效
- **监听端口**: 80 (HTTP), 443 (HTTPS)
- **SSL 协议**: TLSv1.2, TLSv1.3
- **Gzip 压缩**: 已启用
- **静态文件缓存**: 30 天
- **反向代理**: 转发到 Flask 应用 (flask-app:5000)

### Flask 应用配置

- **架构**: 模块化设计，应用工厂模式
- **运行端口**: 5000 (容器内)
- **WSGI 服务器**: Gunicorn (4 workers)
- **数据库**: MySQL (通过环境变量配置)
- **Session**: 基于 Flask Session
- **路由**: Blueprint 模块化路由
- **服务层**: 业务逻辑分离到 services 目录

### MySQL 配置

- **版本**: MySQL 8.0
- **数据持久化**: Docker Volume
- **初始化脚本**: `mysql/init.sql`

## 故障排查

### 常见问题

1. **容器无法启动**
   ```bash
   # 查看详细日志
   docker-compose logs
   # 检查端口占用
   netstat -tulpn | grep :80
   ```

2. **数据库连接失败**
   ```bash
   # 检查 MySQL 容器状态
   docker-compose ps mysql
   # 查看 MySQL 日志
   docker-compose logs mysql
   ```

3. **SSL 证书错误**
   - 检查证书文件路径和权限
   - 确认证书文件格式正确
   - 查看 Nginx 错误日志

4. **API 调用失败**
   - 检查 API Key 是否配置
   - 查看 Flask 应用日志
   - 确认网络连接正常

## TODO / 开发计划

以下是计划中的功能改进和优化：

1. **集成 Redis 缓存**
   - 添加 Redis 服务到 Docker Compose
   - 将 Flask Session 从默认存储迁移到 Redis
   - 提升 Session 管理的性能和可扩展性
   - 支持多实例部署时的 Session 共享

2. **实现流式聊天响应**
   - 修改 `/api/chat` 接口支持流式输出
   - 前端实现 Server-Sent Events (SSE) 或 WebSocket 接收流式数据
   - 优化用户体验，实现打字机效果
   - 减少用户等待时间，提升交互体验

3. **API 访问频率限制**
   - 使用 Redis 实现聊天 API 访问频率限制
   - 限制规则：1 分钟内最多访问 5 次
   - 基于用户 ID 或 IP 地址进行限流
   - 返回友好的错误提示信息

## 许可证

本项目仅用于学习目的。

## 更新日志

### v2.0 - 架构重构（最新）

**重大改进**:
- ✨ **模块化架构重构**: 采用应用工厂模式和 Blueprint 路由模块化
- 📁 **代码组织优化**: 
  - 路由按功能拆分到 `routes/` 目录
  - 业务逻辑封装到 `services/` 目录
  - 配置、模型、数据库管理独立模块
- 🐳 **Docker 优化**: 
  - 移除 Nginx Dockerfile，直接使用官方 nginx:alpine 镜像
  - 配置通过 volumes 挂载，便于开发时修改
- 🗑️ **清理冗余**: 删除不再需要的 `html/` 静态文件夹

**技术改进**:
- 应用工厂模式 (`create_app()`)
- Blueprint 路由模块化
- 服务层分离（Service Layer Pattern）
- 统一的数据库会话管理
- 配置集中管理，支持环境切换

### v1.0 - 初始版本

- 集成 Flask 后端框架
- 添加 MySQL 数据库支持
- 集成 DeepSeek AI 聊天功能
- 实现用户认证系统
- 添加 Token 使用统计
- 配置 Nginx 反向代理
- 支持 HTTPS/SSL

## 许可证

本项目采用 [MIT License](LICENSE) 许可证。
详细许可证内容请查看 [LICENSE](LICENSE) 文件。
