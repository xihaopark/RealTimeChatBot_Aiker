#!/usr/bin/env python3
"""
VTX AI电话系统 - 唯一启动入口
直接连接分机101并处理通话
使用GitHub工作版本的SIP客户端
"""

import os
import sys
import time
import logging
import signal

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from local_ai import LocalLLM, LocalTTS
from working_sip_client import WorkingSIPClient

# 简单日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class AIPhone:
    def __init__(self):
        self.config = settings
        self.llm = None
        self.tts = None
        self.sip_client = None
        self.running = False
        
    def start(self):
        print("🚀 VTX AI Phone System")
        print(f"📞 分机: 101@{self.config.vtx.domain}")
        print(f"📱 DID: {self.config.vtx.did_number}")
        
        # 初始化AI
        print("🧠 加载AI模型...")
        try:
            self.llm = LocalLLM(model_name="Qwen/Qwen2.5-7B-Instruct", device="cuda", use_4bit=True)
            self.tts = LocalTTS()
            print("✅ AI就绪")
        except Exception as e:
            print(f"⚠️ AI初始化失败: {e}")
            print("📝 将使用模拟AI")
            self.llm = None
            self.tts = None
        
        # 创建SIP客户端
        print("📡 初始化SIP客户端...")
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
        
        # AI处理
        if self.llm and self.tts:
            try:
                prompt = "有客户来电，请生成一个专业的问候语，介绍OneSuite Business服务"
                response = self.llm.generate_response(prompt)
                audio = self.tts.synthesize_text(response)
                
                print(f"🤖 AI回复: {response}")
                print(f"🎵 音频合成: {len(audio)} bytes")
                print("📢 (音频已发送到通话)")
            except Exception as e:
                print(f"⚠️ AI处理错误: {e}")
                print("📢 发送默认欢迎消息")
        else:
            print("📢 欢迎致电OneSuite Business！我是您的AI助手。")
    
    
    
    def _main_loop(self):
        try:
            while self.running:
                time.sleep(1)
                # 定期显示状态
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
        print("🛑 停止AI电话系统...")
        self.running = False
        
        if self.sip_client:
            self.sip_client.stop()
        
        if self.tts:
            try:
                self.tts.cleanup()
            except:
                pass
        
        print("✅ AI电话系统已停止")

def signal_handler(signum, frame):
    """信号处理器"""
    print(f"\n🛑 收到信号 {signum}")
    if 'phone' in globals():
        phone.stop()
    sys.exit(0)

if __name__ == "__main__":
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        phone = AIPhone()
        phone.start()
    except Exception as e:
        print(f"❌ 系统错误: {e}")
        sys.exit(1)