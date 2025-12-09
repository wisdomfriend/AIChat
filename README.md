# Nginx 展示网站

这是一个使用 Docker 和 Docker Compose 部署的 Nginx 静态网站演示项目，用于学习和测试 Nginx 的 HTTP 服务器功能。

## 技术栈

- **Nginx**: Web 服务器
- **Docker**: 容器化技术
- **Docker Compose**: 容器编排
- **HTML/CSS/JavaScript**: 前端技术

## 项目结构

```
nginx-shop/
├── docker-compose.yml      # Docker Compose 配置文件
├── Dockerfile              # Docker 镜像构建文件
├── nginx/
│   └── nginx.conf         # Nginx 配置文件
├── html/
│   ├── index.html         # 主页面
│   ├── css/
│   │   └── style.css      # 样式文件
│   └── js/
│       └── main.js        # JavaScript 脚本
└── logs/                  # Nginx 日志目录（自动创建）
```

## 快速开始

### 前置要求

- Docker (版本 20.10+)
- Docker Compose (版本 1.29+)

### 启动服务

```bash
# 构建并启动容器
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 访问网站

启动成功后，在浏览器中访问：
- http://localhost:8080

## 功能特性

1. **静态文件服务**: 高效提供 HTML、CSS、JavaScript 等静态资源
2. **Gzip 压缩**: 启用 Gzip 压缩以减小传输文件大小
3. **缓存控制**: 静态资源缓存策略
4. **安全头**: 添加基本的安全响应头
5. **API 端点**: 演示简单的 API 响应
6. **响应式设计**: 适配不同屏幕尺寸

## Nginx 配置说明

主要配置项：

- **监听端口**: 80（容器内）
- **工作进程**: auto（自动检测 CPU 核心数）
- **Gzip 压缩**: 已启用
- **静态文件缓存**: 30 天
- **日志**: 访问日志和错误日志

## 开发说明

### 修改静态文件

修改 `html/` 目录下的文件后，需要重新构建镜像：

```bash
docker-compose up -d --build
```

或者取消注释 `docker-compose.yml` 中的 volumes 挂载，实现实时修改（不推荐生产环境）。

### 修改 Nginx 配置

修改 `nginx/nginx.conf` 后，需要重新构建镜像：

```bash
docker-compose up -d --build
```

或者取消注释 `docker-compose.yml` 中的配置挂载。

### 查看日志

```bash
# 实时查看日志
docker-compose logs -f nginx

# 查看访问日志
tail -f logs/access.log

# 查看错误日志
tail -f logs/error.log
```

## 部署到 Linux 服务器

1. 将项目文件上传到服务器
2. 确保服务器已安装 Docker 和 Docker Compose
3. 在项目目录执行：

```bash
docker-compose up -d
```

4. 配置防火墙开放 8080 端口（或修改为其他端口）

## 端口修改

如需修改端口，编辑 `docker-compose.yml` 中的端口映射：

```yaml
ports:
  - "你的端口:80"
```

## 许可证

本项目仅用于学习目的。

