#!/bin/bash
"""
PCMU修复版部署脚本
使用北美标准G.711 μ-law编码
"""

echo "🎯 PCMU修复版部署脚本"
echo "使用北美标准G.711 μ-law编码"
echo "=================================="

# 检查Python环境
echo "🔍 检查Python环境..."
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ Python3未安装"
    exit 1
fi

# 检查audioop库
echo "🔍 检查audioop库..."
python3 -c "import audioop; print('✅ audioop库可用')"
if [ $? -ne 0 ]; then
    echo "❌ audioop库不可用"
    exit 1
fi

# 检查配置文件
echo "🔍 检查配置文件..."
if [ ! -f "config/settings.py" ]; then
    echo "❌ 配置文件不存在: config/settings.py"
    exit 1
fi

# 运行北美VoIP诊断
echo "🔍 运行北美VoIP诊断..."
python3 north_america_voip_fix.py diagnose

# 生成测试音频
echo "🎵 生成测试音频..."
python3 north_america_voip_fix.py test

# 检查生成的音频文件
if [ -f "north_america_test.wav" ]; then
    echo "✅ 测试音频文件已生成: north_america_test.wav"
    ls -la north_america_test.wav
else
    echo "❌ 测试音频文件生成失败"
    exit 1
fi

echo ""
echo "🚀 启动PCMU修复版主程序..."
echo "📞 等待来电: 14088779998"
echo "🎵 预期听到: DTMF序列 1-8-7-1"
echo ""

# 启动主程序
python3 main_pcmu_fixed.py 