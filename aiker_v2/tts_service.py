#!/usr/bin/env python3
"""
高性能TTS服务 - 基于Piper
替换RealtimeTTS，实现极速语音合成
"""

import subprocess
import os
import logging
import tempfile
import time
from typing import Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class PiperTTSService:
    """Piper TTS服务类"""
    
    def __init__(self, 
                 piper_executable: str = None,
                 model_zh: str = None,
                 model_en: str = None):
        """
        初始化Piper TTS服务
        
        Args:
            piper_executable: Piper可执行文件路径
            model_zh: 中文模型路径
            model_en: 英文模型路径
        """
        # 设置默认路径
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.piper_executable = piper_executable or os.path.join(project_root, "services", "piper", "piper")
        self.model_zh = model_zh or os.path.join(project_root, "services", "piper", "models", "zh_CN-huayan-medium.onnx")
        self.model_en = model_en or os.path.join(project_root, "services", "piper", "models", "en_US-ljspeech-high.onnx")
        
        # 检查文件是否存在
        self._check_requirements()
        
        logger.info("PiperTTSService initialized")
    
    def _check_requirements(self):
        """检查Piper可执行文件和模型文件"""
        if not os.path.exists(self.piper_executable):
            logger.warning(f"Piper executable not found: {self.piper_executable}")
            logger.info("Please download Piper from: https://github.com/rhasspy/piper/releases")
        
        if not os.path.exists(self.model_zh):
            logger.warning(f"Chinese model not found: {self.model_zh}")
            
        if not os.path.exists(self.model_en):
            logger.warning(f"English model not found: {self.model_en}")
    
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
            
        try:
            # 选择模型
            model_path = self.model_zh if language == 'zh' else self.model_en
            
            if not os.path.exists(model_path):
                logger.error(f"Model not found: {model_path}")
                return None
            
            # 构建命令
            command = [self.piper_executable, '--model', model_path]
            
            if output_format == 'pcm':
                command.append('--output_raw')  # 输出原始PCM
            
            # 执行Piper
            start_time = time.time()
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False  # 处理二进制数据
            )
            
            # 传入文本并获取音频数据
            audio_bytes, stderr = process.communicate(input=text.encode('utf-8'))
            
            if process.returncode != 0:
                logger.error(f"Piper error: {stderr.decode()}")
                return None
            
            elapsed = time.time() - start_time
            logger.debug(f"TTS synthesis completed in {elapsed:.3f}s for {len(text)} chars")
            
            return audio_bytes
            
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return None
    
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
        # 获取16kHz PCM数据
        audio_16k = self.synthesize(text, language, 'pcm')
        if not audio_16k:
            return None
        
        try:
            # 导入音频转换器
            from audio_converter import AudioConverter
            
            # 重采样到8kHz (电话标准)
            audio_8k = AudioConverter.resample_audio(audio_16k, 16000, 8000)
            
            return audio_8k
            
        except Exception as e:
            logger.error(f"Failed to convert audio for RTP: {e}")
            return None
    
    def get_supported_languages(self) -> list:
        """获取支持的语言列表"""
        languages = []
        if os.path.exists(self.model_zh):
            languages.append('zh')
        if os.path.exists(self.model_en):
            languages.append('en')
        return languages
    
    def is_available(self) -> bool:
        """检查TTS服务是否可用"""
        return (os.path.exists(self.piper_executable) and 
                (os.path.exists(self.model_zh) or os.path.exists(self.model_en)))


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
    tts = PiperTTSService()
    return tts.synthesize_for_rtp(text, language)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    tts = PiperTTSService()
    
    if tts.is_available():
        print("Testing Chinese TTS...")
        audio = tts.synthesize("你好，这是Piper语音合成测试。", 'zh')
        if audio:
            print(f"Chinese TTS success: {len(audio)} bytes")
            
        print("Testing English TTS...")
        audio = tts.synthesize("Hello, this is a Piper TTS test.", 'en')
        if audio:
            print(f"English TTS success: {len(audio)} bytes")
    else:
        print("Piper TTS not available. Please check installation.")