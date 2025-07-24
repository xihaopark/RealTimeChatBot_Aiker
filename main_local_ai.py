#!/usr/bin/env python3
"""
VTX AI Phone System - Local AI Version
本地AI语音对话系统，使用RealtimeSTT/TTS和本地LLM
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
from local_ai import LocalSTT, LocalTTS, LocalLLM

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/local_ai_system.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class LocalAIPhoneSystem:
    """本地AI电话系统"""
    
    def __init__(self):
        self.config = settings
        self.is_running = False
        
        # SIP和RTP组件
        self.sip_client = None
        self.active_calls: Dict[str, Dict[str, Any]] = {}
        
        # 本地AI组件
        self.stt_service = None
        self.tts_service = None
        self.llm_service = None
        
        # 初始化AI服务
        self._init_ai_services()
        
        logger.info("LocalAIPhoneSystem initialized")
    
    def _init_ai_services(self):
        """初始化本地AI服务"""
        try:
            # 初始化LLM
            logger.info("Initializing Local LLM...")
            self.llm_service = LocalLLM(
                model_name="Qwen/Qwen2.5-7B-Instruct",
                device="cuda",
                max_length=2048,
                temperature=0.7,
                use_4bit=True
            )
            
            # 初始化TTS
            logger.info("Initializing Local TTS...")
            self.tts_service = LocalTTS(
                engine="system",  # 开始用系统引擎，后续可切换到coqui
                voice="zh",
                device="cuda",
                speed=1.0
            )
            
            # 初始化STT
            logger.info("Initializing Local STT...")
            self.stt_service = LocalSTT(
                model="base",  # 使用base模型平衡准确性和速度
                language="zh",
                device="cuda",
                mic=False
            )
            
            # 设置STT回调
            self.stt_service.set_transcription_callback(self._on_transcription)
            
            logger.info("All AI services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI services: {e}")
            raise
    
    def _on_transcription(self, text: str):
        """STT转录回调"""
        logger.info(f"STT Result: {text}")
        
        # 处理每个活跃的通话
        for call_id, call_info in self.active_calls.items():
            try:
                # 生成AI回复
                response = self.llm_service.generate_response(text)
                logger.info(f"LLM Response: {response}")
                
                # 生成语音
                audio_data = self.tts_service.synthesize_text(response)
                
                if audio_data and call_info.get('rtp_handler'):
                    # 发送音频到RTP流
                    self._send_audio_to_rtp(call_info['rtp_handler'], audio_data)
                    
            except Exception as e:
                logger.error(f"Error processing transcription for call {call_id}: {e}")
    
    def _send_audio_to_rtp(self, rtp_handler: RTPHandler, audio_data: bytes):
        """将音频数据发送到RTP流"""
        try:
            # 音频数据已经是μ-law格式，直接分包发送
            chunk_size = 160  # 20ms @ 8kHz
            
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                if len(chunk) < chunk_size:
                    # 填充最后一个包
                    chunk += b'\x7f' * (chunk_size - len(chunk))
                
                rtp_handler.send_audio(chunk)
                
                # 控制发送速率 (20ms间隔)
                time.sleep(0.02)
                
        except Exception as e:
            logger.error(f"Error sending audio to RTP: {e}")
    
    def start(self):
        """启动系统"""
        try:
            logger.info("Starting Local AI Phone System...")
            
            # 启动AI服务
            self.stt_service.start_listening()
            
            # 获取第一个可用的分机配置
            extension_id = list(self.config.extensions.keys())[0]
            extension = self.config.extensions[extension_id]
            
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
            self.sip_client.start()
            
            self.is_running = True
            logger.info("Local AI Phone System started successfully")
            
            # 主循环
            self._main_loop()
            
        except Exception as e:
            logger.error(f"Failed to start system: {e}")
            self.stop()
    
    def _handle_incoming_call(self, call_info: Dict[str, Any]):
        """处理来电"""
        call_id = call_info.get('call_id')
        remote_ip = call_info.get('remote_ip')
        remote_port = call_info.get('remote_port')
        
        logger.info(f"Incoming call: {call_id} from {remote_ip}:{remote_port}")
        
        try:
            # 创建RTP处理器
            rtp_handler = RTPHandler(
                remote_ip=remote_ip,
                remote_port=remote_port,
                local_port=call_info.get('local_rtp_port', 10000)
            )
            
            # 设置音频接收回调
            rtp_handler.set_audio_callback(self._on_rtp_audio)
            
            # 启动RTP处理
            rtp_handler.start()
            
            # 保存通话信息
            self.active_calls[call_id] = {
                'rtp_handler': rtp_handler,
                'remote_ip': remote_ip,
                'remote_port': remote_port,
                'start_time': time.time()
            }
            
            # 发送欢迎消息
            welcome_msg = "您好，欢迎致电OneSuite，我是您的AI助手，请问有什么可以帮助您的吗？"
            self._send_welcome_message(call_id, welcome_msg)
            
        except Exception as e:
            logger.error(f"Failed to handle incoming call {call_id}: {e}")
    
    def _on_rtp_audio(self, audio_data: bytes):
        """RTP音频接收回调"""
        try:
            # 将音频数据传递给STT服务
            self.stt_service.feed_audio(audio_data)
        except Exception as e:
            logger.error(f"Error processing RTP audio: {e}")
    
    def _send_welcome_message(self, call_id: str, message: str):
        """发送欢迎消息"""
        try:
            call_info = self.active_calls.get(call_id)
            if not call_info:
                return
            
            # 生成欢迎语音
            audio_data = self.tts_service.synthesize_text(message)
            
            if audio_data and call_info.get('rtp_handler'):
                # 延迟一点发送，确保RTP连接稳定
                threading.Timer(1.0, self._send_audio_to_rtp, 
                              args=[call_info['rtp_handler'], audio_data]).start()
                
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")
    
    def _handle_call_end(self, call_id: str):
        """处理通话结束"""
        logger.info(f"Call ended: {call_id}")
        
        if call_id in self.active_calls:
            call_info = self.active_calls[call_id]
            
            # 停止RTP处理
            if call_info.get('rtp_handler'):
                call_info['rtp_handler'].stop()
            
            # 清理通话记录
            del self.active_calls[call_id]
            logger.info(f"Cleaned up call {call_id}")
    
    def _main_loop(self):
        """主循环"""
        try:
            while self.is_running:
                time.sleep(1)
                
                # 清理超时的通话
                current_time = time.time()
                timeout_calls = []
                
                for call_id, call_info in self.active_calls.items():
                    if current_time - call_info['start_time'] > 1800:  # 30分钟超时
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
        logger.info("Stopping Local AI Phone System...")
        
        self.is_running = False
        
        # 停止所有活跃通话
        for call_id in list(self.active_calls.keys()):
            self._handle_call_end(call_id)
        
        # 停止SIP客户端
        if self.sip_client:
            self.sip_client.stop()
        
        # 停止AI服务
        if self.stt_service:
            self.stt_service.stop_listening()
        
        if self.tts_service:
            self.tts_service.cleanup()
        
        logger.info("Local AI Phone System stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "is_running": self.is_running,
            "active_calls": len(self.active_calls),
            "sip_status": "connected" if self.sip_client and self.sip_client.is_registered else "disconnected",
            "ai_services": {
                "stt": "initialized" if self.stt_service else "not_initialized",
                "tts": "initialized" if self.tts_service else "not_initialized", 
                "llm": "initialized" if self.llm_service else "not_initialized"
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
        phone_system = LocalAIPhoneSystem()
        phone_system.start()
        
    except Exception as e:
        logger.error(f"System error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()