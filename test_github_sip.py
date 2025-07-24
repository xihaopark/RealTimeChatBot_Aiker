#!/usr/bin/env python3
"""
测试GitHub版本SIP客户端连接 + 完整AI对话系统
使用GPU环境中的本地AI服务
"""

import os
import sys
import time
import signal

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from working_sip_client import WorkingSIPClient
from ai_phone_handler import AIPhoneHandler

class SIPTest:
    def __init__(self):
        self.config = settings
        self.sip_client = None
        self.ai_handler = None
        self.running = False
    
    def start(self):
        print("🧪 GitHub版本SIP客户端测试")
        print(f"📞 分机: 101@{self.config.vtx.domain}")
        print(f"🌐 服务器: {self.config.vtx.server}:{self.config.vtx.port}")
        print(f"📱 DID: {self.config.vtx.did_number}")
        print("-" * 50)
        
        # 初始化AI处理器
        print("🤖 初始化AI处理器...")
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
            print(f"📞 等待来电: {self.config.vtx.did_number}")
            self._main_loop()
        else:
            print("❌ SIP客户端启动失败")
    
    def _handle_incoming_call(self, call_info):
        """处理来电"""
        print(f"📞 来电处理: {call_info['caller']}")
        print(f"📍 远程RTP: {call_info['remote_ip']}:{call_info['remote_port']}")
        print(f"📍 本地RTP: {call_info['local_rtp_port']}")
        
        # 连接AI处理器到RTP流
        if self.ai_handler and 'rtp_handler' in call_info:
            rtp_handler = call_info['rtp_handler']
            
            # 设置AI处理器的音频输出回调
            self.ai_handler.set_audio_callback(rtp_handler.send_audio)
            
            # 设置RTP的音频接收回调为AI处理器
            rtp_handler.set_audio_callback(self.ai_handler.process_audio_chunk)
            
            print("🤖 AI对话系统已连接")
            
            # 发送欢迎消息
            self.ai_handler.send_welcome_message()
        else:
            print("🤖 使用基本欢迎消息")
            print("🎵 欢迎致电OneSuite Business！我是您的AI助手。")
    
    def _main_loop(self):
        try:
            while self.running:
                time.sleep(1)
                # 每60秒显示一次状态
                if hasattr(self, '_last_status') and time.time() - self._last_status > 60:
                    self._show_status()
                elif not hasattr(self, '_last_status'):
                    self._last_status = time.time()
                    
        except KeyboardInterrupt:
            print("\n🛑 用户中断，系统停止")
        finally:
            self.stop()
    
    def _show_status(self):
        """显示系统状态"""
        if self.sip_client:
            status = "🟢 已注册" if self.sip_client.is_registered else "🔴 未注册"
            print(f"💓 系统状态: {status}")
        self._last_status = time.time()
    
    def stop(self):
        """停止系统"""
        print("🛑 停止SIP测试...")
        self.running = False
        
        if self.ai_handler:
            self.ai_handler.stop()
            
        if self.sip_client:
            self.sip_client.stop()
        
        print("✅ SIP测试已停止")

def signal_handler(signum, frame):
    """信号处理器"""
    print(f"\n🛑 收到信号 {signum}")
    if 'test' in globals():
        test.stop()
    sys.exit(0)

if __name__ == "__main__":
    print("🚀 VTX AI Phone System - 完整版")
    print("📍 请确保在GPU环境中运行: source gpu_env/bin/activate")
    print("=" * 60)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        test = SIPTest()
        test.start()
    except Exception as e:
        print(f"❌ 测试错误: {e}")
        sys.exit(1)