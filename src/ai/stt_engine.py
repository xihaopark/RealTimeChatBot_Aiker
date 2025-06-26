"""
语音识别引擎 (Speech-to-Text)
使用 OpenAI Whisper API 或本地 Whisper 模型
"""

import os
import time
import numpy as np
import queue
import threading
from typing import Optional, Callable, List, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("⚠️ OpenAI 库未安装，将使用本地 Whisper")

try:
    import whisper
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False
    print("⚠️ Whisper 库未安装")


class STTProvider(Enum):
    """STT 提供商"""
    OPENAI = "openai"
    WHISPER_LOCAL = "whisper_local"


@dataclass
class STTConfig:
    """STT 配置"""
    provider: STTProvider = STTProvider.OPENAI
    model: str = "whisper-1"  # OpenAI 模型
    local_model_size: str = "base"  # 本地模型: tiny, base, small, medium, large
    language: str = "zh"  # 语言代码
    sample_rate: int = 16000  # 采样率
    chunk_duration: float = 2.0  # 每个音频块的持续时间（秒）
    silence_threshold: float = 0.01  # 静音阈值
    min_speech_duration: float = 0.5  # 最小语音持续时间
    api_key: Optional[str] = None  # OpenAI API 密钥


class AudioBuffer:
    """音频缓冲区"""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.buffer = []
        self.lock = threading.Lock()
    
    def add_audio(self, audio_data: np.ndarray):
        """添加音频数据"""
        with self.lock:
            self.buffer.append(audio_data)
    
    def get_audio(self, duration: Optional[float] = None) -> Optional[np.ndarray]:
        """获取音频数据"""
        with self.lock:
            if not self.buffer:
                return None
            
            # 合并所有音频
            audio = np.concatenate(self.buffer)
            
            if duration:
                # 获取指定时长的音频
                samples_needed = int(duration * self.sample_rate)
                if len(audio) >= samples_needed:
                    result = audio[:samples_needed]
                    # 保留剩余的音频
                    self.buffer = [audio[samples_needed:]] if len(audio) > samples_needed else []
                    return result
                else:
                    return None
            else:
                # 获取所有音频
                self.buffer.clear()
                return audio
    
    def clear(self):
        """清空缓冲区"""
        with self.lock:
            self.buffer.clear()
    
    def duration(self) -> float:
        """获取缓冲区中音频的总时长"""
        with self.lock:
            if not self.buffer:
                return 0.0
            total_samples = sum(len(chunk) for chunk in self.buffer)
            return total_samples / self.sample_rate


