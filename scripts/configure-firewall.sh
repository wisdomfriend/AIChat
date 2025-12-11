#!/bin/bash

# SSL 证书 HTTPS 防火墙配置脚本
# 用于开放 80 (HTTP) 和 443 (HTTPS) 端口

echo "=========================================="
echo "配置防火墙 - 开放 HTTP 和 HTTPS 端口"
echo "=========================================="
echo ""

# 检测系统类型
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "无法检测操作系统类型"
    exit 1
fi

echo "检测到操作系统: $OS"
echo ""

# 检测防火墙类型
if command -v ufw &> /dev/null; then
    FIREWALL_TYPE="ufw"
    echo "检测到防火墙: UFW (Ubuntu/Debian)"
elif command -v firewall-cmd &> /dev/null; then
    FIREWALL_TYPE="firewalld"
    echo "检测到防火墙: firewalld (CentOS/RHEL)"
elif command -v iptables &> /dev/null; then
    FIREWALL_TYPE="iptables"
    echo "检测到防火墙: iptables"
else
    echo "未检测到防火墙，可能需要手动配置"
    echo "请确保在云服务器控制台的安全组中开放 80 和 443 端口"
    exit 1
fi

echo ""
echo "开始配置防火墙..."
echo ""

# 配置 UFW
if [ "$FIREWALL_TYPE" = "ufw" ]; then
    echo "使用 UFW 配置防火墙..."
    
    # 检查是否需要 sudo
    if [ "$EUID" -ne 0 ]; then
        SUDO="sudo"
        echo "需要 root 权限，将使用 sudo"
    else
        SUDO=""
    fi
    
    # 开放 HTTP 端口
    echo "开放 80 端口 (HTTP)..."
    $SUDO ufw allow 80/tcp
    
    # 开放 HTTPS 端口
    echo "开放 443 端口 (HTTPS)..."
    $SUDO ufw allow 443/tcp
    
    # 重新加载防火墙
    echo "重新加载防火墙规则..."
    $SUDO ufw reload
    
    # 显示状态
    echo ""
    echo "防火墙状态:"
    $SUDO ufw status
    
    echo ""
    echo "✅ UFW 配置完成！"

# 配置 firewalld
elif [ "$FIREWALL_TYPE" = "firewalld" ]; then
    echo "使用 firewalld 配置防火墙..."
    
    # 检查是否需要 sudo
    if [ "$EUID" -ne 0 ]; then
        SUDO="sudo"
        echo "需要 root 权限，将使用 sudo"
    else
        SUDO=""
    fi
    
    # 开放 HTTP 端口
    echo "开放 80 端口 (HTTP)..."
    $SUDO firewall-cmd --permanent --add-port=80/tcp
    
    # 开放 HTTPS 端口
    echo "开放 443 端口 (HTTPS)..."
    $SUDO firewall-cmd --permanent --add-port=443/tcp
    
    # 重新加载防火墙
    echo "重新加载防火墙规则..."
    $SUDO firewall-cmd --reload
    
    # 显示状态
    echo ""
    echo "防火墙状态:"
    $SUDO firewall-cmd --list-ports
    
    echo ""
    echo "✅ firewalld 配置完成！"

# 配置 iptables
elif [ "$FIREWALL_TYPE" = "iptables" ]; then
    echo "使用 iptables 配置防火墙..."
    
    # 检查是否需要 sudo
    if [ "$EUID" -ne 0 ]; then
        SUDO="sudo"
        echo "需要 root 权限，将使用 sudo"
    else
        SUDO=""
    fi
    
    # 开放 HTTP 端口
    echo "开放 80 端口 (HTTP)..."
    $SUDO iptables -A INPUT -p tcp --dport 80 -j ACCEPT
    
    # 开放 HTTPS 端口
    echo "开放 443 端口 (HTTPS)..."
    $SUDO iptables -A INPUT -p tcp --dport 443 -j ACCEPT
    
    # 保存规则（根据系统不同）
    if command -v iptables-save &> /dev/null; then
        echo "保存 iptables 规则..."
        if [ -f /etc/redhat-release ]; then
            # CentOS/RHEL
            $SUDO service iptables save 2>/dev/null || $SUDO iptables-save > /etc/iptables/rules.v4
        else
            # 其他系统
            $SUDO iptables-save > /etc/iptables/rules.v4 2>/dev/null || echo "请手动保存 iptables 规则"
        fi
    fi
    
    echo ""
    echo "✅ iptables 配置完成！"
    echo "⚠️  注意：请确保 iptables 规则已保存，否则重启后会丢失"
fi

echo ""
echo "=========================================="
echo "防火墙配置完成！"
echo "=========================================="
echo ""
echo "已开放的端口："
echo "  - 80  (HTTP)"
echo "  - 443 (HTTPS)"
echo ""
echo "⚠️  重要提示："
echo "如果您的服务器在云平台（阿里云、腾讯云、华为云等），"
echo "还需要在云服务器控制台的【安全组】中开放 80 和 443 端口！"
echo ""
echo "云服务器安全组配置："
echo "  1. 登录云服务器控制台"
echo "  2. 找到您的服务器实例"
echo "  3. 进入【安全组】设置"
echo "  4. 添加入站规则："
echo "     - 端口：80，协议：TCP，源：0.0.0.0/0"
echo "     - 端口：443，协议：TCP，源：0.0.0.0/0"
echo ""

