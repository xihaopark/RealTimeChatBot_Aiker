import numpy as np
import librosa
from typing import Union, List


class AudioConverter:
    """音频格式转换器，处理RTP/μ-law和PCM之间的转换"""
    
    @staticmethod
    def mulaw_to_pcm(mulaw_data: bytes) -> np.ndarray:
        """将μ-law数据转换为16位PCM"""
        mulaw_array = np.frombuffer(mulaw_data, dtype=np.uint8)
        
        # μ-law解码表
        exp_lut = [0, 132, 396, 924, 1980, 4092, 8316, 16764]
        
        pcm_data = []
        for mulaw_val in mulaw_array:
            mulaw_val = int(mulaw_val)
            mulaw_val = (~mulaw_val) & 0xFF
            sign = (mulaw_val & 0x80)
            exponent = (mulaw_val >> 4) & 0x07
            mantissa = mulaw_val & 0x0F
            
            if exponent < len(exp_lut):
                sample = exp_lut[exponent] + (mantissa << (exponent + 3))
            else:
                sample = 0
            
            if sign == 0:
                sample = -sample
            
            # 限制在int16范围内
            sample = max(-32768, min(32767, sample))
            pcm_data.append(sample)
            
        return np.array(pcm_data, dtype=np.int16)
    
    @staticmethod
    def pcm_to_mulaw(pcm_data: np.ndarray) -> bytes:
        """将16位PCM转换为μ-law"""
        BIAS = 132
        
        def encode_sample(sample):
            # 限制范围
            sample = int(sample)
            sample = max(-32635, min(32635, sample))
            
            # 处理符号
            if sample < 0:
                sample = -sample
                sign = 0x80
            else:
                sign = 0
                
            # 添加偏置
            sample = sample + BIAS
            
            # 找到段位置
            segment = 0
            for i in range(8):
                if sample <= 0xFF:
                    break
                segment += 1
                sample >>= 1
                
            # 限制段位置
            if segment >= 8:
                segment = 7
                
            # 计算量化值
            if segment == 0:
                mantissa = (sample >> 4) & 0x0F
            else:
                mantissa = (sample >> (segment + 3)) & 0x0F
                
            # 组合最终值
            mulaw = ~(sign | (segment << 4) | mantissa)
            return mulaw & 0xFF
        
        mulaw_data = []
        for sample in pcm_data:
            encoded = encode_sample(sample)
            # 确保值在uint8范围内
            encoded = max(0, min(255, encoded))
            mulaw_data.append(encoded)
            
        return bytes(mulaw_data)
    
    @staticmethod
    def resample_audio(audio_data: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
        """重采样音频数据"""
        if src_rate == dst_rate:
            return audio_data
        return librosa.resample(audio_data.astype(np.float32), orig_sr=src_rate, target_sr=dst_rate)
    
    @staticmethod
    def convert_rtp_to_pcm16k(rtp_audio: bytes) -> np.ndarray:
        """将RTP μ-law音频(8kHz)转换为16kHz PCM，供RealtimeSTT使用"""
        # μ-law to PCM
        pcm_8k = AudioConverter.mulaw_to_pcm(rtp_audio)
        
        # 8kHz to 16kHz
        pcm_16k = AudioConverter.resample_audio(pcm_8k, 8000, 16000)
        
        return pcm_16k
    
    @staticmethod
    def convert_pcm16k_to_rtp(pcm_16k: np.ndarray) -> bytes:
        """将16kHz PCM转换为RTP μ-law音频(8kHz)"""
        # 16kHz to 8kHz
        pcm_8k = AudioConverter.resample_audio(pcm_16k, 16000, 8000)
        
        # PCM to μ-law
        mulaw_data = AudioConverter.pcm_to_mulaw(pcm_8k.astype(np.int16))
        
        return mulaw_data