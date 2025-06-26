#!/usr/bin/env python3
"""
VTX AI Phone System - 主程序（集成 AI）
"""

import sys
import os
import time
import signal
import threading
from typing import Optional

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from src.sip import SIPClient
from src.sdp import SDPParser
from src.rtp import RTPHandler
from src.audio import AudioGenerator
from src.ai.conversation_manager import ConversationManager, ConversationConfig
from src.ai.stt_engine import STTConfig, STTProvider
from src.ai.tts_engine import TTSConfig, TTSProvider
from src.ai.llm_handler import LLMConfig, LLMProvider, SYSTEM_PROMPTS


class VTXAIPhoneSystem:
    """VTX AI 电话系统主类"""
    
    def __init__(self):
        # 获取配置
        ext = settings.get_extension('101')
        if not ext:
            raise ValueError("分机 101 未配置")
        
        # 创建 SIP 客户端
        self.sip_client = SIPClient(
            server=settings.vtx.server,
            port=settings.vtx.port,
            domain=settings.vtx.domain,
            username=ext.username,
            password=ext.password
        )
        
        # AI 配置
        self.ai_enabled = True  # 是否启用 AI
        self.conversation_manager = None
        self.current_rtp_handler = None
        
        # 初始化 AI（如果启用）
        if self.ai_enabled:
            self._init_ai()
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = False
        
        print("🎯 VTX AI 电话系统")
        print(f"服务器: {settings.vtx.server}:{settings.vtx.port}")
        print(f"域名: {settings.vtx.domain}")
        print(f"DID: {settings.vtx.did_number}")
        print(f"分机: {ext.username}")
        print(f"AI: {'启用' if self.ai_enabled else '禁用'}")
        print("-" * 50)
    
    def _init_ai(self):
        """初始化 AI 组件"""
        # STT 配置
        stt_config = STTConfig(
            provider=STTProvider.WHISPER_LOCAL,  # 使用本地 Whisper
            local_model_size="base",
            language="zh",
            chunk_duration=2.0
        )
        
        # TTS 配置
        tts_config = TTSConfig(
            provider=TTSProvider.EDGE_TTS,
            voice="zh-CN-XiaoxiaoNeural",  # 晓晓的声音
            speed=1.0
        )
        
        # LLM 配置
        llm_config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
            system_prompt=SYSTEM_PROMPTS["客服"],
            temperature=0.7,
            max_tokens=150
        )
        
        # 对话配置
        conversation_config = ConversationConfig(
            stt_config=stt_config,
            tts_config=tts_config,
            llm_config=llm_config,
            silence_timeout=2.0,
            enable_beep=True
        )
        
        # 创建对话管理器
        self.conversation_manager = ConversationManager(conversation_config)
        
        # 设置回调
        self.conversation_manager.set_audio_output_callback(self._on_ai_audio_output)
        self.conversation_manager.set_callbacks(
            transcription=self._on_transcription,
            response=self._on_ai_response
        )
    
    def _signal_handler(self, signum, frame):
        """信号处理"""
        print(f"\n收到信号 {signum}，准备退出...")
        self.running = False
    
    def start(self):
        """启动系统"""
        # 设置来电处理
        self.sip_client.set_incoming_call_handler(self._handle_incoming_call)
        
        # 启动 SIP 客户端
        if not self.sip_client.start():
            print("❌ 系统启动失败")
            return False
        
        # 启动 AI（如果启用）
        if self.ai_enabled and self.conversation_manager:
            self.conversation_manager.start()
        
        print("\n✅ 系统启动成功")
        print(f"📞 等待来电: {settings.vtx.did_number}")
        print("按 Ctrl+C 退出...\n")
        
        self.running = True
        
        # 主循环
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        
        # 停止系统
        self.stop()
        
        return True
    
    def stop(self):
        """停止系统"""
        print("\n🛑 停止系统...")
        
        # 停止 AI
        if self.conversation_manager:
            self.conversation_manager.stop()
        
        # 停止 SIP
        self.sip_client.stop()
        
        print("✅ 系统已停止")
    
    def _handle_incoming_call(self, call, request):
        """处理来电"""
        print(f"\n📞 来电: {call.call_id}")
        
        # 提取来电信息
        from_header = request.get_header('From')
        if from_header:
            import re
            match = re.search(r'sip:([^@]+)@', from_header)
            if match:
                caller = match.group(1)
                print(f"   来电号码: {caller}")
        
        # 解析 SDP
        body = request.body
        if body:
            sdp = SDPParser.parse(body)
            rtp_info = SDPParser.extract_rtp_info(sdp)
            
            if rtp_info:
                remote_ip, remote_port, codecs = rtp_info
                print(f"   远程 RTP: {remote_ip}:{remote_port}")
                print(f"   编解码器: {', '.join(codecs)}")
                
                # 分配本地 RTP 端口
                local_rtp_port = self.sip_client._get_next_rtp_port()
                
                # 创建 RTP 处理器
                rtp_handler = RTPHandler(
                    self.sip_client.local_ip,
                    local_rtp_port
                )
                call.rtp_handler = rtp_handler
                self.current_rtp_handler = rtp_handler
                
                # 设置 RTP 音频接收回调
                if self.ai_enabled:
                    rtp_handler.set_audio_callback(self._on_rtp_audio_received)
                
                # 构建响应 SDP
                response_sdp = SDPParser.build(
                    self.sip_client.local_ip,
                    local_rtp_port,
                    codecs=codecs
                )
                
                # 接听电话
                time.sleep(2)  # 模拟振铃
                self.sip_client._send_response(
                    request, 200, "OK",
                    to_tag=call.local_tag,
                    body=response_sdp
                )
                
                # 启动 RTP
                rtp_handler.start(remote_ip, remote_port)
                
                if self.ai_enabled:
                    # AI 模式：播放欢迎语
                    self._play_welcome_message()
                else:
                    # 测试模式：发送测试音频
                    self._send_test_audio(rtp_handler)
            else:
                print("⚠️ 无法解析 RTP 信息")
                # 发送忙音
                time.sleep(2)
                self.sip_client._send_response(
                    request, 486, "Busy Here",
                    to_tag=call.local_tag
                )
        else:
            print("⚠️ 没有 SDP")
            # 发送忙音
            time.sleep(2)
            self.sip_client._send_response(
                request, 486, "Busy Here",
                to_tag=call.local_tag
            )
    
    def _play_welcome_message(self):
        """播放欢迎语"""
        welcome_text = "您好，我是AI助手小晓，很高兴为您服务。请问有什么可以帮助您的吗？"
        
        # 合成欢迎语
        if self.conversation_manager:
            self.conversation_manager.tts_engine.synthesize(welcome_text, priority=True)
    
    def _on_rtp_audio_received(self, audio_data: bytes):
        """RTP 音频接收回调"""
        # 将音频传递给 AI
        if self.conversation_manager:
            self.conversation_manager.add_audio_input(audio_data, format="ulaw")
    
    def _on_ai_audio_output(self, audio_data: bytes):
        """AI 音频输出回调"""
        # 通过 RTP 发送音频
        if self.current_rtp_handler:
            self.current_rtp_handler.send_audio(audio_data, payload_type=0)
    
    def _on_transcription(self, text: str):
        """语音识别结果回调"""
        print(f"👤 用户说: {text}")
    
    def _on_ai_response(self, text: str):
        """AI 回复回调"""
        print(f"🤖 AI 回复: {text}")
    
    def _send_test_audio(self, rtp_handler):
        """发送测试音频（非 AI 模式）"""
        print("🎵 发送测试音频: 1871")
        
        # 生成测试音频
        test_audio = AudioGenerator.generate_test_pattern_1871()
        print(f"   音频长度: {len(test_audio)} 字节")
        print(f"   持续时间: {len(test_audio) / 8000:.1f} 秒")
        
        # 分包发送
        packet_size = 160  # 20ms @ 8kHz
        packets_sent = 0
        
        for i in range(0, len(test_audio), packet_size):
            packet = test_audio[i:i+packet_size]
            
            # 确保包大小正确
            if len(packet) < packet_size:
                packet += b'\xFF' * (packet_size - len(packet))
            
            rtp_handler.send_audio(packet, payload_type=0)
            packets_sent += 1
            
            # 进度提示
            if packets_sent % 50 == 0:
                print(f"   已发送: {packets_sent * 0.02:.1f} 秒")
            
            time.sleep(0.02)  # 20ms
        
        print(f"✅ 音频发送完成: {packets_sent} 个包")


def main():
    """主函数"""
    print("=" * 60)
    print("VTX AI Phone System v2.0")
    print("=" * 60)
    
    # 检查 AI 依赖
    ai_available = True
    try:
        import whisper
        print("✅ Whisper 已安装")
    except ImportError:
        print("⚠️ Whisper 未安装，AI 功能将受限")
        ai_available = False
    
    try:
        import edge_tts
        print("✅ Edge-TTS 已安装")
    except ImportError:
        print("⚠️ Edge-TTS 未安装，语音合成将不可用")
        ai_available = False
    
    try:
        import openai
        print("✅ OpenAI 已安装")
        if not os.getenv("OPENAI_API_KEY"):
            print("⚠️ 未设置 OPENAI_API_KEY 环境变量")
            ai_available = False
    except ImportError:
        print("⚠️ OpenAI 未安装，无法使用 LLM")
        ai_available = False
    
    print("-" * 60)
    
    try:
        system = VTXAIPhoneSystem()
        
        # 如果 AI 依赖不完整，禁用 AI
        if not ai_available:
            print("⚠️ AI 依赖不完整，将以测试模式运行")
            system.ai_enabled = False
        
        system.start()
    except Exception as e:
        print(f"❌ 系统错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())