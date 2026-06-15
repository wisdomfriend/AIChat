#!/bin/bash

# MySQL data export/import tool
# Usage: ./mysql_data_tool.sh [export|import] [backup_file]

set -e

DEFAULT_MYSQL_BACKUP="mysql_backup_$(date +%Y%m%d_%H%M%S).sql"
MYSQL_CONTAINER="mysql-db"
MYSQL_DATABASE="nginx_shop"
MYSQL_USER="guopengfei_learning"
MYSQL_PASSWORD="Gpf_learning"
MYSQL_ROOT_PASSWORD="rootpassword-new123"

show_help() {
    echo "MySQL data export/import tool"
    echo ""
    echo "USAGE:"
    echo "  $0 <operation> [backup_file]"
    echo ""
    echo "OPERATIONS:"
    echo "  export   - export database to SQL file"
    echo "  import   - import database from SQL file"
    echo "  help     - show this help message"
    echo ""
    echo "PARAMETERS:"
    echo "  backup_file  - SQL backup file path"
    echo "                 default: mysql_backup_YYYYMMDD_HHMMSS.sql"
    echo ""
    echo "EXAMPLES:"
    echo "  $0 export"
    echo "  $0 export my_backup.sql"
    echo "  $0 import my_backup.sql"
    echo ""
    echo "NOTES:"
    echo "  - export runs while container is running"
    echo "  - import will overwrite existing data"
    echo "  - make sure MySQL container is running"
}

check_docker() {
    if ! docker info >/dev/null 2>&1; then
        echo "ERROR: Docker is not running or not accessible"
        exit 1
    fi
}

check_mysql_container() {
    if ! docker ps --format "{{.Names}}" | grep -q "^${MYSQL_CONTAINER}$"; then
        echo "ERROR: MySQL container '${MYSQL_CONTAINER}' is not running"
        echo "Start it with: docker compose up -d mysql"
        exit 1
    fi
    echo "MySQL container is running"
}

confirm_action() {
    local message=$1
    echo -n "$message (y/N): "
    read -r response
    case "$response" in
        [yY]|[yY][eE][sS]) return 0 ;;
        *) return 1 ;;
    esac
}

perform_mysql_export() {
    local backup_file=$1

    echo "Exporting MySQL database..."
    echo "Backup file: $backup_file"
    echo "Database: $MYSQL_DATABASE"
    echo ""

    check_mysql_container

    if [ -f "$backup_file" ]; then
        echo "WARNING: file already exists: $backup_file"
        if ! confirm_action "Overwrite existing file?"; then
            echo "Export cancelled"
            return 1
        fi
    fi

    echo "Running mysqldump..."
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
        local size
        size=$(ls -lh "$backup_file" | awk '{print $5}')
        echo "Export succeeded"
        echo "Backup file: $(pwd)/$backup_file"
        echo "File size: $size"
        return 0
    else
        echo "Export failed"
        return 1
    fi
}

perform_mysql_import() {
    local backup_file=$1

    echo "Importing MySQL database..."
    echo "Backup file: $backup_file"
    echo "Database: $MYSQL_DATABASE"
    echo ""

    check_mysql_container

    if [ ! -f "$backup_file" ]; then
        echo "ERROR: backup file not found: $backup_file"
        return 1
    fi

    echo "WARNING: import will:"
    echo "  1. drop database '${MYSQL_DATABASE}' if it exists"
    echo "  2. recreate database '${MYSQL_DATABASE}'"
    echo "  3. restore all data from backup file"
    echo ""
    echo "This will overwrite existing data."
    echo ""

    if ! confirm_action "Continue import?"; then
        echo "Import cancelled"
        return 1
    fi

    echo "Running mysql import..."
    docker exec -i ${MYSQL_CONTAINER} mysql \
        -uroot \
        -p${MYSQL_ROOT_PASSWORD} < "$backup_file"

    if [ $? -eq 0 ]; then
        echo "Import succeeded"
        return 0
    else
        echo "Import failed"
        return 1
    fi
}

main() {
    check_docker

    local operation=${1:-}
    local backup_file=${2:-}

    if [ -z "$operation" ] || [ "$operation" = "help" ] || [ "$operation" = "-h" ] || [ "$operation" = "--help" ]; then
        show_help
        exit 0
    fi

    if [ -z "$backup_file" ]; then
        backup_file="$DEFAULT_MYSQL_BACKUP"
    fi

    case "$operation" in
        export)
            perform_mysql_export "$backup_file"
            ;;
        import)
            perform_mysql_import "$backup_file"
            ;;
        *)
            echo "ERROR: invalid operation: $operation"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
