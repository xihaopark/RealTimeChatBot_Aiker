#!/usr/bin/env python3
"""
VTX AI Phone System V2 - 主应用程序
高性能版本：Vosk STT + Llama.cpp LLM + Piper TTS
"""

import asyncio
import logging
import os
import sys
import signal
import threading
import time
from typing import Dict, Any, Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from settings import Settings
from sip_client import EnhancedSIPClient
from rtp_handler import RTPHandler
from call_handler import CallManager, CallInfo
from tts_service import PiperTTSService
from llm_service import LlamaCppLLMService
from stt_service import VoskSTTService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/aiker_v2.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class AikerV2System:
    """VTX AI电话系统 V2"""
    
    def __init__(self):
        self.config = Settings()
        self.is_running = False
        
        # 核心组件
        self.sip_client: Optional[EnhancedSIPClient] = None
        self.call_manager: Optional[CallManager] = None
        
        # AI服务状态检查
        self._check_ai_services()
        
        logger.info("AikerV2System initialized")
    
    def _check_ai_services(self):
        """检查AI服务可用性"""
        logger.info("Checking AI services availability...")
        
        # 检查TTS服务
        tts = PiperTTSService()
        if tts.is_available():
            languages = tts.get_supported_languages()
            logger.info(f"✅ Piper TTS available - Languages: {languages}")
        else:
            logger.warning("⚠️  Piper TTS not available")
        
        # 检查LLM服务
        llm = LlamaCppLLMService()
        if llm.is_available():
            logger.info("✅ Llama.cpp LLM available")
        else:
            logger.warning("⚠️  Llama.cpp LLM not available")
        
        # 检查STT服务
        stt = VoskSTTService()
        if stt.is_available():
            languages = stt.get_supported_languages()
            logger.info(f"✅ Vosk STT available - Languages: {languages}")
        else:
            logger.warning("⚠️  Vosk STT not available")
    
    def start(self):
        """启动系统"""
        try:
            logger.info("🚀 Starting VTX AI Phone System V2...")
            
            # 初始化通话管理器
            self.call_manager = CallManager()
            
            # 获取分机配置
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
            logger.info("Starting SIP client...")
            self.sip_client.start()
            
            # 等待SIP注册完成
            self._wait_for_sip_registration()
            
            self.is_running = True
            logger.info("✅ VTX AI Phone System V2 started successfully")
            
            # 启动主循环
            self._main_loop()
            
        except Exception as e:
            logger.error(f"Failed to start system: {e}")
            self.stop()
            raise
    
    def _wait_for_sip_registration(self, timeout: int = 30):
        """等待SIP注册完成"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.sip_client and self.sip_client.is_registered:
                logger.info("✅ SIP registration successful")
                return
            time.sleep(1)
        
        raise RuntimeError("SIP registration timeout")
    
    def _handle_incoming_call(self, call_info_dict: Dict[str, Any]):
        """处理来电"""
        try:
            call_id = call_info_dict.get('call_id')
            remote_ip = call_info_dict.get('remote_ip')
            remote_port = call_info_dict.get('remote_port')
            local_rtp_port = call_info_dict.get('local_rtp_port', 10000)
            
            logger.info(f"📞 Incoming call: {call_id} from {remote_ip}:{remote_port}")
            
            # 创建RTP处理器
            rtp_handler = RTPHandler(
                remote_ip=remote_ip,
                remote_port=remote_port,
                local_port=local_rtp_port
            )
            
            # 启动RTP处理
            rtp_handler.start()
            
            # 创建通话信息
            call_info = CallInfo(
                call_id=call_id,
                remote_ip=remote_ip,
                remote_port=remote_port,
                local_rtp_port=local_rtp_port,
                rtp_handler=rtp_handler
            )
            
            # 交给通话管理器处理
            call_handler = self.call_manager.handle_incoming_call(call_info)
            
            logger.info(f"✅ Call {call_id} handler started")
            
        except Exception as e:
            logger.error(f"Error handling incoming call: {e}")
    
    def _main_loop(self):
        """主循环"""
        try:
            last_cleanup = time.time()
            
            while self.is_running:
                time.sleep(5)  # 5秒检查间隔
                
                # 定期清理超时通话 (每5分钟)
                current_time = time.time()
                if current_time - last_cleanup > 300:
                    self._cleanup_timeout_calls()
                    last_cleanup = current_time
                
                # 显示系统状态 (每分钟)
                if int(current_time) % 60 == 0:
                    self._log_system_status()
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Main loop error: {e}")
        finally:
            self.stop()
    
    def _cleanup_timeout_calls(self):
        """清理超时通话"""
        if self.call_manager:
            self.call_manager.cleanup_timeout_calls()
    
    def _log_system_status(self):
        """记录系统状态"""
        try:
            if self.call_manager:
                active_calls = self.call_manager.get_active_calls()
                logger.info(f"📊 System Status - Active calls: {len(active_calls)}")
                
                # 显示每个通话的详细信息
                for call_id, stats in active_calls.items():
                    duration = int(stats.get('duration', 0))
                    language = stats.get('language', 'unknown')
                    logger.debug(f"  Call {call_id}: {duration}s, language={language}")
                    
        except Exception as e:
            logger.debug(f"Error logging system status: {e}")
    
    def stop(self):
        """停止系统"""
        logger.info("🛑 Stopping VTX AI Phone System V2...")
        
        self.is_running = False
        
        # 停止所有通话
        if self.call_manager:
            active_calls = list(self.call_manager.active_calls.keys())
            for call_id in active_calls:
                self.call_manager.end_call(call_id)
        
        # 停止SIP客户端
        if self.sip_client:
            self.sip_client.stop()
        
        logger.info("✅ VTX AI Phone System V2 stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = {
            "is_running": self.is_running,
            "sip_registered": self.sip_client.is_registered if self.sip_client else False,
            "active_calls": 0,
            "ai_services": {
                "tts_available": PiperTTSService().is_available(),
                "llm_available": LlamaCppLLMService().is_available(),
                "stt_available": VoskSTTService().is_available()
            }
        }
        
        if self.call_manager:
            status["active_calls"] = len(self.call_manager.active_calls)
            status["call_details"] = self.call_manager.get_active_calls()
        
        return status


# 全局系统实例
phone_system: Optional[AikerV2System] = None

def signal_handler(signum, frame):
    """信号处理器"""
    logger.info(f"Received signal {signum}")
    if phone_system:
        phone_system.stop()
    sys.exit(0)

def main():
    """主函数"""
    global phone_system
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 检查环境
        logger.info("🔍 Checking environment...")
        
        # 检查配置文件
        if not os.path.exists('onesuite-business-data.json'):
            logger.warning("Business data file not found, using defaults")
        
        # 创建日志目录
        os.makedirs('../logs', exist_ok=True)
        
        # 创建并启动系统
        logger.info("🏗️  Initializing system...")
        phone_system = AikerV2System()
        
        logger.info("🎯 Starting system...")
        phone_system.start()
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"System error: {e}")
        sys.exit(1)
    finally:
        if phone_system:
            phone_system.stop()

if __name__ == "__main__":
    main()