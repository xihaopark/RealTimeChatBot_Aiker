#!/bin/bash

# VTX AI Phone System 测试脚本

echo "🧪 VTX AI Phone System 测试工具"
echo "=================================="

# 检查当前状态
echo "📊 当前系统状态:"
if pgrep -f "python3.*main.py" > /dev/null; then
    echo "✅ VTX系统正在运行"
    RUNNING=true
else
    echo "❌ VTX系统未运行"
    RUNNING=false
fi

echo ""
echo "🎯 测试选项:"
echo "1. 启动VTX系统"
echo "2. 停止VTX系统"
echo "3. 重启VTX系统"
echo "4. 生成测试音频"
echo "5. 测试音频播放"
echo "6. 检查系统状态"
echo "7. 测试网络连接"
echo "8. 清理缓存"
echo "0. 退出"

read -p "请选择操作 (0-8): " choice

case $choice in
    1)
        echo "🚀 启动VTX系统..."
        ./start_vtx.sh
        ;;
    2)
        echo "🛑 停止VTX系统..."
        pkill -f "python3.*main.py"
        echo "✅ VTX系统已停止"
        ;;
    3)
        echo "🔄 重启VTX系统..."
        pkill -f "python3.*main.py"
        sleep 2
        ./start_vtx.sh
        ;;
    4)
        echo "🎵 生成测试音频..."
        python3 test_audio_generation.py
        ;;
    5)
        echo "🎵 测试音频播放..."
        python3 test_audio_playback.py
        ;;
    6)
        echo "📊 检查系统状态..."
        ./monitor_vtx.sh
        ;;
    7)
        echo "🌐 测试网络连接..."
        echo "测试VTX服务器连接:"
        ping -c 3 core1-us-lax.myippbx.com
        echo ""
        echo "测试DNS解析:"
        nslookup core1-us-lax.myippbx.com
        ;;
    8)
        echo "🧹 清理缓存..."
        if [ -d "audio_cache" ]; then
            rm -rf audio_cache/*
            echo "✅ 音频缓存已清理"
        fi
        if [ -d "__pycache__" ]; then
            rm -rf __pycache__
            echo "✅ Python缓存已清理"
        fi
        ;;
    0)
        echo "👋 退出测试工具"
        exit 0
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "✅ 操作完成" 