#!/bin/bash

# mdserver-web 远程同步脚本
# 功能：先备份远程服务器上的目录，然后从开发机同步文件到服务器
#
# 使用说明：
# 1. 需要先安装 expect: brew install expect (macOS) 或 apt-get install expect (Linux)
# 2. 运行脚本: ./sync_to_server.sh
# 3. 按提示输入服务器地址、普通账号用户名和 root 密码
# 4. 脚本会自动备份远程目录，然后同步文件
#
# 注意：
# - 普通账号需要能够 SSH 登录（支持密钥或密码认证）
# - 普通账号需要有 su root 的权限
# - 如果普通账号使用密码认证，rsync 同步时会提示输入密码

# 配置参数
REMOTE_DIR="/www/server/mdserver-web"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"  # 脚本所在目录（项目根目录）
REMOTE_BACKUP_DIR="/www/server"  # 备份文件存放目录

# 生成时间戳
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="mdserver-web-${TIMESTAMP}.zip"

# 全局变量（通过交互输入）
REMOTE_HOST=""
REMOTE_USER=""
ROOT_PASSWORD=""

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

# 交互式输入配置信息
input_config() {
    echo ""
    print_info "请输入服务器连接信息："
    echo ""
    
    # 输入服务器地址
    read -p "服务器地址 (IP或域名): " REMOTE_HOST
    if [ -z "$REMOTE_HOST" ]; then
        print_error "服务器地址不能为空！"
        exit 1
    fi
    
    # 输入普通账号用户名
    read -p "普通账号用户名: " REMOTE_USER
    if [ -z "$REMOTE_USER" ]; then
        print_error "用户名不能为空！"
        exit 1
    fi
    
    # 输入 root 密码（用于 su root）
    echo ""
    print_warn "需要 root 权限执行备份和同步操作"
    read -sp "请输入 root 密码: " ROOT_PASSWORD
    echo ""
    if [ -z "$ROOT_PASSWORD" ]; then
        print_error "root 密码不能为空！"
        exit 1
    fi
    
    echo ""
    print_info "配置信息："
    echo "  服务器地址: ${REMOTE_HOST}"
    echo "  普通账号: ${REMOTE_USER}"
    echo "  远程目录: ${REMOTE_DIR}"
    echo ""
}

# 使用 su root 执行远程命令
execute_as_root() {
    local command="$1"
    # 转义命令中的特殊字符
    local escaped_command=$(echo "$command" | sed "s/'/'\\\\''/g")
    
    local expect_script=$(cat <<EOF
set timeout 300
spawn ssh -o StrictHostKeyChecking=no ${REMOTE_USER}@${REMOTE_HOST} "su - root -c '${escaped_command}'"
expect {
    -re "password:" {
        send "${ROOT_PASSWORD}\r"
        exp_continue
    }
    -re "Password:" {
        send "${ROOT_PASSWORD}\r"
        exp_continue
    }
    "yes/no" {
        send "yes\r"
        exp_continue
    }
    eof
}
catch wait result
set exit_code [lindex \$result 3]
exit \$exit_code
EOF
)
    expect -c "$expect_script"
}

# 检查 SSH 连接
check_ssh_connection() {
    print_info "检查 SSH 连接..."
    
    # 检查 expect 是否安装
    if ! command -v expect &> /dev/null; then
        print_error "未安装 expect，请先安装："
        echo "  macOS: brew install expect"
        echo "  Ubuntu/Debian: sudo apt-get install expect"
        echo "  CentOS/RHEL: sudo yum install expect"
        exit 1
    fi
    
    # 测试 SSH 连接（使用 expect 处理密码）
    local expect_script=$(cat <<EOF
spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 ${REMOTE_USER}@${REMOTE_HOST} "echo 'SSH连接成功'"
expect {
    "password:" {
        send "dummy\r"
        exp_continue
    }
    "Password:" {
        send "dummy\r"
        exp_continue
    }
    "yes/no" {
        send "yes\r"
        exp_continue
    }
    "SSH连接成功" {
        exit 0
    }
    timeout {
        exit 1
    }
    eof
}
catch wait result
exit [lindex \$result 3]
EOF
)
    
    # 先测试普通账号连接（不输入密码，只测试连接性）
    ssh -o ConnectTimeout=5 -o BatchMode=yes ${REMOTE_USER}@${REMOTE_HOST} "echo 'test'" > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        print_warn "SSH 密钥认证失败，将使用密码认证"
        print_info "请确保可以正常登录到 ${REMOTE_USER}@${REMOTE_HOST}"
    else
        print_info "SSH 连接正常（使用密钥认证）"
    fi
}

