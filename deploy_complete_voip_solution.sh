#!/bin/bash
"""
完整VoIP解决方案部署脚本
整合北美G.711 μ-law标准、技术验证和PCMU修复
"""

echo "🎯 完整VoIP解决方案部署"
echo "基于北美G.711 μ-law标准"
echo "=================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查函数
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✅ $1 已安装${NC}"
        return 0
    else
        echo -e "${RED}❌ $1 未安装${NC}"
        return 1
    fi
}

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✅ $1 存在${NC}"
        return 0
    else
        echo -e "${RED}❌ $1 不存在${NC}"
        return 1
    fi
}

# 1. 环境检查
echo -e "\n${BLUE}🔍 环境检查${NC}"
echo "=================="

check_command "python3"
check_command "git"
check_file "config/settings.py"

# 检查Python依赖
echo -e "\n${BLUE}🔍 Python依赖检查${NC}"
python3 -c "import audioop; print('✅ audioop库可用')" || {
    echo -e "${RED}❌ audioop库不可用${NC}"
    exit 1
}

# 2. 技术验证
echo -e "\n${BLUE}🔍 技术验证${NC}"
echo "=================="

echo "运行完整技术分析..."
python3 voip_technical_analysis.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 技术验证通过${NC}"
else
    echo -e "${RED}❌ 技术验证失败${NC}"
    exit 1
fi

# 3. 北美VoIP诊断
echo -e "\n${BLUE}🔍 北美VoIP诊断${NC}"
echo "=================="

echo "运行北美VoIP诊断..."
python3 north_america_voip_fix.py diagnose

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 北美VoIP诊断通过${NC}"
else
    echo -e "${RED}❌ 北美VoIP诊断失败${NC}"
    exit 1
fi

# 4. 生成测试音频
echo -e "\n${BLUE}🎵 生成测试音频${NC}"
echo "=================="

echo "生成北美标准测试音频..."
python3 north_america_voip_fix.py test

if [ -f "north_america_test.wav" ]; then
    echo -e "${GREEN}✅ 测试音频已生成${NC}"
    ls -la north_america_test.wav
else
    echo -e "${RED}❌ 测试音频生成失败${NC}"
    exit 1
fi

# 5. 系统状态检查
echo -e "\n${BLUE}🔍 系统状态检查${NC}"
echo "=================="

# 检查网络端口
echo "检查网络端口..."
netstat -an | grep -E ":(5060|10000|10001|10002)" | head -5

# 检查音频设备（macOS）
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "检查音频设备..."
    system_profiler SPAudioDataType | grep -A 5 "Default Input\|Default Output"
fi

# 6. 部署选项
echo -e "\n${BLUE}🚀 部署选项${NC}"
echo "=================="

echo "1. 运行PCMU修复版主程序"
echo "2. 运行紧急修复版"
echo "3. 运行原始版本"
echo "4. 运行RTP流捕获"
echo "5. 退出"

read -p "选择部署选项 (1-5): " choice

case $choice in
    1)
        echo -e "\n${GREEN}🚀 启动PCMU修复版主程序${NC}"
        echo "使用北美标准G.711 μ-law编码"
        echo "预期听到: DTMF序列 1-8-7-1"
        echo "按Ctrl+C退出..."
        echo ""
        python3 main_pcmu_fixed.py
        ;;
    2)
        echo -e "\n${YELLOW}🚀 启动紧急修复版${NC}"
        echo "使用系统标准audioop编解码器"
        echo "预期听到: 清晰的DTMF音调"
        echo "按Ctrl+C退出..."
        echo ""
        python3 src/main_emergency_fix.py
        ;;
    3)
        echo -e "\n${BLUE}🚀 启动原始版本${NC}"
        echo "使用原始AI集成版本"
        echo "按Ctrl+C退出..."
        echo ""
        python3 src/main.py
        ;;
    4)
        echo -e "\n${BLUE}📡 启动RTP流捕获${NC}"
        port=${1:-10000}
        duration=${2:-10}
        echo "捕获端口: $port, 时长: $duration秒"
        python3 north_america_voip_fix.py capture $port $duration
        ;;
    5)
        echo "退出..."
        exit 0
        ;;
    *)
        echo "无效选择"
        exit 1
        ;;
esac

# 7. 部署后检查
if [ $choice -ne 4 ] && [ $choice -ne 5 ]; then
    echo -e "\n${BLUE}📊 部署后状态${NC}"
    echo "=================="
    
    echo "检查进程状态..."
    ps aux | grep python | grep -v grep
    
    echo -e "\n${GREEN}✅ 部署完成${NC}"
    echo "系统已启动，等待来电..."
    echo "测试号码: 14088779998"
fi 