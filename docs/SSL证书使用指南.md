# SSL 证书使用指南

本指南将帮助您完成从购买证书到配置到服务器的完整流程。

## 📋 前提条件

- ✅ 已购买 SSL 证书（状态：未使用）
- ✅ 域名已解析到服务器（DNS 已生效）
- ✅ 服务器已安装 Nginx
- ✅ 服务器可以访问（80 端口已开放）

---

## 第一步：签发证书（申请证书）

### 1.1 点击"签发"按钮

在证书管理页面，您会看到证书状态为 **"未使用"**，点击 **"签发"** 按钮开始申请。

### 1.2 填写域名信息

在签发页面，您需要填写：

**单域名证书：**
- **主域名**：`guopengfei.top`
- **附加域名（可选）**：`www.guopengfei.top`（如果支持）

**注意：** 有些证书支持在申请时同时填写多个域名（如主域名和 www 子域名），有些需要分别购买。

### 1.3 选择验证方式

通常有两种验证方式：

#### 方式 A：DNS 验证（推荐）

**步骤：**
1. 证书服务商会提供一条 **TXT 记录**
2. 在您的域名 DNS 解析中添加这条 TXT 记录
3. 等待 DNS 生效（通常几分钟）

**示例：**
```
记录类型：TXT
主机记录：_dnsauth
记录值：abc123def456ghi789（证书服务商提供）
TTL：600
```

#### 方式 B：文件验证

**步骤：**
1. 证书服务商会提供一个验证文件（如 `fileauth.txt`）
2. 将文件上传到您网站的根目录
3. 确保可以通过 `http://guopengfei.top/.well-known/pki-validation/fileauth.txt` 访问

**注意：** 如果使用 Docker，需要将验证文件放到 `html/` 目录。

### 1.4 提交申请

填写完信息后，点击"提交"或"确认"按钮。

### 1.5 等待签发

- **DV 证书**：通常 5-10 分钟
- **OV 证书**：1-3 个工作日
- **EV 证书**：5-7 个工作日

签发完成后，证书状态会变为 **"已签发"** 或 **"有效"**。

---

## 第二步：下载证书

### 2.1 下载证书文件

证书签发完成后，点击 **"下载证书"** 按钮。

### 2.2 证书文件格式

下载的证书通常包含以下文件：

#### 格式 A：PEM 格式（Nginx 常用）

```
证书文件：
- fullchain.crt 或 certificate.crt（包含证书链）
- private.key 或 key.key（私钥文件）

或者：
- cert.pem（证书）
- key.pem（私钥）
- chain.pem（证书链，可选）
```

#### 格式 B：其他格式

如果下载的是其他格式（如 `.p12`、`.pfx`），需要转换为 PEM 格式。

### 2.3 保存证书文件

将证书文件保存到服务器的安全位置，建议：

```bash
# 创建证书目录
sudo mkdir -p /etc/nginx/ssl/guopengfei.top

# 上传证书文件到此目录
# fullchain.crt 或 certificate.crt
# private.key 或 key.key
```

**重要：** 私钥文件（`.key`）必须保密，不要泄露给他人！

---

## 第三步：配置 Nginx 使用 HTTPS

### 3.1 修改 Nginx 配置文件

编辑 Nginx 配置文件（根据您的实际路径）：

```bash
# 如果使用 Docker，编辑项目中的配置文件
nano nginx/nginx.conf

# 或者直接在服务器上编辑
sudo nano /etc/nginx/nginx.conf
# 或
sudo nano /etc/nginx/sites-available/default
```

### 3.2 添加 HTTPS 配置

在配置文件中添加 HTTPS server 块：

