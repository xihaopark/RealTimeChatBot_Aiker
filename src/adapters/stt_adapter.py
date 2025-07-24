"""STT适配器 - 支持本地/API模式切换"""

import time
import logging
from typing import Optional, Dict, Any
import requests

from .base_adapter import BaseAdapter
from ..local_engines.stt_engine import LocalSTTEngine


class STTAdapter(BaseAdapter):
    """语音识别适配器，支持本地Whisper和Deepgram API"""

    def __init__(self, use_local: bool = True, config: Optional[Dict[str, Any]] = None):
        super().__init__(use_local, config)
        self.logger = logging.getLogger(__name__)
        
        # API配置（从config或环境变量加载）
        self.deepgram_api_key = self.config.get("deepgram_api_key", "")
        self.api_url = "https://api.deepgram.com/v1/listen"

    def _initialize_engines(self):
        """根据配置初始化引擎"""
        self.local_engine = None
        if self.use_local:
            try:
                self.local_engine = LocalSTTEngine(
                    model_path=self.config.get("model_path", "large-v3"),
                    config=self.config
                )
            except Exception as e:
                self.logger.error(f"本地STT引擎初始化失败: {e}。如果配置了API密钥，将尝试回退。")
    
    def process(self, audio_data: bytes) -> str:
        """
        处理音频数据，返回识别的文本。
        如果本地引擎失败，并且配置了API密钥，则会自动回退。
        """
        start_time = time.time()
        
        # 优先使用本地引擎
        if self.use_local and self.local_engine and self.local_engine.is_initialized:
            try:
                result = self.local_engine.process(audio_data)
                self._log_performance(start_time, "本地", len(result))
                return result
            except Exception as e:
                self.logger.error(f"本地STT处理失败: {e}。尝试回退到API。")
                self.performance_stats["fallback_count"] += 1

        # 回退或直接使用API
        if self.deepgram_api_key:
            try:
                result = self._process_api(audio_data)
                self._log_performance(start_time, "API", len(result))
                return result
            except Exception as api_error:
                self.logger.error(f"API STT处理也失败: {api_error}")
        else:
            self.logger.error("STT处理失败，且未配置API回退。")
            
        return ""

    def _process_api(self, audio_data: bytes) -> str:
        """使用Deepgram API处理"""
        headers = {
            "Authorization": f"Token {self.deepgram_api_key}",
            "Content-Type": "audio/mulaw"
        }
        params = {
            "model": "nova-2", "language": "zh-CN",
            "encoding": "mulaw", "sample_rate": 8000,
            "punctuate": "true", "utterances": "true",
            "endpointing": "500", "smart_format": "true"
        }
        
        response = requests.post(self.api_url, headers=headers, params=params, data=audio_data, timeout=10)
        response.raise_for_status() # Will raise an exception for 4xx/5xx status
        
        data = response.json()
        transcript = data.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
        return transcript.strip()

    def _log_performance(self, start_time: float, mode: str, result_len: int):
        """记录性能日志"""
        latency = (time.time() - start_time) * 1000
        self.logger.info(f"STT处理完成 - 模式: {mode}, 延迟: {latency:.0f}ms, 文本长度: {result_len}")
        self._update_stats(is_local=(mode=="本地"), latency=latency/1000, success=True) 