#!/usr/bin/env python3
"""
SIP注册测试脚本
测试SIP客户端的注册功能
"""

import os
import sys
import time
import signal
import threading

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from sip_client import EnhancedSIPClient


def test_sip_registration():
    """测试SIP注册"""
    print("=== SIP注册测试 ===")
    
    try:
        # 获取分机配置
        extension_id = list(settings.extensions.keys())[0]
        extension = settings.extensions[extension_id]
        
        print(f"测试分机: {extension.username}")
        print(f"服务器: {settings.vtx.server}:{settings.vtx.port}")
        print(f"域名: {settings.vtx.domain}")
        
        # 创建SIP客户端
        sip_client = EnhancedSIPClient(
            username=extension.username,
            password=extension.password,
            domain=settings.vtx.domain,
            server=settings.vtx.server,
            port=settings.vtx.port
        )
        
        # 设置来电处理（测试用）
        def handle_call(call_info):
            print(f"📞 收到来电: {call_info}")
        
        sip_client.set_call_handler(handle_call)
        
        print("\n🚀 启动SIP客户端...")
        
        # 启动客户端
        if sip_client.start():
            print("✅ SIP客户端启动成功")
            
            # 等待注册完成
            print("⏳ 等待注册...")
            time.sleep(5)
            
            if sip_client.is_registered:
                print("✅ SIP注册成功!")
                print(f"📞 可以接收来电: {settings.vtx.did_number}")
                
                # 保持运行30秒来测试
                print("🕐 保持运行30秒以测试来电...")
                
                def stop_test():
                    time.sleep(30)
                    print("\n⏰ 测试时间结束")
                    sip_client.stop()
                
                # 启动定时器
                timer = threading.Timer(30, stop_test)
                timer.start()
                
                # 主循环
                try:
                    while sip_client.is_registered:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n⚠️ 用户中断")
                
                timer.cancel()
                sip_client.stop()
                
                return True
                
            else:
                print("❌ SIP注册失败")
                sip_client.stop()
                return False
                
        else:
            print("❌ SIP客户端启动失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def signal_handler(signum, frame):
    """信号处理器"""
    print(f"\n🛑 收到信号 {signum}，正在退出...")
    sys.exit(0)


def main():
    """主函数"""
    print("VTX AI Phone System - SIP注册测试\n")
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 运行测试
    success = test_sip_registration()
    
    if success:
        print("\n🎉 SIP注册测试成功!")
        print("💡 提示: 如果需要测试来电，请使用软电话拨打: {}".format(settings.vtx.did_number))
        return 0
    else:
        print("\n❌ SIP注册测试失败")
        print("💡 提示: 请检查网络连接和分机配置")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)