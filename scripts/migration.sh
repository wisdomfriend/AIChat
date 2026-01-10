#!/bin/bash

# MySQL 和 Redis 数据迁移脚本
# Usage: ./migration.sh [export|import] [service] [backup_file]
# 
# 此脚本用于在服务器之间迁移 MySQL 和 Redis 数据
# 支持导出和导入 nginx_shop 数据库和 Redis 缓存的所有数据

set -e  # 遇到错误立即退出

# 默认值
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
DEFAULT_MYSQL_BACKUP="mysql_backup_$(date +%Y%m%d_%H%M%S).sql"
DEFAULT_REDIS_BACKUP="redis_backup_$(date +%Y%m%d_%H%M%S).rdb"
MYSQL_CONTAINER="mysql-db"
MYSQL_DATABASE="nginx_shop"
MYSQL_USER="guopengfei_learning"
MYSQL_PASSWORD="Gpf_learning"
MYSQL_ROOT_PASSWORD="rootpassword"
REDIS_CONTAINER="redis-cache"
REDIS_PASSWORD="Gpf_learning"
REDIS_DATA_DIR="/data"

# 显示帮助信息
show_help() {
    echo "MySQL 和 Redis 数据迁移工具"
    echo ""
    echo "USAGE:"
    echo "  $0 <operation> [service] [backup_file_or_dir]"
    echo ""
    echo "OPERATIONS:"
    echo "  export   - 导出数据到备份文件"
    echo "  import   - 从备份文件导入数据"
    echo "  help     - 显示此帮助信息"
    echo ""
    echo "SERVICES:"
    echo "  mysql   - 仅操作 MySQL 数据库"
    echo "  redis   - 仅操作 Redis 缓存"
    echo "  all     - 操作 MySQL 和 Redis (默认)"
    echo ""
    echo "PARAMETERS:"
    echo "  backup_file_or_dir  - 备份文件或目录路径"
    echo "                        MySQL: SQL 文件 (默认: 自动生成)"
    echo "                        Redis: RDB 文件 (默认: 自动生成)"
    echo "                        all: 备份目录 (默认: backup_YYYYMMDD_HHMMSS)"
    echo ""
    echo "EXAMPLES:"
    echo "  # 导出所有数据"
    echo "  $0 export                           # 导出到默认目录"
    echo "  $0 export all my_backup            # 导出到指定目录"
    echo ""
    echo "  # 导出 MySQL"
    echo "  $0 export mysql                    # 导出到默认文件"
    echo "  $0 export mysql my_backup.sql      # 导出到指定文件"
    echo ""
    echo "  # 导出 Redis"
    echo "  $0 export redis                    # 导出到默认文件"
    echo "  $0 export redis my_backup.rdb      # 导出到指定文件"
    echo ""
    echo "  # 导入所有数据"
    echo "  $0 import                          # 从默认目录导入"
    echo "  $0 import all my_backup            # 从指定目录导入"
    echo ""
    echo "  # 导入 MySQL"
    echo "  $0 import mysql                    # 从默认文件导入"
    echo "  $0 import mysql my_backup.sql      # 从指定文件导入"
    echo ""
    echo "  # 导入 Redis"
    echo "  $0 import redis                    # 从默认文件导入"
    echo "  $0 import redis my_backup.rdb      # 从指定文件导入"
    echo ""
    echo "注意事项:"
    echo "  - 导出操作会在容器运行时执行，无需停止服务"
    echo "  - 导入操作会清空现有数据并替换为新数据，请谨慎操作"
    echo "  - 建议在导入前先执行导出操作备份当前数据"
    echo "  - 确保相关容器正在运行"
}

# 检查 Docker 是否运行
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        echo "❌ 错误: Docker 未运行或无法访问"
        echo "请启动 Docker 后重试"
        exit 1
    fi
}

# 检查 MySQL 容器是否运行
check_mysql_container() {
    if ! docker ps --format "{{.Names}}" | grep -q "^${MYSQL_CONTAINER}$"; then
        echo "❌ 错误: MySQL 容器 '${MYSQL_CONTAINER}' 未运行"
        echo "请先启动 MySQL 容器:"
        echo "   docker-compose up -d mysql"
        exit 1
    fi
    echo "✅ MySQL 容器运行正常"
}

