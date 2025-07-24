#!/bin/bash

# VTX AI电话系统启动脚本 - HTTP TTS版本
echo "🚀 启动VTX AI电话系统（HTTP TTS版）"
echo "======================================"

# 设置CUDA环境变量
export LD_LIBRARY_PATH=/usr/local/cuda-11.8/targets/x86_64-linux/lib:$LD_LIBRARY_PATH
export CUDA_VISIBLE_DEVICES=0

# 设置其他环境变量
export TRANSFORMERS_VERBOSITY=error

echo "🔧 环境已配置"
echo "📚 库路径: $LD_LIBRARY_PATH"

# 检查CosyVoice服务是否可用
echo "🔍 检查CosyVoice服务..."
if curl -s http://localhost:50000/docs > /dev/null 2>&1; then
    echo "✅ CosyVoice服务运行正常"
else
    echo "⚠️ CosyVoice服务不可用，将使用fallback音频"
    echo "💡 要启动CosyVoice服务，请在另一个终端运行："
    echo "   ./start_cosyvoice.sh"
fi

echo ""
echo "🎯 启动AI电话系统..."
python production_local_ai.py