#!/bin/bash

# VTX AI Phone System V2 启动脚本
# 使用 llama-cpp-python + Vosk + Piper

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
echo -e "${GREEN}🚀 VTX AI Phone System V2${NC}"
echo "=================================================================="
echo "🧠 LLM: llama-cpp-python (GPU加速)"
echo "🎤 STT: Vosk (轻量高效)"
echo "🎵 TTS: Piper (极速合成)"
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
        log_warn "⚠️  CUDA不可用，LLM将使用CPU模式"
    fi
else
    log_warn "⚠️  未检测到NVIDIA GPU，将使用CPU模式"
fi

# 设置环境变量
log_step "设置环境变量..."
export SDL_AUDIODRIVER=dummy
export ALSA_SUPPRESS_WARNINGS=1

# 检查并创建必要目录
log_step "准备目录结构..."
mkdir -p logs
mkdir -p services/piper/models
mkdir -p services/vosk/models
mkdir -p services/llama.cpp/models

# 检查核心组件
log_step "检查AI服务组件..."

# 检查Piper
if [ -f "services/piper/piper" ]; then
    log_info "✅ Piper TTS已安装"
else
    log_warn "⚠️  Piper TTS未安装，请运行: ./services/setup_piper.sh"
fi

# 检查Vosk模型
if [ -d "services/vosk/models/vosk-model-cn-0.22" ] || [ -d "services/vosk/models/vosk-model-small-cn-0.22" ]; then
    log_info "✅ Vosk中文模型已安装"
else
    log_warn "⚠️  Vosk中文模型未安装，请运行: ./services/setup_vosk.sh"
fi

# 检查LLM模型
if ls services/llama.cpp/models/*.gguf 1> /dev/null 2>&1; then
    log_info "✅ GGUF模型已安装"
    ls -lh services/llama.cpp/models/*.gguf | head -3
else
    log_warn "⚠️  GGUF模型未安装，请下载模型到 services/llama.cpp/models/"
fi

# 检查Python依赖
log_step "检查Python依赖..."
MISSING_DEPS=()

python3 -c "import llama_cpp" 2>/dev/null || MISSING_DEPS+=("llama-cpp-python")
python3 -c "import vosk" 2>/dev/null || MISSING_DEPS+=("vosk")
python3 -c "import torch" 2>/dev/null || MISSING_DEPS+=("torch")

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    log_error "缺少依赖: ${MISSING_DEPS[*]}"
    log_info "请先安装依赖: pip install -r requirements_v2.txt"
    exit 1
fi

log_info "✅ 所有依赖已满足"

# 显示启动信息
echo ""
echo "=================================================================="
echo -e "${BLUE}🎯 系统启动参数${NC}"
echo "=================================================================="
echo "📁 工作目录: $(pwd)"
echo "🐍 Python: $(which python3) ($PYTHON_VERSION)"
echo "🔧 GPU加速: $(python3 -c "import torch; print('✅ CUDA' if torch.cuda.is_available() else '❌ CPU Only')" 2>/dev/null || echo '❌ CPU Only')"
echo "📝 日志文件: logs/aiker_v2.log"
echo "=================================================================="

# 确认启动
echo ""
read -p "🚀 准备启动系统，按回车继续 (Ctrl+C 取消)..."

# 启动系统
log_step "启动VTX AI Phone System V2..."
echo ""

# 切换到aiker_v2目录并启动
cd aiker_v2
python3 app_v2.py

# 如果脚本到达这里，说明程序正常退出
log_info "✅ 系统已正常退出"