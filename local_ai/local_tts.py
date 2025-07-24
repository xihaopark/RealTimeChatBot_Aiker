import numpy as np
from .audio_converter import AudioConverter
import io
import time
import threading
import logging
from typing import Optional, Callable

# 动态导入TTS引擎
try:
    from RealtimeTTS import TextToAudioStream, SystemEngine
    SYSTEM_TTS_AVAILABLE = True
except ImportError:
    SYSTEM_TTS_AVAILABLE = False

try:
    from RealtimeTTS import CoquiEngine
    COQUI_TTS_AVAILABLE = True
except ImportError:
    COQUI_TTS_AVAILABLE = False


class MockTTSEngine:
    """模拟TTS引擎，用于测试或当真实引擎不可用时"""
    
    def __init__(self):
        self.sample_rate = 16000
    
    def synthesize(self, text: str) -> np.ndarray:
        """生成模拟音频（静音）"""
        # 生成1秒的静音
        duration = max(0.5, len(text) * 0.1)  # 根据文本长度调整
        samples = int(self.sample_rate * duration)
        return np.zeros(samples, dtype=np.int16)


class LocalTTS:
    """本地文本转语音服务，使用RealtimeTTS替代ElevenLabs"""
    
    def __init__(self, 
                 engine: str = "system",
                 voice: str = "zh",
                 device: str = "cuda",
                 speed: float = 1.0):
        """
        初始化本地TTS
        Args:
            engine: TTS引擎 (system, coqui)
            voice: 语音ID或语言
            device: 计算设备 (cuda/cpu)
            speed: 语音速度
        """
        self.engine_name = engine
        self.voice = voice
        self.device = device
        self.speed = speed
        
        # 初始化TTS引擎
        self.engine = self._init_engine()
        
        # 跳过音频流初始化，直接使用引擎
        self.stream = None
        logging.info("Using direct engine synthesis to avoid audio device issues")
        
        logging.info(f"LocalTTS initialized: engine={engine}, voice={voice}, device={device}")
    
    def _init_engine(self):
        """初始化TTS引擎"""
        try:
            # 优先使用Coqui高质量TTS
            if COQUI_TTS_AVAILABLE:
                try:
                    logging.info("Initializing Coqui TTS engine for high quality synthesis")
                    return CoquiEngine(
                        model_name="tts_models/multilingual/multi-dataset/xtts_v2",
                        device=self.device if self.device == "cuda" else "cpu",
                        speed=self.speed,
                        language="zh-cn"  # 明确指定中文
                    )
                except Exception as e:
                    logging.warning(f"Coqui TTS initialization failed: {e}")
            
            # 回退到系统TTS
            if SYSTEM_TTS_AVAILABLE:
                logging.info("Using SystemEngine TTS")
                return SystemEngine()
            else:
                # 如果没有可用的TTS引擎，创建一个模拟引擎
                logging.warning("No TTS engines available, using mock engine")
                return MockTTSEngine()
        except Exception as e:
            logging.error(f"Failed to initialize TTS engine: {e}")
            # 回退到模拟引擎
            logging.warning("Falling back to mock TTS engine")
            return MockTTSEngine()
    
    def synthesize_text(self, text: str) -> bytes:
        """
        合成文本为音频
        Args:
            text: 要合成的文本
        Returns:
            bytes: μ-law编码的音频数据，8kHz采样率
        """
        try:
            # 使用RealtimeTTS生成音频
            audio_data = self._generate_audio(text)
            
            if audio_data is None or len(audio_data) == 0:
                logging.warning("No audio generated")
                return b''
            
            # 转换为μ-law格式
            mulaw_data = AudioConverter.convert_pcm16k_to_rtp(audio_data)
            
            logging.info(f"Generated audio: {len(audio_data)} samples -> {len(mulaw_data)} bytes μ-law")
            return mulaw_data
            
        except Exception as e:
            logging.error(f"TTS synthesis error: {e}")
            return b''
    
    def _generate_audio(self, text: str) -> Optional[np.ndarray]:
        """生成音频数据"""
        try:
            # 如果是模拟引擎，直接调用synthesize方法
            if hasattr(self.engine, '__class__') and 'Mock' in self.engine.__class__.__name__:
                return self.engine.synthesize(text)
            
            # 直接使用引擎生成音频
            logging.info(f"Direct engine synthesis: {text}")
            
            try:
                # 优先使用Coqui TTS引擎
                if hasattr(self.engine, '__class__') and 'CoquiEngine' in str(self.engine.__class__):
                    logging.info("Using Coqui TTS engine for synthesis")
                    try:
                        # 创建临时的TextToAudioStream来使用Coqui引擎
                        import tempfile
                        import wave
                        
                        # 创建临时文件保存音频
                        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                            try:
                                # 使用Coqui引擎生成音频
                                temp_stream = TextToAudioStream(
                                    engine=self.engine,
                                    log_characters=False
                                )
                                
                                # Feed文本
                                temp_stream.feed(text)
                                
                                # 收集音频数据
                                audio_chunks = []
                                
                                def collect_chunks(chunk):
                                    if chunk is not None:
                                        audio_chunks.append(chunk)
                                
                                # 播放并收集音频
                                temp_stream.play(
                                    on_audio_chunk=collect_chunks,
                                    muted=True
                                )
                                
                                if audio_chunks:
                                    # 合并音频块
                                    audio_data = np.concatenate(audio_chunks)
                                    
                                    # 确保格式正确
                                    if len(audio_data.shape) > 1:
                                        audio_data = np.mean(audio_data, axis=1)
                                    
                                    if audio_data.dtype != np.int16:
                                        if np.issubdtype(audio_data.dtype, np.floating):
                                            audio_data = (audio_data * 32767).astype(np.int16)
                                        else:
                                            audio_data = audio_data.astype(np.int16)
                                    
                                    logging.info(f"Generated audio via Coqui TTS: {len(audio_data)} samples")
                                    return audio_data
                                else:
                                    raise Exception("No audio chunks collected from Coqui TTS")
                                    
                            except Exception as coqui_error:
                                logging.error(f"Coqui TTS synthesis failed: {coqui_error}")
                            finally:
                                # 清理临时文件
                                try:
                                    import os
                                    os.unlink(tmp_file.name)
                                except:
                                    pass
                    
                    except Exception as e:
                        logging.error(f"Coqui TTS setup failed: {e}")
                
                # 回退到espeak
                elif hasattr(self.engine, '__class__') and 'SystemEngine' in str(self.engine.__class__):
                    logging.info("Using espeak for synthesis")
                    import tempfile
                    import subprocess
                    import wave
                    
                    # 使用espeak生成WAV文件
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                        try:
                            # 使用更好的espeak参数生成高质量音频
                            subprocess.run([
                                'espeak', 
                                '-v', 'zh+f3',  # 中文女声，音调更自然
                                '-s', '160',     # 语速适中
                                '-p', '50',      # 音调
                                '-a', '100',     # 音量
                                '-g', '10',      # 词间停顿
                                '-w', tmp_file.name, 
                                text
                            ], check=True, capture_output=True)
                            
                            # 读取生成的WAV文件
                            with wave.open(tmp_file.name, 'rb') as wav_file:
                                frames = wav_file.readframes(wav_file.getnframes())
                                audio_data = np.frombuffer(frames, dtype=np.int16)
                                
                                # 确保是16kHz单声道
                                if wav_file.getframerate() != 16000:
                                    ratio = 16000 / wav_file.getframerate()
                                    new_length = int(len(audio_data) * ratio)
                                    audio_data = np.interp(
                                        np.linspace(0, len(audio_data), new_length),
                                        np.arange(len(audio_data)),
                                        audio_data
                                    ).astype(np.int16)
                                
                                if wav_file.getnchannels() > 1:
                                    audio_data = audio_data.reshape(-1, wav_file.getnchannels())
                                    audio_data = np.mean(audio_data, axis=1).astype(np.int16)
                                
                                logging.info(f"Generated audio via espeak: {len(audio_data)} samples")
                                return audio_data
                                
                        except subprocess.CalledProcessError as e:
                            logging.warning(f"espeak failed: {e}")
                        except Exception as e:
                            logging.warning(f"WAV processing failed: {e}")
                        finally:
                            try:
                                import os
                                os.unlink(tmp_file.name)
                            except:
                                pass
                
                # 最终fallback - 生成欢迎提示音序列
                logging.warning("All TTS engines failed, generating welcome tone sequence")
                duration = max(3.0, len(text) * 0.15)
                samples = int(16000 * duration)
                
                # 生成三声提示音：高-中-低，模拟"欢迎致电"
                t = np.linspace(0, duration, samples)
                tone1 = np.sin(2 * np.pi * 800 * t) * np.exp(-t * 2)  # 高音，快速衰减
                tone2 = np.sin(2 * np.pi * 600 * (t - 0.5)) * np.exp(-(t - 0.5) * 2) * (t > 0.5)  # 中音
                tone3 = np.sin(2 * np.pi * 400 * (t - 1.0)) * np.exp(-(t - 1.0) * 2) * (t > 1.0)  # 低音
                
                welcome_tone = ((tone1 + tone2 + tone3) * 8000).astype(np.int16)
                logging.info(f"Generated welcome tone sequence: {len(welcome_tone)} samples, duration={duration:.1f}s")
                return welcome_tone
                
            except Exception as synthesis_error:
                logging.error(f"Direct synthesis error: {synthesis_error}")
                # 最终fallback - 生成静音
                duration = max(2.0, len(text) * 0.15)
                samples = int(16000 * duration)
                return np.zeros(samples, dtype=np.int16)
            
        except Exception as e:
            logging.error(f"Audio generation error: {e}")
            # 返回静音作为fallback
            duration = max(2.0, len(text) * 0.15)
            samples = int(16000 * duration)
            return np.zeros(samples, dtype=np.int16)
    
    def synthesize_streaming(self, text: str, callback: Callable[[bytes], None]):
        """
        流式合成文本为音频
        Args:
            text: 要合成的文本
            callback: 音频块回调函数
        """
        def streaming_thread():
            try:
                self.stream.feed(text)
                
                while True:
                    try:
                        chunk = self.stream.get_audio_chunk()
                        if chunk is None:
                            break
                        
                        # 转换音频块格式
                        if len(chunk.shape) > 1:
                            chunk = np.mean(chunk, axis=1)
                        
                        if chunk.dtype != np.int16:
                            if chunk.dtype == np.float32 or chunk.dtype == np.float64:
                                chunk = (chunk * 32767).astype(np.int16)
                            else:
                                chunk = chunk.astype(np.int16)
                        
                        # 转换为μ-law
                        mulaw_chunk = AudioConverter.convert_pcm16k_to_rtp(chunk)
                        
                        # 调用回调
                        callback(mulaw_chunk)
                        
                    except Exception as e:
                        logging.error(f"Streaming chunk error: {e}")
                        break
                        
            except Exception as e:
                logging.error(f"Streaming synthesis error: {e}")
        
        thread = threading.Thread(target=streaming_thread, daemon=True)
        thread.start()
    
    def test_synthesis(self, text: str = "你好，这是语音合成测试。"):
        """测试语音合成"""
        print(f"Testing TTS with text: {text}")
        audio_data = self.synthesize_text(text)
        print(f"Generated {len(audio_data)} bytes of audio data")
        return audio_data
    
    def cleanup(self):
        """清理资源"""
        try:
            if hasattr(self.stream, 'stop'):
                self.stream.stop()
            if hasattr(self.engine, 'cleanup'):
                self.engine.cleanup()
        except Exception as e:
            logging.error(f"Cleanup error: {e}")