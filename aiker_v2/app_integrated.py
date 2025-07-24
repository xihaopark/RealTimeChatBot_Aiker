#!/usr/bin/env python3
"""
VTX AI Phone System V2 - 一体化版本 (适配Vast.ai容器环境)
所有AI服务运行在单一进程内，无需外部服务依赖
"""

import sys
import os
import logging
import signal
import threading
import time
from typing import Dict, Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入V1的核心模块 (SIP/RTP处理)
from sip_client import EnhancedSIPClient
from rtp_handler import RTPHandler

# 导入V2的一体化AI服务
from llm_service_integrated import TransformersLLMService
from stt_service_integrated import RealtimeSTTService, CallTranscriber  
from tts_service_integrated import RealtimeTTSService

# 导入音频转换器
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'local_ai'))
from audio_converter import AudioConverter

# 导入配置和业务数据
from config.settings import SIP_CONFIG
import json

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/aiker_v2_integrated.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CallInfo:
    """通话信息"""
    def __init__(self, call_id: str, remote_ip: str, remote_port: int, local_rtp_port: int):
        self.call_id = call_id
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.local_rtp_port = local_rtp_port
        self.rtp_handler: Optional[RTPHandler] = None
        self.start_time = time.time()

class CallHandler(threading.Thread):
    """通话处理器"""
    
    def __init__(self, call_info: CallInfo, tts_service: RealtimeTTSService, 
                 llm_service: TransformersLLMService, business_data: dict):
        super().__init__(daemon=True)
        self.call_info = call_info
        self.tts_service = tts_service
        self.llm_service = llm_service
        self.business_data = business_data
        
        # 通话状态
        self.running = True
        self.language = None  # 待确定
        self.conversation_history = []
        
        # STT转录器 (语言确定后初始化)
        self.transcriber: Optional[CallTranscriber] = None
        
        # 音频转换器
        self.audio_converter = AudioConverter()
        
        logger.info(f"CallHandler created for {call_info.call_id}")
    
    def run(self):
        """运行通话处理逻辑"""
        try:
            logger.info(f"[{self.call_info.call_id}] Call handler started")
            
            # 1. 播放语言选择IVR
            self._play_language_ivr()
            
            # 2. 等待用户选择语言 (模拟，实际需要DTMF解析)
            self.language = 'zh'  # 默认中文，实际项目中应解析DTMF
            
            # 3. 初始化STT转录器
            self._init_transcriber()
            
            # 4. 播放欢迎语
            self._play_welcome_message()
            
            # 5. 设置音频处理回调
            if self.call_info.rtp_handler:
                self.call_info.rtp_handler.set_audio_callback(self._handle_incoming_audio)
            
            # 6. 主循环 - 等待通话结束
            while self.running:
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"[{self.call_info.call_id}] Call handler error: {e}")
        finally:
            self._cleanup()
    
    def _play_language_ivr(self):
        """播放语言选择IVR"""
        try:
            ivr_text = "For English service, press 1. 中文服务请按2。"
            self._synthesize_and_send(ivr_text, 'en')  # 双语IVR
        except Exception as e:
            logger.error(f"[{self.call_info.call_id}] IVR playback error: {e}")
    
    def _init_transcriber(self):
        """初始化STT转录器"""
        try:
            if self.language:
                self.transcriber = CallTranscriber(
                    language=self.language, 
                    call_id=self.call_info.call_id
                )
                logger.info(f"[{self.call_info.call_id}] STT transcriber initialized for {self.language}")
        except Exception as e:
            logger.error(f"[{self.call_info.call_id}] Failed to initialize transcriber: {e}")
    
    def _play_welcome_message(self):
        """播放欢迎语"""
        try:
            if self.language == 'zh':
                welcome_text = "您好，欢迎致电OneSuite AI客服，我是您的专属AI助手，请问有什么可以帮助您的吗？"
            else:
                welcome_text = "Hello, welcome to OneSuite AI customer service. I'm your AI assistant. How can I help you today?"
            
            self._synthesize_and_send(welcome_text, self.language)
        except Exception as e:
            logger.error(f"[{self.call_info.call_id}] Welcome message error: {e}")
    
    def _synthesize_and_send(self, text: str, language: str):
        """合成语音并发送"""
        try:
            if not self.call_info.rtp_handler:
                return
            
            # TTS合成
            audio_pcm_8k = self.tts_service.synthesize_for_rtp(text, language)
            if not audio_pcm_8k:
                logger.error(f"[{self.call_info.call_id}] TTS synthesis failed for: {text}")
                return
            
            # 转换为μ-law并发送
            mulaw_data = self.audio_converter.pcm_to_mulaw(audio_pcm_8k)
            self.call_info.rtp_handler.send_audio_stream(mulaw_data)
            
            logger.debug(f"[{self.call_info.call_id}] Sent TTS audio: {len(audio_pcm_8k)} bytes")
            
        except Exception as e:
            logger.error(f"[{self.call_info.call_id}] TTS synthesis error: {e}")
    
    def _handle_incoming_audio(self, mulaw_chunk: bytes):
        """处理来自用户的音频"""
        try:
            if not self.transcriber:
                return
            
            # μ-law转换为PCM
            pcm_chunk = self.audio_converter.mulaw_to_pcm(mulaw_chunk)
            
            # STT处理
            recognized_text = self.transcriber.feed_audio(pcm_chunk)
            
            if recognized_text:
                logger.info(f"[{self.call_info.call_id}] User ({self.language}): {recognized_text}")
                
                # 生成AI回复
                self._process_user_input(recognized_text)
                
        except Exception as e:
            logger.error(f"[{self.call_info.call_id}] Audio processing error: {e}")
    
    def _process_user_input(self, user_text: str):
        """处理用户输入并生成回复"""
        try:
            # LLM生成回复
            ai_response = self.llm_service.generate_response(
                user_text, 
                conversation_id=self.call_info.call_id
            )
            
            if ai_response:
                logger.info(f"[{self.call_info.call_id}] AI ({self.language}): {ai_response}")
                
                # 合成并发送AI回复
                self._synthesize_and_send(ai_response, self.language)
                
                # 更新对话历史
                self.conversation_history.append({
                    "user": user_text,
                    "assistant": ai_response,
                    "timestamp": time.time()
                })
            
        except Exception as e:
            logger.error(f"[{self.call_info.call_id}] AI processing error: {e}")
    
    def stop(self):
        """停止通话处理"""
        self.running = False
        logger.info(f"[{self.call_info.call_id}] Call handler stopping")
    
    def _cleanup(self):
        """清理资源"""
        try:
            if self.transcriber:
                self.transcriber.cleanup()
            
            logger.info(f"[{self.call_info.call_id}] Call handler cleaned up")
        except Exception as e:
            logger.error(f"[{self.call_info.call_id}] Cleanup error: {e}")

