#!/bin/bash

echo "🚀 启动简化版AI电话系统"
echo "================================"

# 激活环境
source gpu_env/bin/activate

# 检查环境
echo "📋 系统信息:"
echo "- Python: $(python --version)"
echo "- CUDA: $(nvidia-smi --query-gpu=name --format=csv,noheader,nounits | head -1)"
echo "- GPU内存: $(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1) MB"
echo ""

echo "🔧 AI配置:"
echo "- LLM: Qwen2.5-7B-Instruct (4bit量化)"
echo "- TTS: 系统TTS引擎"
echo "- STT: 暂时跳过 (CUDNN问题)"
echo ""

echo "📞 SIP配置:"
echo "- 分机: 101"
echo "- 域名: aiker.myippbx.com"
echo "- DID: 14088779998"
echo ""

echo "▶️ 启动系统..."
echo "按 Ctrl+C 停止"
echo ""

# 启动简化版系统
python simple_ai_phone.py