# 检查 Redis 容器是否运行
check_redis_container() {
    if ! docker ps --format "{{.Names}}" | grep -q "^${REDIS_CONTAINER}$"; then
        echo "❌ 错误: Redis 容器 '${REDIS_CONTAINER}' 未运行"
        echo "请先启动 Redis 容器:"
        echo "   docker-compose up -d redis"
        exit 1
    fi
    echo "✅ Redis 容器运行正常"
}

# 确认用户操作
confirm_action() {
    local message=$1
    echo -n "$message (y/N): "
    read -r response
    case "$response" in
        [yY]|[yY][eE][sS]) return 0 ;;
        *) return 1 ;;
    esac
}

# 执行 MySQL 导出操作
perform_mysql_export() {
    local backup_file=$1
    
    echo "🚀 开始导出 MySQL 数据..."
    echo "📁 备份文件: $backup_file"
    echo "🗄️  数据库: $MYSQL_DATABASE"
    echo ""
    
    # 检查容器
    check_mysql_container
    
    # 检查文件是否已存在
    if [ -f "$backup_file" ]; then
        echo "⚠️  警告: 文件 '$backup_file' 已存在"
        if ! confirm_action "是否覆盖现有文件?"; then
            echo "❌ 导出操作已取消"
            return 1
        fi
    fi
    
    # 执行导出
    echo "📦 正在导出数据..."
    docker exec ${MYSQL_CONTAINER} mysqldump \
        -u${MYSQL_USER} \
        -p${MYSQL_PASSWORD} \
        --routines \
        --triggers \
        --events \
        --add-drop-database \
        --no-tablespaces \
        --databases ${MYSQL_DATABASE} 2>/dev/null > "$backup_file"
    
    if [ $? -eq 0 ]; then
        local size=$(ls -lh "$backup_file" | awk '{print $5}')
        echo "✅ MySQL 导出成功!"
        echo "📍 备份文件: $(pwd)/$backup_file"
        echo "📊 文件大小: $size"
        return 0
    else
        echo "❌ MySQL 导出失败，请检查错误信息"
        return 1
    fi
}

# 执行 Redis 导出操作
perform_redis_export() {
    local backup_file=$1
    
    echo "🚀 开始导出 Redis 数据..."
    echo "📁 备份文件: $backup_file"
    echo ""
    
    # 检查容器
    check_redis_container
    
    # 检查文件是否已存在
    if [ -f "$backup_file" ]; then
        echo "⚠️  警告: 文件 '$backup_file' 已存在"
        if ! confirm_action "是否覆盖现有文件?"; then
            echo "❌ 导出操作已取消"
            return 1
        fi
    fi
    
    # 执行导出 - 使用 BGSAVE 创建 RDB 快照
    echo "📦 正在创建 Redis 快照..."
    docker exec ${REDIS_CONTAINER} redis-cli -a "${REDIS_PASSWORD}" --no-auth-warning BGSAVE >/dev/null 2>&1
    
    # 等待 BGSAVE 完成 - 使用 INFO persistence 检查
    echo "⏳ 等待快照完成..."
    local max_wait=60
    local waited=0
    while [ $waited -lt $max_wait ]; do
        local bgsave_status=$(docker exec ${REDIS_CONTAINER} redis-cli -a "${REDIS_PASSWORD}" --no-auth-warning INFO persistence 2>/dev/null | grep -o "rdb_bgsave_in_progress:[0-9]*" | cut -d: -f2)
        if [ "$bgsave_status" = "0" ]; then
            break
        fi
        sleep 1
        waited=$((waited + 1))
    done
    
    if [ $waited -ge $max_wait ]; then
        echo "⚠️  警告: BGSAVE 等待超时，但继续尝试复制文件..."
    fi
    
    # 查找 RDB 文件位置
    local rdb_path=$(docker exec ${REDIS_CONTAINER} redis-cli -a "${REDIS_PASSWORD}" --no-auth-warning CONFIG GET dir 2>/dev/null | grep -v "^dir$" | tr -d '\r' | head -n1)
    local rdb_file="${rdb_path}/dump.rdb"
    
    # 复制 RDB 文件到宿主机
    echo "📥 正在复制 RDB 文件..."
    docker cp ${REDIS_CONTAINER}:${rdb_file} "$backup_file"
    
    if [ $? -eq 0 ]; then
        local size=$(ls -lh "$backup_file" | awk '{print $5}')
        echo "✅ Redis 导出成功!"
        echo "📍 备份文件: $(pwd)/$backup_file"
        echo "📊 文件大小: $size"
        return 0
    else
        echo "❌ Redis 导出失败，请检查错误信息"
        return 1
    fi
}

