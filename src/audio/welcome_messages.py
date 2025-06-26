#!/usr/bin/env python3
"""
VTX AI Phone System - 本地欢迎语音频
Aiker - OneSuite 商业客服机器人
"""

import os
import wave
import numpy as np
from typing import Optional


class WelcomeMessages:
    """本地欢迎语音频管理器"""
    
    def __init__(self, audio_dir: str = "audio_files"):
        self.audio_dir = audio_dir
        self._ensure_audio_dir()
        self._generate_welcome_audio()
    
    def _ensure_audio_dir(self):
        """确保音频目录存在"""
        if not os.path.exists(self.audio_dir):
            os.makedirs(self.audio_dir)
            print(f"📁 创建音频目录: {self.audio_dir}")
    
    def _generate_welcome_audio(self):
        """生成欢迎语音频文件"""
        # 欢迎语文本
        welcome_text = "您好，我是Aiker，OneSuite的商业客服助手。很高兴为您服务，请问有什么可以帮助您的吗？"
        
        # 生成音频文件路径
        welcome_file = os.path.join(self.audio_dir, "welcome_message.wav")
        
        # 如果文件不存在，生成音频
        if not os.path.exists(welcome_file):
            self._create_welcome_audio(welcome_text, welcome_file)
            print(f"🎵 生成欢迎语音频: {welcome_file}")
        else:
            print(f"✅ 欢迎语音频已存在: {welcome_file}")
    
    def _create_welcome_audio(self, text: str, file_path: str):
        """创建欢迎语音频文件"""
        try:
            # 生成简单的音频信号（1871Hz正弦波）
            sample_rate = 8000
            duration = 3.0  # 3秒
            frequency = 1871  # Hz
            
            # 生成时间数组
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            
            # 生成正弦波
            audio_signal = np.sin(2 * np.pi * frequency * t)
            
            # 添加淡入淡出效果
            fade_duration = 0.1  # 100ms
            fade_samples = int(fade_duration * sample_rate)
            
            # 淡入
            fade_in = np.linspace(0, 1, fade_samples)
            audio_signal[:fade_samples] *= fade_in
            
            # 淡出
            fade_out = np.linspace(1, 0, fade_samples)
            audio_signal[-fade_samples:] *= fade_out
            
            # 转换为16位整数
            audio_int16 = (audio_signal * 32767).astype(np.int16)
            
            # 保存为WAV文件
            with wave.open(file_path, 'wb') as wav_file:
                wav_file.setnchannels(1)  # 单声道
                wav_file.setsampwidth(2)  # 16位
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_int16.tobytes())
            
            print(f"✅ 欢迎语音频创建成功: {file_path}")
            
        except Exception as e:
            print(f"❌ 欢迎语音频创建失败: {e}")
    
    def get_welcome_audio(self) -> Optional[bytes]:
        """获取欢迎语音频数据"""
        try:
            welcome_file = os.path.join(self.audio_dir, "welcome_message.wav")
            
            if os.path.exists(welcome_file):
                with wave.open(welcome_file, 'rb') as wav_file:
                    audio_data = wav_file.readframes(wav_file.getnframes())
                    return audio_data
            else:
                print(f"❌ 欢迎语音频文件不存在: {welcome_file}")
                return None
                
        except Exception as e:
            print(f"❌ 读取欢迎语音频失败: {e}")
            return None
    
    def get_welcome_audio_ulaw(self) -> Optional[bytes]:
        """获取μ-law格式的欢迎语音频"""
        try:
            audio_data = self.get_welcome_audio()
            if audio_data:
                # 转换为μ-law格式
                from ..utils.audio_utils import AudioUtils
                ulaw_audio = AudioUtils.ulaw_encode(audio_data)
                return ulaw_audio
            return None
            
        except Exception as e:
            print(f"❌ 转换μ-law格式失败: {e}")
            return None


# 全局实例
welcome_messages = WelcomeMessages() 