FROM nginx:alpine

# 复制自定义 nginx 配置
COPY nginx/nginx.conf /etc/nginx/nginx.conf

# 复制静态文件到 nginx 默认目录
COPY html/ /usr/share/nginx/html/

# 暴露端口
EXPOSE 80

# 启动 nginx
CMD ["nginx", "-g", "daemon off;"]

