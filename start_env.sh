#!/bin/bash

# VTX AI Phone System - 环境启动脚本
echo "🚀 启动 VTX AI Phone System 虚拟环境..."

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行以下命令创建："
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements_cpu.txt"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

echo "✅ 虚拟环境已激活"
echo "📦 Python 版本: $(python --version)"
echo "📍 虚拟环境路径: $(which python)"

# 检查关键依赖
echo "🔍 检查关键依赖..."
python -c "
try:
    import openai
    import aiohttp
    import pydub
    import edge_tts
    import elevenlabs
    import deepgram
    print('✅ 所有关键依赖已安装')
except ImportError as e:
    print(f'❌ 缺少依赖: {e}')
    print('请运行: pip install -r requirements_cpu.txt')
"

echo ""
echo "🎯 环境配置完成！"
echo "💡 提示："
echo "   - 使用 'python main.py' 启动主程序"
echo "   - 使用 'python main_ai.py' 启动AI版本"
echo "   - 使用 'deactivate' 退出虚拟环境"
echo ""

# 保持shell在虚拟环境中
exec "$SHELL" 