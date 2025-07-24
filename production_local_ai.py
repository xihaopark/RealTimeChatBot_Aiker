#!/usr/bin/env python3
"""
生产就绪的本地AI电话系统
专注于实际IP电话接听和处理
"""

import asyncio
import logging
import os
import sys
import signal
import threading
import time
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from sip_client import EnhancedSIPClient
from rtp_handler import RTPHandler
# 直接导入HTTPTTSService，避免通过__init__.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'local_ai'))
from http_tts import HTTPTTSService

# 配置日志（提前配置）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/production_ai_system.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 条件导入其他AI服务
try:
    from local_ai import LocalLLM, LocalSTT, AudioConverter
    AI_SERVICES_AVAILABLE = True
    logger.info("Full AI services available")
except ImportError as e:
    logger.warning(f"Some AI services not available: {e}")
    AI_SERVICES_AVAILABLE = False
    # 创建简化的AudioConverter
    import audioop
    class AudioConverter:
        @staticmethod
        def convert_pcm16k_to_rtp(pcm_data):
            if hasattr(pcm_data, 'tobytes'):
                pcm_bytes = pcm_data.tobytes()
            else:
                pcm_bytes = pcm_data
            return audioop.lin2ulaw(pcm_bytes, 2)
    logger.info("Using simplified AI services with HTTP TTS")