class CallManager:
    """通话管理器"""
    
    def __init__(self):
        # AI服务
        self.tts_service: Optional[RealtimeTTSService] = None
        self.llm_service: Optional[TransformersLLMService] = None
        
        # 业务数据
        self.business_data = {}
        
        # 活跃通话
        self.active_calls: Dict[str, CallHandler] = {}
        self.lock = threading.RLock()
        
        # 初始化服务
        self._init_services()
        self._load_business_data()
    
    def _init_services(self):
        """初始化AI服务"""
        try:
            logger.info("Initializing AI services...")
            
            # 初始化TTS服务
            self.tts_service = RealtimeTTSService(
                engine_type="coqui",  # 使用本地Coqui引擎
                device="auto"
            )
            logger.info("✅ TTS service initialized")
            
            # 初始化LLM服务
            self.llm_service = TransformersLLMService(
                model_name="Qwen/Qwen2.5-7B-Instruct",
                device="auto",
                use_4bit=True  # 使用4bit量化节省显存
            )
            logger.info("✅ LLM service initialized")
            
            logger.info("🚀 All AI services ready!")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI services: {e}")
            raise
    
    def _load_business_data(self):
        """加载业务数据"""
        try:
            business_data_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'data', 'onesuite-business-data.json'
            )
            
            if os.path.exists(business_data_path):
                with open(business_data_path, 'r', encoding='utf-8') as f:
                    self.business_data = json.load(f)
                logger.info("✅ Business data loaded")
            else:
                logger.warning("Business data file not found")
                self.business_data = {"company": "OneSuite", "services": []}
                
        except Exception as e:
            logger.error(f"Failed to load business data: {e}")
            self.business_data = {}
    
    def handle_incoming_call(self, call_info: CallInfo) -> CallHandler:
        """处理来电"""
        try:
            with self.lock:
                # 创建通话处理器
                call_handler = CallHandler(
                    call_info=call_info,
                    tts_service=self.tts_service,
                    llm_service=self.llm_service,
                    business_data=self.business_data
                )
                
                # 添加到活跃通话列表
                self.active_calls[call_info.call_id] = call_handler
                
                # 启动通话处理
                call_handler.start()
                
                logger.info(f"✅ Call {call_info.call_id} handler started")
                return call_handler
                
        except Exception as e:
            logger.error(f"Failed to handle incoming call: {e}")
            raise
    
    def end_call(self, call_id: str):
        """结束通话"""
        with self.lock:
            if call_id in self.active_calls:
                call_handler = self.active_calls[call_id]
                call_handler.stop()
                del self.active_calls[call_id]
                logger.info(f"✅ Call {call_id} ended")
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        with self.lock:
            return {
                "active_calls": len(self.active_calls),
                "tts_available": self.tts_service.is_available() if self.tts_service else False,
                "llm_available": self.llm_service.is_available() if self.llm_service else False,
                "tts_stats": self.tts_service.get_stats() if self.tts_service else {},
                "llm_stats": self.llm_service.get_stats() if self.llm_service else {}
            }
    
    def cleanup(self):
        """清理资源"""
        logger.info("Cleaning up call manager...")
        
        # 停止所有活跃通话
        with self.lock:
            for call_id, call_handler in list(self.active_calls.items()):
                call_handler.stop()
            self.active_calls.clear()
        
        # 清理AI服务
        if self.tts_service:
            self.tts_service.cleanup()
        
        if self.llm_service:
            self.llm_service.cleanup()
        
        logger.info("✅ Call manager cleaned up")

