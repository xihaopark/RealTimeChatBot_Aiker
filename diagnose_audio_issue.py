#!/usr/bin/env python3
"""
音频问题诊断脚本
按步骤运行诊断工具，从最基础开始排查
"""

import os
import sys
import time
import subprocess
from datetime import datetime

def print_header(title):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"🔍 {title}")
    print("=" * 60)

def print_step(step_num, description):
    """打印步骤"""
    print(f"\n📋 步骤 {step_num}: {description}")
    print("-" * 40)

def run_command(cmd, description):
    """运行命令"""
    print(f"🚀 {description}")
    print(f"命令: {cmd}")
    print()
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print("输出:")
        print(result.stdout)
        if result.stderr:
            print("错误:")
            print(result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return False

def check_network_connectivity():
    """检查网络连通性"""
    print_step(1, "检查网络连通性")
    
    # 检查本地IP
    print("📍 检查本地IP...")
    result = subprocess.run("ifconfig | grep 'inet ' | grep -v 127.0.0.1", 
                          shell=True, capture_output=True, text=True)
    print(result.stdout)
    
    # 检查防火墙
    print("\n🔥 检查防火墙状态...")
    result = subprocess.run("sudo iptables -L -n | grep -E '(udp|5060|10000)'", 
                          shell=True, capture_output=True, text=True)
    if result.stdout:
        print("防火墙规则:")
        print(result.stdout)
    else:
        print("未发现相关防火墙规则")
    
    # 检查端口占用
    print("\n🔌 检查端口占用...")
    result = subprocess.run("netstat -tuln | grep -E '(5060|10000|15000)'", 
                          shell=True, capture_output=True, text=True)
    if result.stdout:
        print("端口占用情况:")
        print(result.stdout)
    else:
        print("相关端口未被占用")

def run_rtp_signal_detector():
    """运行RTP信号检测器"""
    print_step(2, "运行RTP信号检测器")
    
    print("🎯 开始RTP信号检测...")
    print("请拨打测试号码，观察是否有RTP包到达")
    print("检测时长: 10秒")
    
    # 运行快速扫描
    success = run_command("python rtp_signal_detector.py quick", 
                         "RTP信号快速扫描")
    
    if not success:
        print("⚠️ RTP信号检测器运行失败")
        return False
    
    return True

def run_minimal_sip_rtp_test():
    """运行最小化SIP/RTP测试"""
    print_step(3, "运行最小化SIP/RTP测试")
    
    print("🎯 启动最小化SIP/RTP测试...")
    print("这个测试将:")
    print("  1. 监听SIP INVITE")
    print("  2. 解析SDP获取RTP端口")
    print("  3. 监听RTP流量")
    print("  4. 发送测试RTP包")
    print("\n请拨打测试号码进行测试")
    
    # 运行最小化测试
    success = run_command("python minimal_sip_rtp_test.py", 
                         "最小化SIP/RTP测试")
    
    return success

def analyze_results():
    """分析结果"""
    print_step(4, "分析诊断结果")
    
    print("📊 基于以上测试，请回答以下问题:")
    print()
    print("1. 网络连通性:")
    print("   □ 本地IP正常")
    print("   □ 防火墙无阻止")
    print("   □ 端口未被占用")
    print()
    print("2. RTP信号检测:")
    print("   □ 检测到UDP包")
    print("   □ 检测到RTP包")
    print("   □ RTP包格式正确")
    print()
    print("3. SIP/RTP测试:")
    print("   □ 收到INVITE")
    print("   □ SDP解析成功")
    print("   □ RTP端口正确")
    print("   □ 收到RTP包")
    print("   □ 发送RTP包成功")
    print()
    print("4. 音频问题:")
    print("   □ 听到测试音频")
    print("   □ 对方听到音频")
    print("   □ 双向通信正常")

def generate_report():
    """生成诊断报告"""
    print_step(5, "生成诊断报告")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"audio_diagnosis_report_{timestamp}.md"
    
    report_content = f"""# 音频问题诊断报告

**诊断时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 诊断步骤

### 1. 网络连通性检查
- 本地IP: [请填写]
- 防火墙状态: [请填写]
- 端口占用: [请填写]

### 2. RTP信号检测
- 检测到UDP包: [是/否]
- 检测到RTP包: [是/否]
- RTP包格式: [请填写]

### 3. 最小化SIP/RTP测试
- 收到INVITE: [是/否]
- SDP解析: [成功/失败]
- RTP端口: [请填写]
- 收到RTP包: [是/否]
- 发送RTP包: [成功/失败]

### 4. 音频测试
- 听到测试音频: [是/否]
- 对方听到音频: [是/否]
- 双向通信: [正常/异常]

## 问题分析

### 可能的问题
1. **网络层问题**
   - 防火墙阻止UDP流量
   - NAT配置问题
   - 端口映射错误

2. **SIP层问题**
   - SDP解析错误
   - RTP端口分配错误
   - 媒体协商失败

3. **RTP层问题**
   - RTP包格式错误
   - 负载类型不匹配
   - 时间戳问题

4. **音频编解码问题**
   - μ-law编码错误
   - 采样率不匹配
   - 音频格式问题

## 建议解决方案

### 立即行动
1. [根据诊断结果填写]
2. [根据诊断结果填写]
3. [根据诊断结果填写]

### 下一步计划
1. [根据诊断结果填写]
2. [根据诊断结果填写]
3. [根据诊断结果填写]

---
*报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"✅ 诊断报告已生成: {report_file}")
    print(f"请根据测试结果填写报告内容")

def main():
    """主函数"""
    print_header("音频问题诊断工具")
    print("🎯 从最基础开始诊断音频问题")
    print("📋 将按步骤运行诊断工具")
    print("⏱️ 预计总时间: 5-10分钟")
    
    # 检查工具是否存在
    tools = ["rtp_signal_detector.py", "minimal_sip_rtp_test.py"]
    missing_tools = []
    
    for tool in tools:
        if not os.path.exists(tool):
            missing_tools.append(tool)
    
    if missing_tools:
        print(f"\n❌ 缺少诊断工具: {', '.join(missing_tools)}")
        print("请确保所有诊断工具都在当前目录")
        return 1
    
    print(f"\n✅ 所有诊断工具就绪")
    
    try:
        # 步骤1: 检查网络连通性
        check_network_connectivity()
        
        # 步骤2: 运行RTP信号检测器
        print("\n" + "=" * 60)
        print("🎯 准备运行RTP信号检测器")
        print("请确保测试号码可用，然后按回车继续...")
        input()
        
        run_rtp_signal_detector()
        
        # 步骤3: 运行最小化SIP/RTP测试
        print("\n" + "=" * 60)
        print("🎯 准备运行最小化SIP/RTP测试")
        print("请确保测试号码可用，然后按回车继续...")
        input()
        
        run_minimal_sip_rtp_test()
        
        # 步骤4: 分析结果
        analyze_results()
        
        # 步骤5: 生成报告
        generate_report()
        
        print_header("诊断完成")
        print("✅ 所有诊断步骤已完成")
        print("📋 请根据测试结果填写诊断报告")
        print("🔧 根据报告建议进行问题修复")
        
    except KeyboardInterrupt:
        print("\n\n🛑 诊断被用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 诊断过程中出现错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 