# 执行导出操作（根据服务类型）
perform_export() {
    local service=$1
    local backup_path=$2
    
    case "$service" in
        mysql)
            perform_mysql_export "$backup_path"
            ;;
        redis)
            perform_redis_export "$backup_path"
            ;;
        all)
            # 创建备份目录
            mkdir -p "$backup_path"
            local mysql_file="${backup_path}/mysql_backup.sql"
            local redis_file="${backup_path}/redis_backup.rdb"
            
            echo "🚀 开始导出所有数据..."
            echo "📁 备份目录: $backup_path"
            echo ""
            
            local mysql_ok=false
            local redis_ok=false
            
            # 导出 MySQL
            if perform_mysql_export "$mysql_file"; then
                mysql_ok=true
            fi
            echo ""
            
            # 导出 Redis
            if perform_redis_export "$redis_file"; then
                redis_ok=true
            fi
            echo ""
            
            if [ "$mysql_ok" = true ] && [ "$redis_ok" = true ]; then
                echo "🎉 所有数据导出成功!"
                echo "📍 备份目录: $(pwd)/$backup_path"
                echo "💡 提示: 可以将此目录传输到新服务器后使用 import all 命令导入"
            else
                echo "⚠️  部分数据导出失败，请检查上述错误信息"
                exit 1
            fi
            ;;
        *)
            echo "❌ 错误: 未知的服务类型 '$service'"
            exit 1
            ;;
    esac
}

# 执行 MySQL 导入操作
perform_mysql_import() {
    local backup_file=$1
    
    echo "🔄 开始导入 MySQL 数据..."
    echo "📁 备份文件: $backup_file"
    echo "🗄️  数据库: $MYSQL_DATABASE"
    echo ""
    
    # 检查容器
    check_mysql_container
    
    # 检查备份文件是否存在
    if [ ! -f "$backup_file" ]; then
        echo "❌ 错误: 备份文件 '$backup_file' 不存在"
        echo "请确保文件路径正确"
        return 1
    fi
    
    # 警告用户
    echo "⚠️  警告: 导入操作将执行以下操作:"
    echo "  1. 删除现有数据库 '${MYSQL_DATABASE}' (如果存在)"
    echo "  2. 创建新数据库 '${MYSQL_DATABASE}'"
    echo "  3. 导入备份文件中的所有数据"
    echo ""
    echo "🔴 重要: 此操作会覆盖现有数据!"
    echo ""
    
    if ! confirm_action "确定要继续导入吗?"; then
        echo "❌ 导入操作已取消"
        return 1
    fi
    
    # 执行导入
    echo "📥 正在导入数据..."
    docker exec -i ${MYSQL_CONTAINER} mysql \
        -uroot \
        -p${MYSQL_ROOT_PASSWORD} < "$backup_file"
    
    if [ $? -eq 0 ]; then
        echo "✅ MySQL 导入成功!"
        return 0
    else
        echo "❌ MySQL 导入失败，请检查错误信息"
        return 1
    fi
}

