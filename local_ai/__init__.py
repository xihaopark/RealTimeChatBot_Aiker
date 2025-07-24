"""
Local AI服务模块
包含本地语音识别(STT)、语音合成(TTS)和大语言模型(LLM)服务
"""

from .audio_converter import AudioConverter
from .local_stt import LocalSTT
from .local_tts import LocalTTS
from .local_llm import LocalLLM

__version__ = "1.0.0"
__all__ = ['AudioConverter', 'LocalSTT', 'LocalTTS', 'LocalLLM']