class IntegratedAIPhoneSystem:
    """一体化AI电话系统"""
    
    def __init__(self):
        self.call_manager = CallManager()
        self.sip_client: Optional[EnhancedSIPClient] = None
        self.running = False
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def start(self):
        """启动系统"""
        try:
            logger.info("🚀 Starting VTX AI Phone System V2 (Integrated)")
            
            # 创建SIP客户端
            self.sip_client = EnhancedSIPClient(
                username=SIP_CONFIG['username'],
                password=SIP_CONFIG['password'],
                server=SIP_CONFIG['server'],
                port=SIP_CONFIG['port'],
                local_ip=SIP_CONFIG.get('local_ip', '0.0.0.0')
            )
            
            # 设置来电处理回调
            self.sip_client.set_incoming_call_handler(self._handle_incoming_call)
            
            # 启动SIP客户端
            self.sip_client.start()
            
            # 注册到SIP服务器
            if self.sip_client.register():
                logger.info("✅ SIP registration successful")
                self.running = True
                
                # 显示状态
                self._print_status()
                
                # 主循环
                self._main_loop()
            else:
                logger.error("❌ SIP registration failed")
                
        except Exception as e:
            logger.error(f"Failed to start system: {e}")
            raise
    
    def _handle_incoming_call(self, call_data: dict):
        """处理来电回调"""
        try:
            call_id = call_data.get('call_id', f"call_{int(time.time())}")
            remote_ip = call_data.get('remote_ip', 'unknown')
            remote_port = call_data.get('remote_port', 0)
            local_rtp_port = call_data.get('local_rtp_port', 10000)
            
            # 创建通话信息
            call_info = CallInfo(
                call_id=call_id,
                remote_ip=remote_ip,
                remote_port=remote_port,
                local_rtp_port=local_rtp_port
            )
            
            # 创建RTP处理器
            call_info.rtp_handler = RTPHandler(
                local_port=local_rtp_port,
                remote_ip=remote_ip,
                remote_port=remote_port
            )
            
            # 启动RTP处理器
            call_info.rtp_handler.start()
            
            # 交给通话管理器处理
            self.call_manager.handle_incoming_call(call_info)
            
            logger.info(f"📞 Incoming call handled: {call_id}")
            
        except Exception as e:
            logger.error(f"Error handling incoming call: {e}")
    
    def _print_status(self):
        """打印系统状态"""
        stats = self.call_manager.get_stats()
        
        print("\n" + "="*60)
        print("🎯 VTX AI Phone System V2 - Status")
        print("="*60)
        print(f"📞 SIP Registration: ✅ Connected")
        print(f"🎤 TTS Service: {'✅ Ready' if stats['tts_available'] else '❌ Not Ready'}")
        print(f"🧠 LLM Service: {'✅ Ready' if stats['llm_available'] else '❌ Not Ready'}")
        print(f"📊 Active Calls: {stats['active_calls']}")
        print("="*60)
        print("🔥 System ready to receive calls!")
        print("   Press Ctrl+C to stop")
        print("="*60)
    
    def _main_loop(self):
        """主循环"""
        try:
            while self.running:
                time.sleep(1)
                
                # 定期打印统计信息
                if int(time.time()) % 30 == 0:  # 每30秒
                    stats = self.call_manager.get_stats()
                    logger.info(f"📊 Active calls: {stats['active_calls']}")
                    
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Main loop error: {e}")
    
    def stop(self):
        """停止系统"""
        logger.info("🛑 Stopping VTX AI Phone System V2...")
        
        self.running = False
        
        # 停止SIP客户端
        if self.sip_client:
            self.sip_client.stop()
        
        # 清理通话管理器
        self.call_manager.cleanup()
        
        logger.info("✅ System stopped successfully")

def main():
    """主函数"""
    try:
        # 创建日志目录
        os.makedirs('logs', exist_ok=True)
        
        # 创建并启动系统
        system = IntegratedAIPhoneSystem()
        system.start()
        
    except Exception as e:
        logger.error(f"System startup failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())