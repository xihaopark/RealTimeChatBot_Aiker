#!/usr/bin/env python3
"""
高性能STT服务 - 基于Vosk
替换RealtimeSTT，实现轻量级流式语音识别
"""

import json
import logging
import os
import threading
import time
from typing import Optional, Callable, Dict, Any
from pathlib import Path

try:
    import vosk
    import soundfile as sf
    import numpy as np
except ImportError as e:
    logging.error(f"Missing required packages: {e}")
    logging.error("Please install: pip install vosk soundfile numpy")
    raise

logger = logging.getLogger(__name__)

class VoskSTTService:
    """Vosk STT服务类"""
    
    def __init__(self,
                 model_path_zh: str = None,
                 model_path_en: str = None,
                 sample_rate: int = 8000,
                 language: str = 'zh'):
        """
        初始化Vosk STT服务
        
        Args:
            model_path_zh: 中文模型路径
            model_path_en: 英文模型路径
            sample_rate: 采样率 (电话标准8kHz)
            language: 默认语言
        """
        self.sample_rate = sample_rate
        self.language = language
        
        # 设置默认模型路径
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.model_path_zh = model_path_zh or os.path.join(project_root, "services", "vosk", "models", "vosk-model-cn-0.22")
        self.model_path_en = model_path_en or os.path.join(project_root, "services", "vosk", "models", "vosk-model-en-us-0.22")
        
        # 模型和识别器
        self.models: Dict[str, vosk.Model] = {}
        self.recognizers: Dict[str, vosk.KaldiRecognizer] = {}
        
        # 回调函数
        self.transcription_callback: Optional[Callable[[str, str], None]] = None
        self.partial_callback: Optional[Callable[[str, str], None]] = None
        
        # 线程安全
        self.lock = threading.RLock()
        
        # 加载模型
        self._load_models()
        
        logger.info("VoskSTTService initialized")
    
    def _load_models(self):
        """加载Vosk模型"""
        try:
            # 加载中文模型
            if os.path.exists(self.model_path_zh):
                logger.info(f"Loading Chinese model: {self.model_path_zh}")
                self.models['zh'] = vosk.Model(self.model_path_zh)
                self.recognizers['zh'] = vosk.KaldiRecognizer(self.models['zh'], self.sample_rate)
                self.recognizers['zh'].SetWords(True)  # 启用词级时间戳
                logger.info("Chinese model loaded successfully")
            else:
                logger.warning(f"Chinese model not found: {self.model_path_zh}")
            
            # 加载英文模型
            if os.path.exists(self.model_path_en):
                logger.info(f"Loading English model: {self.model_path_en}")
                self.models['en'] = vosk.Model(self.model_path_en)
                self.recognizers['en'] = vosk.KaldiRecognizer(self.models['en'], self.sample_rate)
                self.recognizers['en'].SetWords(True)
                logger.info("English model loaded successfully")
            else:
                logger.warning(f"English model not found: {self.model_path_en}")
            
            if not self.recognizers:
                raise RuntimeError("No Vosk models loaded successfully")
                
        except Exception as e:
            logger.error(f"Failed to load Vosk models: {e}")
            raise
    
    def set_transcription_callback(self, callback: Callable[[str, str], None]):
        """
        设置转录完成回调
        
        Args:
            callback: 回调函数 (text, language)
        """
        self.transcription_callback = callback
    
    def set_partial_callback(self, callback: Callable[[str, str], None]):
        """
        设置部分转录回调
        
        Args:
            callback: 回调函数 (partial_text, language)
        """
        self.partial_callback = callback
    
    def process_audio_chunk(self, audio_data: bytes, language: str = None) -> Optional[str]:
        """
        处理音频块并返回识别结果
        
        Args:
            audio_data: PCM音频数据 (16-bit, 单声道, 8kHz)
            language: 语言代码 ('zh' 或 'en')
            
        Returns:
            最终识别文本，如果没有完整识别则返回None
        """
        if language is None:
            language = self.language
        
        if language not in self.recognizers:
            logger.error(f"Language '{language}' not supported")
            return None
        
        try:
            with self.lock:
                recognizer = self.recognizers[language]
                
                # 处理音频数据
                if recognizer.AcceptWaveform(audio_data):
                    # 完整识别结果
                    result = json.loads(recognizer.Result())
                    text = result.get('text', '').strip()
                    
                    if text:
                        logger.debug(f"STT result ({language}): {text}")
                        
                        # 调用回调
                        if self.transcription_callback:
                            threading.Thread(
                                target=self.transcription_callback,
                                args=(text, language),
                                daemon=True
                            ).start()
                        
                        return text
                else:
                    # 部分识别结果
                    partial_result = json.loads(recognizer.PartialResult())
                    partial_text = partial_result.get('partial', '')
                    
                    if partial_text and self.partial_callback:
                        threading.Thread(
                            target=self.partial_callback,
                            args=(partial_text, language),
                            daemon=True
                        ).start()
                
                return None
                
        except Exception as e:
            logger.error(f"STT processing error: {e}")
            return None
    
    def process_audio_file(self, file_path: str, language: str = None) -> str:
        """
        处理音频文件
        
        Args:
            file_path: 音频文件路径
            language: 语言代码
            
        Returns:
            识别的文本
        """
        if language is None:
            language = self.language
        
        if language not in self.recognizers:
            raise ValueError(f"Language '{language}' not supported")
        
        try:
            # 读取音频文件
            audio_data, sr = sf.read(file_path)
            
            # 转换为16-bit PCM
            if audio_data.dtype != np.int16:
                audio_data = (audio_data * 32767).astype(np.int16)
            
            # 重采样到8kHz (如果需要)
            if sr != self.sample_rate:
                from scipy import signal
                audio_data = signal.resample(audio_data, int(len(audio_data) * self.sample_rate / sr))
                audio_data = audio_data.astype(np.int16)
            
            # 转换为字节
            audio_bytes = audio_data.tobytes()
            
            # 处理音频
            with self.lock:
                recognizer = self.recognizers[language]
                recognizer.AcceptWaveform(audio_bytes)
                result = json.loads(recognizer.FinalResult())
                return result.get('text', '')
                
        except Exception as e:
            logger.error(f"Failed to process audio file {file_path}: {e}")
            return ""
    
    def reset_recognizer(self, language: str = None):
        """重置识别器状态"""
        if language is None:
            language = self.language
        
        if language in self.recognizers:
            with self.lock:
                # 重新创建识别器
                self.recognizers[language] = vosk.KaldiRecognizer(self.models[language], self.sample_rate)
                self.recognizers[language].SetWords(True)
                logger.debug(f"Reset recognizer for language: {language}")
    
    def get_supported_languages(self) -> list:
        """获取支持的语言列表"""
        return list(self.recognizers.keys())
    
    def is_available(self, language: str = None) -> bool:
        """检查STT服务是否可用"""
        if language is None:
            return len(self.recognizers) > 0
        return language in self.recognizers
    
    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        return {
            "supported_languages": self.get_supported_languages(),
            "sample_rate": self.sample_rate,
            "models_loaded": len(self.models),
            "current_language": self.language
        }


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
        self.stt_service = VoskSTTService(language=language)
        
        # 设置回调
        self.stt_service.set_transcription_callback(self._on_transcription)
        self.stt_service.set_partial_callback(self._on_partial)
        
        # 结果存储
        self.transcripts = []
        self.current_partial = ""
        
        logger.info(f"CallTranscriber created for {self.call_id} ({language})")
    
    def _on_transcription(self, text: str, language: str):
        """转录完成回调"""
        timestamp = time.time()
        self.transcripts.append({
            "text": text,
            "language": language,
            "timestamp": timestamp,
            "type": "final"
        })
        logger.info(f"[{self.call_id}] Final: {text}")
    
    def _on_partial(self, text: str, language: str):
        """部分转录回调"""
        self.current_partial = text
        logger.debug(f"[{self.call_id}] Partial: {text}")
    
    def feed_audio(self, audio_data: bytes) -> Optional[str]:
        """
        输入音频数据
        
        Args:
            audio_data: PCM音频数据
            
        Returns:
            如果有完整识别结果则返回文本
        """
        return self.stt_service.process_audio_chunk(audio_data, self.language)
    
    def get_full_transcript(self) -> str:
        """获取完整转录文本"""
        return " ".join([t["text"] for t in self.transcripts])
    
    def get_transcript_history(self) -> list:
        """获取转录历史"""
        return self.transcripts.copy()


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
    
    stt = VoskSTTService()
    
    if stt.is_available():
        print("Vosk STT Service is available")
        print(f"Supported languages: {stt.get_supported_languages()}")
        
        # 创建测试转录器
        transcriber = create_transcriber('zh', 'test_call')
        print("Test transcriber created")
        
        # 显示统计信息
        print(f"Stats: {stt.get_stats()}")
    else:
        print("Vosk STT not available. Please check model installation.")