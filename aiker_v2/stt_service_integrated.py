#!/usr/bin/env python3
"""
一体化STT服务 - 基于RealtimeSTT (适配Vast.ai容器环境)
直接在进程内运行语音识别，无需外部服务
"""

import logging
import threading
import time
import queue
import numpy as np
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass

try:
    from RealtimeSTT import AudioToTextRecorder
    import torch
    import soundfile as sf
except ImportError as e:
    logging.error(f"Missing required packages: {e}")
    logging.error("Please install: pip install RealtimeSTT torch soundfile")
    raise

logger = logging.getLogger(__name__)

@dataclass
class TranscriptionResult:
    """转录结果"""
    text: str
    language: str
    confidence: float
    timestamp: float
    is_final: bool = True

class RealtimeSTTService:
    """RealtimeSTT一体化服务类"""
    
    def __init__(self,
                 model_name: str = "tiny",  # 轻量模型适合容器环境
                 language: str = "zh",
                 device: str = "auto",
                 use_microphone: bool = False):
        """
        初始化RealtimeSTT服务
        
        Args:
            model_name: Whisper模型名称 (tiny, base, small, medium, large)
            language: 默认语言
            device: 设备 (auto, cuda, cpu)
            use_microphone: 是否使用麦克风 (容器环境设为False)
        """
        self.model_name = model_name
        self.language = language
        self.device = device
        self.use_microphone = use_microphone
        
        # 音频参数
        self.sample_rate = 16000
        self.chunk_size = 1024
        
        # RealtimeSTT实例
        self.recorder = None
        self.recorder_ready = False
        
        # 回调函数
        self.transcription_callback: Optional[Callable[[TranscriptionResult], None]] = None
        self.partial_callback: Optional[Callable[[str, str], None]] = None
        
        # 线程安全
        self.lock = threading.RLock()
        self.audio_queue = queue.Queue()
        self.running = False
        self.worker_thread = None
        
        # 初始化录音器
        self._init_recorder()
        
        logger.info("RealtimeSTTService initialized")
    
    def _init_recorder(self):
        """初始化RealtimeSTT录音器"""
        try:
            # 设置设备
            if self.device == "auto":
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # RealtimeSTT配置
            recorder_config = {
                'model': self.model_name,
                'language': self.language,
                'use_microphone': self.use_microphone,
                'device': self.device,
                'compute_type': 'float16' if self.device == 'cuda' else 'float32',
                'input_device_index': None,  # 不使用音频设备
                'wake_words': '',  # 不使用唤醒词
                'wake_words_sensitivity': 0.5,
                'wake_word_timeout': 5,
                'wake_word_activation_delay': 0,
                'silero_sensitivity': 0.1,
                'webrtc_sensitivity': 3,
                'post_speech_silence_duration': 0.2,
                'min_length_of_recording': 0.3,
                'min_gap_between_recordings': 0,
                'enable_realtime_transcription': True,
                'realtime_processing_pause': 0.02,
                'realtime_model_type': self.model_name,
                'on_recording_start': self._on_recording_start,
                'on_recording_stop': self._on_recording_stop,
                'on_transcription_start': self._on_transcription_start,
                'handle_buffer_overflow': True,
                'level': logging.WARNING,  # 减少日志输出
            }
            
            # 创建录音器实例
            self.recorder = AudioToTextRecorder(**recorder_config)
            self.recorder_ready = True
            
            logger.info(f"RealtimeSTT recorder initialized with {self.model_name} model on {self.device}")
            
        except Exception as e:
            logger.error(f"Failed to initialize RealtimeSTT recorder: {e}")
            self.recorder_ready = False
            raise
    
    def _on_recording_start(self):
        """录音开始回调"""
        logger.debug("Recording started")
    
    def _on_recording_stop(self):
        """录音停止回调"""
        logger.debug("Recording stopped")
    
    def _on_transcription_start(self):
        """转录开始回调"""
        logger.debug("Transcription started")
    
    def set_transcription_callback(self, callback: Callable[[TranscriptionResult], None]):
        """设置转录完成回调"""
        self.transcription_callback = callback
    
    def set_partial_callback(self, callback: Callable[[str, str], None]):
        """设置部分转录回调"""
        self.partial_callback = callback
    
    def start_stream_processing(self):
        """启动流式音频处理"""
        if not self.recorder_ready:
            raise RuntimeError("Recorder not ready")
        
        if self.running:
            logger.warning("Stream processing already running")
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._audio_worker, daemon=True)
        self.worker_thread.start()
        
        logger.info("Stream processing started")
    
    def stop_stream_processing(self):
        """停止流式音频处理"""
        self.running = False
        
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)
        
        # 清空音频队列
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        
        logger.info("Stream processing stopped")
    
    def _audio_worker(self):
        """音频处理工作线程"""
        logger.debug("Audio worker thread started")
        
        while self.running:
            try:
                # 从队列获取音频数据
                audio_chunk = self.audio_queue.get(timeout=0.1)
                
                if audio_chunk is None:  # 停止信号
                    break
                
                # 处理音频数据
                self._process_audio_chunk(audio_chunk)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in audio worker: {e}")
        
        logger.debug("Audio worker thread stopped")
    
    def _process_audio_chunk(self, audio_data: bytes):
        """处理音频块"""
        try:
            # 将字节转换为numpy数组
            # 假设输入是16位PCM，单声道
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # 转换为float32并归一化
            audio_float = audio_array.astype(np.float32) / 32768.0
            
            # 确保采样率正确 (假设输入是8kHz，需要转换到16kHz)
            if len(audio_float) > 0:
                # 简单的上采样到16kHz
                audio_16k = np.repeat(audio_float, 2)  # 8kHz -> 16kHz
                
                # 添加到录音器缓冲区
                if self.recorder and hasattr(self.recorder, 'feed_audio'):
                    self.recorder.feed_audio(audio_16k)
                else:
                    # 如果没有feed_audio方法，使用文件转录
                    result_text = self._transcribe_audio_array(audio_16k)
                    if result_text:
                        self._handle_transcription_result(result_text)
        
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
    
    def _transcribe_audio_array(self, audio_array: np.ndarray) -> str:
        """直接转录音频数组"""
        try:
            if len(audio_array) < self.sample_rate * 0.3:  # 至少0.3秒
                return ""
            
            # 使用recorder的模型进行转录
            if self.recorder and hasattr(self.recorder, 'transcribe'):
                result = self.recorder.transcribe(audio_array)
                return result if isinstance(result, str) else ""
            
            return ""
            
        except Exception as e:
            logger.error(f"Error transcribing audio array: {e}")
            return ""
    
    def _handle_transcription_result(self, text: str):
        """处理转录结果"""
        if not text.strip():
            return
        
        result = TranscriptionResult(
            text=text.strip(),
            language=self.language,
            confidence=0.8,  # 默认置信度
            timestamp=time.time(),
            is_final=True
        )
        
        logger.debug(f"Transcription result: {result.text}")
        
        # 调用回调函数
        if self.transcription_callback:
            try:
                self.transcription_callback(result)
            except Exception as e:
                logger.error(f"Error in transcription callback: {e}")
    
    def feed_audio(self, audio_data: bytes):
        """
        输入音频数据进行处理
        
        Args:
            audio_data: PCM音频数据 (8kHz, 16-bit, mono)
        """
        if not self.running:
            logger.warning("Stream processing not running")
            return
        
        try:
            self.audio_queue.put(audio_data, timeout=0.1)
        except queue.Full:
            logger.warning("Audio queue is full, dropping audio chunk")
    
    def transcribe_file(self, file_path: str) -> str:
        """
        转录音频文件
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            转录文本
        """
        try:
            # 读取音频文件
            audio_data, sample_rate = sf.read(file_path)
            
            # 确保是单声道
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)
            
            # 重采样到16kHz (如果需要)
            if sample_rate != 16000:
                from scipy import signal
                audio_data = signal.resample(audio_data, int(len(audio_data) * 16000 / sample_rate))
            
            # 使用录音器转录
            if self.recorder and hasattr(self.recorder, 'transcribe'):
                result = self.recorder.transcribe(audio_data)
                return result if isinstance(result, str) else ""
            
            return ""
            
        except Exception as e:
            logger.error(f"Error transcribing file {file_path}: {e}")
            return ""
    
    def get_supported_languages(self) -> list:
        """获取支持的语言列表"""
        # Whisper支持的主要语言
        return ['zh', 'en', 'ja', 'ko', 'es', 'fr', 'de', 'it', 'pt', 'ru']
    
    def set_language(self, language: str):
        """设置识别语言"""
        if language in self.get_supported_languages():
            self.language = language
            logger.info(f"Language set to: {language}")
        else:
            logger.warning(f"Unsupported language: {language}")
    
    def is_available(self) -> bool:
        """检查STT服务是否可用"""
        return self.recorder_ready and self.recorder is not None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        return {
            "model_name": self.model_name,
            "language": self.language,
            "device": self.device,
            "sample_rate": self.sample_rate,
            "recorder_ready": self.recorder_ready,
            "is_running": self.running,
            "audio_queue_size": self.audio_queue.qsize() if hasattr(self.audio_queue, 'qsize') else 0,
            "is_available": self.is_available()
        }
    
    def cleanup(self):
        """清理资源"""
        self.stop_stream_processing()
        
        if self.recorder:
            try:
                # 停止录音器
                if hasattr(self.recorder, 'shutdown'):
                    self.recorder.shutdown()
            except:
                pass
            self.recorder = None
        
        self.recorder_ready = False
        logger.info("STT service cleaned up")


