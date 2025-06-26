#!/usr/bin/env python3
"""
VTX AI Phone System - 主程序集成 (增强版)
集成新的AI提供商和流式引擎
"""

import sys
import os
import time
import signal
import threading
import asyncio
from typing import Optional

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from src.sip import SIPClient
from src.sdp import SDPParser
from src.rtp import RTPHandler
from src.audio import AudioGenerator

# 新增的AI组件导入
from src.ai.providers.deepgram_provider import DeepgramSTTProvider, DeepgramConfig
from src.ai.providers.elevenlabs_provider import ElevenLabsTTSProvider, ElevenLabsConfig
from src.ai.enhanced.streaming_stt import StreamingSTTEngine, StreamingSTTConfig, STTProvider
from src.utils.api_manager import api_manager
from src.utils.performance_monitor import performance_monitor


class EnhancedVTXAIPhoneSystem:
    """增强版 VTX AI 电话系统"""
    
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
        
        # AI 组件配置
        self.ai_enabled = True
        self.current_rtp_handler = None
        
        # 初始化AI组件
        if self.ai_enabled:
            self._init_enhanced_ai()
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = False
        
        print("🎯 增强版 VTX AI 电话系统")
        print(f"服务器: {settings.vtx.server}:{settings.vtx.port}")
        print(f"域名: {settings.vtx.domain}")
        print(f"DID: {settings.vtx.did_number}")
        print(f"分机: {ext.username}")
        print(f"AI: {'增强模式' if self.ai_enabled else '禁用'}")
        print("-" * 50)
    
    def _init_enhanced_ai(self):
        """初始化增强AI组件"""
        print("🤖 初始化增强AI组件...")
        
        try:
            # 1. 检查API密钥
            missing_services = api_manager.get_missing_services()
            if missing_services:
                print(f"⚠️ 缺少API密钥: {', '.join(missing_services)}")
                print("   部分AI功能可能无法使用")
            
            # 2. 初始化Deepgram STT
            if api_manager.has_key('deepgram'):
                deepgram_config = DeepgramConfig(
                    model="nova-2",
                    language="zh-CN",
                    interim_results=True,
                    endpointing=300
                )
                self.deepgram_provider = DeepgramSTTProvider(deepgram_config)
                print("✅ Deepgram STT 提供商已初始化")
            else:
                self.deepgram_provider = None
                print("⚠️ Deepgram STT 不可用（缺少API密钥）")
            
            # 3. 初始化ElevenLabs TTS
            if api_manager.has_key('elevenlabs'):
                elevenlabs_config = ElevenLabsConfig(
                    voice_name="Rachel",
                    model_id="eleven_multilingual_v2",
                    stability=0.5,
                    similarity_boost=0.8
                )
                self.elevenlabs_provider = ElevenLabsTTSProvider(elevenlabs_config)
                print("✅ ElevenLabs TTS 提供商已初始化")
            else:
                self.elevenlabs_provider = None
                print("⚠️ ElevenLabs TTS 不可用（缺少API密钥）")
            
            # 4. 初始化流式STT引擎
            streaming_config = StreamingSTTConfig(
                primary_provider=STTProvider.DEEPGRAM if self.deepgram_provider else STTProvider.WHISPER_LOCAL,
                fallback_provider=STTProvider.WHISPER_LOCAL,
                auto_fallback=True,
                target_latency=0.8
            )
            self.streaming_stt_engine = StreamingSTTEngine(streaming_config)
            
            # 设置回调
            self.streaming_stt_engine.set_transcript_callback(self._on_transcript)
            self.streaming_stt_engine.set_error_callback(self._on_ai_error)
            
            if self.elevenlabs_provider:
                self.elevenlabs_provider.set_audio_callback(self._on_tts_audio_ready)
                self.elevenlabs_provider.set_error_callback(self._on_ai_error)
            
            print("✅ 增强AI组件初始化完成")
            
        except Exception as e:
            print(f"❌ AI组件初始化失败: {e}")
            self.ai_enabled = False
    
    def _signal_handler(self, signum, frame):
        """信号处理"""
        print(f"\n收到信号 {signum}，准备退出...")
        self.running = False
    
    async def start(self):
        """启动系统"""
        # 设置来电处理
        self.sip_client.set_incoming_call_handler(self._handle_incoming_call)
        
        # 启动 SIP 客户端
        if not self.sip_client.start():
            print("❌ 系统启动失败")
            return False
        
        # 启动增强AI组件
        if self.ai_enabled and self.streaming_stt_engine:
            await self.streaming_stt_engine.start()
        
        print("\n✅ 增强系统启动成功")
        print(f"📞 等待来电: {settings.vtx.did_number}")
        print("🤖 AI模式: 增强版（Deepgram + ElevenLabs）")
        print("按 Ctrl+C 退出...\n")
        
        self.running = True
        
        # 主循环
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        
        # 停止系统
        await self.stop()
        
        return True
    
    async def stop(self):
        """停止系统"""
        print("\n🛑 停止增强系统...")
        
        # 停止AI组件
        if self.streaming_stt_engine:
            await self.streaming_stt_engine.stop()
        
        # 停止 SIP
        self.sip_client.stop()
        
        # 打印性能报告
        performance_monitor.print_performance_report()
        
        print("✅ 增强系统已停止")
    
    def _handle_incoming_call(self, call, request):
        """处理来电"""
        print(f"\n📞 来电: {call.call_id}")
        
        # 记录开始时间（性能监控）
        call_start_time = time.time()
        
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
                
                # 记录响应时间
                response_time = time.time() - call_start_time
                performance_monitor.record_response_time(response_time)
                
                if self.ai_enabled:
                    # AI 模式：播放增强欢迎语
                    asyncio.create_task(self._play_enhanced_welcome())
                else:
                    # 测试模式：发送测试音频
                    self._send_test_audio(rtp_handler)
            else:
                print("⚠️ 无法解析 RTP 信息")
                self._send_busy_response(request, call)
        else:
            print("⚠️ 没有 SDP")
            self._send_busy_response(request, call)
    
    def _send_busy_response(self, request, call):
        """发送忙音响应"""
        time.sleep(2)
        self.sip_client._send_response(
            request, 486, "Busy Here",
            to_tag=call.local_tag
        )
    
    async def _play_enhanced_welcome(self):
        """播放增强欢迎语"""
        welcome_text = "您好，我是增强版AI助手，搭载了最新的语音识别和合成技术。请问有什么可以帮助您的？"
        
        # 使用ElevenLabs合成（如果可用）
        if self.elevenlabs_provider:
            print(f"🔊 使用ElevenLabs合成欢迎语...")
            try:
                async with self.elevenlabs_provider as provider:
                    await provider.synthesize(welcome_text)
            except Exception as e:
                print(f"❌ ElevenLabs合成失败: {e}")
                # 回退到传统欢迎方式
                self._send_test_audio(self.current_rtp_handler)
        else:
            print("🔊 使用传统音频欢迎...")
            self._send_test_audio(self.current_rtp_handler)
    
    def _on_rtp_audio_received(self, audio_data: bytes):
        """RTP 音频接收回调"""
        # 将音频传递给增强STT引擎
        if self.streaming_stt_engine and self.ai_enabled:
            self.streaming_stt_engine.add_audio(audio_data)
    
    def _on_transcript(self, text: str, is_final: bool):
        """语音识别结果回调"""
        if is_final:
            print(f"👤 用户说（最终）: {text}")
            # TODO: 传递给LLM处理
            asyncio.create_task(self._process_user_input(text))
        else:
            print(f"👤 用户说（中间）: {text}")
    
    async def _process_user_input(self, text: str):
        """处理用户输入"""
        # 简单的AI回复逻辑（待实现完整LLM集成）
        ai_response = f"我听到您说：{text}。这是一个测试回复。"
        
        print(f"🤖 AI 回复: {ai_response}")
        
        # 使用ElevenLabs合成回复
        if self.elevenlabs_provider:
            try:
                async with self.elevenlabs_provider as provider:
                    await provider.synthesize(ai_response)
            except Exception as e:
                print(f"❌ 合成回复失败: {e}")
    
    def _on_tts_audio_ready(self, audio_data: bytes, text: str):
        """TTS音频就绪回调"""
        print(f"🔊 音频合成完成: {len(audio_data)} 字节")
        
        # 通过 RTP 发送音频（需要格式转换）
        if self.current_rtp_handler:
            # TODO: 将MP3转换为μ-law格式
            # 暂时使用原始数据（需要改进）
            try:
                # 简单分包发送
                packet_size = 160
                for i in range(0, len(audio_data), packet_size):
                    packet = audio_data[i:i+packet_size]
                    if len(packet) < packet_size:
                        packet += b'\xFF' * (packet_size - len(packet))
                    
                    self.current_rtp_handler.send_audio(packet, payload_type=0)
                    time.sleep(0.02)  # 20ms间隔
                    
            except Exception as e:
                print(f"❌ 音频发送失败: {e}")
    
    def _on_ai_error(self, error: str):
        """AI错误回调"""
        print(f"❌ AI错误: {error}")
        performance_monitor.record_error()
    
    def _send_test_audio(self, rtp_handler):
        """发送测试音频（传统模式）"""
        print("🎵 发送测试音频: 1871")
        
        # 生成测试音频
        test_audio = AudioGenerator.generate_test_pattern_1871()
        print(f"   音频长度: {len(test_audio)} 字节")
        
        # 分包发送
        packet_size = 160  # 20ms @ 8kHz
        for i in range(0, len(test_audio), packet_size):
            packet = test_audio[i:i+packet_size]
            if len(packet) < packet_size:
                packet += b'\xFF' * (packet_size - len(packet))
            
            rtp_handler.send_audio(packet, payload_type=0)
            time.sleep(0.02)  # 20ms
        
        print(f"✅ 测试音频发送完成")


async def main():
    """主函数"""
    print("=" * 60)
    print("VTX AI Phone System v2.0 (Enhanced)")
    print("=" * 60)
    
    # 检查API密钥状态
    print("🔑 API密钥状态检查...")
    available_services = api_manager.get_available_services()
    missing_services = api_manager.get_missing_services()
    
    print(f"✅ 可用服务: {', '.join(available_services) if available_services else '无'}")
    if missing_services:
        print(f"⚠️ 缺失服务: {', '.join(missing_services)}")
    
    print("-" * 60)
    
    try:
        system = EnhancedVTXAIPhoneSystem()
        await system.start()
    except Exception as e:
        print(f"❌ 系统错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    asyncio.run(main()) 