#!/bin/bash

# VTX AI Phone System - Local AI版本启动脚本

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

# 检查是否在项目目录
if [ ! -f "main_local_ai.py" ]; then
    log_error "请在项目根目录运行此脚本"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "gpu_env" ]; then
    log_error "未找到gpu_env虚拟环境，请先运行环境初始化"
    exit 1
fi

log_info "激活GPU虚拟环境..."
source gpu_env/bin/activate

# 检查CUDA
log_info "检查CUDA可用性..."
python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')" 2>/dev/null
if [ $? -ne 0 ]; then
    log_warn "无法检查CUDA状态，可能需要安装PyTorch"
fi

# 检查依赖
log_info "检查依赖包..."
python -c "import RealtimeSTT, RealtimeTTS, transformers" 2>/dev/null
if [ $? -ne 0 ]; then
    log_warn "缺少依赖包，正在安装..."
    pip install RealtimeSTT RealtimeTTS transformers accelerate bitsandbytes
fi

# 创建日志目录
if [ ! -d "logs" ]; then
    log_info "创建日志目录..."
    mkdir -p logs
fi

# 检查模型是否下载
log_info "检查模型状态..."
if [ ! -d "$HOME/.cache/huggingface" ] || [ -z "$(ls -A $HOME/.cache/huggingface 2>/dev/null)" ]; then
    log_warn "未检测到已下载的模型，建议先运行: python download_models.py"
    read -p "是否继续启动？(y/N): " continue_start
    if [[ ! $continue_start =~ ^[Yy]$ ]]; then
        log_info "启动已取消"
        exit 0
    fi
fi

# 性能配置选择
echo
log_info "选择性能配置:"
echo "1. 高质量模式 (需要更多GPU内存)"
echo "2. 平衡模式 (推荐)"
echo "3. 快速模式 (较低延迟)"
echo "4. CPU模式 (无GPU需求)"

read -p "选择配置 (1-4) [默认: 2]: " perf_choice
case $perf_choice in
    1)
        export LOCAL_AI_PROFILE="high_quality"
        log_info "使用高质量配置"
        ;;
    3)
        export LOCAL_AI_PROFILE="fast"
        log_info "使用快速配置"
        ;;
    4)
        export LOCAL_AI_PROFILE="cpu_only"
        log_info "使用CPU配置"
        ;;
    *)
        export LOCAL_AI_PROFILE="balanced"
        log_info "使用平衡配置"
        ;;
esac

# 日志级别选择
read -p "日志级别 (DEBUG/INFO/WARN/ERROR) [默认: INFO]: " log_level
export LOCAL_AI_LOG_LEVEL=${log_level:-INFO}

# 检查端口占用
log_info "检查端口占用..."
if netstat -tuln | grep -q ":5060 "; then
    log_warn "SIP端口5060已被占用"
fi

if netstat -tuln | grep -q ":10000 "; then
    log_warn "RTP端口10000已被占用"
fi

# 显示系统信息
echo
log_info "系统信息:"
echo "- Python: $(python --version)"
echo "- PyTorch: $(python -c 'import torch; print(torch.__version__)' 2>/dev/null || echo '未安装')"
echo "- CUDA: $(python -c 'import torch; print(torch.version.cuda)' 2>/dev/null || echo '不可用')"
echo "- GPU: $(python -c 'import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "无")' 2>/dev/null || echo '无')"

# 启动确认
echo
read -p "是否开始启动本地AI系统？(Y/n): " start_confirm
if [[ $start_confirm =~ ^[Nn]$ ]]; then
    log_info "启动已取消"
    exit 0
fi

# 启动系统
echo
log_info "启动VTX AI Phone System - Local AI版本..."
log_info "日志将保存到 logs/local_ai_system.log"
log_info "按 Ctrl+C 停止系统"

# 设置信号处理
trap 'log_info "正在停止系统..."; kill $PID 2>/dev/null; exit 0' INT TERM

# 启动主程序
python main_local_ai.py &
PID=$!

# 等待进程结束
wait $PID

log_info "系统已停止"