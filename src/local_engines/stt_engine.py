#!/usr/bin/env python3
"""
本地STT（语音到文本）引擎 - 使用faster-whisper实现
"""

import time
import logging
import numpy as np
from scipy.signal import resample_poly
import faster_whisper
from typing import Optional, Dict, Any

from .base_engine import BaseLocalEngine

class LocalSTTEngine(BaseLocalEngine):
    """
    使用faster-whisper实现本地STT引擎。
    处理流程: μ-law -> 16-bit PCM -> 8kHz to 16kHz resample -> float32 -> transcribe
    """
    
    def __init__(self, model_path: str = "large-v3", config: Optional[Dict[str, Any]] = None):
        """
        初始化STT引擎。
        
        Args:
            model_path: Whisper模型名称或路径。
            config: 包含设备、计算类型等配置的字典。
        """
        # 必须在super().__init__之前定义，因为父类的初始化会调用_load_model
        self.config = config or {}
        self.compute_type = self.config.get("compute_type", "float16")
        self.language_code = self.config.get("language", "zh")
        self.beam_size = self.config.get("beam_size", 5)
        super().__init__(model_path, config)

    def _load_model(self):
        """加载faster-whisper模型"""
        self.logger.info(f"正在加载faster-whisper模型: {self.model_path} (compute_type: {self.compute_type})")
        try:
            return faster_whisper.WhisperModel(
                self.model_path,
                device=self.device,
                compute_type=self.compute_type
            )
        except Exception as e:
            self.logger.error(f"加载模型 {self.model_path} 失败: {e}")
            self.logger.error("请确保模型已下载或路径正确。可以尝试运行: python -c \"from faster_whisper import WhisperModel; WhisperModel('large-v3')\"")
            raise

    def _post_init_setup(self):
        """模型加载后的设置，此处无需额外操作"""
        self.logger.info("LocalSTTEngine初始化完成。")

    def _ulaw_to_pcm(self, ulaw_data: bytes) -> np.ndarray:
        """μ-law解码为16-bit PCM numpy数组，使用numpy实现以提高兼容性"""
        # μ-law expansion table
        EXPAND_1_TABLE = np.array([0, 132, 396, 924, 1980, 4092, 8316, 16764], dtype=np.int16)
        EXPAND_2_TABLE = np.array([0, 1, 2, 3, 4, 5, 6, 7], dtype=np.int16)

        ulaw_bytes = np.frombuffer(ulaw_data, dtype=np.uint8)
        
        sign_bit = (ulaw_bytes < 128)
        exponent = ((ulaw_bytes ^ 128) >> 4) & 0x07
        mantissa = ulaw_bytes & 0x0F
        
        pcm_result = EXPAND_1_TABLE[exponent] + (mantissa << (exponent + 3))
        
        return np.where(sign_bit, -pcm_result, pcm_result)

    def _resample_audio(self, audio: np.ndarray, orig_sr: int = 8000, target_sr: int = 16000) -> np.ndarray:
        """重采样音频到目标采样率"""
        if orig_sr == target_sr:
            return audio
        try:
            num_samples = int(len(audio) * target_sr / orig_sr)
            return resample_poly(audio, target_sr, orig_sr, window=('kaiser', 5.0))[:num_samples]
        except Exception as e:
            self.logger.error(f"重采样失败: {e}")
            return np.array([], dtype=np.float32)

    def process(self, audio_data: bytes) -> str:
        """
        处理完整的STT流程
        """
        if not self.is_initialized:
            self.logger.error("引擎未初始化，无法处理请求。")
            return ""

        start_time = time.time()
        
        # 1. μ-law → PCM
        pcm_audio = self._ulaw_to_pcm(audio_data)
        if pcm_audio.size == 0:
            return ""
        
        # 2. 8kHz → 16kHz
        audio_16k = self._resample_audio(pcm_audio)
        if audio_16k.size == 0:
            return ""
        
        # 3. 归一化为float32
        audio_float = audio_16k.astype(np.float32) / 32768.0
        
        # 4. Whisper推理
        try:
            segments, _ = self.model.transcribe(
                audio_float,
                language=self.language_code,
                beam_size=self.beam_size,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            # 5. 拼接结果
            text = " ".join([seg.text for seg in segments])
            transcribed_text = text.strip()
            
            latency = time.time() - start_time
            self._update_performance_stats(latency)
            self.logger.info(f"转录成功，耗时: {latency:.3f}秒. 结果: '{transcribed_text}'")
            
            return transcribed_text

        except Exception as e:
            self.logger.error(f"Whisper推理失败: {e}")
            return "" 