#!/usr/bin/env python3
"""
VTX AI Phone System - ElevenLabs TTS提供商
实现高品质语音合成功能
"""

import asyncio
import aiohttp
import json
import logging
import time
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from ...utils.api_manager import api_manager
from ...utils.performance_monitor import performance_monitor

logger = logging.getLogger(__name__)


@dataclass
class ElevenLabsConfig:
    """ElevenLabs配置"""
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel（英文）
    voice_name: str = "Rachel"               # 语音名称
    model_id: str = "eleven_multilingual_v2" # 多语言模型v2
    stability: float = 0.5                   # 稳定性 (0-1)
    similarity_boost: float = 0.8            # 相似度增强 (0-1)
    style: float = 0.0                       # 风格强度 (0-1)
    use_speaker_boost: bool = True           # 启用说话者增强
    optimize_streaming_latency: int = 1      # 优化流式延迟 (0-4)
    output_format: str = "ulaw_8000"         # 输出格式
    
    def to_voice_settings(self) -> Dict[str, Any]:
        """转换为语音设置"""
        return {
            "stability": self.stability,
            "similarity_boost": self.similarity_boost,
            "style": self.style,
            "use_speaker_boost": self.use_speaker_boost
        }


class VoiceInfo:
    """语音信息"""
    def __init__(self, voice_id: str, name: str, category: str, description: str = ""):
        self.voice_id = voice_id
        self.name = name
        self.category = category
        self.description = description


