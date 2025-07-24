#!/usr/bin/env python3
"""
本地AI引擎的基类
"""

import os
import time
import logging
import threading
from typing import Any, Optional, Dict, List
from abc import ABC, abstractmethod

class BaseLocalEngine(ABC):
    """本地引擎基类"""
    
    def __init__(self, model_path: str, config: Optional[Dict[str, Any]] = None):
        self.model_path = model_path
        self.config = config or {}
        self.logger = logging.getLogger(f"LocalEngine.{self.__class__.__name__}")
        self.device = self._select_device()
        self.model = None
        self.is_initialized = False
        
        # 性能监控
        self.performance_stats = {
            "total_requests": 0,
            "total_time": 0.0,
            "avg_latency": 0.0,
            "max_latency": 0.0,
            "min_latency": float('inf')
        }
        
        self.initialize()  # 自动初始化模型
        
    def initialize(self):
        """初始化引擎"""
        if self.is_initialized:
            return
            
        start_time = time.time()
        self.logger.info(f"正在初始化{self.__class__.__name__}...")
        
        try:
            self.model = self._load_model()
            self._post_init_setup()
            self.is_initialized = True
            
            init_time = time.time() - start_time
            self.logger.info(f"引擎初始化完成，耗时: {init_time:.2f}秒")
            
        except Exception as e:
            self.logger.error(f"引擎初始化失败: {e}")
            raise
    
    @abstractmethod
    def _load_model(self):
        """加载模型（子类实现）"""
        pass
    
    @abstractmethod
    def _post_init_setup(self):
        """初始化后的设置（子类实现）"""
        pass
    
    @abstractmethod
    def process(self, input_data: Any) -> Any:
        """处理输入数据（子类实现）"""
        pass
    
    def _select_device(self) -> str:
        """选择计算设备"""
        try:
            import torch
            if torch.cuda.is_available():
                device = "cuda"
                self.logger.info(f"使用GPU: {torch.cuda.get_device_name()}")
            else:
                device = "cpu"
                self.logger.info("使用CPU")
            return device
        except ImportError:
            self.logger.info("PyTorch未安装，使用CPU")
            return "cpu"
    
    def _update_performance_stats(self, latency: float):
        """更新性能统计"""
        self.performance_stats["total_requests"] += 1
        self.performance_stats["total_time"] += latency
        self.performance_stats["avg_latency"] = (
            self.performance_stats["total_time"] / self.performance_stats["total_requests"]
        )
        self.performance_stats["max_latency"] = max(
            self.performance_stats["max_latency"], latency
        )
        self.performance_stats["min_latency"] = min(
            self.performance_stats["min_latency"], latency
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.performance_stats.copy()
    
    def reset_performance_stats(self):
        """重置性能统计"""
        self.performance_stats = {
            "total_requests": 0,
            "total_time": 0.0,
            "avg_latency": 0.0,
            "max_latency": 0.0,
            "min_latency": float('inf')
        } 