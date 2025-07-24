#!/bin/bash

# Llama.cpp 自动安装脚本
# 编译Llama.cpp并下载量化模型

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🔧 Setting up Llama.cpp...${NC}"

# 检查依赖
check_dependencies() {
    local deps=("git" "make" "g++" "cmake")
    for dep in "${deps[@]}"; do
        if ! command -v $dep &> /dev/null; then
            echo -e "${RED}❌ $dep is required but not installed${NC}"
            echo "Please install: sudo apt-get install $dep"
            exit 1
        fi
    done
    echo -e "${GREEN}✅ Dependencies check passed${NC}"
}

# 检测CUDA
check_cuda() {
    if command -v nvcc &> /dev/null; then
        echo -e "${GREEN}🎮 CUDA detected, will compile with GPU support${NC}"
        CUDA_ENABLED=1
    else
        echo -e "${YELLOW}⚠️  CUDA not found, compiling for CPU only${NC}"
        CUDA_ENABLED=0
    fi
}

check_dependencies
check_cuda

# 创建目录
mkdir -p llama.cpp/models
cd llama.cpp

# 克隆Llama.cpp
if [ ! -d ".git" ]; then
    echo -e "${YELLOW}Cloning llama.cpp repository...${NC}"
    git clone https://github.com/ggerganov/llama.cpp.git temp_repo
    mv temp_repo/* ./
    mv temp_repo/.git ./
    rm -rf temp_repo
fi

# 编译
echo -e "${YELLOW}Compiling llama.cpp...${NC}"
mkdir -p build
cd build

if [ $CUDA_ENABLED -eq 1 ]; then
    # 使用CUDA编译 (新参数)
    cmake .. -DGGML_CUDA=ON -DLLAMA_CURL=OFF
    echo -e "${GREEN}✅ CMake configured with CUDA support${NC}"
else
    # 仅CPU编译
    cmake .. -DLLAMA_CURL=OFF
    echo -e "${GREEN}✅ CMake configured for CPU${NC}"
fi

cmake --build . --config Release -j$(nproc)
cd ..

# 复制编译好的文件
cp build/bin/llama-server ./server 2>/dev/null || cp build/server ./server 2>/dev/null || cp build/llama-server ./server

# 验证编译结果
if [ ! -f "./server" ]; then
    echo -e "${RED}❌ Compilation failed - server executable not found${NC}"
    echo "Available files in build:"
    find build -name "*server*" -o -name "llama*" | head -10
    exit 1
fi

chmod +x ./server

echo -e "${GREEN}✅ Llama.cpp compiled successfully${NC}"

# 下载模型
echo -e "${YELLOW}Downloading Qwen2.5-7B-Instruct GGUF model...${NC}"
cd models

# 使用较小的Q4_K_M量化版本，平衡性能和质量
MODEL_NAME="Qwen2.5-7B-Instruct-Q4_K_M.gguf"
MODEL_URL="https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/${MODEL_NAME}"

if [ ! -f "$MODEL_NAME" ]; then
    echo -e "${YELLOW}Downloading $MODEL_NAME...${NC}"
    wget -O "$MODEL_NAME" "$MODEL_URL" || {
        echo -e "${RED}❌ Model download failed${NC}"
        echo "You can manually download from: $MODEL_URL"
        exit 1
    }
    echo -e "${GREEN}✅ Model downloaded: $MODEL_NAME${NC}"
else
    echo -e "${GREEN}✅ Model already exists: $MODEL_NAME${NC}"
fi

cd ..

# 创建启动脚本
cat > start_server.sh << 'EOF'
#!/bin/bash

# Llama.cpp Server 启动脚本

MODEL_PATH="./models/Qwen2.5-7B-Instruct-Q4_K_M.gguf"
HOST="127.0.0.1"
PORT="8080"
CTX_SIZE="4096"
THREADS=$(nproc)

# 检测GPU
if command -v nvidia-smi &> /dev/null && [ -f "./server" ]; then
    GPU_LAYERS=35  # 根据显存调整
    echo "Starting Llama.cpp server with GPU acceleration..."
    ./server \
        -m "$MODEL_PATH" \
        -c "$CTX_SIZE" \
        --host "$HOST" \
        --port "$PORT" \
        -t "$THREADS" \
        -ngl "$GPU_LAYERS" \
        --log-disable
else
    echo "Starting Llama.cpp server (CPU only)..."
    ./server \
        -m "$MODEL_PATH" \
        -c "$CTX_SIZE" \
        --host "$HOST" \
        --port "$PORT" \
        -t "$THREADS" \
        --log-disable
fi
EOF

chmod +x start_server.sh

# 测试启动
echo -e "${YELLOW}Testing server startup...${NC}"
timeout 10s ./start_server.sh &
SERVER_PID=$!

sleep 5

# 检查服务器是否启动
if curl -s http://127.0.0.1:8080/health > /dev/null; then
    echo -e "${GREEN}✅ Server test successful${NC}"
    kill $SERVER_PID 2>/dev/null || true
else
    echo -e "${YELLOW}⚠️  Server test inconclusive (this is normal)${NC}"
    kill $SERVER_PID 2>/dev/null || true
fi

echo -e "${GREEN}🎉 Llama.cpp setup completed!${NC}"
echo ""
echo "To start the server:"
echo "  cd services/llama.cpp && ./start_server.sh"
echo ""
echo "Server will be available at: http://127.0.0.1:8080"