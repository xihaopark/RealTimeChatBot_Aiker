#!/usr/bin/env python3
"""
VTX AI Phone System - 修复的G.711编解码器
专注解决：生成可用的G.711μ-law音频流
"""

import struct
import numpy as np
import time
from typing import Callable, Optional


class FixedG711Codec:
    """修复的G.711编解码器 - 确保生成标准μ-law"""
    
    # 标准μ-law编码表（ITU-T G.711）
    ULAW_TABLE = [
        0xff, 0xfe, 0xfd, 0xfc, 0xfb, 0xfa, 0xf9, 0xf8,
        0xf7, 0xf6, 0xf5, 0xf4, 0xf3, 0xf2, 0xf1, 0xf0,
        0xef, 0xee, 0xed, 0xec, 0xeb, 0xea, 0xe9, 0xe8,
        0xe7, 0xe6, 0xe5, 0xe4, 0xe3, 0xe2, 0xe1, 0xe0,
        0xdf, 0xde, 0xdd, 0xdc, 0xdb, 0xda, 0xd9, 0xd8,
        0xd7, 0xd6, 0xd5, 0xd4, 0xd3, 0xd2, 0xd1, 0xd0,
        0xcf, 0xce, 0xcd, 0xcc, 0xcb, 0xca, 0xc9, 0xc8,
        0xc7, 0xc6, 0xc5, 0xc4, 0xc3, 0xc2, 0xc1, 0xc0,
        0xbf, 0xbe, 0xbd, 0xbc, 0xbb, 0xba, 0xb9, 0xb8,
        0xb7, 0xb6, 0xb5, 0xb4, 0xb3, 0xb2, 0xb1, 0xb0,
        0xaf, 0xae, 0xad, 0xac, 0xab, 0xaa, 0xa9, 0xa8,
        0xa7, 0xa6, 0xa5, 0xa4, 0xa3, 0xa2, 0xa1, 0xa0,
        0x9f, 0x9e, 0x9d, 0x9c, 0x9b, 0x9a, 0x99, 0x98,
        0x97, 0x96, 0x95, 0x94, 0x93, 0x92, 0x91, 0x90,
        0x8f, 0x8e, 0x8d, 0x8c, 0x8b, 0x8a, 0x89, 0x88,
        0x87, 0x86, 0x85, 0x84, 0x83, 0x82, 0x81, 0x80,
        0x7f, 0x7e, 0x7d, 0x7c, 0x7b, 0x7a, 0x79, 0x78,
        0x77, 0x76, 0x75, 0x74, 0x73, 0x72, 0x71, 0x70,
        0x6f, 0x6e, 0x6d, 0x6c, 0x6b, 0x6a, 0x69, 0x68,
        0x67, 0x66, 0x65, 0x64, 0x63, 0x62, 0x61, 0x60,
        0x5f, 0x5e, 0x5d, 0x5c, 0x5b, 0x5a, 0x59, 0x58,
        0x57, 0x56, 0x55, 0x54, 0x53, 0x52, 0x51, 0x50,
        0x4f, 0x4e, 0x4d, 0x4c, 0x4b, 0x4a, 0x49, 0x48,
        0x47, 0x46, 0x45, 0x44, 0x43, 0x42, 0x41, 0x40,
        0x3f, 0x3e, 0x3d, 0x3c, 0x3b, 0x3a, 0x39, 0x38,
        0x37, 0x36, 0x35, 0x34, 0x33, 0x32, 0x31, 0x30,
        0x2f, 0x2e, 0x2d, 0x2c, 0x2b, 0x2a, 0x29, 0x28,
        0x27, 0x26, 0x25, 0x24, 0x23, 0x22, 0x21, 0x20,
        0x1f, 0x1e, 0x1d, 0x1c, 0x1b, 0x1a, 0x19, 0x18,
        0x17, 0x16, 0x15, 0x14, 0x13, 0x12, 0x11, 0x10,
        0x0f, 0x0e, 0x0d, 0x0c, 0x0b, 0x0a, 0x09, 0x08,
        0x07, 0x06, 0x05, 0x04, 0x03, 0x02, 0x01, 0x00
    ]
    
    @staticmethod
    def linear_to_ulaw_standard(pcm_sample):
        """标准ITU-T G.711 μ-law编码"""
        # 确保输入在有效范围内
        pcm_sample = max(-32768, min(32767, int(pcm_sample)))
        
        # 获取符号
        sign = 0x80 if pcm_sample < 0 else 0x00
        if pcm_sample < 0:
            pcm_sample = -pcm_sample
        
        # 添加偏置
        pcm_sample += 132
        if pcm_sample > 32767:
            pcm_sample = 32767
        
        # 查找指数
        exp = 0
        temp = pcm_sample
        for i in range(8):
            if temp <= (128 << i):
                exp = i
                break
        else:
            exp = 7
        
        # 计算尾数
        if exp == 0:
            mantissa = (pcm_sample >> 3) & 0x0F
        else:
            mantissa = ((pcm_sample >> (exp + 2)) & 0x0F)
        
        # 组合结果
        ulaw_byte = sign | (exp << 4) | mantissa
        
        # 取反（μ-law标准要求）
        return (~ulaw_byte) & 0xFF
    
    @staticmethod
    def encode_buffer_standard(pcm_data):
        """使用标准算法编码整个缓冲区"""
        if isinstance(pcm_data, bytes):
            # 解析为16位有符号整数（小端序）
            samples = struct.unpack(f'<{len(pcm_data)//2}h', pcm_data)
        else:
            samples = pcm_data
        
        ulaw_data = bytearray()
        for sample in samples:
            ulaw_byte = FixedG711Codec.linear_to_ulaw_standard(sample)
            ulaw_data.append(ulaw_byte)
        
        return bytes(ulaw_data)
    
    @staticmethod
    def generate_test_tone_ulaw(frequency=440, duration=3.0, sample_rate=8000, amplitude=0.3):
        """生成标准μ-law编码的测试音调"""
        print(f"🎵 生成测试音调: {frequency}Hz, {duration}秒, 幅度{amplitude}")
        
        # 生成PCM样本
        samples_count = int(duration * sample_rate)
        t = np.linspace(0, duration, samples_count, endpoint=False)
        
        # 生成正弦波
        pcm_wave = amplitude * np.sin(2 * np.pi * frequency * t)
        
        # 添加渐入渐出避免爆音
        fade_samples = int(0.05 * sample_rate)  # 50ms渐入渐出
        if fade_samples > 0:
            # 渐入
            pcm_wave[:fade_samples] *= np.linspace(0, 1, fade_samples)
            # 渐出
            pcm_wave[-fade_samples:] *= np.linspace(1, 0, fade_samples)
        
        # 转换为16位整数
        pcm_int16 = (pcm_wave * 32767).astype(np.int16)
        
        # 编码为μ-law
        ulaw_data = FixedG711Codec.encode_buffer_standard(pcm_int16.tobytes())
        
        print(f"✅ 生成完成: {len(pcm_int16)} PCM样本 -> {len(ulaw_data)} μ-law字节")
        return ulaw_data


