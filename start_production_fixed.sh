#!/bin/bash

# VTX AI电话系统启动脚本 - 修复CUDA库问题
echo "🚀 启动VTX AI电话系统（修复版）"
echo "=================================="

# 设置CUDA环境变量
export LD_LIBRARY_PATH=/usr/local/cuda-11.8/targets/x86_64-linux/lib:$LD_LIBRARY_PATH
export CUDA_VISIBLE_DEVICES=0

# 设置其他环境变量
export ALSA_PCM_CARD=null
export ALSA_PCM_DEVICE=0
export SDL_AUDIODRIVER=dummy
export TRANSFORMERS_VERBOSITY=error

# 完全禁用PyAudio音频设备检测
export PULSE_RUNTIME_PATH=/tmp/no-pulse
export PULSE_SERVER=unix:/tmp/no-pulse/pulse/native
export XDG_RUNTIME_DIR=/tmp/no-pulse

echo "🔧 CUDA环境已配置"
echo "📚 库路径: $LD_LIBRARY_PATH"

# 检查CUDA库是否可用
if [ -f "/usr/lib/x86_64-linux-gnu/libcublas.so.12" ]; then
    echo "✅ CUDA BLAS库已就绪"
else
    echo "⚠️ 创建CUDA BLAS符号链接..."
    sudo ln -sf /usr/local/cuda-11.8/targets/x86_64-linux/lib/libcublas.so.11 /usr/lib/x86_64-linux-gnu/libcublas.so.12
    sudo ln -sf /usr/local/cuda-11.8/targets/x86_64-linux/lib/libcublasLt.so.11 /usr/lib/x86_64-linux-gnu/libcublasLt.so.12
    echo "✅ CUDA符号链接已创建"
fi

echo "🎯 启动AI电话系统..."
python production_local_ai.py