#!/usr/bin/env python3
"""
适配器的基类
"""
import logging
import time
from typing import Any, Optional, Dict
from abc import ABC, abstractmethod

class BaseAdapter(ABC):
    """基础适配器类"""
    
    def __init__(self, use_local: bool = True, config: Optional[Dict[str, Any]] = None):
        self.use_local = use_local
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 性能监控
        self.performance_stats = {
            "total_requests": 0,
            "local_requests": 0,
            "api_requests": 0,
            "fallback_count": 0,
            "avg_latency": 0.0,
            "error_count": 0
        }
        
        # 初始化引擎
        self._initialize_engines()
    
    @abstractmethod
    def _initialize_engines(self):
        """初始化引擎（子类实现）"""
        pass
    
    @abstractmethod
    def process(self, *args, **kwargs) -> Any:
        """处理请求（子类实现）"""
        pass
    
    def _update_stats(self, is_local: bool, latency: float, success: bool):
        """更新统计信息"""
        self.performance_stats["total_requests"] += 1
        
        if is_local:
            self.performance_stats["local_requests"] += 1
        else:
            self.performance_stats["api_requests"] += 1
        
        if not success:
            self.performance_stats["error_count"] += 1
        
        # 更新平均延迟
        total_requests = self.performance_stats["total_requests"]
        if total_requests > 0:
            current_avg = self.performance_stats["avg_latency"]
            self.performance_stats["avg_latency"] = (
                (current_avg * (total_requests - 1) + latency) / total_requests
            )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.performance_stats.copy()
    
    def reset_performance_stats(self):
        """重置性能统计"""
        self.performance_stats = {
            "total_requests": 0,
            "local_requests": 0,
            "api_requests": 0,
            "fallback_count": 0,
            "avg_latency": 0.0,
            "error_count": 0
        } 