class RealTimeVAD:
    """实时语音活动检测器"""
    
    def __init__(self, threshold=0.01, sample_rate=8000):
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.is_speaking = False
        self.energy_history = []
        self.max_history = 50  # 保留最近50个能量值
        
        # 状态回调
        self.on_speech_start: Optional[Callable] = None
        self.on_speech_end: Optional[Callable] = None
        self.on_energy_update: Optional[Callable[[float], None]] = None
        
    def process_audio_chunk(self, audio_data: bytes) -> bool:
        """处理音频块，返回是否检测到语音"""
        # 解码μ-law为PCM进行能量计算
        pcm_data = self._ulaw_to_pcm_simple(audio_data)
        
        # 计算RMS能量
        if len(pcm_data) > 0:
            samples = np.frombuffer(pcm_data, dtype=np.int16)
            energy = np.sqrt(np.mean(samples.astype(np.float32) ** 2)) / 32768.0
        else:
            energy = 0.0
        
        # 更新能量历史
        self.energy_history.append(energy)
        if len(self.energy_history) > self.max_history:
            self.energy_history.pop(0)
        
        # 调用能量更新回调
        if self.on_energy_update:
            self.on_energy_update(energy)
        
        # 语音活动检测
        was_speaking = self.is_speaking
        
        if energy > self.threshold:
            if not self.is_speaking:
                self.is_speaking = True
                if self.on_speech_start:
                    self.on_speech_start()
                print(f"🎤 检测到语音开始 (能量: {energy:.4f})")
        else:
            if self.is_speaking:
                # 使用短暂的静音容忍避免误判
                recent_energy = self.energy_history[-5:] if len(self.energy_history) >= 5 else self.energy_history
                avg_recent = np.mean(recent_energy) if recent_energy else 0.0
                
                if avg_recent <= self.threshold:
                    self.is_speaking = False
                    if self.on_speech_end:
                        self.on_speech_end()
                    print(f"🔇 语音结束 (平均能量: {avg_recent:.4f})")
        
        return self.is_speaking
    
    def _ulaw_to_pcm_simple(self, ulaw_data: bytes) -> bytes:
        """简单的μ-law到PCM转换（用于能量计算）"""
        # 简化版本，只用于能量计算
        pcm_samples = []
        for ulaw_byte in ulaw_data:
            # 简单的线性近似
            if ulaw_byte == 0xFF:  # 静音
                pcm_samples.append(0)
            else:
                # 粗略转换
                linear_val = (ulaw_byte ^ 0xFF) * 100 - 13000
                pcm_samples.append(max(-32768, min(32767, linear_val)))
        
        return struct.pack(f'<{len(pcm_samples)}h', *pcm_samples)
    
    def get_current_energy(self) -> float:
        """获取当前能量水平"""
        return self.energy_history[-1] if self.energy_history else 0.0
    
    def get_average_energy(self, window=10) -> float:
        """获取平均能量水平"""
        if not self.energy_history:
            return 0.0
        recent = self.energy_history[-window:] if len(self.energy_history) >= window else self.energy_history
        return np.mean(recent) 