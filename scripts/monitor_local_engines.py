#!/usr/bin/env python3
"""实时监控本地引擎性能"""

import time
import psutil
import threading

try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    
try:
    from prometheus_client import start_http_server, Gauge
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# --- Prometheus Metrics Initialization ---
if PROMETHEUS_AVAILABLE:
    gpu_usage = Gauge('gpu_usage_percent', 'GPU usage percentage')
    gpu_memory = Gauge('gpu_memory_mb', 'GPU memory usage in MB')
    stt_latency = Gauge('stt_latency_ms', 'STT processing latency')
    tts_latency = Gauge('tts_latency_ms', 'TTS processing latency')
    llm_latency = Gauge('llm_latency_ms', 'LLM processing latency')
else:
    # Define dummy Gauge if prometheus_client is not available
    class DummyGauge:
        def set(self, value): pass
    gpu_usage = gpu_memory = stt_latency = tts_latency = llm_latency = DummyGauge()
# -----------------------------------------

def monitor_gpu():
    """监控GPU使用情况"""
    if not GPU_AVAILABLE:
        print("⚠️ 'GPUtil' not installed. Cannot monitor GPU.")
        return
        
    while True:
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                gpu_usage.set(gpu.load * 100)
                gpu_memory.set(gpu.memoryUsed)
            else:
                gpu_usage.set(0)
                gpu_memory.set(0)
        except Exception as e:
            print(f"Error monitoring GPU: {e}")
            gpu_usage.set(-1)
            gpu_memory.set(-1)
        time.sleep(1)

def main():
    if not PROMETHEUS_AVAILABLE:
        print("⚠️ 'prometheus_client' not installed. Monitoring data will not be exported.")
        print("Install with: pip install prometheus-client GPUtil")
        # Keep the script running to show other potential issues, but without metrics.
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Script stopped.")
        return
        
    # 启动Prometheus metrics服务器
    start_http_server(8000)
    print("📊 Monitoring server started at http://localhost:8000")
    
    # 启动GPU监控线程
    gpu_thread = threading.Thread(target=monitor_gpu, daemon=True)
    gpu_thread.start()
    
    # 保持运行
    print("Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped")

if __name__ == "__main__":
    main() 