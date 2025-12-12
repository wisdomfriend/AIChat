# Nginx + Flask AI 聊天应用

这是一个基于 Docker 和 Docker Compose 部署的全栈 Web 应用，集成了 AI 聊天功能。项目使用 Nginx 作为反向代理和 Web 服务器，Flask 作为后端框架，MySQL 作为数据库，并集成了 DeepSeek API 提供 AI 聊天服务。

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
├── Dockerfile                  # Nginx 镜像构建文件
├── Dockerfile.flask            # Flask 应用镜像构建文件
├── requirements.txt            # Python 依赖包
├── flask_app/                  # Flask 应用目录
│   ├── app.py                 # Flask 主应用文件
│   ├── templates/            # HTML 模板
│   │   ├── login.html        # 登录页面
│   │   ├── chat.html         # 聊天页面
│   │   ├── dashboard.html    # 用户仪表板
│   │   └── admin.html        # 管理后台
│   └── static/               # 静态资源
│       └── css/              # 样式文件
├── nginx/
│   └── nginx.conf            # Nginx 配置文件
├── mysql/
│   └── init.sql              # 数据库初始化脚本
├── ssl/                      # SSL 证书目录
│   └── guopengfei.top/       # 域名证书文件
├── html/                     # 静态 HTML 文件（可选）
├── docs/                     # 文档目录
│   ├── 部署指南.md
│   ├── SSL证书使用指南.md
│   └── ...
└── scripts/                   # 部署脚本
    ├── install.sh
    └── configure-firewall.sh
```

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

### 环境配置

1. **配置 SSL 证书**

   将 SSL 证书文件放置在 `ssl/guopengfei.top/` 目录下：
   - `fullchain.crt`: 完整证书链
   - `private.key`: 私钥文件

   如果使用其他域名，需要修改 `nginx/nginx.conf` 中的域名配置。

2. **配置数据库**

   默认数据库配置（可在 `docker-compose.yml` 中修改）：
   - 数据库名: `nginx_shop`
   - 用户名: `guopengfei_learning`
   - 密码: `Gpf_learning`

3. **配置 API Key**

   首次启动后，通过管理后台配置 DeepSeek API Key，或直接在数据库中插入。

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

### 访问应用

启动成功后，在浏览器中访问：
- **HTTPS**: https://guopengfei.top (或配置的域名)
- **HTTP**: http://localhost (会自动重定向到 HTTPS)

**默认登录账号**:
- 用户名: `guopengfei_learning`
- 密码: `Gpf_learning`

## 开发说明

### 本地开发

1. **安装 Python 依赖**

```bash
pip install -r requirements.txt
```

2. **配置环境变量**

创建 `.env` 文件或设置环境变量：
```bash
export MYSQL_HOST=localhost
export MYSQL_USER=guopengfei_learning
export MYSQL_PASSWORD=Gpf_learning
export MYSQL_DB=nginx_shop
```

3. **启动 Flask 开发服务器**

```bash
cd flask_app
python app.py
```

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
docker-compose restart nginx
# 或重新构建
docker-compose up -d --build nginx
```

### 数据库操作

```bash
# 进入 MySQL 容器
docker-compose exec mysql mysql -u guopengfei_learning -pGpf_learning nginx_shop

# 备份数据库
docker-compose exec mysql mysqldump -u guopengfei_learning -pGpf_learning nginx_shop > backup.sql

# 恢复数据库
docker-compose exec -T mysql mysql -u guopengfei_learning -pGpf_learning nginx_shop < backup.sql
```

## 部署到生产环境

### 服务器要求

- Linux 服务器（推荐 Ubuntu 20.04+）
- Docker 和 Docker Compose 已安装
- 域名已解析到服务器 IP
- SSL 证书已准备

### 部署步骤

1. **上传项目文件到服务器**

```bash
scp -r nginx-shop user@server:/path/to/
```

2. **配置 SSL 证书**

将证书文件上传到 `ssl/guopengfei.top/` 目录。

3. **修改配置（如需要）**

- 修改 `docker-compose.yml` 中的端口映射
- 修改 `nginx/nginx.conf` 中的域名
- 修改数据库密码等敏感信息

4. **启动服务**

```bash
cd /path/to/nginx-shop
docker-compose up -d
```

5. **配置防火墙**

```bash
# 开放 80 和 443 端口
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

6. **查看日志**

```bash
docker-compose logs -f
```

详细部署指南请参考 `docs/部署指南.md`。

## 配置说明

### Nginx 配置

主要配置项：
- **监听端口**: 80 (HTTP), 443 (HTTPS)
- **SSL 协议**: TLSv1.2, TLSv1.3
- **Gzip 压缩**: 已启用
- **静态文件缓存**: 30 天
- **反向代理**: 转发到 Flask 应用 (flask-app:5000)

### Flask 应用配置

- **运行端口**: 5000 (容器内)
- **WSGI 服务器**: Gunicorn (4 workers)
- **数据库**: MySQL (通过环境变量配置)
- **Session**: 基于 Flask Session

### MySQL 配置

- **版本**: MySQL 8.0
- **数据持久化**: Docker Volume
- **初始化脚本**: `mysql/init.sql`

## API 端点

### 用户相关
- `GET /` - 首页（自动重定向）
- `GET /login` - 登录页面
- `POST /login` - 处理登录
- `GET /logout` - 登出
- `GET /chat` - 聊天页面
- `GET /dashboard` - 用户仪表板
- `GET /admin` - 管理后台

### API 接口
- `POST /api/chat` - AI 聊天接口
- `POST /admin/api_key` - 更新 API Key

## 安全注意事项

1. **生产环境配置**
   - 修改默认密码
   - 使用强密码策略
   - 定期更新依赖包
   - 配置防火墙规则

2. **SSL 证书**
   - 使用有效的 SSL 证书
   - 定期更新证书
   - 配置证书自动续期（如使用 Let's Encrypt）

3. **API Key 管理**
   - 不要在代码中硬编码 API Key
   - 使用环境变量或密钥管理服务
   - 定期轮换 API Key

4. **数据库安全**
   - 使用强密码
   - 限制数据库访问权限
   - 定期备份数据

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

## 文档

项目文档位于 `docs/` 目录：
- `部署指南.md` - 详细部署说明
- `SSL证书使用指南.md` - SSL 证书配置指南
- `SSL技术原理详解.md` - SSL 技术原理
- `域名配置指南.md` - 域名配置说明

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

### 最新版本
- 集成 Flask 后端框架
- 添加 MySQL 数据库支持
- 集成 DeepSeek AI 聊天功能
- 实现用户认证系统
- 添加 Token 使用统计
- 配置 Nginx 反向代理
- 支持 HTTPS/SSL
