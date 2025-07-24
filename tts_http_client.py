#!/usr/bin/env python3
"""
HTTP TTS客户端 - 完全绕过音频设备，直接PCM->RTP
支持CosyVoice、Fish-Speech等HTTP TTS服务
"""

import requests
import numpy as np
import logging
from typing import Optional, Union
import time

class HTTPTTSClient:
    """HTTP TTS客户端，支持多种TTS服务"""
    
    def __init__(self, 
                 server_url: str = "http://localhost:50000",
                 service_type: str = "cosyvoice",
                 timeout: int = 30):
        """
        初始化HTTP TTS客户端
        Args:
            server_url: TTS服务器地址
            service_type: 服务类型 (cosyvoice, fish_speech)
            timeout: 请求超时时间
        """
        self.server_url = server_url.rstrip('/')
        self.service_type = service_type.lower()
        self.timeout = timeout
        
        # 测试连接
        self._test_connection()
        
        logging.info(f"HTTP TTS Client initialized: {server_url} ({service_type})")
    
    def _test_connection(self):
        """测试TTS服务器连接"""
        try:
            response = requests.get(f"{self.server_url}/docs", timeout=5)
            if response.status_code == 200:
                logging.info("TTS server connection successful")
            else:
                logging.warning(f"TTS server responded with status {response.status_code}")
        except Exception as e:
            logging.warning(f"Cannot connect to TTS server: {e}")
    
    def synthesize_text(self, text: str, **kwargs) -> Optional[bytes]:
        """
        合成文本为PCM音频
        Args:
            text: 要合成的文本
            **kwargs: 额外参数，根据TTS服务类型而定
        Returns:
            PCM音频数据 (16kHz, 16-bit, mono) 或 None
        """
        if self.service_type == "cosyvoice":
            return self._synthesize_cosyvoice(text, **kwargs)
        elif self.service_type == "fish_speech":
            return self._synthesize_fish_speech(text, **kwargs)
        else:
            logging.error(f"Unsupported service type: {self.service_type}")
            return None
    
    def _synthesize_cosyvoice(self, text: str, 
                              spk_id: str = "中文女",
                              endpoint: str = "inference_sft") -> Optional[bytes]:
        """
        使用CosyVoice合成语音
        Args:
            text: 文本
            spk_id: 说话人ID
            endpoint: API端点
        """
        try:
            url = f"{self.server_url}/{endpoint}"
            
            # 准备请求数据
            data = {
                'tts_text': text,
                'spk_id': spk_id
            }
            
            logging.info(f"CosyVoice synthesis: {text} (speaker: {spk_id})")
            start_time = time.time()
            
            # 发送POST请求
            response = requests.post(url, data=data, timeout=self.timeout, stream=True)
            
            if response.status_code == 200:
                # 收集所有音频数据
                audio_chunks = []
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        audio_chunks.append(chunk)
                
                if audio_chunks:
                    audio_data = b''.join(audio_chunks)
                    synthesis_time = time.time() - start_time
                    
                    logging.info(f"CosyVoice synthesis completed: {len(audio_data)} bytes in {synthesis_time:.2f}s")
                    return audio_data
                else:
                    logging.error("No audio data received from CosyVoice")
                    return None
            else:
                logging.error(f"CosyVoice synthesis failed: HTTP {response.status_code}")
                logging.error(f"Response: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logging.error(f"CosyVoice synthesis timeout after {self.timeout}s")
            return None
        except Exception as e:
            logging.error(f"CosyVoice synthesis error: {e}")
            return None
    
    def _synthesize_fish_speech(self, text: str, **kwargs) -> Optional[bytes]:
        """
        使用Fish-Speech合成语音
        Args:
            text: 文本
            **kwargs: Fish-Speech特定参数
        """
        try:
            url = f"{self.server_url}/synthesize"
            
            # 准备请求数据 (根据Fish-Speech API调整)
            data = {
                'text': text,
                'voice': kwargs.get('voice', 'default'),
                'format': 'pcm',
                'sample_rate': 16000
            }
            
            logging.info(f"Fish-Speech synthesis: {text}")
            start_time = time.time()
            
            response = requests.post(url, json=data, timeout=self.timeout)
            
            if response.status_code == 200:
                audio_data = response.content
                synthesis_time = time.time() - start_time
                
                logging.info(f"Fish-Speech synthesis completed: {len(audio_data)} bytes in {synthesis_time:.2f}s")
                return audio_data
            else:
                logging.error(f"Fish-Speech synthesis failed: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"Fish-Speech synthesis error: {e}")
            return None
    
    def synthesize_streaming(self, text: str, callback, **kwargs):
        """
        流式合成语音
        Args:
            text: 文本
            callback: 音频块回调函数 callback(audio_chunk: bytes)
            **kwargs: 额外参数
        """
        try:
            if self.service_type == "cosyvoice":
                url = f"{self.server_url}/inference_sft"
                data = {
                    'tts_text': text,
                    'spk_id': kwargs.get('spk_id', '中文女')
                }
                
                response = requests.post(url, data=data, timeout=self.timeout, stream=True)
                
                if response.status_code == 200:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            callback(chunk)
                else:
                    logging.error(f"Streaming synthesis failed: HTTP {response.status_code}")
            
        except Exception as e:
            logging.error(f"Streaming synthesis error: {e}")
    
    def test_synthesis(self, test_text: str = "你好，这是语音合成测试。") -> bool:
        """
        测试合成功能
        Args:
            test_text: 测试文本
        Returns:
            是否成功
        """
        print(f"Testing TTS synthesis: {test_text}")
        
        audio_data = self.synthesize_text(test_text)
        
        if audio_data and len(audio_data) > 0:
            print(f"✅ TTS test successful: {len(audio_data)} bytes generated")
            return True
        else:
            print("❌ TTS test failed: No audio generated")
            return False


class FallbackTTSGenerator:
    """
    当HTTP TTS不可用时的备用TTS生成器
    生成基于文本长度的测试音序列
    """
    
    @staticmethod
    def generate_fallback_audio(text: str, sample_rate: int = 16000) -> bytes:
        """
        生成基于文本的提示音序列
        Args:
            text: 文本 (用于计算音频长度)
            sample_rate: 采样率
        Returns:
            PCM音频数据
        """
        # 基于文本长度计算音频时长
        duration = max(2.0, len(text) * 0.12)  # 每个字符约120ms
        samples = int(sample_rate * duration)
        
        t = np.linspace(0, duration, samples)
        
        # 生成多音调提示音序列，模拟语音节奏
        if len(text) <= 10:
            # 短文本：两声提示音
            tone1 = np.sin(2 * np.pi * 600 * t) * np.exp(-t * 1.5) * (t < duration/2)
            tone2 = np.sin(2 * np.pi * 400 * (t - duration/2)) * np.exp(-(t - duration/2) * 1.5) * (t >= duration/2)
            audio = tone1 + tone2
        else:
            # 长文本：三声提示音
            tone1 = np.sin(2 * np.pi * 700 * t) * np.exp(-t * 2) * (t < duration/3)
            tone2 = np.sin(2 * np.pi * 550 * (t - duration/3)) * np.exp(-(t - duration/3) * 2) * ((t >= duration/3) & (t < 2*duration/3))
            tone3 = np.sin(2 * np.pi * 400 * (t - 2*duration/3)) * np.exp(-(t - 2*duration/3) * 2) * (t >= 2*duration/3)
            audio = tone1 + tone2 + tone3
        
        # 转换为16-bit PCM
        audio_int16 = (audio * 16383 * 0.6).astype(np.int16)
        
        logging.info(f"Generated fallback audio: {len(audio_int16)} samples, duration={duration:.1f}s")
        return audio_int16.tobytes()


if __name__ == "__main__":
    # 测试HTTP TTS客户端
    logging.basicConfig(level=logging.INFO)
    
    # 测试CosyVoice客户端
    try:
        tts = HTTPTTSClient("http://localhost:50000", "cosyvoice")
        tts.test_synthesis("你好，欢迎致电OneSuite Business！")
    except Exception as e:
        print(f"TTS client test failed: {e}")
        
        # 测试备用音频生成器
        print("Testing fallback audio generator...")
        fallback_audio = FallbackTTSGenerator.generate_fallback_audio("你好，欢迎致电！")
        print(f"Fallback audio generated: {len(fallback_audio)} bytes")