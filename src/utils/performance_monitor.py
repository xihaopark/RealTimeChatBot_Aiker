#!/usr/bin/env python3
"""
VTX AI Phone System - 性能监控工具
"""

import time
import statistics
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    response_times: List[float] = field(default_factory=list)
    stt_latency: List[float] = field(default_factory=list)
    tts_latency: List[float] = field(default_factory=list)
    llm_latency: List[float] = field(default_factory=list)
    error_count: int = 0
    total_requests: int = 0
    start_time: float = field(default_factory=time.time)
    
    def add_response_time(self, response_time: float):
        """添加响应时间"""
        self.response_times.append(response_time)
        self.total_requests += 1
    
    def add_stt_latency(self, latency: float):
        """添加STT延迟"""
        self.stt_latency.append(latency)
    
    def add_tts_latency(self, latency: float):
        """添加TTS延迟"""
        self.tts_latency.append(latency)
    
    def add_llm_latency(self, latency: float):
        """添加LLM延迟"""
        self.llm_latency.append(latency)
    
    def increment_error(self):
        """增加错误计数"""
        self.error_count += 1
    
    def get_stats(self) -> Dict[str, float]:
        """获取统计信息"""
        stats = {
            'total_requests': self.total_requests,
            'error_count': self.error_count,
            'error_rate': self.error_count / max(self.total_requests, 1),
            'uptime': time.time() - self.start_time
        }
        
        if self.response_times:
            stats.update({
                'avg_response_time': statistics.mean(self.response_times),
                'min_response_time': min(self.response_times),
                'max_response_time': max(self.response_times),
                'median_response_time': statistics.median(self.response_times)
            })
        
        if self.stt_latency:
            stats['avg_stt_latency'] = statistics.mean(self.stt_latency)
        
        if self.tts_latency:
            stats['avg_tts_latency'] = statistics.mean(self.tts_latency)
        
        if self.llm_latency:
            stats['avg_llm_latency'] = statistics.mean(self.llm_latency)
        
        return stats


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, max_history: int = 1000):
        self.metrics = PerformanceMetrics()
        self.max_history = max_history
        self.recent_response_times = deque(maxlen=max_history)
        self.target_latency = 0.8  # 目标延迟800ms
        
    def record_response_time(self, response_time: float):
        """记录响应时间"""
        self.metrics.add_response_time(response_time)
        self.recent_response_times.append(response_time)
        
        # 检查是否超过目标延迟
        if response_time > self.target_latency:
            logger.warning(f"⚠️ 响应时间 {response_time:.2f}s 超过目标 {self.target_latency}s")
    
    def record_stt_latency(self, latency: float):
        """记录STT延迟"""
        self.metrics.add_stt_latency(latency)
    
    def record_tts_latency(self, latency: float):
        """记录TTS延迟"""
        self.metrics.add_tts_latency(latency)
    
    def record_llm_latency(self, latency: float):
        """记录LLM延迟"""
        self.metrics.add_llm_latency(latency)
    
    def record_error(self):
        """记录错误"""
        self.metrics.increment_error()
    
    def get_current_stats(self) -> Dict[str, float]:
        """获取当前统计信息"""
        return self.metrics.get_stats()
    
    def get_recent_performance(self, window_size: int = 10) -> Dict[str, float]:
        """获取最近的性能指标"""
        if len(self.recent_response_times) < window_size:
            return {}
        
        recent_times = list(self.recent_response_times)[-window_size:]
        
        return {
            'recent_avg_response_time': statistics.mean(recent_times),
            'recent_min_response_time': min(recent_times),
            'recent_max_response_time': max(recent_times),
            'recent_median_response_time': statistics.median(recent_times)
        }
    
    def is_performance_acceptable(self) -> bool:
        """检查性能是否可接受"""
        if not self.recent_response_times:
            return True
        
        recent_avg = statistics.mean(list(self.recent_response_times)[-10:])
        return recent_avg <= self.target_latency
    
    def print_performance_report(self):
        """打印性能报告"""
        stats = self.get_current_stats()
        recent_stats = self.get_recent_performance()
        
        print("\n📊 性能监控报告")
        print("=" * 60)
        print(f"总请求数: {stats.get('total_requests', 0)}")
        print(f"错误数: {stats.get('error_count', 0)}")
        print(f"错误率: {stats.get('error_rate', 0):.2%}")
        print(f"运行时间: {stats.get('uptime', 0):.1f}秒")
        
        if 'avg_response_time' in stats:
            print(f"\n响应时间统计:")
            print(f"  平均: {stats['avg_response_time']:.3f}s")
            print(f"  中位数: {stats['median_response_time']:.3f}s")
            print(f"  最小: {stats['min_response_time']:.3f}s")
            print(f"  最大: {stats['max_response_time']:.3f}s")
        
        if 'avg_stt_latency' in stats:
            print(f"STT平均延迟: {stats['avg_stt_latency']:.3f}s")
        
        if 'avg_tts_latency' in stats:
            print(f"TTS平均延迟: {stats['avg_tts_latency']:.3f}s")
        
        if 'avg_llm_latency' in stats:
            print(f"LLM平均延迟: {stats['avg_llm_latency']:.3f}s")
        
        if recent_stats:
            print(f"\n最近10次响应时间:")
            print(f"  平均: {recent_stats['recent_avg_response_time']:.3f}s")
            print(f"  中位数: {recent_stats['recent_median_response_time']:.3f}s")
        
        # 性能评估
        if self.is_performance_acceptable():
            print(f"\n✅ 性能状态: 良好 (目标: <{self.target_latency}s)")
        else:
            print(f"\n⚠️ 性能状态: 需要优化 (目标: <{self.target_latency}s)")
        
        print("=" * 60)
    
    def reset(self):
        """重置监控数据"""
        self.metrics = PerformanceMetrics()
        self.recent_response_times.clear()
        logger.info("性能监控数据已重置")
    
    def export_metrics(self) -> Dict:
        """导出性能指标"""
        return {
            'metrics': self.metrics.__dict__,
            'recent_performance': self.get_recent_performance(),
            'performance_acceptable': self.is_performance_acceptable(),
            'target_latency': self.target_latency
        }


# 全局性能监控器实例
performance_monitor = PerformanceMonitor() 