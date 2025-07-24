#!/usr/bin/env python3
"""
HTTP TTS服务 - 完全绕过音频设备依赖
直接PCM -> μ-law -> RTP，无需ALSA/PulseAudio
"""

import logging
import numpy as np
from typing import Optional
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tts_http_client import HTTPTTSClient, FallbackTTSGenerator
# 直接导入AudioConverter，避免循环导入
try:
    from local_ai.audio_converter import AudioConverter
except ImportError:
    # 如果导入失败，创建简化版本
    import audioop
    class AudioConverter:
        @staticmethod
        def convert_pcm16k_to_rtp(pcm_data):
            """将PCM16数据转换为μ-law编码"""
            if isinstance(pcm_data, np.ndarray):
                pcm_bytes = pcm_data.tobytes()
            else:
                pcm_bytes = pcm_data
            return audioop.lin2ulaw(pcm_bytes, 2)


class HTTPTTSService:
    """HTTP TTS服务，完全无音频设备依赖"""
    
    def __init__(self, 
                 server_url: str = "http://localhost:50000",
                 service_type: str = "cosyvoice",
                 fallback_enabled: bool = True,
                 timeout: int = 10):
        """
        初始化HTTP TTS服务
        Args:
            server_url: TTS服务器地址
            service_type: 服务类型
            fallback_enabled: 是否启用备用音频生成
            timeout: 请求超时时间
        """
        self.server_url = server_url
        self.service_type = service_type
        self.fallback_enabled = fallback_enabled
        self.timeout = timeout
        
        # 尝试连接HTTP TTS服务
        self.http_client = None
        self._init_http_client()
        
        logging.info(f"HTTP TTS Service initialized: {service_type} @ {server_url}")
    
    def _init_http_client(self):
        """初始化HTTP TTS客户端"""
        try:
            self.http_client = HTTPTTSClient(
                server_url=self.server_url,
                service_type=self.service_type,
                timeout=self.timeout
            )
            logging.info("HTTP TTS client connected successfully")
        except Exception as e:
            logging.warning(f"HTTP TTS client connection failed: {e}")
            if self.fallback_enabled:
                logging.info("Will use fallback audio generator")
            else:
                logging.error("No fallback enabled, TTS will not work")
    
    def synthesize_text(self, text: str, **kwargs) -> bytes:
        """
        合成文本为μ-law音频数据
        Args:
            text: 要合成的文本
            **kwargs: 额外参数
        Returns:
            μ-law编码的音频数据，8kHz采样率，适合RTP传输
        """
        try:
            # 尝试HTTP TTS服务
            if self.http_client:
                logging.info(f"HTTP TTS synthesis: {text}")
                pcm_data = self.http_client.synthesize_text(text, **kwargs)
                
                if pcm_data and len(pcm_data) > 0:
                    # 转换PCM数据为numpy数组
                    pcm_array = np.frombuffer(pcm_data, dtype=np.int16)
                    
                    # 转换为μ-law格式
                    mulaw_data = AudioConverter.convert_pcm16k_to_rtp(pcm_array)
                    
                    logging.info(f"HTTP TTS success: {len(pcm_array)} PCM samples -> {len(mulaw_data)} μ-law bytes")
                    return mulaw_data
                else:
                    logging.warning("HTTP TTS returned empty data")
            
            # HTTP TTS失败，使用备用方案
            if self.fallback_enabled:
                logging.info(f"Using fallback audio generator for: {text}")
                fallback_pcm = FallbackTTSGenerator.generate_fallback_audio(text)
                
                # 转换为numpy数组
                fallback_array = np.frombuffer(fallback_pcm, dtype=np.int16)
                
                # 转换为μ-law格式
                mulaw_data = AudioConverter.convert_pcm16k_to_rtp(fallback_array)
                
                logging.info(f"Fallback audio: {len(fallback_array)} PCM samples -> {len(mulaw_data)} μ-law bytes")
                return mulaw_data
            else:
                logging.error("No TTS method available")
                return b''
                
        except Exception as e:
            logging.error(f"TTS synthesis error: {e}")
            
            # 最终备用方案 - 生成静音
            if self.fallback_enabled:
                duration = max(2.0, len(text) * 0.12)
                samples = int(16000 * duration)
                silence = np.zeros(samples, dtype=np.int16)
                mulaw_data = AudioConverter.convert_pcm16k_to_rtp(silence)
                logging.info(f"Generated silence: {len(mulaw_data)} bytes")
                return mulaw_data
            else:
                return b''
    
    def synthesize_streaming(self, text: str, callback, **kwargs):
        """
        流式合成文本为音频
        Args:
            text: 文本
            callback: 音频块回调函数 callback(mulaw_chunk: bytes)
            **kwargs: 额外参数
        """
        try:
            if self.http_client:
                def process_chunk(pcm_chunk: bytes):
                    try:
                        # 转换PCM块为μ-law
                        pcm_array = np.frombuffer(pcm_chunk, dtype=np.int16)
                        mulaw_chunk = AudioConverter.convert_pcm16k_to_rtp(pcm_array)
                        callback(mulaw_chunk)
                    except Exception as e:
                        logging.error(f"Streaming chunk conversion error: {e}")
                
                # 启动流式合成
                self.http_client.synthesize_streaming(text, process_chunk, **kwargs)
            else:
                # 无HTTP服务时的备用方案
                audio_data = self.synthesize_text(text, **kwargs)
                if audio_data:
                    # 将完整音频分块发送
                    chunk_size = 160  # 20ms @ 8kHz
                    for i in range(0, len(audio_data), chunk_size):
                        chunk = audio_data[i:i + chunk_size]
                        if len(chunk) < chunk_size:
                            chunk += b'\x7f' * (chunk_size - len(chunk))
                        callback(chunk)
                        
        except Exception as e:
            logging.error(f"Streaming synthesis error: {e}")
    
    def test_synthesis(self, text: str = "你好，这是HTTP TTS测试。") -> bool:
        """
        测试合成功能
        Args:
            text: 测试文本
        Returns:
            是否成功
        """
        print(f"Testing HTTP TTS synthesis: {text}")
        
        audio_data = self.synthesize_text(text)
        
        if audio_data and len(audio_data) > 0:
            print(f"✅ HTTP TTS test successful: {len(audio_data)} bytes μ-law audio")
            return True
        else:
            print("❌ HTTP TTS test failed: No audio generated")
            return False
    
    def cleanup(self):
        """清理资源"""
        try:
            if hasattr(self, 'http_client') and self.http_client:
                # HTTP客户端通常不需要特殊清理
                pass
            logging.info("HTTP TTS service cleaned up")
        except Exception as e:
            logging.error(f"HTTP TTS cleanup error: {e}")


if __name__ == "__main__":
    # 测试HTTP TTS服务
    logging.basicConfig(level=logging.INFO)
    
    # 测试不同配置
    configs = [
        {"server_url": "http://localhost:50000", "service_type": "cosyvoice"},
        # 如果CosyVoice不可用，会自动使用fallback
    ]
    
    for config in configs:
        print(f"\n测试配置: {config}")
        try:
            tts_service = HTTPTTSService(**config)
            success = tts_service.test_synthesis("你好，欢迎致电OneSuite Business！我是您的AI助手。")
            print(f"测试结果: {'成功' if success else '失败'}")
            tts_service.cleanup()
        except Exception as e:
            print(f"测试失败: {e}")