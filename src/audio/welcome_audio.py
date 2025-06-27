#!/usr/bin/env python3
"""
预生成欢迎语音模块
包含Aiker AI客服的欢迎语音
"""

import os
from pathlib import Path
from typing import Optional
import numpy as np


class WelcomeAudio:
    """欢迎语音管理器"""
    
    # Aiker欢迎词
    WELCOME_TEXT = "您好，我是Aiker智能客服助手，很高兴为您服务。请问有什么可以帮助您的吗？"
    
    # 其他常用语音
    AUDIO_MESSAGES = {
        "welcome": WELCOME_TEXT,
        "busy": "抱歉，我现在很忙，请稍后再试。",
        "goodbye": "感谢您的来电，祝您生活愉快，再见！",
        "error": "抱歉，系统出现了一些问题，请稍后再试。",
        "timeout": "抱歉，等待时间过长，请重新拨打。",
        "processing": "正在为您处理，请稍等...",
        "confirm": "好的，我明白了。",
        "repeat": "抱歉，我没有听清楚，请您再说一遍。"
    }
    
    def __init__(self, cache_dir: str = "audio_cache"):
        """
        初始化欢迎语音管理器
        
        Args:
            cache_dir: 音频缓存目录
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self._cached_audio = {}
    
    def get_welcome_text(self) -> str:
        """获取欢迎词文本"""
        return self.WELCOME_TEXT
    
    def get_audio_message(self, message_type: str) -> str:
        """
        获取指定类型的语音消息
        
        Args:
            message_type: 消息类型 (welcome, busy, goodbye, error, timeout, processing, confirm, repeat)
            
        Returns:
            语音消息文本
        """
        return self.AUDIO_MESSAGES.get(message_type, self.WELCOME_TEXT)
    
    def generate_welcome_audio(self, tts_engine) -> Optional[bytes]:
        """
        生成欢迎语音（μ-law编码）
        
        Args:
            tts_engine: TTS引擎实例
            
        Returns:
            音频数据或None
        """
        try:
            print(f"🔊 生成Aiker欢迎语音: {self.WELCOME_TEXT}")
            
            # 使用TTS引擎生成语音
            tts_engine.synthesize(self.WELCOME_TEXT, priority=True)
            
            # 等待生成完成
            import time
            max_wait = 10  # 最大等待10秒
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                audio_data = tts_engine.get_audio(timeout=0.1)
                if audio_data:
                    audio_bytes, text = audio_data
                    print(f"✅ 欢迎语音生成完成: {len(audio_bytes)} 字节")
                    return audio_bytes
                time.sleep(0.1)
            
            print("❌ 欢迎语音生成超时")
            return None
            
        except Exception as e:
            print(f"❌ 生成欢迎语音失败: {e}")
            return None
    
    def save_welcome_audio(self, audio_data: bytes, filename: str = "welcome_audio.ulaw"):
        """
        保存欢迎语音到文件（同时生成μ-law和WAV格式）
        
        Args:
            audio_data: 音频数据 (μ-law格式)
            filename: 文件名
        """
        try:
            # 保存μ-law格式（用于电话系统）
            ulaw_path = self.cache_dir / filename
            with open(ulaw_path, 'wb') as f:
                f.write(audio_data)
            print(f"💾 欢迎语音已保存: {ulaw_path}")
            
            # 转换为WAV格式（用于播放器播放）
            wav_filename = filename.replace('.ulaw', '.wav')
            wav_path = self.cache_dir / wav_filename
            
            # 使用ffmpeg转换
            import subprocess
            try:
                # 从μ-law转换为WAV
                cmd = [
                    'ffmpeg',
                    '-f', 'mulaw',           # 输入格式：μ-law
                    '-ar', '8000',           # 采样率：8kHz
                    '-ac', '1',              # 声道：单声道
                    '-i', str(ulaw_path),    # 输入文件
                    '-y',                    # 覆盖输出文件
                    str(wav_path)            # 输出文件
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"🎵 WAV副本已生成: {wav_path}")
                else:
                    print(f"⚠️ WAV转换失败: {result.stderr}")
                    
            except Exception as e:
                print(f"⚠️ WAV转换错误: {e}")
                
        except Exception as e:
            print(f"❌ 保存欢迎语音失败: {e}")
    
    def load_welcome_audio(self, filename: str = "welcome_audio.ulaw") -> Optional[bytes]:
        """
        从文件加载欢迎语音
        
        Args:
            filename: 文件名
            
        Returns:
            音频数据或None
        """
        try:
            file_path = self.cache_dir / filename
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    audio_data = f.read()
                print(f"📂 欢迎语音已加载: {file_path} ({len(audio_data)} 字节)")
                return audio_data
            else:
                print(f"⚠️ 欢迎语音文件不存在: {file_path}")
                return None
        except Exception as e:
            print(f"❌ 加载欢迎语音失败: {e}")
            return None
    
    def get_wav_path(self) -> Optional[Path]:
        """
        获取WAV文件路径
        
        Returns:
            WAV文件路径或None
        """
        wav_path = self.cache_dir / "welcome_audio.wav"
        return wav_path if wav_path.exists() else None
    
    def get_or_generate_welcome_audio(self, tts_engine) -> Optional[bytes]:
        """
        获取或生成欢迎语音
        
        Args:
            tts_engine: TTS引擎实例
            
        Returns:
            音频数据或None
        """
        # 先尝试加载缓存的音频
        cached_audio = self.load_welcome_audio()
        if cached_audio:
            return cached_audio
        
        # 如果没有缓存，生成新的音频
        audio_data = self.generate_welcome_audio(tts_engine)
        if audio_data:
            # 保存到缓存
            self.save_welcome_audio(audio_data)
            return audio_data
        
        return None
    
    def clear_cache(self):
        """清空音频缓存"""
        try:
            for file in self.cache_dir.glob("*.ulaw"):
                file.unlink()
            print("🗑️ 音频缓存已清空")
        except Exception as e:
            print(f"❌ 清空缓存失败: {e}")


# 全局欢迎语音管理器实例
welcome_audio = WelcomeAudio()


def get_welcome_text() -> str:
    """获取欢迎词的便捷函数"""
    return welcome_audio.get_welcome_text()


def get_audio_message(message_type: str) -> str:
    """获取语音消息的便捷函数"""
    return welcome_audio.get_audio_message(message_type)


if __name__ == "__main__":
    # 测试欢迎语音管理器
    print("🎵 欢迎语音管理器测试")
    print("=" * 40)
    print(f"欢迎词: {get_welcome_text()}")
    print(f"忙音消息: {get_audio_message('busy')}")
    print(f"再见消息: {get_audio_message('goodbye')}")
    print("=" * 40) 