# 执行 Redis 导入操作
perform_redis_import() {
    local backup_file=$1
    
    echo "🔄 开始导入 Redis 数据..."
    echo "📁 备份文件: $backup_file"
    echo ""
    
    # 检查容器
    check_redis_container
    
    # 检查备份文件是否存在
    if [ ! -f "$backup_file" ]; then
        echo "❌ 错误: 备份文件 '$backup_file' 不存在"
        echo "请确保文件路径正确"
        return 1
    fi
    
    # 警告用户
    echo "⚠️  警告: 导入操作将执行以下操作:"
    echo "  1. 停止 Redis 服务"
    echo "  2. 替换 Redis 数据文件"
    echo "  3. 删除 AOF 文件（如果存在）"
    echo "  4. 重启 Redis 服务"
    echo ""
    echo "🔴 重要: 此操作会覆盖现有数据!"
    echo ""
    
    if ! confirm_action "确定要继续导入吗?"; then
        echo "❌ 导入操作已取消"
        return 1
    fi
    
    # 获取 Redis 数据目录和 AOF 文件路径
    local rdb_path=$(docker exec ${REDIS_CONTAINER} redis-cli -a "${REDIS_PASSWORD}" --no-auth-warning CONFIG GET dir 2>/dev/null | grep -v "^dir$" | tr -d '\r' | head -n1)
    local rdb_file="${rdb_path}/dump.rdb"
    local aof_file="${rdb_path}/appendonly.aof"
    
    # 停止 Redis（优雅关闭并保存）
    echo "🛑 正在停止 Redis 服务..."
    docker exec ${REDIS_CONTAINER} redis-cli -a "${REDIS_PASSWORD}" --no-auth-warning SHUTDOWN SAVE 2>/dev/null || true
    
    # 等待容器停止
    echo "⏳ 等待 Redis 容器停止..."
    local max_wait=10
    local waited=0
    while docker ps --format "{{.Names}}" | grep -q "^${REDIS_CONTAINER}$" && [ $waited -lt $max_wait ]; do
        sleep 1
        waited=$((waited + 1))
    done
    
    # 如果容器仍在运行，强制停止
    if docker ps --format "{{.Names}}" | grep -q "^${REDIS_CONTAINER}$"; then
        echo "⚠️  容器仍在运行，正在强制停止..."
        docker stop ${REDIS_CONTAINER}
        sleep 2
    fi
    
    # 使用临时容器挂载 Redis volume 来复制文件
    echo "📥 正在复制 RDB 文件到 Redis 数据目录..."
    
    # 获取备份文件的绝对路径（兼容不同系统）
    local backup_abs_path
    if [ -f "$backup_file" ]; then
        # 如果是相对路径，转换为绝对路径
        if [[ "$backup_file" != /* ]]; then
            backup_abs_path="$(cd "$(dirname "$backup_file")" && pwd)/$(basename "$backup_file")"
        else
            backup_abs_path="$backup_file"
        fi
    else
        backup_abs_path="$backup_file"
    fi
    local backup_dir=$(dirname "$backup_abs_path")
    local backup_filename=$(basename "$backup_abs_path")
    
    # 获取 Redis volume 名称
    local redis_volume=$(docker inspect ${REDIS_CONTAINER} --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}' 2>/dev/null || echo "")
    
    if [ -z "$redis_volume" ]; then
        echo "❌ 无法找到 Redis volume"
        echo "💡 提示: 正在重启 Redis 容器..."
        docker start ${REDIS_CONTAINER} 2>/dev/null || true
        return 1
    fi
    
    # 使用临时容器复制文件到 volume
    docker run --rm \
        -v "$redis_volume:/data" \
        -v "$backup_dir:/backup:ro" \
        alpine sh -c "cp /backup/$backup_filename /data/dump.rdb && rm -f /data/appendonly.aof && chown 999:999 /data/dump.rdb"
    
    if [ $? -ne 0 ]; then
        echo "❌ 复制 RDB 文件失败"
        echo "💡 提示: 正在重启 Redis 容器..."
        docker start ${REDIS_CONTAINER} 2>/dev/null || true
        return 1
    fi
    
    # 启动 Redis 容器
    echo "🚀 正在启动 Redis 容器..."
    docker start ${REDIS_CONTAINER}
    
    # 等待 Redis 启动
    echo "⏳ 等待 Redis 启动..."
    sleep 5
    
    # 验证 Redis 是否正常运行
    local max_retries=10
    local retry=0
    while [ $retry -lt $max_retries ]; do
        if docker exec ${REDIS_CONTAINER} redis-cli -a "${REDIS_PASSWORD}" --no-auth-warning ping >/dev/null 2>&1; then
            echo "✅ Redis 导入成功!"
            return 0
        fi
        sleep 1
        retry=$((retry + 1))
    done
    
    echo "❌ Redis 导入后启动失败，请检查错误信息"
    echo "💡 提示: 可以查看容器日志: docker logs ${REDIS_CONTAINER}"
    return 1
}

# 执行导入操作（根据服务类型）
perform_import() {
    local service=$1
    local backup_path=$2
    
    case "$service" in
        mysql)
            perform_mysql_import "$backup_path"
            ;;
        redis)
            perform_redis_import "$backup_path"
            ;;
        all)
            local backup_dir="$backup_path"
            local mysql_file="${backup_dir}/mysql_backup.sql"
            local redis_file="${backup_dir}/redis_backup.rdb"
            
            echo "🔄 开始导入所有数据..."
            echo "📁 备份目录: $backup_dir"
            echo ""
            
            # 检查备份目录是否存在
            if [ ! -d "$backup_dir" ]; then
                echo "❌ 错误: 备份目录 '$backup_dir' 不存在"
                echo "请确保目录路径正确"
                exit 1
            fi
            
            local mysql_ok=false
            local redis_ok=false
            
            # 导入 MySQL
            if [ -f "$mysql_file" ]; then
                if perform_mysql_import "$mysql_file"; then
                    mysql_ok=true
                fi
                echo ""
            else
                echo "⚠️  警告: MySQL 备份文件 '$mysql_file' 不存在，跳过"
                echo ""
            fi
            
            # 导入 Redis
            if [ -f "$redis_file" ]; then
                if perform_redis_import "$redis_file"; then
                    redis_ok=true
                fi
                echo ""
            else
                echo "⚠️  警告: Redis 备份文件 '$redis_file' 不存在，跳过"
                echo ""
            fi
            
            if [ "$mysql_ok" = true ] || [ "$redis_ok" = true ]; then
                echo "🎉 数据导入完成!"
                echo "💡 提示: 可以重启应用服务:"
                echo "   docker-compose restart flask-app"
            else
                echo "❌ 所有数据导入失败，请检查上述错误信息"
                exit 1
            fi
            ;;
        *)
            echo "❌ 错误: 未知的服务类型 '$service'"
            exit 1
            ;;
    esac
}

# 主函数
main() {
    # 检查 Docker
    check_docker
    
    # 解析命令行参数
    local operation=${1:-}
    local service=${2:-all}
    local backup_path=${3:-}
    
    # 处理帮助或无参数情况
    if [ -z "$operation" ] || [ "$operation" = "help" ] || [ "$operation" = "-h" ] || [ "$operation" = "--help" ]; then
        show_help
        exit 0
    fi
    
    # 如果第二个参数是文件路径而不是服务名，则调整参数
    if [ "$operation" = "export" ] || [ "$operation" = "import" ]; then
        # 检查第二个参数是否是服务名
        if [ "$service" != "mysql" ] && [ "$service" != "redis" ] && [ "$service" != "all" ]; then
            # 第二个参数是文件路径，服务默认为 all
            backup_path="$service"
            service="all"
        fi
        
        # 设置默认备份路径
        if [ -z "$backup_path" ]; then
            if [ "$service" = "all" ]; then
                backup_path="$BACKUP_DIR"
            elif [ "$service" = "mysql" ]; then
                backup_path="$DEFAULT_MYSQL_BACKUP"
            elif [ "$service" = "redis" ]; then
                backup_path="$DEFAULT_REDIS_BACKUP"
            fi
        fi
    fi
    
    # 验证操作类型
    case "$operation" in
        export)
            perform_export "$service" "$backup_path"
            ;;
        import)
            perform_import "$service" "$backup_path"
            ;;
        *)
            echo "❌ 错误: 无效的操作 '$operation'"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数，传递所有参数
main "$@"
