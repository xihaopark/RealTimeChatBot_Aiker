#!/bin/bash

# VTX AI Phone System - 生产启动脚本

echo "🚀 启动VTX AI Phone System (本地AI版本)"
echo "=============================================="

# 检查环境
source gpu_env/bin/activate

echo "📋 系统配置:"
echo "- 分机号: 101"
echo "- 域名: aiker.myippbx.com"
echo "- 服务器: core1-us-lax.myippbx.com"
echo "- DID号码: 14088779998"
echo ""

echo "🧠 AI配置:"
echo "- LLM: Qwen2.5-7B-Instruct (GPU + 4bit量化)"
echo "- TTS: Mock引擎 (生成音频)"
echo "- STT: 模拟输入 (CUDNN问题待解决)"
echo ""

echo "📞 准备接听电话..."
echo "按 Ctrl+C 停止系统"
echo ""

# 启动系统
python production_local_ai.py