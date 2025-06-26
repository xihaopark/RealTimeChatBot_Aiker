#!/usr/bin/env python3
"""
VTX AI Phone System - 流式STT引擎
整合Deepgram和本地Whisper，提供智能回退机制
"""

import asyncio
import time
import logging
import queue
import threading
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import numpy as np

from ..providers.deepgram_provider import DeepgramSTTProvider, DeepgramConfig
from ...utils.performance_monitor import performance_monitor
from ...utils.audio_utils import AudioUtils

logger = logging.getLogger(__name__)


class STTState(Enum):
    """STT引擎状态"""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    ERROR = "error"


class STTProvider(Enum):
    """STT提供商"""
    DEEPGRAM = "deepgram"
    WHISPER_LOCAL = "whisper_local"


@dataclass
class StreamingSTTConfig:
    """流式STT配置"""
    primary_provider: STTProvider = STTProvider.DEEPGRAM
    fallback_provider: STTProvider = STTProvider.WHISPER_LOCAL
    auto_fallback: bool = True
    max_retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # 音频缓冲配置
    chunk_size: int = 160          # 20ms @ 8kHz
    buffer_duration: float = 2.0   # 2秒缓冲
    silence_threshold: float = 0.01
    min_speech_duration: float = 0.5
    
    # 性能配置
    target_latency: float = 0.8    # 目标延迟800ms
    enable_interim_results: bool = True
    
    # Deepgram特定配置
    deepgram_config: Optional[DeepgramConfig] = None


class AudioBuffer:
    """音频缓冲管理器"""
    
    def __init__(self, max_duration: float = 5.0, sample_rate: int = 8000):
        self.max_duration = max_duration
        self.sample_rate = sample_rate
        self.max_samples = int(max_duration * sample_rate)
        
        self.buffer = np.array([], dtype=np.int16)
        self.lock = threading.Lock()
        
    def add_audio(self, audio_data: bytes):
        """添加音频数据"""
        with self.lock:
            # 转换为numpy数组
            if isinstance(audio_data, bytes):
                # 假设是μ-law编码，先解码
                pcm_data = AudioUtils().ulaw_decode(audio_data)
                audio_array = np.frombuffer(pcm_data, dtype=np.int16)
            else:
                audio_array = np.array(audio_data, dtype=np.int16)
            
            # 添加到缓冲区
            self.buffer = np.concatenate([self.buffer, audio_array])
            
            # 限制缓冲区大小
            if len(self.buffer) > self.max_samples:
                excess = len(self.buffer) - self.max_samples
                self.buffer = self.buffer[excess:]
    
    def get_audio(self, duration: Optional[float] = None) -> Optional[bytes]:
        """获取音频数据"""
        with self.lock:
            if len(self.buffer) == 0:
                return None
            
            if duration:
                samples_needed = int(duration * self.sample_rate)
                if len(self.buffer) >= samples_needed:
                    # 获取指定时长的音频
                    audio_chunk = self.buffer[:samples_needed]
                    self.buffer = self.buffer[samples_needed:]
                    return audio_chunk.tobytes()
                else:
                    return None
            else:
                # 获取所有音频
                audio_data = self.buffer.tobytes()
                self.buffer = np.array([], dtype=np.int16)
                return audio_data
    
    def clear(self):
        """清空缓冲区"""
        with self.lock:
            self.buffer = np.array([], dtype=np.int16)
    
    def get_duration(self) -> float:
        """获取缓冲区音频时长"""
        with self.lock:
            return len(self.buffer) / self.sample_rate
    
    def has_speech(self, threshold: float = 0.01) -> bool:
        """检测是否包含语音"""
        with self.lock:
            if len(self.buffer) == 0:
                return False
            
            # 计算RMS能量
            audio_float = self.buffer.astype(np.float32) / 32768.0
            rms = np.sqrt(np.mean(audio_float ** 2))
            
            return rms > threshold


