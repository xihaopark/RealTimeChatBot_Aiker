#!/usr/bin/env python3
"""
通话处理器 - 高性能版本
整合Vosk STT + Llama.cpp LLM + Piper TTS
"""

import threading
import time
import logging
import json
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field

from stt_service import CallTranscriber
from tts_service import PiperTTSService
from llm_service import LlamaCppLLMService
from audio_converter import AudioConverter

logger = logging.getLogger(__name__)

@dataclass
class CallInfo:
    """通话信息"""
    call_id: str
    remote_ip: str
    remote_port: int
    local_rtp_port: int
    start_time: float = field(default_factory=time.time)
    language: Optional[str] = None
    rtp_handler: Any = None

class CallHandler(threading.Thread):
    """单通话处理器"""
    
    def __init__(self, 
                 call_info: CallInfo,
                 tts_service: PiperTTSService,
                 llm_service: LlamaCppLLMService,
                 business_data: Dict[str, Any] = None):
        """
        初始化通话处理器
        
        Args:
            call_info: 通话信息
            tts_service: TTS服务实例
            llm_service: LLM服务实例
            business_data: 业务数据
        """
        super().__init__(daemon=True)
        
        self.call_info = call_info
        self.tts_service = tts_service
        self.llm_service = llm_service
        self.business_data = business_data or {}
        
        # 状态管理
        self.running = True
        self.language = None  # 用户选择的语言
        self.transcriber: Optional[CallTranscriber] = None
        self.conversation_id = f"conv_{call_info.call_id}"
        
        # 音频处理
        self.audio_buffer = bytearray()
        self.silence_counter = 0
        self.max_silence = 50  # 静音检测阈值
        
        # 状态标记
        self.in_ivr = True  # 是否在语言选择阶段
        self.last_activity = time.time()
        
        logger.info(f"CallHandler initialized for {call_info.call_id}")
    
    def run(self):
        """主处理流程"""
        try:
            # 设置RTP音频回调
            if self.call_info.rtp_handler:
                self.call_info.rtp_handler.set_audio_callback(self.handle_incoming_audio)
            
            # 播放语言选择提示
            self._play_language_selection()
            
            # 等待语言选择或超时
            self._wait_for_language_selection()
            
            # 主对话循环
            self._start_conversation()
            
        except Exception as e:
            logger.error(f"CallHandler error for {self.call_info.call_id}: {e}")
        finally:
            self.cleanup()
    
    def _play_language_selection(self):
        """播放语言选择提示"""
        try:
            # 双语提示音
            prompt_text = "For English service, press 1. 中文服务请按2。如需继续，请开始说话。"
            
            # 使用英文TTS生成提示音
            audio_data = self.tts_service.synthesize_for_rtp(prompt_text, 'en')
            
            if audio_data and self.call_info.rtp_handler:
                # 延迟1秒后播放，确保RTP连接稳定
                threading.Timer(1.0, self._send_audio_to_rtp, args=[audio_data]).start()
                
        except Exception as e:
            logger.error(f"Failed to play language selection: {e}")
    
    def _wait_for_language_selection(self):
        """等待语言选择"""
        # 默认等待10秒，如果用户没有选择语言则默认为中文
        start_time = time.time()
        timeout = 10.0
        
        while self.running and self.in_ivr and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        # 如果没有明确选择语言，默认使用中文
        if self.language is None:
            self.language = 'zh'
            logger.info(f"Default language set to Chinese for {self.call_info.call_id}")
    
    def _start_conversation(self):
        """开始对话"""
        try:
            # 初始化STT转录器
            self.transcriber = CallTranscriber(self.language, self.call_info.call_id)
            self.transcriber.stt_service.set_transcription_callback(self._on_transcription_complete)
            
            self.in_ivr = False
            
            # 发送欢迎消息
            welcome_msg = self._get_welcome_message()
            self._send_ai_response(welcome_msg)
            
            logger.info(f"Conversation started for {self.call_info.call_id} in {self.language}")
            
        except Exception as e:
            logger.error(f"Failed to start conversation: {e}")
    
    def _get_welcome_message(self) -> str:
        """获取欢迎消息"""
        if self.language == 'zh':
            return "您好，欢迎致电OneSuite，我是您的AI助手。请问有什么可以帮助您的吗？"
        else:
            return "Hello, welcome to OneSuite. I'm your AI assistant. How may I help you today?"
    
    def handle_incoming_audio(self, audio_data: bytes):
        """处理来电音频"""
        try:
            self.last_activity = time.time()
            
            # 在IVR阶段检测DTMF (简化实现)
            if self.in_ivr:
                self._detect_dtmf_simple(audio_data)
                return
            
            # 在对话阶段进行STT
            if self.transcriber:
                # 将μ-law转换为PCM
                pcm_audio = AudioConverter.mulaw_to_pcm(audio_data)
                
                # 检测静音
                if self._is_silence(pcm_audio):
                    self.silence_counter += 1
                else:
                    self.silence_counter = 0
                
                # 输入到STT
                self.transcriber.feed_audio(pcm_audio)
                
        except Exception as e:
            logger.error(f"Error handling incoming audio: {e}")
    
    def _detect_dtmf_simple(self, audio_data: bytes):
        """简化的DTMF检测 (基于音频能量)"""
        try:
            # 转换为PCM进行分析
            pcm_audio = AudioConverter.mulaw_to_pcm(audio_data)
            
            # 计算能量水平 (简化的DTMF检测)
            energy = sum(abs(sample) for sample in pcm_audio) / len(pcm_audio)
            
            # 如果检测到高能量 (可能是DTMF)
            if energy > 1000:  # 阈值需要调整
                # 假设用户按了键，直接开始对话
                logger.info(f"Possible DTMF detected, starting conversation")
                if self.language is None:
                    self.language = 'zh'  # 默认中文
                self.in_ivr = False
                
        except Exception as e:
            logger.debug(f"DTMF detection error: {e}")
    
    def _is_silence(self, pcm_data: bytes, threshold: int = 300) -> bool:
        """检测静音"""
        try:
            if len(pcm_data) < 2:
                return True
            
            # 计算音频能量
            energy = sum(abs(int.from_bytes(pcm_data[i:i+2], 'little', signed=True)) 
                        for i in range(0, len(pcm_data)-1, 2)) / (len(pcm_data) // 2)
            
            return energy < threshold
            
        except Exception:
            return True
    
    def _on_transcription_complete(self, text: str, language: str):
        """STT转录完成回调"""
        if not text.strip():
            return
            
        logger.info(f"[{self.call_info.call_id}] User ({language}): {text}")
        
        try:
            # 生成AI回复
            ai_response = self.llm_service.generate_response(
                text, 
                self.conversation_id
            )
            
            logger.info(f"[{self.call_info.call_id}] AI ({language}): {ai_response}")
            
            # 发送AI回复
            self._send_ai_response(ai_response)
            
        except Exception as e:
            logger.error(f"Error processing transcription: {e}")
            # 发送错误回复
            error_msg = "抱歉，我现在遇到了一些问题，请稍后再试。" if language == 'zh' else "Sorry, I'm experiencing some issues. Please try again later."
            self._send_ai_response(error_msg)
    
    def _send_ai_response(self, text: str):
        """发送AI回复"""
        try:
            if not text.strip():
                return
            
            # 使用TTS合成语音
            audio_data = self.tts_service.synthesize_for_rtp(text, self.language)
            
            if audio_data and self.call_info.rtp_handler:
                self._send_audio_to_rtp(audio_data)
            else:
                logger.warning("Failed to synthesize or send audio response")
                
        except Exception as e:
            logger.error(f"Error sending AI response: {e}")
    
    def _send_audio_to_rtp(self, audio_data: bytes):
        """将音频数据发送到RTP"""
        try:
            if not self.call_info.rtp_handler:
                return
            
            # 转换为μ-law格式
            mulaw_data = AudioConverter.pcm_to_mulaw(audio_data)
            
            # 分包发送 (160字节/包, 20ms间隔)
            chunk_size = 160
            
            for i in range(0, len(mulaw_data), chunk_size):
                if not self.running:
                    break
                    
                chunk = mulaw_data[i:i + chunk_size]
                
                # 填充最后一个包
                if len(chunk) < chunk_size:
                    chunk += b'\x7f' * (chunk_size - len(chunk))
                
                # 发送音频包
                self.call_info.rtp_handler.send_audio(chunk)
                
                # 控制发送速率
                time.sleep(0.02)  # 20ms
                
        except Exception as e:
            logger.error(f"Error sending audio to RTP: {e}")
    
    def stop(self):
        """停止通话处理"""
        self.running = False
        logger.info(f"CallHandler stopped for {self.call_info.call_id}")
    
    def cleanup(self):
        """清理资源"""
        try:
            self.running = False
            
            # 清理转录器
            if self.transcriber:
                self.transcriber = None
            
            # 清理会话历史
            if hasattr(self.llm_service, 'clear_conversation'):
                self.llm_service.clear_conversation(self.conversation_id)
            
            logger.info(f"CallHandler cleaned up for {self.call_info.call_id}")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取通话统计信息"""
        duration = time.time() - self.call_info.start_time
        
        return {
            "call_id": self.call_info.call_id,
            "duration": duration,
            "language": self.language,
            "in_ivr": self.in_ivr,
            "last_activity": self.last_activity,
            "running": self.running,
            "transcript_count": len(self.transcriber.transcripts) if self.transcriber else 0
        }


class CallManager:
    """通话管理器"""
    
    def __init__(self):
        self.active_calls: Dict[str, CallHandler] = {}
        self.tts_service = PiperTTSService()
        self.llm_service = LlamaCppLLMService()
        self.business_data = self._load_business_data()
        self.lock = threading.RLock()
        
        logger.info("CallManager initialized")
    
    def _load_business_data(self) -> Dict[str, Any]:
        """加载业务数据"""
        try:
            with open('onesuite-business-data.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load business data: {e}")
            return {}
    
    def handle_incoming_call(self, call_info: CallInfo) -> CallHandler:
        """处理来电"""
        with self.lock:
            # 创建通话处理器
            call_handler = CallHandler(
                call_info=call_info,
                tts_service=self.tts_service,
                llm_service=self.llm_service,
                business_data=self.business_data
            )
            
            # 保存并启动
            self.active_calls[call_info.call_id] = call_handler
            call_handler.start()
            
            logger.info(f"Incoming call handled: {call_info.call_id}")
            return call_handler
    
    def end_call(self, call_id: str):
        """结束通话"""
        with self.lock:
            if call_id in self.active_calls:
                call_handler = self.active_calls[call_id]
                call_handler.stop()
                del self.active_calls[call_id]
                logger.info(f"Call ended: {call_id}")
    
    def get_active_calls(self) -> Dict[str, Dict[str, Any]]:
        """获取活跃通话统计"""
        with self.lock:
            return {
                call_id: handler.get_stats()
                for call_id, handler in self.active_calls.items()
            }
    
    def cleanup_timeout_calls(self, timeout: int = 1800):
        """清理超时通话"""
        current_time = time.time()
        timeout_calls = []
        
        with self.lock:
            for call_id, handler in self.active_calls.items():
                if current_time - handler.call_info.start_time > timeout:
                    timeout_calls.append(call_id)
        
        for call_id in timeout_calls:
            logger.warning(f"Call timeout: {call_id}")
            self.end_call(call_id)