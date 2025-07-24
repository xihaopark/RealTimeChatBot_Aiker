#!/usr/bin/env python3
"""
一体化TTS服务 - 基于RealtimeTTS (适配Vast.ai容器环境)
直接在进程内运行语音合成，无需外部服务或音频设备
"""

import logging
import threading
import time
import tempfile
import os
from typing import Optional, Dict, Any
from pathlib import Path

try:
    from RealtimeTTS import TextToAudioStream, CoquiEngine, OpenAIEngine, ElevenlabsEngine
    import numpy as np
    import soundfile as sf
except ImportError as e:
    logging.error(f"Missing required packages: {e}")
    logging.error("Please install: pip install RealtimeTTS soundfile numpy")
    raise

logger = logging.getLogger(__name__)

class RealtimeTTSService:
    """RealtimeTTS一体化服务类"""
    
    def __init__(self,
                 engine_type: str = "coqui",  # coqui, openai, elevenlabs
                 voice_zh: str = "tts_models/zh-CN/baker/tacotron2-DDC-GST",
                 voice_en: str = "tts_models/en/ljspeech/tacotron2-DDC",
                 device: str = "auto",
                 use_neural_speed: bool = True):
        """
        初始化RealtimeTTS服务
        
        Args:
            engine_type: TTS引擎类型
            voice_zh: 中文语音模型
            voice_en: 英文语音模型  
            device: 设备 (auto, cuda, cpu)
            use_neural_speed: 是否使用神经网络加速
        """
        self.engine_type = engine_type
        self.voice_zh = voice_zh
        self.voice_en = voice_en
        self.device = device
        self.use_neural_speed = use_neural_speed
        
        # TTS引擎和流
        self.engine = None
        self.stream = None
        self.engine_ready = False
        
        # 线程安全
        self.lock = threading.RLock()
        
        # 音频参数
        self.sample_rate = 22050  # RealtimeTTS默认采样率
        self.target_sample_rate = 8000  # 电话标准采样率
        
        # 初始化TTS引擎
        self._init_engine()
        
        logger.info("RealtimeTTSService initialized")
    
    def _init_engine(self):
        """初始化TTS引擎"""
        try:
            # 设置设备
            if self.device == "auto":
                import torch
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            
            logger.info(f"Initializing {self.engine_type} TTS engine on {self.device}")
            
            # 设置环境变量以避免音频设备问题
            os.environ["SDL_AUDIODRIVER"] = "dummy"
            os.environ["ALSA_SUPPRESS_WARNINGS"] = "1"
            
            # 根据引擎类型初始化
            if self.engine_type == "coqui":
                self.engine = CoquiEngine(
                    voice=self.voice_zh,  # 默认使用中文模型
                    device=self.device,
                    speed=1.0,
                    use_neural_speed=self.use_neural_speed,
                    # 禁用音频播放相关功能
                    play_realtime=False
                )
            elif self.engine_type == "openai":
                # 需要API密钥
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OpenAI API key not found in environment")
                
                self.engine = OpenAIEngine(
                    api_key=api_key,
                    voice="alloy",  # 默认语音
                    play_realtime=False
                )
            elif self.engine_type == "elevenlabs":
                # 需要API密钥
                api_key = os.getenv("ELEVENLABS_API_KEY")
                if not api_key:
                    raise ValueError("ElevenLabs API key not found in environment")
                
                self.engine = ElevenlabsEngine(
                    api_key=api_key,
                    voice="Rachel",  # 默认语音
                    play_realtime=False
                )
            else:
                raise ValueError(f"Unsupported engine type: {self.engine_type}")
            
            # 创建音频流
            self.stream = TextToAudioStream(
                engine=self.engine,
                play_realtime=False,  # 不实时播放
                output_device_index=None,  # 不使用音频设备
                buffer_threshold_seconds=0.5,
                on_audio_stream_start=self._on_stream_start,
                on_audio_stream_stop=self._on_stream_stop,
                level=logging.WARNING  # 减少日志输出
            )
            
            self.engine_ready = True
            logger.info("TTS engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize TTS engine: {e}")
            self.engine_ready = False
            raise
    
    def _on_stream_start(self):
        """音频流开始回调"""
        logger.debug("TTS stream started")
    
    def _on_stream_stop(self):
        """音频流停止回调"""
        logger.debug("TTS stream stopped")
    
    def synthesize(self, text: str, language: str = 'zh', output_format: str = 'pcm') -> Optional[bytes]:
        """
        合成语音
        
        Args:
            text: 要合成的文本
            language: 语言 ('zh' 或 'en')
            output_format: 输出格式 ('pcm' 或 'wav')
            
        Returns:
            音频字节流，失败返回None
        """
        if not text.strip():
            return None
        
        if not self.engine_ready:
            logger.error("TTS engine not ready")
            return None
        
        try:
            with self.lock:
                # 根据语言切换模型 (如果使用Coqui引擎)
                if self.engine_type == "coqui" and hasattr(self.engine, 'set_voice'):
                    voice = self.voice_zh if language == 'zh' else self.voice_en
                    self.engine.set_voice(voice)
                
                start_time = time.time()
                
                # 生成音频到临时文件
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_path = temp_file.name
                
                try:
                    # 合成音频
                    self.stream.feed(text)
                    self.stream.play_async(
                        fast_sentence_fragment=True,
                        buffer_threshold_seconds=0.1,
                        log_synthesized_text=False,
                        reset_generated_audio=True,
                        output_wavfile=temp_path
                    )
                    
                    # 等待合成完成
                    timeout = 30  # 30秒超时
                    start_wait = time.time()
                    while self.stream.is_playing() and (time.time() - start_wait) < timeout:
                        time.sleep(0.1)
                    
                    # 读取生成的音频文件
                    if os.path.exists(temp_path):
                        audio_data, sr = sf.read(temp_path)
                        
                        # 确保是单声道
                        if len(audio_data.shape) > 1:
                            audio_data = audio_data.mean(axis=1)
                        
                        # 重采样到目标采样率
                        if sr != self.target_sample_rate:
                            audio_data = self._resample_audio(audio_data, sr, self.target_sample_rate)
                        
                        # 转换格式
                        if output_format == 'pcm':
                            # 转换为16位PCM
                            audio_pcm = (audio_data * 32767).astype(np.int16)
                            result = audio_pcm.tobytes()
                        else:  # wav
                            # 保存为WAV格式
                            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_file:
                                sf.write(wav_file.name, audio_data, self.target_sample_rate)
                                with open(wav_file.name, 'rb') as f:
                                    result = f.read()
                                os.unlink(wav_file.name)
                        
                        elapsed = time.time() - start_time
                        logger.debug(f"TTS synthesis completed in {elapsed:.3f}s for {len(text)} chars")
                        
                        return result
                    else:
                        logger.error("TTS output file not found")
                        return None
                        
                finally:
                    # 清理临时文件
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return None
    
    def _resample_audio(self, audio_data: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """重采样音频"""
        try:
            from scipy import signal
            # 计算重采样比例
            num_samples = int(len(audio_data) * target_sr / orig_sr)
            resampled = signal.resample(audio_data, num_samples)
            return resampled.astype(np.float32)
        except ImportError:
            # 如果没有scipy，使用简单的线性插值
            logger.warning("scipy not available, using simple resampling")
            ratio = target_sr / orig_sr
            new_length = int(len(audio_data) * ratio)
            indices = np.linspace(0, len(audio_data) - 1, new_length)
            return np.interp(indices, np.arange(len(audio_data)), audio_data).astype(np.float32)
    
    def synthesize_to_file(self, text: str, output_path: str, language: str = 'zh') -> bool:
        """
        合成语音并保存到文件
        
        Args:
            text: 要合成的文本
            output_path: 输出文件路径
            language: 语言
            
        Returns:
            成功返回True，失败返回False
        """
        try:
            audio_data = self.synthesize(text, language, 'wav')
            if audio_data:
                with open(output_path, 'wb') as f:
                    f.write(audio_data)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to save TTS output: {e}")
            return False
    
    def synthesize_for_rtp(self, text: str, language: str = 'zh') -> Optional[bytes]:
        """
        为RTP传输合成音频 (8kHz, 16-bit PCM)
        
        Args:
            text: 要合成的文本
            language: 语言
            
        Returns:
            适用于RTP的8kHz PCM音频数据
        """
        return self.synthesize(text, language, 'pcm')
    
    def get_supported_languages(self) -> list:
        """获取支持的语言列表"""
        if self.engine_type == "coqui":
            return ['zh', 'en']  # 根据已配置的模型
        elif self.engine_type == "openai":
            return ['zh', 'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko']
        elif self.engine_type == "elevenlabs":
            return ['en', 'zh', 'es', 'fr', 'de', 'it', 'pt', 'pl']
        else:
            return ['zh', 'en']
    
    def set_voice(self, voice_name: str, language: str = 'zh'):
        """设置语音模型"""
        try:
            if self.engine_type == "coqui" and hasattr(self.engine, 'set_voice'):
                if language == 'zh':
                    self.voice_zh = voice_name
                else:
                    self.voice_en = voice_name
                logger.info(f"Voice set to {voice_name} for language {language}")
            else:
                logger.warning(f"Voice setting not supported for {self.engine_type} engine")
        except Exception as e:
            logger.error(f"Failed to set voice: {e}")
    
    def is_available(self) -> bool:
        """检查TTS服务是否可用"""
        return self.engine_ready and self.engine is not None and self.stream is not None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        stats = {
            "engine_type": self.engine_type,
            "device": self.device,
            "sample_rate": self.sample_rate,
            "target_sample_rate": self.target_sample_rate,
            "engine_ready": self.engine_ready,
            "supported_languages": self.get_supported_languages(),
            "is_available": self.is_available()
        }
        
        # 添加引擎特定信息
        if self.engine_type == "coqui":
            stats["voice_zh"] = self.voice_zh
            stats["voice_en"] = self.voice_en
        
        return stats
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.stream:
                # 停止流
                if hasattr(self.stream, 'stop'):
                    self.stream.stop()
                self.stream = None
            
            if self.engine:
                # 清理引擎
                if hasattr(self.engine, 'shutdown'):
                    self.engine.shutdown()
                self.engine = None
            
            self.engine_ready = False
            logger.info("TTS service cleaned up")
            
        except Exception as e:
            logger.error(f"Error during TTS cleanup: {e}")


# 便捷函数
def synthesize(text: str, language: str = 'zh') -> Optional[bytes]:
    """
    快速合成语音的便捷函数
    
    Args:
        text: 要合成的文本
        language: 语言
        
    Returns:
        PCM音频字节流
    """
    tts = RealtimeTTSService()
    return tts.synthesize_for_rtp(text, language)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    tts = RealtimeTTSService()
    
    if tts.is_available():
        print("Testing Chinese TTS...")
        audio = tts.synthesize("你好，这是RealtimeTTS语音合成测试。", 'zh')
        if audio:
            print(f"Chinese TTS success: {len(audio)} bytes")
            
        print("Testing English TTS...")
        audio = tts.synthesize("Hello, this is a RealtimeTTS test.", 'en')
        if audio:
            print(f"English TTS success: {len(audio)} bytes")
        
        # 显示统计信息
        print(f"Stats: {tts.get_stats()}")
        
        # 清理
        tts.cleanup()
    else:
        print("RealtimeTTS not available. Please check installation.")