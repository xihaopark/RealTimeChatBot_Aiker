#!/bin/bash

# VTX AI Phone System 启动脚本 v2.0
# 支持AI模式和测试模式

echo "🚀 VTX AI Phone System v2.0"
echo "=================================="

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查主程序文件
MAIN_PROGRAM="main.py"
if [ ! -f "$MAIN_PROGRAM" ]; then
    echo "❌ 主程序不存在: $MAIN_PROGRAM"
    echo "🔍 查找其他主程序文件..."
    if [ -f "src/main.py" ]; then
        echo "⚠️ 找到 src/main.py，但建议使用根目录的 main.py"
        MAIN_PROGRAM="src/main.py"
    else
        echo "❌ 未找到任何主程序文件"
        exit 1
    fi
fi

# 检查配置文件
if [ ! -f "config/settings.py" ]; then
    echo "⚠️ 配置文件不存在，使用默认配置"
fi

# 检查API密钥
if [ ! -d "api_keys" ]; then
    echo "⚠️ API密钥目录不存在"
fi

# 检查音频缓存
if [ ! -d "audio_cache" ]; then
    echo "📁 创建音频缓存目录..."
    mkdir -p audio_cache
fi

# 检查是否已有进程在运行
if pgrep -f "python3.*main.py" > /dev/null; then
    echo "⚠️ 检测到已有VTX进程在运行"
    echo "正在停止旧进程..."
    pkill -f "python3.*main.py"
    sleep 2
fi

# 显示启动信息
echo "📞 启动AI电话系统..."
echo "📁 主程序: $MAIN_PROGRAM"
echo "🎵 支持音频通话"
echo "🤖 AI功能: 启用"
echo "📞 测试号码: 14088779998"
echo ""

# 启动主程序
echo "🚀 正在启动..."
python3 "$MAIN_PROGRAM"

# 如果程序异常退出，显示错误信息
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 程序异常退出"
    echo "�� 请检查日志文件或重新启动"
fi
