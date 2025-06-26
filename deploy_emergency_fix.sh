#!/bin/bash
# 紧急音频修复部署脚本

echo "🚨 紧急音频修复部署"
echo "使用系统标准G.711编解码器"
echo "=================================="

# 1. 运行音频测试
echo "🧪 运行紧急音频测试..."
python3 src/audio/system_codec.py

# 2. 检查生成的WAV文件
echo "📁 检查生成的音频文件..."
ls -la debug_*.wav 2>/dev/null || echo "⚠️ 未找到WAV文件"

# 3. 启动修复版主程序
echo "🚀 启动紧急修复版系统..."
echo "📞 拨打 14088779998 测试"
echo "🎧 应该听到清晰的DTMF音调: 1-8-7-1"
echo "=================================="

python3 src/main_emergency_fix.py 