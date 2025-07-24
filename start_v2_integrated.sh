#!/bin/bash

# VTX AI Phone System V2 - 一体化启动脚本 (适配Vast.ai容器环境)
# 所有AI服务运行在单一进程内，无需外部服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 打印欢迎信息
echo "=================================================================="
echo -e "${GREEN}🚀 VTX AI Phone System V2 - Integrated Version${NC}"
echo "=================================================================="
echo "✨ 一体化架构 - 适配Vast.ai容器环境"
echo "🎯 所有AI服务运行在单一Python进程内"
echo "🔥 支持GPU加速的高性能AI电话客服"
echo "=================================================================="

# 检查Python环境
log_step "检查Python环境..."
if ! command -v python3 &> /dev/null; then
    log_error "Python3 not found. Please install Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
log_info "Python版本: $PYTHON_VERSION"

# 检查GPU环境
log_step "检查GPU环境..."
if command -v nvidia-smi &> /dev/null; then
    log_info "NVIDIA GPU检测:"
    nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader,nounits
    
    # 检查CUDA
    if python3 -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')" 2>/dev/null; then
        log_info "✅ CUDA支持已启用"
    else
        log_warn "⚠️  CUDA不可用，将使用CPU模式"
    fi
else
    log_warn "⚠️  未检测到NVIDIA GPU，将使用CPU模式"
fi

# 设置环境变量 (解决音频设备问题)
log_step "设置环境变量..."
export SDL_AUDIODRIVER=dummy
export ALSA_SUPPRESS_WARNINGS=1
export TRANSFORMERS_VERBOSITY=error
export TOKENIZERS_PARALLELISM=false

# 检查并创建日志目录
log_step "准备日志目录..."
mkdir -p logs
log_info "✅ 日志目录: $(pwd)/logs"

# 检查依赖
log_step "检查Python依赖..."
MISSING_DEPS=()

# 检查核心依赖
python3 -c "import torch" 2>/dev/null || MISSING_DEPS+=("torch")
python3 -c "import transformers" 2>/dev/null || MISSING_DEPS+=("transformers")
python3 -c "import RealtimeTTS" 2>/dev/null || MISSING_DEPS+=("RealtimeTTS")
python3 -c "import RealtimeSTT" 2>/dev/null || MISSING_DEPS+=("RealtimeSTT")

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    log_error "缺少依赖: ${MISSING_DEPS[*]}"
    log_info "请先安装依赖: pip install -r requirements_v2_integrated.txt"
    exit 1
fi

log_info "✅ 所有依赖已满足"

# 检查配置文件
log_step "检查配置文件..."
if [ ! -f "config/settings.py" ]; then
    log_error "配置文件 config/settings.py 不存在"
    exit 1
fi

log_info "✅ 配置文件检查通过"

# 检查业务数据
log_step "检查业务数据..."
if [ ! -f "data/onesuite-business-data.json" ]; then
    log_warn "业务数据文件不存在，将使用默认配置"
else
    log_info "✅ 业务数据文件存在"
fi

# 显示启动信息
echo ""
echo "=================================================================="
echo -e "${BLUE}🎯 系统启动参数${NC}"
echo "=================================================================="
echo "📁 工作目录: $(pwd)"
echo "🐍 Python: $(which python3) ($PYTHON_VERSION)"
echo "🔧 GPU加速: $(python3 -c "import torch; print('✅ CUDA' if torch.cuda.is_available() else '❌ CPU Only')" 2>/dev/null || echo '❌ CPU Only')"
echo "📝 日志级别: INFO"
echo "🌐 SIP配置: $(python3 -c "from config.settings import SIP_CONFIG; print(f\"{SIP_CONFIG['username']}@{SIP_CONFIG['server']}:{SIP_CONFIG['port']}\")" 2>/dev/null || echo 'Error reading config')"
echo "=================================================================="

# 确认启动
echo ""
read -p "🚀 准备启动系统，按回车继续 (Ctrl+C 取消)..."

# 启动系统
log_step "启动VTX AI Phone System V2..."
echo ""

# 切换到aiker_v2目录并启动
cd aiker_v2

# 使用Python直接运行 (不使用nohup，便于调试)
python3 app_integrated.py

# 如果脚本到达这里，说明程序正常退出
log_info "✅ 系统已正常退出"