class STTEngine:
    """语音识别引擎"""
    
    def __init__(self, config: Optional[STTConfig] = None):
        """
        初始化 STT 引擎
        
        Args:
            config: STT 配置
        """
        self.config = config or STTConfig()
        self.running = False
        
        # 初始化提供商
        if self.config.provider == STTProvider.OPENAI:
            if not HAS_OPENAI:
                print("⚠️ OpenAI 不可用，切换到本地 Whisper")
                self.config.provider = STTProvider.WHISPER_LOCAL
            else:
                # 设置 OpenAI API
                if self.config.api_key:
                    openai.api_key = self.config.api_key
                elif os.getenv("OPENAI_API_KEY"):
                    openai.api_key = os.getenv("OPENAI_API_KEY")
                else:
                    print("⚠️ 未设置 OpenAI API 密钥")
                    self.config.provider = STTProvider.WHISPER_LOCAL
        
        if self.config.provider == STTProvider.WHISPER_LOCAL:
            if not HAS_WHISPER:
                raise RuntimeError("Whisper 库未安装，无法使用语音识别")
            # 加载本地模型
            print(f"📥 加载 Whisper 模型: {self.config.local_model_size}")
            self.whisper_model = whisper.load_model(self.config.local_model_size)
        
        # 音频缓冲区
        self.audio_buffer = AudioBuffer(self.config.sample_rate)
        
        # 识别结果队列
        self.result_queue = queue.Queue()
        
        # 回调函数
        self.on_transcription: Optional[Callable[[str, float], None]] = None
        
        # 处理线程
        self.process_thread = None
        
        print(f"🎤 STT 引擎初始化: {self.config.provider.value}")
    
    def start(self):
        """启动 STT 引擎"""
        if self.running:
            return
        
        self.running = True
        self.process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self.process_thread.start()
        
        print("🎤 STT 引擎已启动")
    
    def stop(self):
        """停止 STT 引擎"""
        self.running = False
        if self.process_thread:
            self.process_thread.join(timeout=2)
        
        print("🎤 STT 引擎已停止")
    
    def add_audio(self, audio_data: bytes, format: str = "ulaw"):
        """
        添加音频数据
        
        Args:
            audio_data: 音频数据
            format: 音频格式 (ulaw, pcm16)
        """
        # 转换为 PCM16
        if format == "ulaw":
            from ..audio import G711Codec
            pcm_data = G711Codec.decode_buffer(audio_data)
            audio_array = np.frombuffer(pcm_data, dtype=np.int16)
        else:
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
        
        # 转换采样率（如果需要）
        # 假设输入是 8kHz，需要转换到 16kHz
        if format == "ulaw":  # 8kHz
            # 简单的上采样（重复样本）
            audio_array = np.repeat(audio_array, 2)
        
        # 归一化到 [-1, 1]
        audio_float = audio_array.astype(np.float32) / 32768.0
        
        # 添加到缓冲区
        self.audio_buffer.add_audio(audio_float)
    
    def _process_loop(self):
        """处理循环"""
        while self.running:
            # 检查缓冲区
            if self.audio_buffer.duration() >= self.config.chunk_duration:
                # 获取音频块
                audio_chunk = self.audio_buffer.get_audio(self.config.chunk_duration)
                
                if audio_chunk is not None and self._is_speech(audio_chunk):
                    # 执行语音识别
                    start_time = time.time()
                    text = self._transcribe(audio_chunk)
                    duration = time.time() - start_time
                    
                    if text and text.strip():
                        # 添加到结果队列
                        self.result_queue.put((text, duration))
                        
                        # 调用回调
                        if self.on_transcription:
                            self.on_transcription(text, duration)
                        
                        print(f"🎤 识别: {text} (耗时: {duration:.2f}s)")
            
            # 短暂休眠
            time.sleep(0.1)
    
    def _is_speech(self, audio: np.ndarray) -> bool:
        """
        检测是否包含语音
        
        Args:
            audio: 音频数据
            
        Returns:
            是否包含语音
        """
        # 计算能量
        energy = np.sqrt(np.mean(audio ** 2))
        
        # 检查是否超过静音阈值
        return energy > self.config.silence_threshold
    
    def _transcribe(self, audio: np.ndarray) -> Optional[str]:
        """
        执行语音识别
        
        Args:
            audio: 音频数据 (float32, 归一化)
            
        Returns:
            识别的文本
        """
        try:
            if self.config.provider == STTProvider.OPENAI:
                return self._transcribe_openai(audio)
            else:
                return self._transcribe_whisper(audio)
        except Exception as e:
            print(f"❌ 语音识别错误: {e}")
            return None
    
    def _transcribe_openai(self, audio: np.ndarray) -> Optional[str]:
        """使用 OpenAI API 进行语音识别"""
        # 转换为 int16
        audio_int16 = (audio * 32768).astype(np.int16)
        
        # 创建临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            import wave
            with wave.open(f.name, 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(self.config.sample_rate)
                wav.writeframes(audio_int16.tobytes())
            
            temp_path = f.name
        
        try:
            # 调用 OpenAI API
            with open(temp_path, 'rb') as audio_file:
                response = openai.Audio.transcribe(
                    model=self.config.model,
                    file=audio_file,
                    language=self.config.language
                )
            
            return response['text']
        finally:
            # 删除临时文件
            os.unlink(temp_path)
    
    def _transcribe_whisper(self, audio: np.ndarray) -> Optional[str]:
        """使用本地 Whisper 进行语音识别"""
        # Whisper 期望 float32 音频
        result = self.whisper_model.transcribe(
            audio,
            language=self.config.language,
            fp16=False  # 使用 FP32（更稳定）
        )
        
        return result.get('text', '')
    
    def get_transcription(self, timeout: float = 0.1) -> Optional[Tuple[str, float]]:
        """
        获取识别结果
        
        Args:
            timeout: 超时时间
            
        Returns:
            (文本, 耗时) 或 None
        """
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def set_callback(self, callback: Callable[[str, float], None]):
        """设置识别回调"""
        self.on_transcription = callback
    
    def clear_buffer(self):
        """清空音频缓冲区"""
        self.audio_buffer.clear()


# 简单的 VAD（语音活动检测）
class SimpleVAD:
    """简单的语音活动检测"""
    
    def __init__(self, threshold: float = 0.01, frame_duration: float = 0.02):
        self.threshold = threshold
        self.frame_duration = frame_duration
        self.speech_frames = 0
        self.silence_frames = 0
        self.is_speaking = False
    
    def process(self, audio: np.ndarray, sample_rate: int = 16000) -> bool:
        """
        处理音频帧
        
        Returns:
            是否检测到语音活动
        """
        # 计算能量
        energy = np.sqrt(np.mean(audio ** 2))
        
        # 更新计数
        if energy > self.threshold:
            self.speech_frames += 1
            self.silence_frames = 0
        else:
            self.silence_frames += 1
            self.speech_frames = 0
        
        # 状态转换
        if not self.is_speaking and self.speech_frames > 10:  # 200ms
            self.is_speaking = True
        elif self.is_speaking and self.silence_frames > 50:  # 1s
            self.is_speaking = False
        
        return self.is_speaking