```nginx
# HTTP 服务器 - 重定向到 HTTPS
server {
    listen 80;
    server_name guopengfei.top www.guopengfei.top;
    
    # 重定向所有 HTTP 请求到 HTTPS
    return 301 https://$server_name$request_uri;
}

# HTTPS 服务器
server {
    listen 443 ssl http2;
    server_name guopengfei.top www.guopengfei.top;
    
    # SSL 证书配置
    ssl_certificate /etc/nginx/ssl/guopengfei.top/fullchain.crt;
    ssl_certificate_key /etc/nginx/ssl/guopengfei.top/private.key;
    
    # SSL 配置优化
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # 网站根目录
    root /usr/share/nginx/html;
    index index.html;
    
    # 字符集设置
    charset utf-8;
    
    # 安全头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # 静态文件缓存
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
    
    # 主页面
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # API 端点示例
    location /api/time {
        default_type application/json;
        add_header Content-Type application/json;
        return 200 "{\"server_time\":\"$time_iso8601\",\"timestamp\":$msec}";
    }
    
    location /api/info {
        default_type application/json;
        add_header Content-Type application/json;
        return 200 "{\"nginx_version\":\"$nginx_version\",\"server_time\":\"$time_iso8601\",\"host\":\"$host\",\"remote_addr\":\"$remote_addr\"}";
    }
    
    # 禁止访问隐藏文件
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
    
    # 错误页面
    error_page 404 /index.html;
    error_page 500 502 503 504 /index.html;
}
```

### 3.3 如果使用 Docker

如果您使用 Docker，需要：

1. **将证书文件放到项目目录**
   ```bash
   mkdir -p ssl/guopengfei.top
   # 将证书文件复制到此目录
   # fullchain.crt
   # private.key
   ```

2. **修改 docker-compose.yml**
   ```yaml
   services:
     nginx:
       build:
         context: .
         dockerfile: Dockerfile
       container_name: nginx-shop
       ports:
         - "80:80"
         - "443:443"  # 添加 HTTPS 端口
       volumes:
         - ./logs:/var/log/nginx
         - ./ssl:/etc/nginx/ssl:ro  # 挂载证书目录
       restart: unless-stopped
       networks:
         - nginx-network
   ```

3. **修改 nginx.conf 中的证书路径**
   ```nginx
   ssl_certificate /etc/nginx/ssl/guopengfei.top/fullchain.crt;
   ssl_certificate_key /etc/nginx/ssl/guopengfei.top/private.key;
   ```

### 3.4 测试配置文件

```bash
# 测试 Nginx 配置是否正确
sudo nginx -t

# 如果使用 Docker
docker compose config
```

如果显示 `syntax is ok` 和 `test is successful`，说明配置正确。

---

## 第四步：重新加载 Nginx

### 4.1 重新加载配置

```bash
# 重新加载 Nginx（不中断服务）
sudo nginx -s reload

# 或者重启 Nginx
sudo systemctl restart nginx
```

### 4.2 如果使用 Docker

```bash
# 重新构建并启动
docker compose down
docker compose up -d --build

# 查看日志
docker compose logs -f nginx
```

---

## 第五步：配置防火墙

### 5.1 开放 443 端口（HTTPS）

**Ubuntu/Debian (UFW):**
```bash
sudo ufw allow 443/tcp
sudo ufw reload
```

**CentOS/RHEL (firewalld):**
```bash
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload
```

### 5.2 云服务器安全组

在云服务器控制台的**安全组**中开放 443 端口：
- **端口**：443
- **协议**：TCP
- **源**：0.0.0.0/0

---

## 第六步：测试 HTTPS

### 6.1 浏览器访问

在浏览器中访问：
```
https://guopengfei.top
```

**成功标志：**
- ✅ 地址栏显示绿色的锁图标 🔒
- ✅ 显示"安全"或"Secure"
- ✅ 没有警告信息

### 6.2 测试 HTTP 重定向

访问：
```
http://guopengfei.top
```

应该自动重定向到：
```
https://guopengfei.top
```

### 6.3 使用命令行测试

```bash
# 测试 HTTPS 连接
curl -I https://guopengfei.top

# 查看证书信息
openssl s_client -connect guopengfei.top:443 -servername guopengfei.top
```

