#!/bin/bash

# VTX AI Phone System 快速启动脚本
# 使用方法: ./vtx.sh [start|stop|status|restart|test]

case "${1:-start}" in
    start)
        echo "🚀 启动VTX AI电话系统..."
        ./start_vtx.sh
        ;;
    stop)
        echo "🛑 停止VTX系统..."
        pkill -f "python3.*main.py"
        echo "✅ VTX系统已停止"
        ;;
    status)
        echo "📊 VTX系统状态..."
        ./monitor_vtx.sh
        ;;
    restart)
        echo "🔄 重启VTX系统..."
        pkill -f "python3.*main.py"
        sleep 2
        ./start_vtx.sh
        ;;
    test)
        echo "🧪 打开测试工具..."
        ./test_vtx.sh
        ;;
    *)
        echo "VTX AI Phone System 快速控制"
        echo "================================"
        echo "用法: ./vtx.sh [命令]"
        echo ""
        echo "命令:"
        echo "  start   - 启动系统"
        echo "  stop    - 停止系统"
        echo "  status  - 查看状态"
        echo "  restart - 重启系统"
        echo "  test    - 打开测试工具"
        echo ""
        echo "示例:"
        echo "  ./vtx.sh start    # 启动系统"
        echo "  ./vtx.sh status   # 查看状态"
        echo "  ./vtx.sh stop     # 停止系统"
        ;;
esac 