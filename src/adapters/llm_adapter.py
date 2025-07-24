#!/usr/bin/env python3
"""
LLM适配器
"""
from typing import List, Dict
from .base_adapter import BaseAdapter
from ..local_engines.llm_engine import LocalLLMEngine

class LLMAdapter(BaseAdapter):
    def _initialize_engines(self):
        """初始化LLM引擎"""
        self.local_engine = None
        if self.use_local:
            try:
                self.local_engine = LocalLLMEngine(
                    model_path=self.config.get("model", "default_llm_model"),
                    config=self.config
                )
                self.local_engine.initialize()
            except Exception as e:
                self.logger.error(f"本地LLM引擎初始化失败: {e}")
        
        # TODO: 初始化API引擎作为备用

    def process(self, prompt: str, history: List[Dict[str, str]]) -> str:
        """
        处理LLM请求，自动回退到API（如果配置）
        """
        if self.use_local and self.local_engine:
            return self.local_engine.process(prompt, history)
        else:
            # TODO: 实现API回退逻辑
            self.logger.warning("本地LLM引擎不可用，回退到API（未实现）")
            return "API LLM引擎生成的回复（占位符）" 