class ProductionAIPhoneSystem:
    """生产就绪的AI电话系统"""
    
    def __init__(self):
        self.config = settings
        self.is_running = False
        
        # SIP和RTP组件
        self.sip_client = None
        self.active_calls: Dict[str, Dict[str, Any]] = {}
        
        # 本地AI组件
        self.llm_service = None
        self.tts_service = None
        self.stt_service = None
        
        # 初始化AI服务
        self._init_ai_services()
        
        logger.info("Production AI Phone System initialized")
    
    def _init_ai_services(self):
        """初始化本地AI服务"""
        try:
            # 初始化HTTP TTS (完全绕过音频设备) - 优先初始化
            logger.info("Initializing HTTP TTS Service...")
            self.tts_service = HTTPTTSService(
                server_url="http://localhost:50000",  # CosyVoice服务地址
                service_type="cosyvoice",
                fallback_enabled=True,
                timeout=10
            )
            logger.info("HTTP TTS Service ready")
            
            # 条件初始化其他AI服务
            if AI_SERVICES_AVAILABLE:
                # 初始化LLM
                logger.info("Initializing Local LLM...")
                self.llm_service = LocalLLM(
                    model_name="Qwen/Qwen2.5-7B-Instruct",
                    device="cuda",
                    max_length=1024,
                    temperature=0.7,
                    use_4bit=True
                )
                logger.info("Local LLM ready")
                
                # 初始化STT
                logger.info("Initializing Local STT...")
                self.stt_service = LocalSTT(
                    model="tiny",
                    language="zh",
                    device="cuda",  # 恢复CUDA支持
                    mic=False
                )
                logger.info("Local STT ready")
            else:
                logger.warning("AI services not available, using minimal mode")
                # 创建简化的AI服务
                self.llm_service = self._create_mock_llm()
                self.stt_service = self._create_mock_stt()
            
            logger.info("All AI services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI services: {e}")
            raise
    
    def _create_mock_llm(self):
        """创建简化的LLM服务"""
        class MockLLM:
            def generate_response(self, text):
                return f"收到您的消息：{text}。抱歉，完整的AI服务暂时不可用，请稍后再试。"
        return MockLLM()
    
    def _create_mock_stt(self):
        """创建简化的STT服务"""
        class MockSTT:
            def __init__(self):
                self.recorder = None
                self.transcription_callback = None
            
            def set_transcription_callback(self, callback):
                self.transcription_callback = callback
            
            def start_listening(self):
                pass
                
            def stop_listening(self):
                pass
                
            def feed_audio(self, audio_data):
                # 智能音频活动检测
                if not hasattr(self, '_feed_count'):
                    self._feed_count = 0
                    self._silence_count = 0
                    self._speech_detected = False
                
                self._feed_count += 1
                
                # 简单的能量检测
                if len(audio_data) > 0:
                    energy = sum(abs(b - 127) for b in audio_data) / len(audio_data)
                    
                    if energy > 15:  # 有语音活动
                        if not self._speech_detected:
                            self._speech_detected = True
                            self._silence_count = 0
                    else:  # 静音
                        self._silence_count += 1
                        
                        # 检测到语音结束
                        if self._speech_detected and self._silence_count > 20:  # 约1秒静音
                            if self.transcription_callback:
                                # 模拟识别结果
                                mock_responses = [
                                    "你好",
                                    "我想咨询一下服务",
                                    "请问你们的价格是多少",
                                    "谢谢",
                                    "我需要帮助"
                                ]
                                import random
                                response = random.choice(mock_responses)
                                self.transcription_callback(response)
                            
                            self._speech_detected = False
                            self._silence_count = 0
        
        return MockSTT()
    
    def start(self):
        """启动系统"""
        try:
            logger.info("Starting Production AI Phone System...")
            
            # 获取第一个可用的分机配置
            extension_id = list(self.config.extensions.keys())[0]
            extension = self.config.extensions[extension_id]
            
            logger.info(f"Using extension: {extension.username}@{self.config.vtx.domain}")
            
            # 初始化SIP客户端
            self.sip_client = EnhancedSIPClient(
                username=extension.username,
                password=extension.password,
                domain=self.config.vtx.domain,
                server=self.config.vtx.server,
                port=self.config.vtx.port
            )
            
            # 设置呼叫处理回调
            self.sip_client.set_call_handler(self._handle_incoming_call)
            
            # 启动SIP客户端
            if self.sip_client.start():
                self.is_running = True
                logger.info("AI Phone System started successfully")
                logger.info(f"Ready to receive calls on: {self.config.vtx.did_number}")
                
                # 主循环
                self._main_loop()
            else:
                logger.error("Failed to start SIP client")
                
        except Exception as e:
            logger.error(f"Failed to start system: {e}")
            self.stop()
    
    def _handle_incoming_call(self, call_info: Dict[str, Any]):
        """处理来电"""
        call_id = call_info.get('call_id')
        caller = call_info.get('caller', 'Unknown')
        remote_ip = call_info.get('remote_ip')
        remote_port = call_info.get('remote_port')
        local_rtp_port = call_info.get('local_rtp_port')
        
        logger.info(f"Incoming call: {call_id} from {caller} ({remote_ip}:{remote_port})")
        
        try:
            # 创建RTP处理器
            rtp_handler = RTPHandler("0.0.0.0", local_rtp_port)
            
            # 设置音频接收回调
            rtp_handler.set_audio_callback(self._on_rtp_audio)
            
            # 启动RTP处理
            if rtp_handler.start(remote_ip, remote_port):
                # 保存通话信息
                self.active_calls[call_id] = {
                    'rtp_handler': rtp_handler,
                    'caller': caller,
                    'remote_ip': remote_ip,
                    'remote_port': remote_port,
                    'start_time': time.time(),
                    'last_audio_time': time.time()
                }
                
                # 启动STT监听
                self._start_stt_for_call(call_id)
                
                # 发送欢迎消息
                self._send_welcome_message(call_id)
                
                logger.info(f"Call {call_id} established successfully")
            else:
                logger.error(f"Failed to start RTP for call {call_id}")
                
        except Exception as e:
            logger.error(f"Failed to handle incoming call {call_id}: {e}")
    
    def _start_stt_for_call(self, call_id: str):
        """为通话启动STT监听"""
        try:
            if not self.stt_service:
                logger.warning("STT service not available")
                return
            
            # 设置STT转录回调
            def on_transcription(text: str):
                print(f"🎤 [{call_id}] 用户说话: {text}")  # 立即显示用户说话内容
                logger.info(f"Call {call_id} STT detected: {text}")
                
                # 在后台线程处理LLM和TTS响应
                threading.Thread(
                    target=self._handle_user_speech,
                    args=(call_id, text),
                    daemon=True
                ).start()
            
            self.stt_service.set_transcription_callback(on_transcription)
            self.stt_service.start_listening()
            
            print(f"🎧 STT监听已启动 - 通话 {call_id}")
            logger.info(f"STT listening started for call {call_id}")
            
        except Exception as e:
            logger.error(f"Failed to start STT for call {call_id}: {e}")
    
    def _handle_user_speech(self, call_id: str, user_text: str):
        """处理用户语音输入（STT->LLM->TTS）"""
        try:
            logger.info(f"处理用户语音 [{call_id}]: {user_text}")
            
            # Step 1: LLM生成回复
            logger.info("开始LLM对话生成...")
            start_time = time.time()
            
            try:
                ai_response = self.llm_service.generate_response(user_text)
                llm_time = time.time() - start_time
                logger.info(f"LLM回复生成 ({llm_time:.2f}s): {ai_response}")
                
            except Exception as e:
                logger.error(f"LLM生成失败: {e}")
                ai_response = "抱歉，我遇到了技术问题，请稍后再试。"
            
            # Step 2: TTS合成语音
            logger.info("开始TTS语音合成...")
            start_time = time.time()
            
            try:
                tts_audio = self.tts_service.synthesize_text(ai_response)
                tts_time = time.time() - start_time
                
                if tts_audio and len(tts_audio) > 0:
                    logger.info(f"TTS合成成功 ({tts_time:.2f}s): {len(tts_audio)} bytes")
                    
                    # Step 3: 发送音频回复
                    if call_id in self.active_calls:
                        self._send_audio_to_call(call_id, tts_audio)
                        logger.info("AI音频回复已发送")
                else:
                    logger.warning(f"TTS合成失败 ({tts_time:.2f}s)")
                    
            except Exception as e:
                logger.error(f"TTS合成失败: {e}")
                
        except Exception as e:
            logger.error(f"处理用户语音失败 [{call_id}]: {e}")
    
    def _on_rtp_audio(self, audio_data: bytes):
        """RTP音频接收回调"""
        try:
            # 找到对应的通话
            for call_id, call_info in self.active_calls.items():
                # 更新最后音频时间
                call_info['last_audio_time'] = time.time()
                
                # 直接将音频数据喂给STT服务，不打印无意义的日志
                if len(audio_data) > 0:
                    if self.stt_service and hasattr(self.stt_service, 'feed_audio'):
                        self.stt_service.feed_audio(audio_data)
                    else:
                        # 只在STT不可用时打印一次警告
                        if not hasattr(self, '_stt_warning_printed'):
                            print(f"⚠️ STT服务不可用")
                            self._stt_warning_printed = True
                        
        except Exception as e:
            logger.error(f"Error processing RTP audio: {e}")
    
    
    
    def _send_audio_to_call(self, call_id: str, audio_data: bytes):
        """将音频数据发送到通话"""
        try:
            call_info = self.active_calls.get(call_id)
            if not call_info or not call_info.get('rtp_handler'):
                return
            
            rtp_handler = call_info['rtp_handler']
            
            # 音频数据已经是μ-law格式，分成160字节的包发送
            chunk_size = 160  # 20ms @ 8kHz
            
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                if len(chunk) < chunk_size:
                    # 填充最后一个包
                    chunk += b'\x7f' * (chunk_size - len(chunk))
                
                rtp_handler.send_audio(chunk)
                
                # 控制发送速率 (20ms间隔)
                time.sleep(0.02)
                
            logger.info(f"Audio sent to call {call_id}")
                
        except Exception as e:
            logger.error(f"Error sending audio to call {call_id}: {e}")
    
    def _send_welcome_message(self, call_id: str):
        """发送欢迎消息"""
        try:
            welcome_msg = "您好，欢迎致电OneSuite Business！我是您的AI助手，请问有什么可以帮助您的吗？"
            
            # 延迟发送，确保RTP连接稳定
            def delayed_welcome():
                time.sleep(2)
                logger.info(f"Sending welcome message to call {call_id}")
                
                try:
                    # 使用TTS合成欢迎消息
                    print(f"🔊 开始TTS合成欢迎消息: {welcome_msg}")
                    logger.info(f"TTS合成欢迎消息: {welcome_msg}")
                    
                    audio_data = self.tts_service.synthesize_text(welcome_msg)
                    
                    if audio_data and len(audio_data) > 0:
                        print(f"✅ TTS生成音频成功: {len(audio_data)} bytes")
                        logger.info(f"TTS生成音频: {len(audio_data)} bytes")
                        self._send_audio_to_call(call_id, audio_data)
                        print(f"📤 欢迎音频已发送到通话 {call_id}")
                    else:
                        print(f"❌ TTS生成失败，音频数据为空")
                        logger.warning("TTS生成失败，使用预录制音频")
                        # 使用预录制的欢迎音频作为备选
                        self._send_prerecorded_welcome(call_id)
                        
                except Exception as e:
                    print(f"❌ TTS欢迎消息异常: {e}")
                    logger.error(f"TTS欢迎消息失败: {e}")
                    # 使用预录制音频作为最终备选
                    self._send_prerecorded_welcome(call_id)
            
            threading.Thread(target=delayed_welcome, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")
    
    def _send_prerecorded_welcome(self, call_id: str):
        """发送预录制的欢迎音频"""
        try:
            # 检查是否有预录制的欢迎音频文件
            if os.path.exists("welcome.ulaw"):
                logger.info("使用预录制欢迎音频")
                with open("welcome.ulaw", "rb") as f:
                    audio_data = f.read()
                self._send_audio_to_call(call_id, audio_data)
            else:
                logger.warning("没有找到预录制音频文件，生成DTMF测试音")
                # 生成简单的DTMF音作为最后备选
                self._send_dtmf_greeting(call_id)
        except Exception as e:
            logger.error(f"发送预录制音频失败: {e}")
    
    def _send_dtmf_greeting(self, call_id: str):
        """发送DTMF问候音"""
        try:
            import math
            # 生成一个简单的双音频问候(模拟电话音)
            sample_rate = 8000
            duration = 3.0
            
            audio_data = bytearray()
            for i in range(int(sample_rate * duration)):
                t = i / sample_rate
                # 混合两个频率创建电话问候音
                freq1 = 440  # A音
                freq2 = 554  # 升C音
                
                sample = int(16383 * 0.5 * (
                    math.sin(2 * math.pi * freq1 * t) * math.exp(-t) +
                    math.sin(2 * math.pi * freq2 * t) * math.exp(-t)
                ))
                
                # 转换为μ-law
                if sample < 0:
                    sample = -sample
                    sign = 0x80
                else:
                    sign = 0
                
                sample = min(sample, 32635) + 132
                ulaw = (sign | ((sample >> 8) & 0x7F)) ^ 0xFF
                audio_data.append(ulaw)
            
            logger.info(f"生成DTMF问候音: {len(audio_data)} bytes")
            self._send_audio_to_call(call_id, bytes(audio_data))
            
        except Exception as e:
            logger.error(f"生成DTMF问候音失败: {e}")
    
    def _handle_call_end(self, call_id: str):
        """处理通话结束"""
        logger.info(f"Call ended: {call_id}")
        
        if call_id in self.active_calls:
            call_info = self.active_calls[call_id]
            
            # 停止RTP处理
            if call_info.get('rtp_handler'):
                call_info['rtp_handler'].stop()
            
            # 停止STT监听
            if self.stt_service:
                self.stt_service.stop_listening()
            
            # 清理通话记录
            del self.active_calls[call_id]
            logger.info(f"Cleaned up call {call_id}")
    
    def _main_loop(self):
        """主循环"""
        try:
            logger.info("AI Phone System is running...")
            logger.info("Press Ctrl+C to stop")
            
            while self.is_running:
                time.sleep(1)
                
                # 清理超时的通话
                current_time = time.time()
                timeout_calls = []
                
                for call_id, call_info in self.active_calls.items():
                    # 30分钟超时
                    if current_time - call_info['start_time'] > 1800:
                        timeout_calls.append(call_id)
                    # 如果5秒没有音频活动，也清理（防止僵尸连接）
                    elif current_time - call_info['last_audio_time'] > 300:  # 5分钟无音频
                        timeout_calls.append(call_id)
                
                for call_id in timeout_calls:
                    logger.warning(f"Call {call_id} timed out")
                    self._handle_call_end(call_id)
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Main loop error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """停止系统"""
        logger.info("Stopping AI Phone System...")
        
        self.is_running = False
        
        # 停止所有活跃通话
        for call_id in list(self.active_calls.keys()):
            self._handle_call_end(call_id)
        
        # 停止SIP客户端
        if self.sip_client:
            self.sip_client.stop()
        
        # 清理AI服务
        if self.tts_service:
            self.tts_service.cleanup()
        
        if self.stt_service:
            self.stt_service.stop_listening()
        
        logger.info("AI Phone System stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "is_running": self.is_running,
            "active_calls": len(self.active_calls),
            "sip_registered": self.sip_client.is_registered if self.sip_client else False,
            "ai_services": {
                "llm": "ready" if self.llm_service else "not_ready",
                "tts": "ready" if self.tts_service else "not_ready",
                "stt": "ready" if self.stt_service else "not_ready"
            }
        }


def signal_handler(signum, frame):
    """信号处理器"""
    logger.info(f"Received signal {signum}")
    if 'phone_system' in globals():
        phone_system.stop()
    sys.exit(0)


def main():
    """主函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 创建并启动系统
        global phone_system
        phone_system = ProductionAIPhoneSystem()
        phone_system.start()
        
    except Exception as e:
        logger.error(f"System error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()