class ElevenLabsTTSProvider:
    """ElevenLabs TTS提供商"""
    
    # 预定义的中文友好语音
    RECOMMENDED_VOICES = {
        "Rachel": "21m00Tcm4TlvDq8ikWAM",      # 温暖友好的女声
        "Domi": "AZnzlk1XvdvUeBnXmlld",        # 年轻活泼的女声  
        "Bella": "EXAVITQu4vr4xnSDxMaL",       # 柔和的女声
        "Antoni": "ErXwobaYiN019PkySvjV",      # 温和的男声
        "Elli": "MF3mGyEYCl7XYWbV9V6O",       # 情感丰富的女声
        "Josh": "TxGEqnHWrfWFTfGW9XjX",       # 专业的男声
        "Arnold": "VR6AewLTigWG4xSOukaG",     # 成熟的男声
        "Sam": "yoZ06aMxZJJ28mfd3POQ"          # 清晰的男声
    }
    
    def __init__(self, config: Optional[ElevenLabsConfig] = None):
        self.config = config or ElevenLabsConfig()
        self.api_key = api_manager.get_key('elevenlabs')
        
        if not self.api_key:
            raise ValueError("ElevenLabs API密钥未配置")
        
        self.base_url = "https://api.elevenlabs.io/v1"
        self.session = None
        
        # 回调函数
        self.on_audio_ready: Optional[Callable[[bytes, str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 语音缓存
        self.available_voices = {}
        
        logger.info(f"🔊 ElevenLabs TTS提供商初始化")
        logger.info(f"   语音: {self.config.voice_name}")
        logger.info(f"   模型: {self.config.model_id}")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
    
    async def synthesize(self, text: str, voice_id: Optional[str] = None) -> Optional[bytes]:
        """合成语音"""
        if not text.strip():
            logger.warning("⚠️ 文本为空，跳过合成")
            return None
        
        voice_id = voice_id or self.config.voice_id
        if not voice_id:
            logger.error("❌ 语音ID未配置")
            return None
            
        start_time = time.time()
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.base_url}/text-to-speech/{voice_id}"
            
            payload = {
                "text": text,
                "model_id": self.config.model_id,
                "voice_settings": self.config.to_voice_settings()
            }
            
            # 添加流式优化参数
            if hasattr(self.config, 'optimize_streaming_latency'):
                payload["optimize_streaming_latency"] = self.config.optimize_streaming_latency
            
            logger.info(f"🔊 开始合成: {text[:50]}...")
            
            async with self.session.post(
                url, 
                headers=self._get_headers(),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    audio_data = await response.read()
                    
                    # 性能监控
                    latency = time.time() - start_time
                    performance_monitor.record_tts_latency(latency)
                    
                    logger.info(f"✅ 合成完成: {len(audio_data)} 字节, 耗时 {latency:.3f}s")
                    
                    # 转换音频格式
                    processed_audio = await self._process_audio(audio_data)
                    
                    # 调用回调
                    if self.on_audio_ready:
                        self.on_audio_ready(processed_audio, text)
                    
                    return processed_audio
                
                else:
                    error_text = await response.text()
                    error_msg = f"ElevenLabs API错误 {response.status}: {error_text}"
                    logger.error(f"❌ {error_msg}")
                    
                    if self.on_error:
                        self.on_error(error_msg)
                    
                    return None
                    
        except asyncio.TimeoutError:
            error_msg = "合成超时"
            logger.error(f"❌ {error_msg}")
            if self.on_error:
                self.on_error(error_msg)
            return None
            
        except Exception as e:
            error_msg = f"合成失败: {e}"
            logger.error(f"❌ {error_msg}")
            if self.on_error:
                self.on_error(error_msg)
            return None
    
    async def _process_audio(self, audio_data: bytes) -> bytes:
        """处理音频数据"""
        try:
            # ElevenLabs默认返回MP3格式
            # 需要转换为μ-law格式以适配SIP协议
            
            # 这里需要使用音频转换工具
            # 暂时返回原始数据，后续会在音频工具中处理
            return audio_data
            
        except Exception as e:
            logger.error(f"❌ 音频处理失败: {e}")
            return audio_data
    
    async def get_available_voices(self) -> List[VoiceInfo]:
        """获取可用语音列表"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.base_url}/voices"
            
            async with self.session.get(
                url,
                headers={"xi-api-key": self.api_key}
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    voices = []
                    
                    for voice in data.get("voices", []):
                        voice_info = VoiceInfo(
                            voice_id=voice["voice_id"],
                            name=voice["name"],
                            category=voice.get("category", "unknown"),
                            description=voice.get("description", "")
                        )
                        voices.append(voice_info)
                        self.available_voices[voice["name"]] = voice["voice_id"]
                    
                    logger.info(f"✅ 获取到 {len(voices)} 个可用语音")
                    return voices
                
                else:
                    logger.error(f"❌ 获取语音列表失败: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"❌ 获取语音列表错误: {e}")
            return []
    
    async def set_voice_by_name(self, voice_name: str) -> bool:
        """通过名称设置语音"""
        # 首先检查预定义语音
        if voice_name in self.RECOMMENDED_VOICES:
            self.config.voice_id = self.RECOMMENDED_VOICES[voice_name]
            self.config.voice_name = voice_name
            logger.info(f"🔊 切换语音: {voice_name}")
            return True
        
        # 如果不在预定义中，尝试从API获取
        if not self.available_voices:
            await self.get_available_voices()
        
        if voice_name in self.available_voices:
            self.config.voice_id = self.available_voices[voice_name]
            self.config.voice_name = voice_name
            logger.info(f"🔊 切换语音: {voice_name}")
            return True
        
        logger.warning(f"⚠️ 未找到语音: {voice_name}")
        return False
    
    def get_recommended_voices(self) -> Dict[str, str]:
        """获取推荐的语音列表"""
        return self.RECOMMENDED_VOICES.copy()
    
    async def test_synthesis(self, test_text: str = "你好，这是语音合成测试。") -> bool:
        """测试语音合成"""
        try:
            result = await self.synthesize(test_text)
            return result is not None
        except Exception as e:
            logger.error(f"语音合成测试失败: {e}")
            return False
    
    def set_audio_callback(self, callback: Callable[[bytes, str], None]):
        """设置音频就绪回调"""
        self.on_audio_ready = callback
    
    def set_error_callback(self, callback: Callable[[str], None]):
        """设置错误回调"""
        self.on_error = callback
    
    def update_voice_settings(self, 
                            stability: Optional[float] = None,
                            similarity_boost: Optional[float] = None,
                            style: Optional[float] = None):
        """更新语音设置"""
        if stability is not None:
            self.config.stability = max(0.0, min(1.0, stability))
        if similarity_boost is not None:
            self.config.similarity_boost = max(0.0, min(1.0, similarity_boost))
        if style is not None:
            self.config.style = max(0.0, min(1.0, style))
        
        logger.info(f"🔊 语音设置已更新")
        logger.info(f"   稳定性: {self.config.stability}")
        logger.info(f"   相似度: {self.config.similarity_boost}")
        logger.info(f"   风格: {self.config.style}")


# 创建默认实例
elevenlabs_provider = ElevenLabsTTSProvider() 