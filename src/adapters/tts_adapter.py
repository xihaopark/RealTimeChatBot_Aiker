#!/usr/bin/env python3
"""
TTS适配器
"""
from .base_adapter import BaseAdapter
from ..local_engines.tts_engine import LocalTTSEngine

class TTSAdapter(BaseAdapter):
    def _initialize_engines(self):
        """初始化TTS引擎"""
        self.local_engine = None
        if self.use_local:
            try:
                self.local_engine = LocalTTSEngine(
                    model_path=self.config.get("model", "default_tts_model"),
                    config=self.config
                )
                self.local_engine.initialize()
            except Exception as e:
                self.logger.error(f"本地TTS引擎初始化失败: {e}")
        
        # TODO: 初始化API引擎作为备用

    def process(self, text: str) -> bytes:
        """
        处理TTS请求，自动回退到API（如果配置）
        """
        if self.use_local and self.local_engine:
            return self.local_engine.process(text)
        else:
            # TODO: 实现API回退逻辑
            self.logger.warning("本地TTS引擎不可用，回退到API（未实现）")
            return "API TTS引擎合成的音频".encode('utf-8') 