# 远程备份
remote_backup() {
    print_info "开始备份远程目录: ${REMOTE_DIR}"
    
    # 检查远程目录是否存在（使用 su root）
    local check_cmd="test -d ${REMOTE_DIR} && echo 'exists' || echo 'not_exists'"
    local result=$(execute_as_root "$check_cmd" 2>/dev/null | grep -o "exists\|not_exists" | tail -1)
    
    if [ "$result" != "exists" ]; then
        print_warn "远程目录 ${REMOTE_DIR} 不存在，跳过备份"
        return 0
    fi
    
    # 在远程服务器上创建备份（使用 su root）
    print_info "正在创建备份: ${REMOTE_BACKUP_DIR}/${BACKUP_NAME}"
    
    local backup_cmd="cd ${REMOTE_BACKUP_DIR} && zip -r ${BACKUP_NAME} mdserver-web && ls -lh ${REMOTE_BACKUP_DIR}/${BACKUP_NAME}"
    
    print_info "执行备份命令（需要 root 权限）..."
    local backup_output=$(execute_as_root "$backup_cmd" 2>&1)
    local backup_status=$?
    
    if [ $backup_status -eq 0 ]; then
        echo "$backup_output" | grep -v "password:" | grep -v "Password:"
        print_info "备份完成: ${REMOTE_BACKUP_DIR}/${BACKUP_NAME}"
    else
        print_error "备份失败，输出："
        echo "$backup_output" | grep -v "password:" | grep -v "Password:"
        print_error "是否继续同步？(y/n)"
        read -r response
        if [ "$response" != "y" ] && [ "$response" != "Y" ]; then
            exit 1
        fi
    fi
}

# 同步文件
sync_files() {
    print_info "开始同步文件到远程服务器..."
    print_info "本地目录: ${LOCAL_DIR}"
    print_info "远程目录: ${REMOTE_DIR}"
    
    # 使用 rsync 同步文件
    # 排除一些不需要同步的文件和目录
    EXCLUDE_PATTERNS=(
        "--exclude=.git"
        "--exclude=.gitignore"
        "--exclude=.github"
        "--exclude=*.pyc"
        "--exclude=__pycache__"
        "--exclude=.DS_Store"
        "--exclude=*.log"
        "--exclude=.idea"
        "--exclude=.vscode"
        "--exclude=*.swp"
        "--exclude=*.swo"
        "--exclude=*~"
        "--exclude=sync_to_server.sh"
    )
    
    # 临时目录（普通用户可写）
    local temp_dir="/tmp/mdserver-web-sync-$$"
    
    # 构建 rsync 命令
    RSYNC_CMD="rsync -avz --progress"
    
    # 添加排除模式
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        RSYNC_CMD="$RSYNC_CMD $pattern"
    done
    
    # 第一步：同步到临时目录（普通用户权限）
    print_info "步骤 1/2: 同步文件到临时目录 ${temp_dir}..."
    $RSYNC_CMD "${LOCAL_DIR}/" "${REMOTE_USER}@${REMOTE_HOST}:${temp_dir}/"
    
    if [ $? -ne 0 ]; then
        print_error "文件同步到临时目录失败！"
        exit 1
    fi
    
    # 第二步：使用 su root 将文件移动到目标目录
    print_info "步骤 2/2: 移动文件到目标目录（需要 root 权限）..."
    local move_cmd="su - root -c 'mkdir -p ${REMOTE_DIR} && rm -rf ${REMOTE_DIR}/* ${REMOTE_DIR}/.* 2>/dev/null; cp -r ${temp_dir}/* ${REMOTE_DIR}/ 2>/dev/null; chown -R root:root ${REMOTE_DIR} 2>/dev/null; rm -rf ${temp_dir}'"
    
    local move_output=$(execute_as_root "$move_cmd" 2>&1)
    local move_status=$?
    
    if [ $move_status -eq 0 ]; then
        # 过滤掉密码提示信息
        echo "$move_output" | grep -v "password:" | grep -v "Password:" | grep -v "^$" || true
        print_info "文件同步完成！"
    else
        print_error "移动文件到目标目录失败！"
        echo "$move_output" | grep -v "password:" | grep -v "Password:"
        exit 1
    fi
}

# 主函数
main() {
    echo "=========================================="
    echo "  mdserver-web 远程同步脚本"
    echo "=========================================="
    echo ""
    
    # 交互式输入配置
    input_config
    
    echo "=========================================="
    echo "远程服务器: ${REMOTE_USER}@${REMOTE_HOST}"
    echo "远程目录: ${REMOTE_DIR}"
    echo "本地目录: ${LOCAL_DIR}"
    echo "=========================================="
    echo ""
    
    # 检查 SSH 连接
    check_ssh_connection
    
    # 远程备份
    remote_backup
    
    # 同步文件
    sync_files
    
    print_info "所有操作完成！"
    echo ""
    print_info "备份文件位置: ${REMOTE_BACKUP_DIR}/${BACKUP_NAME}"
}

# 执行主函数
main
