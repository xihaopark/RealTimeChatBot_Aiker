#!/usr/bin/env python3
"""
测试修复后的SIP注册功能
验证同步注册机制是否正常工作
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from sip_client import EnhancedSIPClient
import time

def test_sip_registration():
    """测试SIP注册功能"""
    print("🧪 测试修复后的SIP注册功能")
    print("=" * 50)
    
    # 获取分机配置
    try:
        extension_id = list(settings.extensions.keys())[0]
        extension = settings.extensions[extension_id]
        print(f"📋 使用分机: {extension.username}@{settings.vtx.domain}")
    except Exception as e:
        print(f"❌ 获取分机配置失败: {e}")
        return False
    
    # 创建SIP客户端
    sip_client = EnhancedSIPClient(
        username=extension.username,
        password=extension.password,
        domain=settings.vtx.domain,
        server=settings.vtx.server,
        port=settings.vtx.port
    )
    
    # 设置简单的来电处理回调
    def handle_call(call_info):
        print(f"📞 收到来电测试: {call_info['caller']}")
        print(f"🎵 RTP信息: {call_info['remote_ip']}:{call_info['remote_port']}")
    
    sip_client.set_call_handler(handle_call)
    
    # 测试启动
    print("\n🚀 开始SIP注册测试...")
    if sip_client.start():
        print("✅ SIP注册测试成功!")
        print(f"📞 注册状态: {'已注册' if sip_client.is_registered else '未注册'}")
        
        # 保持运行10秒测试稳定性
        print("⏳ 保持连接10秒测试稳定性...")
        for i in range(10):
            print(f"💓 {10-i}秒... (状态: {'在线' if sip_client.is_registered else '离线'})")
            time.sleep(1)
        
        print("🛑 停止测试...")
        sip_client.stop()
        print("✅ SIP注册测试完成!")
        return True
    else:
        print("❌ SIP注册测试失败!")
        sip_client.stop()
        return False

if __name__ == "__main__":
    try:
        success = test_sip_registration()
        if success:
            print("\n🎉 所有测试通过! SIP注册修复成功!")
            sys.exit(0)
        else:
            print("\n💥 测试失败! 需要进一步调试!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 用户中断测试")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)