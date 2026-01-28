#!/bin/bash

# mdserver-web 服务器端部署脚本
# 功能：备份现有目录 -> 解压新包 -> 覆盖 -> 重启服务
#
# 使用方法：
# 1. 将项目打包成 zip 文件，上传到服务器的 /www/server 目录
# 2. 在服务器上运行此脚本: bash deploy_on_server.sh [zip文件名]
#    如果不指定文件名，脚本会查找 /www/server 目录下最新的 zip 文件

# 配置参数
TARGET_DIR="/www/server/mdserver-web"
BACKUP_DIR="/www/server"
ZIP_DIR="/www/server"

# 生成时间戳
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="mdserver-web-${TIMESTAMP}.zip"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为 root 用户
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "此脚本需要 root 权限运行"
        print_info "请使用: sudo bash $0"
        exit 1
    fi
}

# 查找 zip 文件
find_zip_file() {
    local zip_file="$1"
    
    if [ -n "$zip_file" ]; then
        # 如果指定了文件名，检查是否存在
        if [ ! -f "$zip_file" ]; then
            # 如果不是完整路径，尝试在 ZIP_DIR 下查找
            if [ ! -f "${ZIP_DIR}/${zip_file}" ]; then
                print_error "找不到指定的 zip 文件: $zip_file"
                exit 1
            else
                echo "${ZIP_DIR}/${zip_file}"
            fi
        else
            echo "$zip_file"
        fi
    else
        # 如果没有指定，查找 ZIP_DIR 目录下最新的 zip 文件
        print_info "未指定 zip 文件，查找 ${ZIP_DIR} 目录下最新的 zip 文件..."
        local latest_zip=$(find "$ZIP_DIR" -maxdepth 1 -name "*.zip" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
        
        if [ -z "$latest_zip" ]; then
            # 如果 find -printf 不支持，使用 ls 方式
            latest_zip=$(ls -t "${ZIP_DIR}"/*.zip 2>/dev/null | head -1)
        fi
        
        if [ -z "$latest_zip" ] || [ ! -f "$latest_zip" ]; then
            print_error "在 ${ZIP_DIR} 目录下找不到 zip 文件"
            print_info "请将 zip 文件上传到 ${ZIP_DIR} 目录，或指定文件路径"
            exit 1
        fi
        
        echo "$latest_zip"
    fi
}

# 备份现有目录
backup_directory() {
    print_info "步骤 1/5: 备份现有目录..."
    
    if [ ! -d "$TARGET_DIR" ]; then
        print_warn "目标目录 ${TARGET_DIR} 不存在，跳过备份"
        return 0
    fi
    
    print_info "正在备份 ${TARGET_DIR} 到 ${BACKUP_DIR}/${BACKUP_NAME}..."
    
    cd "$BACKUP_DIR" || exit 1
    
    # 使用 zip 命令备份
    if command -v zip &> /dev/null; then
        zip -r "$BACKUP_NAME" mdserver-web > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            local backup_size=$(du -h "$BACKUP_NAME" | cut -f1)
            print_info "备份完成: ${BACKUP_DIR}/${BACKUP_NAME} (大小: ${backup_size})"
        else
            print_error "备份失败！"
            exit 1
        fi
    else
        # 如果没有 zip，使用 tar
        print_warn "未找到 zip 命令，使用 tar 进行备份..."
        tar -czf "${BACKUP_NAME%.zip}.tar.gz" mdserver-web > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            local backup_size=$(du -h "${BACKUP_NAME%.zip}.tar.gz" | cut -f1)
            print_info "备份完成: ${BACKUP_DIR}/${BACKUP_NAME%.zip}.tar.gz (大小: ${backup_size})"
            BACKUP_NAME="${BACKUP_NAME%.zip}.tar.gz"
        else
            print_error "备份失败！"
            exit 1
        fi
    fi
}

# 停止服务
stop_service() {
    print_info "步骤 2/5: 停止服务..."
    
    # 尝试多种方式停止服务
    if systemctl is-active --quiet mw 2>/dev/null; then
        print_info "使用 systemctl 停止 mw 服务..."
        systemctl stop mw
    elif [ -f /etc/init.d/mw ]; then
        print_info "使用 init.d 停止 mw 服务..."
        /etc/init.d/mw stop
    elif [ -f "$TARGET_DIR/cli.sh" ]; then
        print_info "使用 cli.sh 停止服务..."
        cd "$TARGET_DIR" && bash cli.sh stop
    else
        # 手动停止进程
        print_info "手动停止相关进程..."
        pkill -f "gunicorn.*app:app" 2>/dev/null
        pkill -f "panel_task.py" 2>/dev/null
        sleep 2
    fi
    
    # 确认进程已停止
    local running=$(ps aux | grep -E "gunicorn.*app:app|panel_task.py" | grep -v grep)
    if [ -n "$running" ]; then
        print_warn "仍有进程在运行，强制停止..."
        pkill -9 -f "gunicorn.*app:app" 2>/dev/null
        pkill -9 -f "panel_task.py" 2>/dev/null
        sleep 1
    fi
    
    print_info "服务已停止"
}

# 解压并覆盖
deploy_files() {
    local zip_file="$1"
    
    print_info "步骤 3/5: 解压并部署文件..."
    print_info "解压文件: $zip_file"
    
    # 创建临时解压目录
    local temp_dir="/tmp/mdserver-web-deploy-$$"
    mkdir -p "$temp_dir"
    
    # 解压 zip 文件
    if command -v unzip &> /dev/null; then
        unzip -q "$zip_file" -d "$temp_dir"
        if [ $? -ne 0 ]; then
            print_error "解压失败！"
            rm -rf "$temp_dir"
            exit 1
        fi
    else
        print_error "未找到 unzip 命令，请先安装: yum install unzip 或 apt-get install unzip"
        rm -rf "$temp_dir"
        exit 1
    fi
    
    # 查找解压后的目录（可能是 tpanel 或 mdserver-web）
    local extracted_dir=""
    if [ -d "$temp_dir/tpanel" ]; then
        extracted_dir="$temp_dir/tpanel"
    elif [ -d "$temp_dir/mdserver-web" ]; then
        extracted_dir="$temp_dir/mdserver-web"
    else
        # 如果只有一个子目录，使用它
        local subdirs=$(find "$temp_dir" -maxdepth 1 -type d ! -path "$temp_dir")
        if [ $(echo "$subdirs" | wc -l) -eq 1 ]; then
            extracted_dir=$(echo "$subdirs" | head -1)
        else
            extracted_dir="$temp_dir"
        fi
    fi
    
    print_info "找到解压目录: $extracted_dir"
    
    # 备份现有目录（如果存在）
    if [ -d "$TARGET_DIR" ]; then
        print_info "清理现有目录..."
        # 先移动到临时位置（双重保险）
        local old_dir_backup="/tmp/mdserver-web-old-$$"
        mv "$TARGET_DIR" "$old_dir_backup" 2>/dev/null
    fi
    
    # 创建目标目录
    mkdir -p "$(dirname "$TARGET_DIR")"
    
    # 移动解压的文件到目标目录
    print_info "部署文件到 ${TARGET_DIR}..."
    mv "$extracted_dir" "$TARGET_DIR"
    
    # 设置权限
    chown -R root:root "$TARGET_DIR"
    chmod -R 755 "$TARGET_DIR"
    
    # 清理临时目录
    rm -rf "$temp_dir"
    rm -rf "$old_dir_backup" 2>/dev/null
    
    print_info "文件部署完成"
}

# 安装依赖
install_dependencies() {
    print_info "步骤 3.5/4: 安装 Python 依赖..."
    
    # 检测是否在中国（用于选择 pip 源）
    LOCAL_ADDR="common"
    cn=$(curl -fsSL -m 5 -s http://ipinfo.io/json 2>/dev/null | grep "\"country\": \"CN\"" || echo "")
    if [ ! -z "$cn" ]; then
        LOCAL_ADDR="cn"
        PIPSRC="https://pypi.tuna.tsinghua.edu.cn/simple"
    else
        PIPSRC="https://pypi.python.org/simple"
    fi
    
    print_info "使用 pip 源: $PIPSRC"
    
    # 检查 Python 版本
    if ! command -v python3 &> /dev/null; then
        print_error "未找到 python3，请先安装 Python 3"
        exit 1
    fi
    
    P_VER=$(python3 -V 2>&1 | awk '{print $2}')
    print_info "Python 版本: $P_VER"
    
    # 创建或激活虚拟环境
    if [ ! -f "$TARGET_DIR/bin/activate" ]; then
        print_info "创建虚拟环境..."
        cd "$TARGET_DIR" || exit 1
        
        # 根据 Python 版本选择创建方式
        P_VER_MAJOR=$(echo "$P_VER" | awk -F '.' '{print $1}')
        P_VER_MINOR=$(echo "$P_VER" | awk -F '.' '{print $2}')
        
        if [ "$P_VER_MAJOR" -gt 3 ] || ([ "$P_VER_MAJOR" -eq 3 ] && [ "$P_VER_MINOR" -ge 11 ]); then
            print_info "Python >= 3.11，使用新方式创建虚拟环境"
            python3 -m venv "$TARGET_DIR"
        else
            print_info "Python < 3.11，使用传统方式创建虚拟环境"
            python3 -m venv .
        fi
    fi
    
    # 激活虚拟环境并安装依赖
    print_info "激活虚拟环境并安装依赖..."
    cd "$TARGET_DIR" || exit 1
    source "$TARGET_DIR/bin/activate"
    
    # 升级 pip
    print_info "升级 pip..."
    pip3 install --upgrade pip setuptools wheel -i "$PIPSRC" > /dev/null 2>&1
    
    # 安装 requirements.txt
    if [ -f "$TARGET_DIR/requirements.txt" ]; then
        print_info "安装 requirements.txt 中的依赖..."
        pip3 install -r "$TARGET_DIR/requirements.txt" -i "$PIPSRC"
        if [ $? -ne 0 ]; then
            print_warn "使用国内源安装失败，尝试使用官方源..."
            pip3 install -r "$TARGET_DIR/requirements.txt"
        fi
    else
        print_warn "未找到 requirements.txt 文件"
    fi
    
    # 安装版本特定的依赖
    P_VER_D=$(echo "$P_VER" | awk -F '.' '{print $1}')
    P_VER_M=$(echo "$P_VER" | awk -F '.' '{print $2}')
    NEW_P_VER="${P_VER_D}.${P_VER_M}"
    
    if [ -f "$TARGET_DIR/version/r${NEW_P_VER}.txt" ]; then
        print_info "安装版本特定依赖: version/r${NEW_P_VER}.txt"
        pip3 install -r "$TARGET_DIR/version/r${NEW_P_VER}.txt" -i "$PIPSRC"
    fi
    
    # 创建必要的目录和文件
    mkdir -p "$TARGET_DIR/data"
    mkdir -p "$TARGET_DIR/logs"
    chmod 755 "$TARGET_DIR/data"
    
    # 如果端口文件不存在，创建默认端口文件
    if [ ! -f "$TARGET_DIR/data/port.pl" ]; then
        echo "7200" > "$TARGET_DIR/data/port.pl"
        print_info "创建默认端口配置文件: 7200"
    fi
    
    print_info "依赖安装完成"
}

# 重启服务
restart_service() {
    print_info "步骤 5/5: 重启服务..."
    
    # 尝试多种方式启动服务
    if systemctl list-unit-files | grep -q "mw.service"; then
        print_info "使用 systemctl 启动 mw 服务..."
        systemctl start mw
        sleep 2
        if systemctl is-active --quiet mw; then
            print_info "服务启动成功"
        else
            print_error "服务启动失败，查看状态:"
            systemctl status mw --no-pager
        fi
    elif [ -f /etc/init.d/mw ]; then
        print_info "使用 init.d 启动 mw 服务..."
        /etc/init.d/mw start
        sleep 2
    elif [ -f "$TARGET_DIR/cli.sh" ]; then
        print_info "使用 cli.sh 启动服务..."
        cd "$TARGET_DIR" && bash cli.sh start
        sleep 2
    else
        print_warn "未找到服务启动脚本，请手动启动服务"
        print_info "可以尝试: cd $TARGET_DIR && bash cli.sh start"
    fi
    
    # 检查服务是否运行
    sleep 3
    local running=$(ps aux | grep -E "gunicorn.*app:app|panel_task.py" | grep -v grep)
    if [ -n "$running" ]; then
        print_info "服务运行正常"
        echo "$running" | head -2
    else
        print_warn "未检测到服务进程，请检查服务状态"
    fi
}

# 主函数
main() {
    echo "=========================================="
    echo "  mdserver-web 服务器端部署脚本"
    echo "=========================================="
    echo ""
    
    # 检查 root 权限
    check_root
    
    # 查找 zip 文件
    ZIP_FILE=$(find_zip_file "$1")
    if [ -z "$ZIP_FILE" ]; then
        exit 1
    fi
    
    print_info "使用 zip 文件: $ZIP_FILE"
    echo ""
    
    # 确认操作
    print_warn "即将执行以下操作："
    echo "  1. 备份 ${TARGET_DIR} 到 ${BACKUP_DIR}/${BACKUP_NAME}"
    echo "  2. 停止服务"
    echo "  3. 解压并部署: $ZIP_FILE -> ${TARGET_DIR}"
    echo "  4. 安装 Python 依赖"
    echo "  5. 重启服务"
    echo ""
    read -p "确认继续？(y/n): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        print_info "操作已取消"
        exit 0
    fi
    echo ""
    
    # 执行部署流程
    backup_directory
    echo ""
    
    stop_service
    echo ""
    
    deploy_files "$ZIP_FILE"
    echo ""
    
    install_dependencies
    echo ""
    
    restart_service
    echo ""
    
    print_info "=========================================="
    print_info "部署完成！"
    print_info "=========================================="
    print_info "备份文件: ${BACKUP_DIR}/${BACKUP_NAME}"
    print_info "目标目录: ${TARGET_DIR}"
    echo ""
}

# 执行主函数
main "$@"
