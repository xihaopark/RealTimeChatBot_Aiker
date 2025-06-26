#!/bin/bash
"""
修复版Aiker部署脚本
专注解决：1. 生成可用的G.711μ-law音频流  2. 实时人声检测显示
"""

echo "🎯 修复版Aiker - OneSuite 商业客服机器人"
echo "专注解决：1. 生成可用的G.711μ-law音频流"
echo "          2. 实时人声检测显示"
echo "=================================================="

# 检查Python环境
echo "🔍 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查依赖
echo "📦 检查核心依赖..."
python3 -c "import numpy" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ numpy 未安装，正在安装..."
    pip3 install numpy
fi

# 检查配置文件
echo "⚙️ 检查配置文件..."
if [ ! -f "config/settings.py" ]; then
    echo "❌ 配置文件不存在"
    exit 1
fi

# 检查API密钥
echo "🔑 检查API密钥..."
if [ ! -f "api_keys/openai.key" ]; then
    echo "⚠️ OpenAI API密钥未配置（可选）"
fi

echo "✅ 环境检查完成"
echo ""

# 运行核心音频测试
echo "🧪 运行核心音频功能测试..."
python3 test_core_audio.py
if [ $? -ne 0 ]; then
    echo "❌ 核心音频测试失败"
    exit 1
fi

echo ""
echo "🚀 启动修复版Aiker系统..."
echo "📞 等待来电: 14088779998"
echo "🎧 预期听到: 800Hz测试音调"
echo "🎤 预期看到: 实时VAD检测"
echo ""

# 运行修复版主程序
python3 src/main_fixed.py 