### 6.4 SSL 测试工具

访问 [SSL Labs](https://www.ssllabs.com/ssltest/) 测试您的 SSL 配置：
```
https://www.ssllabs.com/ssltest/analyze.html?d=guopengfei.top
```

---

## 常见问题

### Q1: 证书下载后文件格式不对怎么办？

**A:** 如果下载的是 `.p12` 或 `.pfx` 格式，需要转换为 PEM 格式：

```bash
# 转换为 PEM 格式
openssl pkcs12 -in certificate.p12 -out certificate.crt -clcerts -nokeys
openssl pkcs12 -in certificate.p12 -out private.key -nocerts -nodes
```

### Q2: Nginx 报错 "SSL certificate file not found"

**A:** 检查：
1. 证书文件路径是否正确
2. 文件权限是否正确（建议 644）
3. 文件是否存在

```bash
# 检查文件
ls -la /etc/nginx/ssl/guopengfei.top/

# 设置权限
sudo chmod 644 /etc/nginx/ssl/guopengfei.top/fullchain.crt
sudo chmod 600 /etc/nginx/ssl/guopengfei.top/private.key
```

### Q3: 浏览器显示"不安全"或证书错误

**A:** 可能原因：
1. 证书域名不匹配（检查 server_name）
2. 证书链不完整（使用 fullchain.crt）
3. 证书过期（检查有效期）
4. 系统时间不正确

### Q4: HTTP 没有自动重定向到 HTTPS

**A:** 检查：
1. HTTP server 块是否正确配置了重定向
2. 是否同时监听了 80 和 443 端口
3. Nginx 配置是否已重新加载

### Q5: 证书到期后怎么办？

**A:** 
1. 在证书到期前（建议提前 30 天）续期或重新购买
2. 下载新证书
3. 替换旧证书文件
4. 重新加载 Nginx：`sudo nginx -s reload`

---

## 完整配置示例（Docker 项目）

### 项目结构

```
nginx-shop/
├── docker-compose.yml
├── Dockerfile
├── nginx/
│   └── nginx.conf
├── html/
│   └── index.html
├── ssl/
│   └── guopengfei.top/
│       ├── fullchain.crt
│       └── private.key
└── logs/
```

### docker-compose.yml

```yaml
services:
  nginx:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: nginx-shop
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./logs:/var/log/nginx
      - ./ssl:/etc/nginx/ssl:ro
    restart: unless-stopped
    networks:
      - nginx-network

networks:
  nginx-network:
    driver: bridge
```

### nginx.conf（HTTPS 部分）

```nginx
# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name guopengfei.top www.guopengfei.top;
    return 301 https://$server_name$request_uri;
}

# HTTPS 服务器
server {
    listen 443 ssl http2;
    server_name guopengfei.top www.guopengfei.top;
    
    ssl_certificate /etc/nginx/ssl/guopengfei.top/fullchain.crt;
    ssl_certificate_key /etc/nginx/ssl/guopengfei.top/private.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    
    root /usr/share/nginx/html;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

---

## 快速检查清单

- [ ] 证书已签发（状态：已签发/有效）
- [ ] 证书文件已下载
- [ ] 证书文件已上传到服务器
- [ ] Nginx 配置已修改（添加 HTTPS server 块）
- [ ] 证书路径配置正确
- [ ] Nginx 配置测试通过（`nginx -t`）
- [ ] Nginx 已重新加载
- [ ] 防火墙已开放 443 端口
- [ ] 云服务器安全组已开放 443 端口
- [ ] 可以通过 HTTPS 访问网站
- [ ] HTTP 自动重定向到 HTTPS
- [ ] 浏览器显示"安全"标识

---

## 完成！

现在您的网站已经配置了 HTTPS，可以安全地传输数据了！

**访问地址：**
- HTTPS: `https://guopengfei.top`
- HTTP 会自动重定向到 HTTPS

**记住：** 证书有效期通常为 1 年，到期前记得续期！

