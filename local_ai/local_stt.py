import numpy as np
from .audio_converter import AudioConverter
import threading
import queue
import time
from typing import Callable, Optional
import logging

# 动态导入STT组件
try:
    from RealtimeSTT import AudioToTextRecorder
    REALTIME_STT_AVAILABLE = True
except ImportError as e:
    REALTIME_STT_AVAILABLE = False
    logging.warning(f"RealtimeSTT not available: {e}")


class LocalSTT:
    """本地语音识别服务，使用RealtimeSTT替代Deepgram"""
    
    def __init__(self, 
                 model: str = "tiny",
                 language: str = "zh",
                 device: str = "cuda",
                 mic: bool = False):
        """
        初始化本地STT
        Args:
            model: Whisper模型大小 (tiny, base, small, medium, large)
            language: 识别语言
            device: 计算设备 (cuda/cpu)
            mic: 是否使用麦克风输入
        """
        self.model = model
        self.language = language
        self.device = device
        self.mic = mic
        
        # 初始化RealtimeSTT（如果可用）
        self.recorder = None
        if REALTIME_STT_AVAILABLE:
            # 设置CUDA环境变量
            import os
            os.environ['LD_LIBRARY_PATH'] = '/usr/local/cuda-11.8/targets/x86_64-linux/lib:' + os.environ.get('LD_LIBRARY_PATH', '')
            
            # 优先尝试CUDA，失败后降级到CPU
            for attempt_device, compute_type in [("cuda", "float16"), ("cpu", "int8")]:
                try:
                    logging.info(f"Initializing RealtimeSTT on {attempt_device}")
                    self.recorder = AudioToTextRecorder(
                        model=self.model,
                        language=self.language,
                        compute_type=compute_type,
                        device=attempt_device,
                        use_microphone=self.mic,
                        spinner=False,
                        level=logging.WARNING,
                        silero_sensitivity=0.4,
                        webrtc_sensitivity=2,
                        post_speech_silence_duration=0.7,
                        min_length_of_recording=0.1,
                        min_gap_between_recordings=0.5,
                        enable_realtime_transcription=True,
                        realtime_processing_pause=0.2,
                        realtime_model_type=self.model,
                        wake_words="",
                        wake_words_sensitivity=0.6,
                        wake_word_activation_delay=0.5,
                        wake_word_timeout=5
                    )
                    logging.info(f"RealtimeSTT initialized successfully on {attempt_device}")
                    break
                except Exception as e:
                    logging.error(f"Failed to initialize RealtimeSTT on {attempt_device}: {e}")
                    self.recorder = None
                    if attempt_device == "cpu":
                        # 如果CPU也失败了，彻底放弃
                        break
        
        if not self.recorder:
            logging.warning("RealtimeSTT not available, using mock STT")
        
        self.audio_queue = queue.Queue()
        self.is_listening = False
        self.transcription_callback = None
        
        logging.info(f"LocalSTT initialized: model={model}, language={language}, device={device}")
    
    def set_transcription_callback(self, callback: Callable[[str], None]):
        """设置转录回调函数"""
        self.transcription_callback = callback
    
    def start_listening(self):
        """开始监听音频"""
        if self.is_listening:
            return
            
        self.is_listening = True
        
        if not self.recorder:
            logging.warning("No STT recorder available, using mock mode")
            return
        
        if self.mic:
            # 使用麦克风模式
            self._start_mic_listening()
        else:
            # 使用音频流模式
            self._start_stream_listening()
    
    def stop_listening(self):
        """停止监听"""
        self.is_listening = False
        if hasattr(self.recorder, 'stop'):
            self.recorder.stop()
    
    def feed_audio(self, rtp_audio: bytes):
        """接收RTP音频数据"""
        if not self.is_listening:
            self.start_listening()  # 自动启动监听
            
        try:
            # 转换RTP音频为16kHz PCM
            pcm_data = AudioConverter.convert_rtp_to_pcm16k(rtp_audio)
            
            # 如果有recorder，直接feed给它
            if self.recorder:
                # 转换为float32格式 [-1, 1]
                pcm_float = pcm_data.astype(np.float32) / 32768.0
                self.recorder.feed_audio(pcm_float)
            else:
                # 添加到队列供流监听使用
                self.audio_queue.put(pcm_data)
                
        except Exception as e:
            logging.error(f"Feed audio error: {e}")
    
    def _start_mic_listening(self):
        """麦克风监听模式（测试用）"""
        def listen_thread():
            try:
                while self.is_listening:
                    full_sentence = self.recorder.text()
                    if full_sentence.strip() and self.transcription_callback:
                        self.transcription_callback(full_sentence.strip())
            except Exception as e:
                logging.error(f"Mic listening error: {e}")
        
        thread = threading.Thread(target=listen_thread, daemon=True)
        thread.start()
    
    def _start_stream_listening(self):
        """音频流监听模式"""
        def stream_thread():
            logging.info("Stream listening thread started")
            
            # 如果有recorder，启动实时监听
            if self.recorder:
                try:
                    logging.info("Starting RealtimeSTT continuous listening")
                    while self.is_listening:
                        try:
                            # 使用RealtimeSTT的text()方法获取实时转录
                            text = self.recorder.text()
                            if text and text.strip() and self.transcription_callback:
                                logging.info(f"STT detected: {text}")
                                self.transcription_callback(text.strip())
                        except Exception as e:
                            logging.debug(f"Text retrieval error: {e}")
                            time.sleep(0.1)  # 短暂等待
                            
                except Exception as e:
                    logging.error(f"RealtimeSTT listening error: {e}")
                return
            
            # 如果没有recorder，使用队列模式
            try:
                accumulated_audio = np.array([])
                silence_start = None
                SILENCE_THRESHOLD = 0.01  # 静音阈值
                SILENCE_DURATION = 1.5    # 静音持续时间(秒)
                MIN_AUDIO_LENGTH = 0.5    # 最小音频长度(秒)
                SAMPLE_RATE = 16000
                
                while self.is_listening:
                    try:
                        # 获取音频数据
                        pcm_chunk = self.audio_queue.get(timeout=0.1)
                        
                        # 累积音频
                        accumulated_audio = np.concatenate([accumulated_audio, pcm_chunk])
                        
                        # 检查是否有语音活动
                        audio_level = np.max(np.abs(pcm_chunk)) / 32768.0
                        
                        if audio_level > SILENCE_THRESHOLD:
                            # 检测到语音，重置静音计时
                            silence_start = None
                        else:
                            # 检测到静音
                            if silence_start is None:
                                silence_start = time.time()
                            elif time.time() - silence_start > SILENCE_DURATION:
                                # 静音持续足够长，处理音频
                                if len(accumulated_audio) > MIN_AUDIO_LENGTH * SAMPLE_RATE:
                                    self._process_audio(accumulated_audio)
                                accumulated_audio = np.array([])
                                silence_start = None
                                
                    except queue.Empty:
                        # 处理超时，检查是否有积累的音频需要处理
                        if len(accumulated_audio) > MIN_AUDIO_LENGTH * SAMPLE_RATE:
                            if silence_start and time.time() - silence_start > SILENCE_DURATION:
                                self._process_audio(accumulated_audio)
                                accumulated_audio = np.array([])
                                silence_start = None
                    except Exception as e:
                        logging.error(f"Stream processing error: {e}")
                        
            except Exception as e:
                logging.error(f"Stream listening error: {e}")
        
        thread = threading.Thread(target=stream_thread, daemon=True)
        thread.start()
    
    def _process_audio(self, audio_data: np.ndarray):
        """处理音频数据进行转录"""
        try:
            # 使用RealtimeSTT的feed_audio功能
            # 注意：需要将音频数据转换为合适的格式
            
            # 归一化音频到[-1, 1]范围
            audio_float = audio_data.astype(np.float32) / 32768.0
            
            # 使用RealtimeSTT的feed_audio方法
            if self.recorder:
                # feed_audio接受16-bit mono PCM audio at 16000 Hz
                self.recorder.feed_audio(audio_float)
                
                # 尝试获取转录结果（非阻塞方式）
                try:
                    # 使用text()方法获取实时转录结果
                    text = self.recorder.text()
                    if text and text.strip() and self.transcription_callback:
                        logging.info(f"STT result: {text}")
                        self.transcription_callback(text.strip())
                except Exception as text_error:
                    logging.debug(f"No text available yet: {text_error}")
                    
        except Exception as e:
            logging.error(f"Audio processing error: {e}")
    
    def process_audio_chunk(self, audio_data: bytes) -> str:
        """
        处理单个音频块并返回转录文本
        Args:
            audio_data: 音频数据字节（PCM16格式）
        Returns:
            转录的文本，如果没有识别到则返回空字符串
        """
        try:
            if not self.recorder:
                logging.warning("STT recorder not available")
                return ""
            
            # 将字节数据转换为numpy数组
            if isinstance(audio_data, bytes):
                # 假设是16-bit PCM
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
            else:
                audio_array = audio_data
            
            # 归一化到[-1, 1]范围
            audio_float = audio_array.astype(np.float32) / 32768.0
            
            # 使用RealtimeSTT的feed_audio方法
            self.recorder.feed_audio(audio_float)
            
            # 获取转录结果（非阻塞）
            text = self.recorder.text()
            
            if text and text.strip():
                logging.info(f"STT chunk result: {text}")
                return text.strip()
            
            return ""
            
        except Exception as e:
            logging.error(f"Process audio chunk error: {e}")
            return ""
    
    def test_transcription(self, text: str = "测试语音识别"):
        """测试转录功能"""
        if self.transcription_callback:
            self.transcription_callback(text)