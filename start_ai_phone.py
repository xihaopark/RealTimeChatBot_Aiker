#!/usr/bin/env python3
"""
VTX AI电话系统 - 正式版启动脚本
完整的SIP + AI对话功能
"""

import os
import sys
import signal
import time

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from working_sip_client import WorkingSIPClient
from ai_phone_handler import AIPhoneHandler

class VTXAIPhoneSystem:
    """VTX AI电话系统"""
    
    def __init__(self):
        self.config = settings
        self.sip_client = None
        self.ai_handler = None
        self.running = False
        self.call_count = 0
        
    def start(self):
        """启动系统"""
        print("🚀 VTX AI Phone System - 正式版")
        print("=" * 60)
        print(f"📞 分机: 101@{self.config.vtx.domain}")
        print(f"🌐 服务器: {self.config.vtx.server}:{self.config.vtx.port}")
        print(f"📱 DID: {self.config.vtx.did_number}")
        print("=" * 60)
        
        # 初始化AI处理器
        print("🤖 初始化AI对话系统...")
        self.ai_handler = AIPhoneHandler()
        if not self.ai_handler.start():
            print("⚠️ AI处理器启动失败，继续使用基本功能")
            self.ai_handler = None
        
        # 创建SIP客户端
        ext = self.config.extensions['101']
        self.sip_client = WorkingSIPClient(
            username=ext.username,
            password=ext.password,
            domain=self.config.vtx.domain,
            server=self.config.vtx.server,
            port=self.config.vtx.port
        )
        
        # 设置来电处理回调
        self.sip_client.set_call_handler(self._handle_incoming_call)
        
        # 启动SIP客户端
        if self.sip_client.start():
            self.running = True
            print("🎉 系统启动成功！")
            print(f"📞 等待来电: {self.config.vtx.did_number}")
            print("💡 现在可以拨打电话测试AI对话功能")
            print("-" * 60)
            self._main_loop()
        else:
            print("❌ SIP客户端启动失败")
    
    def _handle_incoming_call(self, call_info):
        """处理来电"""
        self.call_count += 1
        caller = call_info['caller']
        
        print(f"\n🎊 第{self.call_count}通来电！")
        print(f"📞 来电号码: {caller}")
        print(f"🎵 RTP会话: {call_info['remote_ip']}:{call_info['remote_port']} <-> 本地:{call_info['local_rtp_port']}")
        
        # 连接AI处理器到RTP流
        if self.ai_handler and 'rtp_handler' in call_info:
            rtp_handler = call_info['rtp_handler']
            
            # 设置双向音频处理
            self.ai_handler.set_audio_callback(rtp_handler.send_audio)
            rtp_handler.set_audio_callback(self.ai_handler.process_audio_chunk)
            
            print("🤖 AI对话系统已连接 - 准备进行智能对话")
            print("🎤 正在监听您的语音...")
            
            # 发送AI欢迎消息
            self.ai_handler.send_welcome_message()
        else:
            print("🤖 使用基本欢迎消息")
            print("🎵 欢迎致电OneSuite Business！我是您的AI助手。")
        
        print("-" * 40)
    
    def _main_loop(self):
        """主循环"""
        try:
            last_status_time = time.time()
            
            while self.running:
                time.sleep(1)
                
                # 每60秒显示一次状态
                if time.time() - last_status_time > 60:
                    self._show_status()
                    last_status_time = time.time()
                    
        except KeyboardInterrupt:
            print("\n🛑 用户中断，正在关闭系统...")
        finally:
            self.stop()
    
    def _show_status(self):
        """显示系统状态"""
        if self.sip_client:
            status = "🟢 已注册" if self.sip_client.is_registered else "🔴 未注册"
            print(f"💓 系统状态: {status} | 已处理 {self.call_count} 通电话")
    
    def stop(self):
        """停止系统"""
        print("🛑 正在停止VTX AI电话系统...")
        self.running = False
        
        if self.ai_handler:
            self.ai_handler.stop()
            
        if self.sip_client:
            self.sip_client.stop()
        
        print("✅ VTX AI电话系统已停止")
        print("👋 感谢使用！")

def signal_handler(signum, frame):
    """信号处理器"""
    print(f"\n🛑 收到信号 {signum}")
    if 'system' in globals():
        system.stop()
    sys.exit(0)

if __name__ == "__main__":
    print("🔋 请确保在GPU环境中运行:")
    print("   source gpu_env/bin/activate && python start_ai_phone.py")
    print()
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        system = VTXAIPhoneSystem()
        system.start()
    except Exception as e:
        print(f"❌ 系统错误: {e}")
        sys.exit(1)