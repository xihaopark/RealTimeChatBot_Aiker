"""
音频生成模块
生成 DTMF、音调、测试模式等
"""

import math
import numpy as np
from .codec import G711Codec


class AudioGenerator:
    """音频生成器"""
    
    # DTMF 频率表
    DTMF_FREQUENCIES = {
        '1': (697, 1209), '2': (697, 1336), '3': (697, 1477), 'A': (697, 1633),
        '4': (770, 1209), '5': (770, 1336), '6': (770, 1477), 'B': (770, 1633),
        '7': (852, 1209), '8': (852, 1336), '9': (852, 1477), 'C': (852, 1633),
        '*': (941, 1209), '0': (941, 1336), '#': (941, 1477), 'D': (941, 1633),
    }
    
    @staticmethod
    def generate_tone(frequency, duration, sample_rate=8000, amplitude=0.8):
        """
        生成单频音调（μ-law 编码）
        返回: bytes
        """
        samples = int(duration * sample_rate)
        audio_data = bytearray()
        
        for i in range(samples):
            t = i / sample_rate
            sample = int(amplitude * 16383 * math.sin(2 * math.pi * frequency * t))
            ulaw = G711Codec.linear_to_ulaw(sample)
            audio_data.append(ulaw)
        
        return bytes(audio_data)
    
    @staticmethod
    def generate_dtmf(digit, duration=0.5, sample_rate=8000):
        """
        生成 DTMF 音调（μ-law 编码）
        返回: bytes
        """
        if digit not in AudioGenerator.DTMF_FREQUENCIES:
            return b''
        
        low_freq, high_freq = AudioGenerator.DTMF_FREQUENCIES[digit]
        samples = int(duration * sample_rate)
        
        # 生成音调
        audio_data = bytearray()
        
        # 添加渐入渐出
        fade_samples = int(0.01 * sample_rate)  # 10ms
        
        for i in range(samples):
            t = i / sample_rate
            
            # 计算振幅（带渐入渐出）
            if i < fade_samples:
                amplitude = i / fade_samples
            elif i > samples - fade_samples:
                amplitude = (samples - i) / fade_samples
            else:
                amplitude = 1.0
            
            # 混合两个频率
            sample = int(amplitude * 8000 * (
                math.sin(2 * math.pi * low_freq * t) +
                math.sin(2 * math.pi * high_freq * t)
            ))
            
            # 限制范围
            sample = max(-32768, min(32767, sample))
            
            # 转换为 μ-law
            ulaw = G711Codec.linear_to_ulaw(sample)
            audio_data.append(ulaw)
        
        return bytes(audio_data)
    
    @staticmethod
    def generate_silence(duration, sample_rate=8000):
        """
        生成静音（μ-law 编码）
        返回: bytes
        """
        num_samples = int(duration * sample_rate)
        return bytes([G711Codec.get_silence_byte()] * num_samples)
    
    @staticmethod
    def generate_beep(frequency=1000, duration=0.2, sample_rate=8000):
        """
        生成提示音（μ-law 编码）
        返回: bytes
        """
        return AudioGenerator.generate_tone(frequency, duration, sample_rate, 0.5)
    
    @staticmethod
    def generate_dtmf_sequence(digits, digit_duration=0.5, gap_duration=0.2, sample_rate=8000):
        """
        生成 DTMF 数字序列（μ-law 编码）
        返回: bytes
        """
        audio_parts = []
        
        for i, digit in enumerate(digits):
            # 生成 DTMF 音调
            dtmf = AudioGenerator.generate_dtmf(digit, digit_duration, sample_rate)
            audio_parts.append(dtmf)
            
            # 添加间隔（最后一个数字后不加）
            if i < len(digits) - 1:
                silence = AudioGenerator.generate_silence(gap_duration, sample_rate)
                audio_parts.append(silence)
        
        return b''.join(audio_parts)
    
    @staticmethod
    def generate_test_pattern_1871(sample_rate=8000):
        """
        生成测试音频模式 "1871"（μ-law 编码）
        返回: bytes
        """
        audio_parts = []
        
        # 1. 开始提示音（上升音调）
        for freq in [400, 600, 800]:
            beep = AudioGenerator.generate_tone(freq, 0.1, sample_rate, 0.6)
            audio_parts.append(beep)
        
        # 2. 短暂静音
        audio_parts.append(AudioGenerator.generate_silence(0.3, sample_rate))
        
        # 3. DTMF 序列 "1871"
        dtmf_sequence = AudioGenerator.generate_dtmf_sequence(
            "1871", 
            digit_duration=0.6,
            gap_duration=0.3,
            sample_rate=sample_rate
        )
        audio_parts.append(dtmf_sequence)
        
        # 4. 短暂静音
        audio_parts.append(AudioGenerator.generate_silence(0.3, sample_rate))
        
        # 5. 结束提示音（下降音调）
        for freq in [800, 600, 400]:
            beep = AudioGenerator.generate_tone(freq, 0.1, sample_rate, 0.6)
            audio_parts.append(beep)
        
        return b''.join(audio_parts)