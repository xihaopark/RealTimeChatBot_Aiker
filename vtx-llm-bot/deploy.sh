#!/bin/bash

# VTX AI Phone System - 部署脚本
# 用于生产环境的自动化部署

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
PROJECT_NAME="vtx-ai-phone"
SERVICE_NAME="vtx-ai-phone"
PYTHON_VERSION="3.8"
VENV_NAME="venv"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查系统要求
check_requirements() {
    log_info "检查系统要求..."
    
    # 检查Python版本
    if ! command -v python3 &> /dev/null; then
        log_error "Python3未安装，请先安装Python 3.8+"
        exit 1
    fi
    
    local python_version=$(python3 --version | cut -d' ' -f2)
    log_success "Python版本: $python_version"
    
    # 检查pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3未安装，请先安装pip"
        exit 1
    fi
    
    # 检查Git
    if ! command -v git &> /dev/null; then
        log_error "Git未安装，请先安装Git"
        exit 1
    fi
    
    log_success "系统要求检查通过"
}

# 创建虚拟环境
setup_venv() {
    log_info "设置Python虚拟环境..."
    
    if [ ! -d "$VENV_NAME" ]; then
        log_info "创建虚拟环境..."
        python3 -m venv "$VENV_NAME"
    fi
    
    # 激活虚拟环境
    source "$VENV_NAME/bin/activate"
    
    # 升级pip
    log_info "升级pip..."
    pip install --upgrade pip
    
    log_success "虚拟环境设置完成"
}

# 安装依赖
install_dependencies() {
    log_info "安装Python依赖..."
    
    # 激活虚拟环境
    source "$VENV_NAME/bin/activate"
    
    # 安装依赖
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        log_success "依赖安装完成"
    else
        log_error "requirements.txt文件不存在"
        exit 1
    fi
}

# 创建配置文件
setup_config() {
    log_info "设置配置文件..."
    
    # 检查.env文件
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            log_info "复制环境变量模板..."
            cp .env.example .env
            log_warning "请编辑 .env 文件，配置必要的环境变量"
        else
            log_warning "未找到 .env.example 文件，请手动创建 .env 文件"
        fi
    else
        log_success "配置文件已存在"
    fi
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    
    # 创建日志目录
    mkdir -p logs
    mkdir -p recordings
    
    # 设置权限
    chmod 755 logs recordings
    
    log_success "目录创建完成"
}

# 创建系统服务
create_service() {
    log_info "创建系统服务..."
    
    local current_dir=$(pwd)
    local python_path="$current_dir/$VENV_NAME/bin/python"
    local script_path="$current_dir/src/main.py"
    
    # 创建systemd服务文件
    cat > "/tmp/$SERVICE_NAME.service" << EOF
[Unit]
Description=VTX AI Phone System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$current_dir
Environment=PATH=$current_dir/$VENV_NAME/bin
ExecStart=$python_path $script_path
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # 复制服务文件到系统目录
    if command -v sudo &> /dev/null; then
        sudo cp "/tmp/$SERVICE_NAME.service" "/etc/systemd/system/"
        sudo systemctl daemon-reload
        log_success "系统服务创建完成"
    else
        log_warning "未找到sudo，请手动安装服务文件"
        log_info "服务文件位置: /tmp/$SERVICE_NAME.service"
    fi
}

# 启动服务
start_service() {
    log_info "启动服务..."
    
    if command -v sudo &> /dev/null; then
        sudo systemctl enable "$SERVICE_NAME"
        sudo systemctl start "$SERVICE_NAME"
        
        # 检查服务状态
        if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
            log_success "服务启动成功"
        else
            log_error "服务启动失败"
            sudo systemctl status "$SERVICE_NAME"
            exit 1
        fi
    else
        log_warning "未找到sudo，请手动启动服务"
        log_info "运行命令: python src/main.py"
    fi
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    # 检查Python进程
    if pgrep -f "python.*main.py" > /dev/null; then
        log_success "Python进程运行正常"
    else
        log_warning "未检测到Python进程"
    fi
    
    # 检查端口占用
    if command -v netstat &> /dev/null; then
        local sip_port=$(netstat -tlnp 2>/dev/null | grep :5060 || true)
        if [ -n "$sip_port" ]; then
            log_success "SIP端口(5060)监听正常"
        else
            log_warning "SIP端口(5060)未监听"
        fi
    fi
    
    log_success "健康检查完成"
}

# 显示服务状态
show_status() {
    log_info "服务状态信息..."
    
    if command -v sudo &> /dev/null; then
        sudo systemctl status "$SERVICE_NAME" --no-pager
    fi
    
    echo ""
    log_info "查看日志:"
    echo "  sudo journalctl -u $SERVICE_NAME -f"
    echo ""
    log_info "重启服务:"
    echo "  sudo systemctl restart $SERVICE_NAME"
    echo ""
    log_info "停止服务:"
    echo "  sudo systemctl stop $SERVICE_NAME"
}

# 清理部署
cleanup_deploy() {
    log_info "清理部署文件..."
    
    # 删除临时文件
    rm -f "/tmp/$SERVICE_NAME.service"
    
    # 清理Python缓存
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    
    log_success "清理完成"
}

# 显示帮助信息
show_help() {
    echo "VTX AI Phone System - 部署脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  install     完整安装和部署"
    echo "  start       启动服务"
    echo "  stop        停止服务"
    echo "  restart     重启服务"
    echo "  status      查看服务状态"
    echo "  health      执行健康检查"
    echo "  cleanup     清理部署文件"
    echo "  -h, --help  显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 install  完整部署"
    echo "  $0 status   查看状态"
    echo "  $0 health   健康检查"
}

# 主函数
main() {
    echo "🚀 VTX AI Phone System - 部署工具"
    echo "=================================="
    
    case "${1:-install}" in
        install)
            check_requirements
            setup_venv
            install_dependencies
            setup_config
            create_directories
            create_service
            start_service
            health_check
            show_status
            cleanup_deploy
            ;;
        start)
            start_service
            ;;
        stop)
            if command -v sudo &> /dev/null; then
                sudo systemctl stop "$SERVICE_NAME"
                log_success "服务已停止"
            else
                log_error "未找到sudo，请手动停止服务"
            fi
            ;;
        restart)
            if command -v sudo &> /dev/null; then
                sudo systemctl restart "$SERVICE_NAME"
                log_success "服务已重启"
            else
                log_error "未找到sudo，请手动重启服务"
            fi
            ;;
        status)
            show_status
            ;;
        health)
            health_check
            ;;
        cleanup)
            cleanup_deploy
            ;;
        -h|--help)
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
    
    echo ""
    log_success "🎉 部署操作完成！"
}

# 错误处理
trap 'log_error "部署过程中发生错误，请检查日志"; exit 1' ERR

# 运行主函数
main "$@" 