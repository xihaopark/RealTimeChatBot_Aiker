#!/bin/bash

# VTX AI Phone System V2 - 一键部署脚本
# 自动设置高性能AI电话系统

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 显示横幅
show_banner() {
    echo -e "${PURPLE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                                                              ║"
    echo "║            VTX AI Phone System V2 Setup                     ║"
    echo "║                                                              ║"
    echo "║  🚀 High-Performance AI Phone System                        ║"
    echo "║  🎯 Vosk STT + Llama.cpp LLM + Piper TTS                   ║"
    echo "║  ⚡ Optimized for Speed & Concurrency                      ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查系统要求
check_system_requirements() {
    echo -e "${CYAN}🔍 Checking system requirements...${NC}"
    
    # 检查操作系统
    if [[ ! "$OSTYPE" == "linux-gnu"* ]]; then
        echo -e "${RED}❌ This script is designed for Linux systems${NC}"
        exit 1
    fi
    
    # 检查Python版本
    if ! command -v python3 &> /dev/null || ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"; then
        echo -e "${RED}❌ Python 3.8+ is required${NC}"
        exit 1
    fi
    
    # 检查磁盘空间 (至少需要5GB)
    available_space=$(df . | tail -1 | awk '{print $4}')
    required_space=5242880  # 5GB in KB
    
    if [ "$available_space" -lt "$required_space" ]; then
        echo -e "${RED}❌ Insufficient disk space. At least 5GB required${NC}"
        exit 1
    fi
    
    # 检查内存 (建议至少8GB)
    total_memory=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    recommended_memory=8388608  # 8GB in KB
    
    if [ "$total_memory" -lt "$recommended_memory" ]; then
        echo -e "${YELLOW}⚠️  Warning: Less than 8GB RAM detected. Performance may be affected${NC}"
    fi
    
    # 检查CUDA (可选)
    if command -v nvidia-smi &> /dev/null; then
        echo -e "${GREEN}🎮 NVIDIA GPU detected - CUDA acceleration available${NC}"
        export CUDA_AVAILABLE=1
    else
        echo -e "${YELLOW}💻 No NVIDIA GPU detected - using CPU-only mode${NC}"
        export CUDA_AVAILABLE=0
    fi
    
    echo -e "${GREEN}✅ System requirements check passed${NC}"
}

# 安装系统依赖
install_system_dependencies() {
    echo -e "${CYAN}📦 Installing system dependencies...${NC}"
    
    # 更新包列表
    sudo apt-get update -qq
    
    # 安装基础依赖
    sudo apt-get install -y \
        build-essential \
        cmake \
        git \
        wget \
        curl \
        unzip \
        pkg-config \
        libffi-dev \
        libssl-dev \
        libasound2-dev \
        libportaudio2 \
        libsndfile1 \
        python3-dev \
        python3-pip \
        python3-venv
    
    # 安装音频库
    sudo apt-get install -y \
        libasound2-plugins \
        pulseaudio \
        alsa-utils
    
    echo -e "${GREEN}✅ System dependencies installed${NC}"
}

# 设置Python虚拟环境
setup_python_environment() {
    echo -e "${CYAN}🐍 Setting up Python environment...${NC}"
    
    # 创建虚拟环境
    if [ ! -d "venv_v2" ]; then
        python3 -m venv venv_v2
    fi
    
    # 激活虚拟环境
    source venv_v2/bin/activate
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装V2依赖
    pip install -r aiker_v2/requirements.v2.txt
    
    echo -e "${GREEN}✅ Python environment ready${NC}"
}

# 设置AI服务
setup_ai_services() {
    echo -e "${CYAN}🤖 Setting up AI services...${NC}"
    
    cd services
    
    # 设置Piper TTS
    echo -e "${YELLOW}Setting up Piper TTS...${NC}"
    if [ ! -f "piper/piper" ]; then
        ./setup_piper.sh
    else
        echo -e "${GREEN}✅ Piper already installed${NC}"
    fi
    
    # 设置Llama.cpp
    echo -e "${YELLOW}Setting up Llama.cpp...${NC}"
    if [ ! -f "llama.cpp/server" ]; then
        ./setup_llama_cpp.sh
    else
        echo -e "${GREEN}✅ Llama.cpp already installed${NC}"
    fi
    
    # 设置Vosk STT
    echo -e "${YELLOW}Setting up Vosk STT...${NC}"
    if [ ! -d "vosk/models/vosk-model-cn-0.22" ]; then
        ./setup_vosk.sh
    else
        echo -e "${GREEN}✅ Vosk already installed${NC}"
    fi
    
    cd ..
    
    echo -e "${GREEN}✅ AI services setup completed${NC}"
}

# 创建配置文件
create_configuration() {
    echo -e "${CYAN}⚙️  Creating configuration...${NC}"
    
    # 创建环境变量文件
    if [ ! -f ".env" ]; then
        cat > .env << 'EOF'
# VTX AI Phone System V2 Configuration

# VTX服务器配置
VTX_SERVER=core1-us-lax.myippbx.com
VTX_PORT=5060
VTX_DOMAIN=aiker.myippbx.com
VTX_DID=14088779998

# 分机配置 (请修改为您的实际配置)
EXTENSION_1000_USERNAME=1000
EXTENSION_1000_PASSWORD=your_password_here
EXTENSION_1000_DESCRIPTION=AI Assistant Extension

# 网络配置
SIP_PORT=5060
RTP_PORT_START=10000
RTP_PORT_END=10500

# 系统配置
LOG_LEVEL=INFO
MAX_CONCURRENT_CALLS=20
CALL_TIMEOUT_SECONDS=1800

# AI服务配置
STT_PROVIDER=vosk
TTS_PROVIDER=piper
LLM_PROVIDER=llama_cpp

# 音频配置 (解决ALSA问题)
SDL_AUDIODRIVER=dummy
ALSA_PCM_CARD=default
ALSA_PCM_DEVICE=0
EOF
        
        echo -e "${YELLOW}⚠️  Please edit .env file with your actual VTX credentials${NC}"
    fi
    
    # 创建日志目录
    mkdir -p logs
    
    echo -e "${GREEN}✅ Configuration created${NC}"
}

# 创建启动脚本
create_startup_scripts() {
    echo -e "${CYAN}📜 Creating startup scripts...${NC}"
    
    # 主启动脚本
    cat > start_aiker_v2.sh << 'EOF'
#!/bin/bash

# VTX AI Phone System V2 启动脚本

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Starting VTX AI Phone System V2...${NC}"

# 检查环境变量
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found. Please run setup first.${NC}"
    exit 1
fi

# 激活虚拟环境
if [ -d "venv_v2" ]; then
    source venv_v2/bin/activate
    echo -e "${GREEN}✅ Python environment activated${NC}"
else
    echo -e "${RED}❌ Python virtual environment not found${NC}"
    exit 1
fi

# 设置环境变量
export SDL_AUDIODRIVER=dummy
export TRANSFORMERS_VERBOSITY=error

# 检查AI服务
check_services() {
    echo -e "${YELLOW}🔍 Checking AI services...${NC}"
    
    # 检查Llama.cpp服务器
    if ! curl -s http://127.0.0.1:8080/health > /dev/null 2>&1; then
        echo -e "${YELLOW}🤖 Starting Llama.cpp server...${NC}"
        cd services/llama.cpp
        nohup ./start_server.sh > ../../logs/llama_cpp.log 2>&1 &
        LLAMA_PID=$!
        cd ../..
        
        # 等待服务器启动
        echo -e "${YELLOW}⏳ Waiting for LLM server to start...${NC}"
        for i in {1..30}; do
            if curl -s http://127.0.0.1:8080/health > /dev/null 2>&1; then
                echo -e "${GREEN}✅ LLM server is ready${NC}"
                break
            fi
            sleep 2
        done
    else
        echo -e "${GREEN}✅ LLM server already running${NC}"
    fi
    
    # 检查Piper
    if [ ! -f "services/piper/piper" ]; then
        echo -e "${RED}❌ Piper TTS not found${NC}"
        exit 1
    fi
    
    # 检查Vosk模型
    if [ ! -d "services/vosk/models" ]; then
        echo -e "${RED}❌ Vosk models not found${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ All AI services are ready${NC}"
}

# 启动服务检查
check_services

# 启动主应用
echo -e "${GREEN}🎯 Starting main application...${NC}"
cd aiker_v2
python app.py

# 清理函数
cleanup() {
    echo -e "${YELLOW}🛑 Shutting down...${NC}"
    if [ ! -z "$LLAMA_PID" ]; then
        kill $LLAMA_PID 2>/dev/null || true
    fi
    pkill -f "llama.cpp/server" 2>/dev/null || true
}

# 注册清理函数
trap cleanup EXIT INT TERM

EOF
    
    chmod +x start_aiker_v2.sh
    
    # 测试脚本
    cat > test_aiker_v2.sh << 'EOF'
#!/bin/bash

# VTX AI Phone System V2 测试脚本

echo "🧪 Testing VTX AI Phone System V2 components..."

# 激活虚拟环境
source venv_v2/bin/activate

cd aiker_v2

echo "Testing TTS service..."
python -c "
from tts_service import PiperTTSService
tts = PiperTTSService()
print(f'TTS Available: {tts.is_available()}')
print(f'Supported languages: {tts.get_supported_languages()}')
"

echo "Testing STT service..."
python -c "
from stt_service import VoskSTTService
stt = VoskSTTService()
print(f'STT Available: {stt.is_available()}')
print(f'Supported languages: {stt.get_supported_languages()}')
"

echo "Testing LLM service..."
python -c "
from llm_service import LlamaCppLLMService
llm = LlamaCppLLMService()
print(f'LLM Available: {llm.is_available()}')
"

echo "✅ Component testing completed"
EOF
    
    chmod +x test_aiker_v2.sh
    
    echo -e "${GREEN}✅ Startup scripts created${NC}"
}

# 运行测试
run_tests() {
    echo -e "${CYAN}🧪 Running initial tests...${NC}"
    
    # 激活虚拟环境
    source venv_v2/bin/activate
    
    # 测试组件
    if ./test_aiker_v2.sh; then
        echo -e "${GREEN}✅ All tests passed${NC}"
    else
        echo -e "${YELLOW}⚠️  Some tests failed, but system may still work${NC}"
    fi
}

# 显示完成信息
show_completion_info() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                                                              ║"
    echo "║               🎉 Setup Completed Successfully!              ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo -e "${CYAN}📋 Next Steps:${NC}"
    echo "1. Edit .env file with your VTX credentials"
    echo "2. Start the system: ./start_aiker_v2.sh"
    echo "3. Test components: ./test_aiker_v2.sh"
    echo ""
    echo -e "${CYAN}📁 Important Files:${NC}"
    echo "• Configuration: .env"
    echo "• Main application: aiker_v2/app.py"
    echo "• Startup script: start_aiker_v2.sh"
    echo "• Logs directory: logs/"
    echo ""
    echo -e "${CYAN}🔧 AI Services:${NC}"
    echo "• Piper TTS: services/piper/"
    echo "• Llama.cpp LLM: services/llama.cpp/"
    echo "• Vosk STT: services/vosk/"
    echo ""
    echo -e "${YELLOW}⚠️  Remember to configure your VTX credentials in .env before starting!${NC}"
}

# 主函数
main() {
    show_banner
    
    echo -e "${BLUE}Starting VTX AI Phone System V2 setup...${NC}"
    echo "This may take 10-30 minutes depending on your internet connection."
    echo ""
    
    # 询问是否继续
    read -p "Continue with setup? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 0
    fi
    
    # 执行安装步骤
    check_system_requirements
    install_system_dependencies
    setup_python_environment
    setup_ai_services
    create_configuration
    create_startup_scripts
    run_tests
    
    show_completion_info
}

# 错误处理
error_handler() {
    echo -e "${RED}❌ Setup failed at step: $1${NC}"
    echo "Please check the error messages above and try again."
    exit 1
}

trap 'error_handler "Unknown step"' ERR

# 运行主函数
main "$@"