class StreamingSTTEngine:
    """流式STT引擎"""
    
    def __init__(self, config: Optional[StreamingSTTConfig] = None):
        self.config = config or StreamingSTTConfig()
        
        # 初始化提供商
        self.deepgram_provider = None
        self.whisper_provider = None
        
        # 状态管理
        self.state = STTState.IDLE
        self.current_provider = self.config.primary_provider
        self.retry_count = 0
        
        # 音频管理
        self.audio_buffer = AudioBuffer(
            max_duration=self.config.buffer_duration * 2
        )
        self.processing_queue = queue.Queue()
        
        # 回调函数
        self.on_transcript: Optional[Callable[[str, bool], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_state_change: Optional[Callable[[STTState], None]] = None
        
        # 线程管理
        self.processing_thread = None
        self.running = False
        
        logger.info(f"🎤 流式STT引擎初始化")
        logger.info(f"   主要提供商: {self.config.primary_provider.value}")
        logger.info(f"   备用提供商: {self.config.fallback_provider.value}")
    
    async def start(self):
        """启动STT引擎"""
        if self.running:
            return
        
        try:
            # 初始化提供商
            await self._initialize_providers()
            
            # 启动处理线程
            self.running = True
            self.processing_thread = threading.Thread(
                target=self._processing_loop, 
                daemon=True
            )
            self.processing_thread.start()
            
            # 连接到主要提供商
            await self._connect_to_provider(self.config.primary_provider)
            
            self._set_state(STTState.LISTENING)
            logger.info("✅ 流式STT引擎已启动")
            
        except Exception as e:
            logger.error(f"❌ STT引擎启动失败: {e}")
            await self._handle_error(f"启动失败: {e}")
    
    async def stop(self):
        """停止STT引擎"""
        logger.info("🛑 正在停止STT引擎...")
        
        self.running = False
        
        # 断开提供商连接
        if self.deepgram_provider:
            await self.deepgram_provider.disconnect()
        
        # 等待处理线程结束
        if self.processing_thread:
            self.processing_thread.join(timeout=2)
        
        self._set_state(STTState.IDLE)
        logger.info("✅ STT引擎已停止")
    
    async def _initialize_providers(self):
        """初始化提供商"""
        # 初始化Deepgram提供商
        if self.config.primary_provider == STTProvider.DEEPGRAM or \
           self.config.fallback_provider == STTProvider.DEEPGRAM:
            
            deepgram_config = self.config.deepgram_config or DeepgramConfig()
            self.deepgram_provider = DeepgramSTTProvider(deepgram_config)
            
            # 设置回调
            self.deepgram_provider.set_transcript_callback(self._on_deepgram_transcript)
            self.deepgram_provider.set_error_callback(self._on_deepgram_error)
        
        # 初始化Whisper提供商
        if self.config.primary_provider == STTProvider.WHISPER_LOCAL or \
           self.config.fallback_provider == STTProvider.WHISPER_LOCAL:
            
            # TODO: 实现本地Whisper提供商
            logger.info("🎤 本地Whisper提供商暂未实现")
    
    async def _connect_to_provider(self, provider: STTProvider):
        """连接到指定提供商"""
        if provider == STTProvider.DEEPGRAM and self.deepgram_provider:
            success = await self.deepgram_provider.connect()
            if not success:
                raise Exception("Deepgram连接失败")
        elif provider == STTProvider.WHISPER_LOCAL:
            # TODO: 连接本地Whisper
            pass
        else:
            raise Exception(f"未知提供商: {provider}")
    
    def add_audio(self, audio_data: bytes):
        """添加音频数据"""
        if self.state != STTState.LISTENING:
            return
        
        # 添加到缓冲区
        self.audio_buffer.add_audio(audio_data)
        
        # 添加到处理队列
        self.processing_queue.put(audio_data)
    
    def _processing_loop(self):
        """音频处理循环"""
        logger.info("🔄 音频处理循环已启动")
        
        while self.running:
            try:
                # 从队列获取音频数据
                audio_data = self.processing_queue.get(timeout=0.1)
                
                if self.state == STTState.LISTENING:
                    # 发送到当前提供商
                    asyncio.run(self._send_to_current_provider(audio_data))
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"❌ 音频处理错误: {e}")
    
    async def _send_to_current_provider(self, audio_data: bytes):
        """发送音频到当前提供商"""
        try:
            if self.current_provider == STTProvider.DEEPGRAM and self.deepgram_provider:
                if self.deepgram_provider.is_connected():
                    await self.deepgram_provider.send_audio(audio_data)
                else:
                    logger.warning("⚠️ Deepgram未连接，尝试重连")
                    await self._handle_provider_error("Deepgram连接断开")
            
            elif self.current_provider == STTProvider.WHISPER_LOCAL:
                # TODO: 发送到本地Whisper
                pass
                
        except Exception as e:
            logger.error(f"❌ 发送音频失败: {e}")
            await self._handle_provider_error(f"发送音频失败: {e}")
    
    def _on_deepgram_transcript(self, transcript: str, is_final: bool):
        """Deepgram转录回调"""
        logger.debug(f"🎤 Deepgram: {'最终' if is_final else '中间'}: {transcript}")
        
        if self.on_transcript:
            self.on_transcript(transcript, is_final)
    
    def _on_deepgram_error(self, error: str):
        """Deepgram错误回调"""
        logger.error(f"❌ Deepgram错误: {error}")
        asyncio.create_task(self._handle_provider_error(error))
    
    async def _handle_provider_error(self, error: str):
        """处理提供商错误"""
        self.retry_count += 1
        
        if self.retry_count <= self.config.max_retry_attempts:
            logger.warning(f"⚠️ 提供商错误，尝试重连 ({self.retry_count}/{self.config.max_retry_attempts})")
            
            # 等待一段时间后重试
            await asyncio.sleep(self.config.retry_delay)
            
            try:
                await self._connect_to_provider(self.current_provider)
                logger.info("✅ 重连成功")
                self.retry_count = 0
                return
            except Exception as e:
                logger.error(f"❌ 重连失败: {e}")
        
        # 如果重试失败且启用了回退
        if self.config.auto_fallback and self.retry_count > self.config.max_retry_attempts:
            await self._fallback_to_secondary()
        else:
            await self._handle_error(f"提供商错误: {error}")
    
    async def _fallback_to_secondary(self):
        """回退到备用提供商"""
        if self.current_provider == self.config.primary_provider:
            logger.warning("🔄 切换到备用提供商")
            self.current_provider = self.config.fallback_provider
            self.retry_count = 0
            
            try:
                await self._connect_to_provider(self.current_provider)
                logger.info(f"✅ 已切换到 {self.current_provider.value}")
            except Exception as e:
                await self._handle_error(f"备用提供商连接失败: {e}")
        else:
            await self._handle_error("所有提供商都不可用")
    
    async def _handle_error(self, error: str):
        """处理错误"""
        logger.error(f"❌ STT引擎错误: {error}")
        self._set_state(STTState.ERROR)
        
        if self.on_error:
            self.on_error(error)
    
    def _set_state(self, new_state: STTState):
        """设置状态"""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            
            logger.debug(f"📍 STT状态: {old_state.value} -> {new_state.value}")
            
            if self.on_state_change:
                self.on_state_change(new_state)
    
    def set_transcript_callback(self, callback: Callable[[str, bool], None]):
        """设置转录回调"""
        self.on_transcript = callback
    
    def set_error_callback(self, callback: Callable[[str], None]):
        """设置错误回调"""
        self.on_error = callback
    
    def set_state_callback(self, callback: Callable[[STTState], None]):
        """设置状态变化回调"""
        self.on_state_change = callback
    
    def get_current_provider(self) -> STTProvider:
        """获取当前提供商"""
        return self.current_provider
    
    def get_state(self) -> STTState:
        """获取当前状态"""
        return self.state
    
    def get_buffer_duration(self) -> float:
        """获取缓冲区时长"""
        return self.audio_buffer.get_duration()
    
    async def force_fallback(self):
        """强制切换到备用提供商"""
        logger.info("🔄 强制切换到备用提供商")
        await self._fallback_to_secondary()


# 创建默认实例
streaming_stt_engine = StreamingSTTEngine() 