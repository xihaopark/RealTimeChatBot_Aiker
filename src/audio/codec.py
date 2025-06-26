"""
音频编解码模块
支持 G.711 μ-law/A-law 编解码
"""

import struct
import numpy as np


class G711Codec:
    """G.711 编解码器"""
    
    @staticmethod
    def linear_to_ulaw(sample):
        """
        线性 PCM 转 μ-law
        输入: 16位有符号整数 (-32768 到 32767)
        输出: 8位无符号整数 (0 到 255)
        """
        # 限制输入范围
        if sample > 32635:
            sample = 32635
        elif sample < -32635:
            sample = -32635
        
        # 获取符号位
        if sample < 0:
            sample = -sample
            sign = 0x80
        else:
            sign = 0
        
        # 添加偏置
        sample += 132
        
        # 查找段位
        if sample < 256:
            seg = 0
        elif sample < 512:
            seg = 1
        elif sample < 1024:
            seg = 2
        elif sample < 2048:
            seg = 3
        elif sample < 4096:
            seg = 4
        elif sample < 8192:
            seg = 5
        elif sample < 16384:
            seg = 6
        else:
            seg = 7
        
        # 计算底数
        if seg >= 8:
            uval = 0x7F
        else:
            uval = (seg << 4) | ((sample >> (seg + 3)) & 0x0F)
        
        # 反转位
        return (sign | uval) ^ 0xFF
    
    @staticmethod
    def ulaw_to_linear(ulaw):
        """
        μ-law 转线性 PCM
        """
        # μ-law 解码
        ulaw = ~ulaw
        sign = (ulaw & 0x80)
        exponent = (ulaw >> 4) & 0x07
        mantissa = ulaw & 0x0F
        
        sample = ((mantissa << 3) + 132) << exponent
        
        if sign:
            sample = -sample
            
        return sample
    
    @staticmethod
    def encode_buffer(pcm_data):
        """
        编码 PCM 缓冲区为 μ-law
        输入: bytes 或 numpy array (16位 PCM)
        输出: bytes (8位 μ-law)
        """
        if isinstance(pcm_data, bytes):
            # 转换为 16 位整数数组
            samples = np.frombuffer(pcm_data, dtype=np.int16)
        else:
            samples = pcm_data
        
        # 编码每个样本
        ulaw_data = bytearray()
        for sample in samples:
            ulaw_data.append(G711Codec.linear_to_ulaw(int(sample)))
        
        return bytes(ulaw_data)
    
    @staticmethod
    def decode_buffer(ulaw_data):
        """
        解码 μ-law 缓冲区为 PCM
        输入: bytes (8位 μ-law)
        输出: bytes (16位 PCM)
        """
        pcm_samples = []
        for ulaw_byte in ulaw_data:
            pcm_samples.append(G711Codec.ulaw_to_linear(ulaw_byte))
        
        # 转换为 bytes
        return struct.pack(f'{len(pcm_samples)}h', *pcm_samples)
    
    @staticmethod
    def get_silence_byte():
        """获取 μ-law 静音字节值"""
        return 0xFF


class G711Stats:
    """G.711 编解码统计工具"""
    
    @staticmethod
    def analyze_ulaw_data(ulaw_data):
        """分析 μ-law 数据"""
        if not ulaw_data:
            return None
        
        # 解码为 PCM
        pcm_data = G711Codec.decode_buffer(ulaw_data)
        pcm_samples = np.frombuffer(pcm_data, dtype=np.int16)
        
        # 计算统计信息
        stats = {
            'num_samples': len(ulaw_data),
            'duration_ms': len(ulaw_data) * 1000 / 8000,  # 假设 8kHz
            'min_value': int(np.min(pcm_samples)),
            'max_value': int(np.max(pcm_samples)),
            'mean_value': float(np.mean(pcm_samples)),
            'rms_value': float(np.sqrt(np.mean(pcm_samples ** 2))),
            'silence_ratio': np.sum(np.array(list(ulaw_data)) == 0xFF) / len(ulaw_data)
        }
        
        return stats