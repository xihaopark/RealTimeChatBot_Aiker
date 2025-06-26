#!/usr/bin/env python3
"""
VTX AI Phone System - Deepgram STT提供商
实现流式语音识别功能
"""

import asyncio
import json
import logging
import time
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum
import base64

try:
    import websockets
except ImportError:
    websockets = None
    logging.warning("websockets库未安装，Deepgram功能将不可用")

from ...utils.api_manager import api_manager
from ...utils.performance_monitor import performance_monitor

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class DeepgramConfig:
    """Deepgram配置"""
    model: str = "nova-2"              # 使用Nova-2模型（最新最快）
    language: str = "zh-CN"            # 中文
    smart_format: bool = True          # 智能格式化
    interim_results: bool = True       # 返回中间结果
    endpointing: int = 300             # 300ms自动断点检测
    vad_events: bool = True           # 语音活动检测事件
    punctuate: bool = True            # 自动标点
    profanity_filter: bool = False    # 不过滤敏感词
    redact: bool = False              # 不删减内容
    numerals: bool = True             # 数字转换
    filler_words: bool = False        # 不包含填充词
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为API参数字典"""
        return {
            "model": self.model,
            "language": self.language,
            "smart_format": self.smart_format,
            "interim_results": self.interim_results,
            "endpointing": self.endpointing,
            "vad_events": self.vad_events,
            "punctuate": self.punctuate,
            "profanity_filter": self.profanity_filter,
            "redact": self.redact,
            "numerals": self.numerals,
            "filler_words": self.filler_words
        }


class DeepgramSTTProvider:
    """Deepgram流式STT提供商"""
    
    def __init__(self, config: Optional[DeepgramConfig] = None):
        self.config = config or DeepgramConfig()
        self.api_key = api_manager.get_key('deepgram')
        
        if not self.api_key:
            raise ValueError("Deepgram API密钥未配置")
        
        # 连接状态
        self.state = ConnectionState.DISCONNECTED
        self.websocket = None
        
        # 回调函数
        self.on_transcript: Optional[Callable[[str, bool], None]] = None  # (文本, 是否最终结果)
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_connected: Optional[Callable[[], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None
        
        # 性能跟踪
        self.request_start_time = None
        
        logger.info(f"🎤 Deepgram STT提供商初始化")
        logger.info(f"   模型: {self.config.model}")
        logger.info(f"   语言: {self.config.language}")
    
    async def connect(self) -> bool:
        """建立WebSocket连接"""
        if websockets is None:
            logger.error("❌ websockets库未安装，无法连接Deepgram")
            return False
            
        if self.state == ConnectionState.CONNECTED:
            return True
        
        try:
            self.state = ConnectionState.CONNECTING
            logger.info("🔗 正在连接Deepgram...")
            
            # 构建WebSocket URL
            url = self._build_websocket_url()
            
            # 建立连接 - 修复参数问题
            self.websocket = await websockets.connect(
                url,
                additional_headers={"Authorization": f"Token {self.api_key}"},
                ping_interval=20,
                ping_timeout=10
            )
            
            self.state = ConnectionState.CONNECTED
            logger.info("✅ Deepgram连接成功")
            
            # 启动消息监听
            asyncio.create_task(self._listen_for_messages())
            
            if self.on_connected:
                self.on_connected()
            
            return True
            
        except Exception as e:
            self.state = ConnectionState.ERROR
            logger.error(f"❌ Deepgram连接失败: {e}")
            if self.on_error:
                self.on_error(f"连接失败: {e}")
            return False
    
    def _build_websocket_url(self) -> str:
        """构建WebSocket URL"""
        base_url = "wss://api.deepgram.com/v1/listen"
        params = []
        
        for key, value in self.config.to_dict().items():
            if isinstance(value, bool):
                params.append(f"{key}={str(value).lower()}")
            else:
                params.append(f"{key}={value}")
        
        url = f"{base_url}?{'&'.join(params)}"
        logger.debug(f"WebSocket URL: {url}")
        return url
    
    async def disconnect(self):
        """断开连接"""
        if self.websocket and self.state == ConnectionState.CONNECTED:
            try:
                await self.websocket.close()
                logger.info("🔌 Deepgram连接已断开")
            except Exception as e:
                logger.error(f"断开连接时出错: {e}")
        
        self.state = ConnectionState.DISCONNECTED
        self.websocket = None
        
        if self.on_disconnected:
            self.on_disconnected()
    
    async def send_audio(self, audio_data: bytes, is_final: bool = False):
        """发送音频数据"""
        if self.state != ConnectionState.CONNECTED or not self.websocket:
            logger.warning("⚠️ 未连接到Deepgram，无法发送音频")
            return
        
        try:
            if is_final:
                # 发送结束信号
                await self.websocket.send(json.dumps({"type": "CloseStream"}))
                logger.debug("📤 发送流结束信号")
            else:
                # 发送音频数据
                await self.websocket.send(audio_data)
                logger.debug(f"📤 发送音频数据: {len(audio_data)} 字节")
                
                # 记录请求开始时间（用于性能监控）
                if self.request_start_time is None:
                    self.request_start_time = time.time()
                    
        except Exception as e:
            logger.error(f"❌ 发送音频失败: {e}")
            if self.on_error:
                self.on_error(f"发送音频失败: {e}")
    
    async def _listen_for_messages(self):
        """监听WebSocket消息"""
        if websockets is None:
            return
            
        try:
            async for message in self.websocket:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("🔌 WebSocket连接已关闭")
            self.state = ConnectionState.DISCONNECTED
        except Exception as e:
            logger.error(f"❌ 消息监听错误: {e}")
            self.state = ConnectionState.ERROR
            if self.on_error:
                self.on_error(f"消息监听错误: {e}")
    
    async def _handle_message(self, message: str):
        """处理收到的消息"""
        try:
            data = json.loads(message)
            
            # 处理转录结果
            if "channel" in data:
                channel = data["channel"]
                alternatives = channel.get("alternatives", [])
                
                if alternatives:
                    transcript = alternatives[0].get("transcript", "")
                    is_final = not data.get("is_final", True)  # Deepgram的逻辑相反
                    
                    if transcript.strip():
                        # 性能监控
                        if self.request_start_time and is_final:
                            latency = time.time() - self.request_start_time
                            performance_monitor.record_stt_latency(latency)
                            self.request_start_time = None
                            logger.debug(f"STT延迟: {latency:.3f}s")
                        
                        # 调用回调
                        if self.on_transcript:
                            self.on_transcript(transcript, is_final)
                        
                        logger.debug(f"🎤 {'最终' if is_final else '中间'}结果: {transcript}")
            
            # 处理错误消息
            elif "error" in data:
                error_msg = data["error"]
                logger.error(f"❌ Deepgram错误: {error_msg}")
                if self.on_error:
                    self.on_error(f"Deepgram错误: {error_msg}")
            
            # 处理元数据
            elif "metadata" in data:
                metadata = data["metadata"]
                logger.debug(f"📊 元数据: {metadata}")
            
            else:
                logger.debug(f"🔍 未知消息: {data}")
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON解析错误: {e}")
        except Exception as e:
            logger.error(f"❌ 消息处理错误: {e}")
    
    def set_transcript_callback(self, callback: Callable[[str, bool], None]):
        """设置转录回调"""
        self.on_transcript = callback
    
    def set_error_callback(self, callback: Callable[[str], None]):
        """设置错误回调"""
        self.on_error = callback
    
    def set_connection_callbacks(self, 
                               on_connected: Optional[Callable[[], None]] = None,
                               on_disconnected: Optional[Callable[[], None]] = None):
        """设置连接状态回调"""
        self.on_connected = on_connected
        self.on_disconnected = on_disconnected
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.state == ConnectionState.CONNECTED
    
    def get_connection_state(self) -> ConnectionState:
        """获取连接状态"""
        return self.state
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            connected = await self.connect()
            if connected:
                await self.disconnect()
                return True
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
        return False


# 创建默认实例
deepgram_provider = DeepgramSTTProvider() 