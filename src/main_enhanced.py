#!/usr/bin/env python3
"""
VTX AI Phone System v2.0 - 增强版主程序
Aiker - OneSuite 商业客服机器人
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
from src.audio.welcome_messages import welcome_messages
from src.utils.api_manager import api_manager
from src.ai.enhanced.streaming_stt import StreamingSTTEngine
from src.ai.providers.deepgram_provider import DeepgramSTTProvider
from src.ai.providers.elevenlabs_provider import ElevenLabsTTSProvider
from src.utils.audio_utils import AudioUtils
from src.utils.performance_monitor import PerformanceMonitor


class AikerPhoneSystem:
    """Aiker - OneSuite 商业客服机器人电话系统"""
    
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
        
        # AI 组件
        self.stt_engine = None
        self.tts_provider = None
        self.performance_monitor = PerformanceMonitor()
        self.current_rtp_handler = None
        self.current_call = None
        
        # 初始化 AI 组件
        self._init_ai_components()
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = False
        
        print("🎯 Aiker - OneSuite 商业客服机器人")
        print(f"服务器: {settings.vtx.server}:{settings.vtx.port}")
        print(f"域名: {settings.vtx.domain}")
        print(f"DID: {settings.vtx.did_number}")
        print(f"分机: {ext.username}")
        print(f"AI: 增强版（Deepgram + ElevenLabs）")
        print("-" * 50)
    
    def _init_ai_components(self):
        """初始化 AI 组件"""
        print("🤖 初始化增强AI组件...")
        
        # 检查API密钥
        available_services = api_manager.get_available_services()
        print(f"✅ 可用服务: {', '.join(available_services)}")
        
        # 初始化STT引擎
        if 'deepgram' in available_services:
            self.stt_engine = StreamingSTTEngine()
            print("✅ 流式STT引擎初始化完成")
        else:
            print("❌ Deepgram API密钥不可用")
            raise ValueError("Deepgram API密钥不可用")
        
        # 初始化TTS提供商
        if 'elevenlabs' in available_services:
            self.tts_provider = ElevenLabsTTSProvider()
            print("✅ ElevenLabs TTS初始化完成")
        else:
            print("❌ ElevenLabs API密钥不可用")
            raise ValueError("ElevenLabs API密钥不可用")
        
        print("✅ 增强AI组件初始化完成")
    
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
        
        print("\n✅ 系统启动成功")
        print(f"📞 等待来电: {settings.vtx.did_number}")
        print("🤖 AI模式: 增强版（Deepgram + ElevenLabs）")
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
        
        # 停止STT引擎
        if self.stt_engine:
            asyncio.run(self.stt_engine.stop())
        
        # 停止 SIP
        self.sip_client.stop()
        
        print("✅ 系统已停止")
    
    def _handle_incoming_call(self, call, request):
        """处理来电"""
        print(f"\n📞 来电: {call.call_id}")
        self.current_call = call
        
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
                
                # 播放本地欢迎语（快速响应）
                self._play_local_welcome()
                
                # 启动STT引擎
                asyncio.create_task(self._start_stt_processing())
                
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
    
    async def _start_stt_processing(self):
        """启动STT处理"""
        try:
            if self.stt_engine:
                await self.stt_engine.start()
                print("✅ STT引擎启动成功")
                
                # 设置回调
                self.stt_engine.set_transcript_callback(self._on_transcription)
            
        except Exception as e:
            print(f"❌ STT引擎启动失败: {e}")
    
    def _play_local_welcome(self):
        """播放本地欢迎语（快速响应）"""
        print("🔊 播放本地欢迎语...")
        
        # 获取本地欢迎语音频
        welcome_audio = welcome_messages.get_welcome_audio_ulaw()
        
        if welcome_audio:
            # 直接发送音频包
            self._send_audio_packets(welcome_audio)
            print("✅ 本地欢迎语播放完成")
        else:
            print("❌ 本地欢迎语音频不可用，使用TTS合成")
            # 回退到TTS合成
            self._play_welcome_message()
    
    def _play_welcome_message(self):
        """播放TTS欢迎语（备用方案）"""
        welcome_text = "您好，我是Aiker，OneSuite的商业客服助手。很高兴为您服务，请问有什么可以帮助您的吗？"
        
        print(f"🔊 播放TTS欢迎语: {welcome_text}")
        
        # 异步合成和播放
        asyncio.create_task(self._synthesize_and_play(welcome_text))
    
    async def _synthesize_and_play(self, text: str):
        """合成并播放音频"""
        try:
            if self.tts_provider:
                # 合成音频
                audio_data = await self.tts_provider.synthesize(text)
                
                if audio_data:
                    # 转换为μ-law格式
                    ulaw_audio = AudioUtils.ulaw_encode(audio_data)
                    
                    # 通过RTP发送
                    if self.current_rtp_handler:
                        self._send_audio_packets(ulaw_audio)
                        print(f"✅ 音频播放完成: {len(audio_data)} 字节")
                    else:
                        print("❌ RTP处理器不可用")
                else:
                    print("❌ 音频合成失败")
            else:
                print("❌ TTS提供商不可用")
                
        except Exception as e:
            print(f"❌ 音频处理失败: {e}")
    
    def _send_audio_packets(self, audio_data: bytes):
        """发送音频包"""
        if not self.current_rtp_handler:
            return
        
        # 分包发送
        packet_size = 160  # 20ms @ 8kHz
        packets_sent = 0
        
        for i in range(0, len(audio_data), packet_size):
            packet = audio_data[i:i+packet_size]
            
            # 确保包大小正确
            if len(packet) < packet_size:
                packet += b'\xFF' * (packet_size - len(packet))
            
            self.current_rtp_handler.send_audio(packet, payload_type=0)
            packets_sent += 1
            
            time.sleep(0.02)  # 20ms
        
        print(f"📦 音频包发送完成: {packets_sent} 个包")
    
    def _on_rtp_audio_received(self, audio_data: bytes):
        """RTP 音频接收回调"""
        # 将音频传递给STT引擎
        if self.stt_engine:
            self.stt_engine.add_audio(audio_data)
    
    def _on_transcription(self, text: str, is_final: bool = False):
        """语音识别结果回调"""
        if is_final:
            print(f"👤 用户说（最终）: {text}")
            # 生成AI回复
            asyncio.create_task(self._generate_ai_response(text))
        else:
            print(f"👤 用户说（中间）: {text}")
    
    async def _generate_ai_response(self, user_text: str):
        """生成AI回复"""
        try:
            # 构建OneSuite相关的回复
            response_text = self._generate_onesuite_response(user_text)
            
            print(f"🤖 AI 回复: {response_text}")
            
            # 合成并播放回复
            await self._synthesize_and_play(response_text)
            
        except Exception as e:
            print(f"❌ AI回复生成失败: {e}")
    
    def _generate_onesuite_response(self, user_text: str) -> str:
        """生成OneSuite相关的回复"""
        # 简单的关键词匹配回复
        user_text_lower = user_text.lower()
        
        if any(word in user_text_lower for word in ['价格', '费用', '收费', '多少钱']):
            return "OneSuite提供最实惠的商业电话服务，基础套餐每月仅需4.95美元，包含本地号码、自动接待员等功能。您想了解具体套餐详情吗？"
        
        elif any(word in user_text_lower for word in ['功能', '特性', '服务']):
            return "OneSuite提供完整的商业电话解决方案，包括本地号码、免费号码、自动接待员、短信服务、语音邮件转邮件、网络传真等功能。"
        
        elif any(word in user_text_lower for word in ['注册', '开户', '申请']):
            return "您可以通过我们的官网onesuitebusiness.com注册账户，或者下载我们的移动应用。注册过程简单快捷，无需硬件设备。"
        
        elif any(word in user_text_lower for word in ['支持', '帮助', '客服']):
            return "我是Aiker，OneSuite的AI客服助手。如果您需要人工客服，可以访问我们的帮助中心或发送邮件联系我们。"
        
        else:
            return f"我听到您说：{user_text}。我是Aiker，OneSuite的商业客服助手。OneSuite是最实惠的商业电话服务提供商，提供完整的通信解决方案。请问您想了解我们的哪些服务？"


def main():
    """主函数"""
    print("=" * 60)
    print("Aiker - OneSuite 商业客服机器人 v2.0")
    print("=" * 60)
    
    # 检查依赖
    try:
        import asyncio
        import aiohttp
        print("✅ 核心依赖正常")
    except ImportError as e:
        print(f"❌ 依赖缺失: {e}")
        return 1
    
    # 检查API密钥
    try:
        available = api_manager.get_available_services()
        missing = api_manager.get_missing_services()
        
        print(f"✅ 可用服务: {', '.join(available)}")
        if missing:
            print(f"❌ 缺失服务: {', '.join(missing)}")
            return 1
    except Exception as e:
        print(f"❌ API密钥检查失败: {e}")
        return 1
    
    print("-" * 60)
    
    try:
        system = AikerPhoneSystem()
        system.start()
    except Exception as e:
        print(f"❌ 系统错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 