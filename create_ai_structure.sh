#!/bin/bash
# 创建 AI 模块目录结构

echo "创建 AI 模块目录..."

# 创建 ai 目录
mkdir -p src/ai

# 创建文件
touch src/ai/__init__.py
touch src/ai/stt_engine.py
touch src/ai/tts_engine.py
touch src/ai/llm_handler.py
touch src/ai/conversation_manager.py

echo "✅ AI 模块目录结构创建完成"

# 显示创建的结构
echo ""
echo "创建的文件："
ls -la src/ai/