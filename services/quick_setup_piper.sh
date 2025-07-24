#!/bin/bash

# 快速Piper设置脚本 - 直接使用正确的下载链接

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🔧 Quick Piper TTS setup...${NC}"

mkdir -p piper/models
cd piper

# 直接下载正确版本
echo -e "${YELLOW}Downloading Piper binary...${NC}"
wget -O piper.tar.gz "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_amd64.tar.gz"
tar -xzf piper.tar.gz --strip-components=1
chmod +x piper
rm piper.tar.gz

echo -e "${GREEN}✅ Piper binary installed${NC}"

# 下载中文模型
echo -e "${YELLOW}Downloading Chinese model...${NC}"
cd models
wget -O zh_CN-huayan-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx"
wget -O zh_CN-huayan-medium.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx.json"

# 下载英文模型
echo -e "${YELLOW}Downloading English model...${NC}"
wget -O en_US-ljspeech-high.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/ljspeech/high/en_US-ljspeech-high.onnx"
wget -O en_US-ljspeech-high.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/ljspeech/high/en_US-ljspeech-high.onnx.json"

cd ..

echo -e "${GREEN}✅ Piper TTS setup completed!${NC}"

# 快速测试
echo "测试中文TTS..." | ./piper --model models/zh_CN-huayan-medium.onnx --output_raw > /dev/null && echo "✅ Chinese TTS works"
echo "Testing English TTS..." | ./piper --model models/en_US-ljspeech-high.onnx --output_raw > /dev/null && echo "✅ English TTS works"