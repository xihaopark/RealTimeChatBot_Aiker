#!/usr/bin/env python3
"""
VTX AI Phone System - 增强对话配置
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class ConversationState(Enum):
    """对话状态枚举"""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ENDED = "ended"


@dataclass
class EnhancedConversationConfig:
    """增强对话配置"""
    
    # 基础配置
    target_latency: float = 0.8  # 目标延迟800ms（保守目标）
    enable_streaming: bool = True
    enable_local_fallback: bool = True
    
    # STT配置
    stt_primary: str = "deepgram"
    stt_fallback: str = "whisper_local"
    stt_language: str = "zh-CN"
    stt_model: str = "nova-2"  # Deepgram模型
    
    # TTS配置  
    tts_primary: str = "elevenlabs"
    tts_fallback: str = "edge_tts"
    tts_voice: str = "zh-CN-XiaoxiaoNeural"  # 默认中文
    tts_model: str = "eleven_multilingual_v2"  # ElevenLabs模型
    
    # LLM配置
    llm_primary: str = "gpt-4o-mini"
    llm_fallback: str = "gpt-3.5-turbo"
    llm_max_tokens: int = 150
    llm_temperature: float = 0.7
    
    # 性能配置
    audio_chunk_size: int = 160    # 20ms @ 8kHz
    buffer_size: int = 5           # 5个chunk缓冲
    max_silence_ms: int = 2000     # 2秒静音检测
    sample_rate: int = 8000        # 音频采样率
    
    # 音频配置
    audio_format: str = "ulaw"     # μ-law编码
    channels: int = 1              # 单声道
    
    # 系统配置
    target_extension: str = "101"  # 目标分机
    enable_debug: bool = True      # 启用调试模式
    log_level: str = "INFO"        # 日志级别
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "target_latency": self.target_latency,
            "enable_streaming": self.enable_streaming,
            "enable_local_fallback": self.enable_local_fallback,
            "stt_primary": self.stt_primary,
            "stt_fallback": self.stt_fallback,
            "stt_language": self.stt_language,
            "stt_model": self.stt_model,
            "tts_primary": self.tts_primary,
            "tts_fallback": self.tts_fallback,
            "tts_voice": self.tts_voice,
            "tts_model": self.tts_model,
            "llm_primary": self.llm_primary,
            "llm_fallback": self.llm_fallback,
            "llm_max_tokens": self.llm_max_tokens,
            "llm_temperature": self.llm_temperature,
            "audio_chunk_size": self.audio_chunk_size,
            "buffer_size": self.buffer_size,
            "max_silence_ms": self.max_silence_ms,
            "sample_rate": self.sample_rate,
            "audio_format": self.audio_format,
            "channels": self.channels,
            "target_extension": self.target_extension,
            "enable_debug": self.enable_debug,
            "log_level": self.log_level
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnhancedConversationConfig':
        """从字典创建配置"""
        return cls(**data)


# 默认配置实例
default_config = EnhancedConversationConfig()


# 系统提示词配置
SYSTEM_PROMPTS = {
    "客服": """你是一个专业的AI电话客服助手。
请遵循以下规则：
1. 回答要简洁明了，适合电话对话
2. 每次回复控制在1-2句话以内
3. 语言要自然流畅，像真人对话
4. 如遇不明白的问题，礼貌询问
5. 保持友好专业的态度
6. 使用中文回复""",
    
    "助手": """你是一个友好的AI电话助手。
请遵循以下规则：
1. 回答要简洁明了，适合电话对话
2. 每次回复控制在1-2句话以内
3. 语言要自然流畅，像真人对话
4. 如遇不明白的问题，礼貌询问
5. 保持友好专业的态度
6. 使用中文回复""",
    
    "测试": """你是一个测试用的AI助手。
请简单回复："您好，我是AI助手，正在测试中。"
然后等待用户的下一个指令。"""
} 