class CallTranscriber:
    """单通话转录器类"""
    
    def __init__(self, language: str = 'zh', call_id: str = None):
        """
        初始化通话转录器
        
        Args:
            language: 语言代码
            call_id: 通话ID
        """
        self.language = language
        self.call_id = call_id or f"call_{int(time.time())}"
        self.stt_service = RealtimeSTTService(language=language)
        
        # 设置回调
        self.stt_service.set_transcription_callback(self._on_transcription)
        
        # 结果存储
        self.transcripts = []
        self.current_partial = ""
        
        # 启动流式处理
        self.stt_service.start_stream_processing()
        
        logger.info(f"CallTranscriber created for {self.call_id} ({language})")
    
    def _on_transcription(self, result: TranscriptionResult):
        """转录完成回调"""
        self.transcripts.append({
            "text": result.text,
            "language": result.language,
            "timestamp": result.timestamp,
            "confidence": result.confidence,
            "type": "final" if result.is_final else "partial"
        })
        logger.info(f"[{self.call_id}] Final: {result.text}")
    
    def feed_audio(self, audio_data: bytes) -> Optional[str]:
        """
        输入音频数据
        
        Args:
            audio_data: PCM音频数据
            
        Returns:
            如果有新的转录结果则返回文本
        """
        # 记录转录前的数量
        prev_count = len(self.transcripts)
        
        # 输入音频
        self.stt_service.feed_audio(audio_data)
        
        # 检查是否有新结果
        if len(self.transcripts) > prev_count:
            return self.transcripts[-1]["text"]
        
        return None
    
    def get_full_transcript(self) -> str:
        """获取完整转录文本"""
        return " ".join([t["text"] for t in self.transcripts if t["type"] == "final"])
    
    def get_transcript_history(self) -> list:
        """获取转录历史"""
        return self.transcripts.copy()
    
    def cleanup(self):
        """清理资源"""
        if self.stt_service:
            self.stt_service.cleanup()


# 便捷函数
def create_transcriber(language: str = 'zh', call_id: str = None) -> CallTranscriber:
    """
    创建通话转录器的便捷函数
    
    Args:
        language: 语言代码
        call_id: 通话ID
        
    Returns:
        CallTranscriber实例
    """
    return CallTranscriber(language=language, call_id=call_id)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    stt = RealtimeSTTService()
    
    if stt.is_available():
        print("RealtimeSTT Service is available")
        print(f"Supported languages: {stt.get_supported_languages()}")
        
        # 创建测试转录器
        transcriber = create_transcriber('zh', 'test_call')
        print("Test transcriber created")
        
        # 显示统计信息
        print(f"Stats: {stt.get_stats()}")
        
        # 清理
        transcriber.cleanup()
    else:
        print("RealtimeSTT not available. Please check installation.")