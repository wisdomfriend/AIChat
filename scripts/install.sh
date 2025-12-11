#!/bin/bash

# Nginx Shop 项目一键安装脚本
# 适用于 Ubuntu/Debian 系统

set -e  # 遇到错误立即退出

echo "=========================================="
echo "  Nginx Shop 项目自动安装脚本"
echo "=========================================="
echo ""

# 检查是否为 root 用户
IS_ROOT=false
if [ "$EUID" -eq 0 ]; then 
   IS_ROOT=true
   echo "⚠️  警告：您正在使用 root 用户运行此脚本"
   echo "   建议：创建普通用户并添加到 sudo 组，然后使用普通用户运行"
   echo "   命令：adduser username && usermod -aG sudo username"
   echo ""
   read -p "是否继续使用 root 用户安装？(y/n) " -n 1 -r
   echo
   if [[ ! $REPLY =~ ^[Yy]$ ]]; then
       exit 1
   fi
   echo ""
fi

# 检查系统类型
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
    # 尝试从 /etc/os-release 获取 VERSION_CODENAME，如果没有则尝试 lsb_release
    if [ -n "$VERSION_CODENAME" ]; then
        OS_CODENAME="$VERSION_CODENAME"
    else
        OS_CODENAME=$(lsb_release -cs 2>/dev/null || echo "")
    fi
else
    echo "无法检测系统类型"
    exit 1
fi

echo "检测到系统: $OS $VER"
if [ -n "$OS_CODENAME" ]; then
    echo "系统代号: $OS_CODENAME"
fi
echo ""

# 确定 Docker 仓库类型
if [ "$OS" = "ubuntu" ]; then
    DOCKER_REPO="ubuntu"
    DOCKER_CODENAME="$OS_CODENAME"
elif [ "$OS" = "debian" ]; then
    DOCKER_REPO="debian"
    # Debian 版本映射（使用系统代号）
    DOCKER_CODENAME="$OS_CODENAME"
else
    echo "⚠️  警告：未识别的系统类型 $OS，尝试使用 Ubuntu 仓库"
    DOCKER_REPO="ubuntu"
    DOCKER_CODENAME="$OS_CODENAME"
fi

# 检查 Docker 是否已安装
if command -v docker &> /dev/null; then
    echo "✓ Docker 已安装: $(docker --version)"
else
    echo "开始安装 Docker..."
    
    # 根据用户类型选择命令前缀
    if [ "$IS_ROOT" = true ]; then
        CMD_PREFIX=""
    else
        CMD_PREFIX="sudo"
    fi
    
    # 更新系统包
    echo "更新系统包..."
    $CMD_PREFIX apt-get update
    $CMD_PREFIX apt-get install -y ca-certificates curl gnupg lsb-release
    
    # 如果之前没有获取到系统代号，现在再试一次
    if [ -z "$OS_CODENAME" ]; then
        OS_CODENAME=$(lsb_release -cs)
        DOCKER_CODENAME="$OS_CODENAME"
        echo "检测到系统代号: $OS_CODENAME"
    fi
    
    # 添加 Docker 官方 GPG 密钥
    echo "添加 Docker GPG 密钥..."
    $CMD_PREFIX install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/$DOCKER_REPO/gpg | $CMD_PREFIX gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    $CMD_PREFIX chmod a+r /etc/apt/keyrings/docker.gpg
    
    # 设置 Docker 仓库
    echo "设置 Docker 仓库（$DOCKER_REPO）..."
    if [ "$OS" = "debian" ] && [ -n "$DOCKER_CODENAME" ]; then
        # Debian 使用检测到的代号
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$DOCKER_REPO \
          $DOCKER_CODENAME stable" | $CMD_PREFIX tee /etc/apt/sources.list.d/docker.list > /dev/null
    else
        # Ubuntu 或其他系统使用 lsb_release
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$DOCKER_REPO \
          $(lsb_release -cs) stable" | $CMD_PREFIX tee /etc/apt/sources.list.d/docker.list > /dev/null
    fi
    
    # 安装 Docker
    echo "安装 Docker Engine..."
    $CMD_PREFIX apt-get update
    $CMD_PREFIX apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # 启动 Docker 服务
    echo "启动 Docker 服务..."
    $CMD_PREFIX systemctl start docker
    $CMD_PREFIX systemctl enable docker
    
    # 将当前用户添加到 docker 组（root 用户不需要）
    if [ "$IS_ROOT" != true ]; then
        echo "将当前用户添加到 docker 组..."
        $CMD_PREFIX usermod -aG docker $USER
        echo "✓ Docker 安装完成"
        echo "⚠️  注意：您需要重新登录或执行 'newgrp docker' 才能使 docker 组权限生效"
    else
        echo "✓ Docker 安装完成（root 用户无需添加到 docker 组）"
    fi
    echo ""
fi

# 检查 Docker Compose
if docker compose version &> /dev/null; then
    echo "✓ Docker Compose 已安装: $(docker compose version)"
elif command -v docker-compose &> /dev/null; then
    echo "✓ Docker Compose 已安装: $(docker-compose --version)"
else
    echo "安装 Docker Compose..."
    # 根据用户类型选择命令前缀
    if [ "$IS_ROOT" = true ]; then
        CMD_PREFIX=""
    else
        CMD_PREFIX="sudo"
    fi
    $CMD_PREFIX curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    $CMD_PREFIX chmod +x /usr/local/bin/docker-compose
    echo "✓ Docker Compose 安装完成"
fi

echo ""

# 检查项目文件
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ 错误：未找到 docker-compose.yml 文件"
    echo "请确保在项目根目录下运行此脚本"
    exit 1
fi

if [ ! -f "Dockerfile" ]; then
    echo "❌ 错误：未找到 Dockerfile 文件"
    exit 1
fi

# 创建 logs 目录
echo "创建 logs 目录..."
mkdir -p logs
echo "✓ logs 目录已创建"

# 检查端口占用
echo "检查端口 8083 是否被占用..."
# 根据用户类型选择命令前缀
if [ "$IS_ROOT" = true ]; then
    CMD_PREFIX=""
else
    CMD_PREFIX="sudo"
fi
if $CMD_PREFIX netstat -tuln 2>/dev/null | grep -q ":8083 " || $CMD_PREFIX ss -tuln 2>/dev/null | grep -q ":8083 "; then
    echo "⚠️  警告：端口 8083 已被占用"
    echo "您可以修改 docker-compose.yml 中的端口映射"
    read -p "是否继续？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✓ 端口 8083 可用"
fi

echo ""

# 构建并启动容器
echo "构建并启动 Docker 容器..."
if docker compose version &> /dev/null; then
    docker compose up -d --build
else
    docker-compose up -d --build
fi

echo ""

# 等待容器启动
echo "等待容器启动..."
sleep 3

# 检查容器状态
echo "检查容器状态..."
if docker compose version &> /dev/null; then
    docker compose ps
else
    docker-compose ps
fi

echo ""
echo "=========================================="
echo "  安装完成！"
echo "=========================================="
echo ""
echo "访问地址:"
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "  http://$SERVER_IP:8083"
echo "  或"
echo "  http://localhost:8083"
echo ""
echo "常用命令:"
echo "  查看日志: docker compose logs -f"
echo "  停止服务: docker compose down"
echo "  重启服务: docker compose restart"
echo "  重启服务: docker compose up -d --force-recreate"
echo ""
echo "如果无法访问，请检查："
echo "  1. 防火墙是否开放 8083 端口"
echo "  2. 云服务器安全组是否开放 8083 端口"
echo "  3. 执行 'docker compose logs' 查看容器日志"
echo ""

