#!/bin/bash

# mdserver-web 依赖修复脚本
# 用于修复部署后缺少 Python 依赖的问题

TARGET_DIR="/www/server/mdserver-web"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    print_error "此脚本需要 root 权限运行"
    print_info "请使用: sudo bash $0"
    exit 1
fi

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

# 检查 Python
if ! command -v python3 &> /dev/null; then
    print_error "未找到 python3，请先安装 Python 3"
    exit 1
fi

P_VER=$(python3 -V 2>&1 | awk '{print $2}')
print_info "Python 版本: $P_VER"

# 检查目录
if [ ! -d "$TARGET_DIR" ]; then
    print_error "目录不存在: $TARGET_DIR"
    exit 1
fi

cd "$TARGET_DIR" || exit 1

# 创建或激活虚拟环境
if [ ! -f "$TARGET_DIR/bin/activate" ]; then
    print_info "创建虚拟环境..."
    P_VER_MAJOR=$(echo "$P_VER" | awk -F '.' '{print $1}')
    P_VER_MINOR=$(echo "$P_VER" | awk -F '.' '{print $2}')
    
    if [ "$P_VER_MAJOR" -gt 3 ] || ([ "$P_VER_MAJOR" -eq 3 ] && [ "$P_VER_MINOR" -ge 11 ]); then
        python3 -m venv "$TARGET_DIR"
    else
        python3 -m venv .
    fi
    print_info "虚拟环境创建完成"
else
    print_info "虚拟环境已存在"
fi

# 激活虚拟环境
print_info "激活虚拟环境..."
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
    print_error "未找到 requirements.txt 文件"
    exit 1
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

print_info "=========================================="
print_info "依赖安装完成！"
print_info "=========================================="
print_info "现在可以尝试重启服务: mw restart"
echo ""
