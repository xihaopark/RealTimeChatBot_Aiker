#!/bin/bash

# VTX AI Phone System 监控脚本 v2.0

echo "📊 VTX AI Phone System 状态监控"
echo "=================================="

# 检查进程
echo "🔍 检查VTX进程..."
if pgrep -f "python3.*main.py" > /dev/null; then
    echo "✅ VTX主程序运行中"
    echo "📋 进程详情:"
    ps aux | grep "python3.*main.py" | grep -v grep
else
    echo "❌ VTX主程序未运行"
fi

# 检查端口
echo ""
echo "🔌 端口状态:"
echo "SIP端口 (5060):"
netstat -tlnp 2>/dev/null | grep ":5060" || echo "  ❌ 未监听"
echo "RTP端口范围 (10000-20000):"
netstat -tlnp 2>/dev/null | grep -E ":(10[0-9]{3}|1[1-9][0-9]{3}|2[0-9]{4})" || echo "  ❌ 未监听"

# 检查文件状态
echo ""
echo "📁 文件状态:"
if [ -f "main.py" ]; then
    echo "✅ 主程序: main.py"
elif [ -f "src/main.py" ]; then
    echo "✅ 主程序: src/main.py"
else
    echo "❌ 主程序文件不存在"
fi

if [ -d "audio_cache" ]; then
    echo "✅ 音频缓存目录存在"
    echo "  📂 缓存文件:"
    ls -la audio_cache/ 2>/dev/null | head -5
else
    echo "❌ 音频缓存目录不存在"
fi

if [ -d "api_keys" ]; then
    echo "✅ API密钥目录存在"
else
    echo "❌ API密钥目录不存在"
fi

# 检查网络连接
echo ""
echo "🌐 网络连接测试:"
echo "VTX服务器连接:"
ping -c 1 core1-us-lax.myippbx.com >/dev/null 2>&1 && echo "  ✅ 可达" || echo "  ❌ 不可达"

# 检查系统资源
echo ""
echo "💻 系统资源:"
echo "CPU使用率:"
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1
echo "内存使用:"
free -h | grep "Mem:" | awk '{print "  总计: " $2 " 已用: " $3 " 可用: " $4}'

# 检查日志
echo ""
echo "📝 最近日志:"
if [ -f "logs/vtx_system.log" ]; then
    echo "✅ 找到日志文件"
    tail -5 logs/vtx_system.log
else
    echo "❌ 未找到日志文件"
fi

echo ""
echo "🎯 快速操作:"
echo "  启动: ./start_vtx.sh"
echo "  停止: pkill -f 'python3.*main.py'"
echo "  重启: ./start_vtx.sh"
