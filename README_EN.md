# AIChat - Flask AI Chat Application | Docker Full-Stack Deployment Solution

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![English](https://img.shields.io/badge/English-README-blue.svg)](README_EN.md) [![中文](https://img.shields.io/badge/中文-README-red.svg)](README.md)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-green.svg)](https://flask.palletsprojects.com/)
[![LangChain](https://img.shields.io/badge/LangChain-1.2.0-orange.svg)](https://www.langchain.com/)
[![Docker Compose](https://img.shields.io/badge/Docker_Compose-5.0.0-blue.svg)](https://docs.docker.com/compose/)

> **Build your own DeepSeek AI chat application in 5 minutes! Flask + LangChain with user registration, formula display, web search, file upload, and token statistics | One-click Docker deployment, ready to use out of the box**

## Project Overview

**AIChat** is an open-source AI chat web application. The project uses **Flask** as the backend framework, integrates **DeepSeek API** to provide AI chat services, and enables one-click deployment through **Docker Compose**.

![Main Page](./images/main_page.png)
![Swagger Page](./images/swagger.png)

### Core Features

- **AI Chat Functionality**: Integrated DeepSeek API, supports real-time conversation interaction, file upload, and formatted display of formulas/code/markdown
- **User Authentication**: Complete login/registration functionality with Redis Session management
- **Usage Statistics**: Token usage statistics and record queries
- **Admin Dashboard**: API Key management and global statistics
- **Containerized Deployment**: One-click deployment with Docker Compose
- **Responsive Design**: Compatible with mobile devices

### Online Demo

- **Deployment URL**: https://guopengfei.top
- **Author Email**: wisdomfriend@126.com (Feel free to email if you have any questions)

### Technology Tags

`Flask` `Python` `Docker` `DeepSeek API` `LangChain`

## Quick Start

### Prerequisites

- Docker (version 20.10+)
- Docker Compose (version 5.0.0, minimum requirement 1.29+)
- Python 3.9+ (for local development)

### Network Optimization for Mainland China

If you are in Mainland China, it is recommended to configure domestic mirror sources to speed up downloads:

#### 1. Configure Docker Image Accelerator

Create or edit `/etc/docker/daemon.json`:

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

# Restart Docker service to apply configuration
sudo systemctl daemon-reload
sudo systemctl restart docker

# Verify configuration
docker info | grep -A 10 "Registry Mirrors"
```

**Common Domestic Mirror Sources:**
- USTC: `https://docker.mirrors.ustc.edu.cn`
- NetEase: `https://hub-mirror.c.163.com`
- Baidu Cloud: `https://mirror.baidubce.com`
- Alibaba Cloud: Log in to Alibaba Cloud Console to get your exclusive acceleration address

### Start Services

```bash
# Build and start all containers
docker-compose up -d

# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f flask-app

# Stop services
docker-compose down
```

#### Access Services

After starting the containers, you can access the services in the following ways:

- **Direct Flask Application Access**: `http://localhost:5000`

## Development Guide

### Local Development

#### Prerequisites

- Python 3.11

#### Set Up Python Virtual Environment

**Recommended to use venv (Python built-in virtual environment)**

1. **Create Virtual Environment**

```bash
# Windows PowerShell
python -m venv venv
```

2. **Activate Virtual Environment**

```bash
# Windows PowerShell
.\venv\Scripts\Activate.ps1

# If you encounter execution policy errors, run the following command:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Windows CMD
venv\Scripts\activate.bat
```

After successful activation, `(venv)` will be displayed before the command prompt.

3. **Install Python Dependencies**

```bash
# Make sure the virtual environment is activated (you should see (venv) before the prompt)
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
```

**Common Issues:**

- If you encounter `ModuleNotFoundError`, check if the virtual environment is activated
- When running in PyCharm, make sure to configure using the venv interpreter
- When running in terminal, make sure to execute the activation command first

### Redeploy After Code Changes

```bash
# Rebuild and start
docker-compose up -d --build
```

### Modify Nginx Configuration

After modifying `nginx/nginx.conf`:
```bash
# Nginx uses the official image, configuration is mounted via volumes, just restart to take effect
docker-compose restart nginx
```

## Configuration

### Nginx Configuration

Main configuration items:
- **Image**: nginx:alpine
- **Configuration Mount**: `nginx/nginx.conf` is mounted via volumes, restart to take effect after modification
- **Reverse Proxy**: Forwards to Flask application (flask-app:5000)

### Flask Application Configuration

- **Running Port**: 5000
- **WSGI Server**: Gunicorn (4 workers)
- **Database**: MySQL (configured via environment variables)
- **Session**: Redis storage (using custom `FixedRedisSessionInterface`)
  - Session expiration time: 7 days (configurable)
  - Session ID signing: Enabled (enhanced security)

### MySQL Configuration

- **Version**: MySQL 8.0
- **Data Persistence**: Docker Volume
- **Initialization Script**: `mysql/init.sql`

### Redis Configuration

- **Version**: Redis 7 (Alpine)
- **Data Persistence**: Docker Volume + AOF (Append Only File)
- **Port**: 6379

## Troubleshooting

### Common Issues

1. **Containers Cannot Start**
   ```bash
   # View detailed logs
   docker-compose logs
   # Check port occupancy
   netstat -tulpn | grep :80
   ```

2. **Database Connection Failed**
   ```bash
   # Check MySQL container status
   docker-compose ps mysql
   # View MySQL logs
   docker-compose logs mysql
   ```

3. **Redis Connection Failed**
   ```bash
   # Check Redis container status
   docker-compose ps redis
   # View Redis logs
   docker-compose logs redis
   # Test Redis connection
   docker-compose exec redis redis-cli -a Gpf_learning ping
   ```
   - Check if environment variables `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD` are correctly configured

## TODO / Development Roadmap

The following are planned feature improvements and optimizations:

1. ✅ **Redis Cache Integration**
   - ✅ Added Redis service to Docker Compose
   - ✅ Migrated Flask Session from default storage to Redis
   - ✅ Improved Session management performance and scalability
   - ✅ Support for Session sharing in multi-instance deployments
   - ✅ Custom Session interface fixes compatibility issues

2. ✅ **Streaming Chat Response**
   - ✅ Modified `/api/chat` endpoint to support streaming output
   - ✅ Frontend implements Server-Sent Events (SSE) or WebSocket to receive streaming data
   - ✅ Reduced user wait time and improved interaction experience

3. **API Rate Limiting**
   - Use Redis to implement chat API rate limiting
   - Limiting rules: Maximum 5 requests per minute
   - Rate limiting based on user ID or IP address
   - Return friendly error messages

4. ✅ **Display Optimization**
   - ✅ Support formatted display of markdown/formulas/code using KaTeX/Marked.js/Highlight.js

5. ✅ **File Conversation**
   - ✅ Support PDF/DOCX/XLSX file conversations

6. **Conversation Optimization**
   - ✅ Automatic summarization for ultra-long contexts
   - ✅ Support for web search
   - Support for MCP tool calls

## License

This project is licensed under the [MIT License](LICENSE).
For detailed license content, please see the [LICENSE](LICENSE) file.

