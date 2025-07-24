#!/bin/bash

# CosyVoice TTS服务启动脚本
echo "🎤 启动CosyVoice TTS服务"
echo "=========================="

cd CosyVoice

# 设置环境变量
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128

echo "🔧 环境配置完成"
echo "📚 启动CosyVoice FastAPI服务器..."

# 启动CosyVoice服务
python runtime/python/fastapi/server.py \
    --port 50000 \
    --model_dir "iic/CosyVoice-300M"

echo "CosyVoice服务已停止"