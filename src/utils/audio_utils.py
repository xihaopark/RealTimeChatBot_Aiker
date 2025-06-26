#!/usr/bin/env python3
"""
VTX AI Phone System - 音频工具
"""

import numpy as np
import wave
import io
from typing import Optional, Tuple, Union
import logging

logger = logging.getLogger(__name__)


class AudioUtils:
    """音频工具类"""
    
    @staticmethod
    def ulaw_encode(audio_data: bytes, sample_rate: int = 8000) -> bytes:
        """将PCM音频编码为μ-law格式"""
        try:
            # 将字节转换为numpy数组
            if isinstance(audio_data, bytes):
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
            else:
                audio_array = np.array(audio_data, dtype=np.int16)
            
            # μ-law编码
            ulaw_array = AudioUtils._pcm_to_ulaw(audio_array)
            
            # 转换回字节
            return ulaw_array.tobytes()
            
        except Exception as e:
            logger.error(f"μ-law编码失败: {e}")
            return audio_data
    
    @staticmethod
    def ulaw_decode(ulaw_data: bytes, sample_rate: int = 8000) -> bytes:
        """将μ-law格式解码为PCM音频"""
        try:
            # 将字节转换为numpy数组
            ulaw_array = np.frombuffer(ulaw_data, dtype=np.uint8)
            
            # μ-law解码
            pcm_array = AudioUtils._ulaw_to_pcm(ulaw_array)
            
            # 转换回字节
            return pcm_array.tobytes()
            
        except Exception as e:
            logger.error(f"μ-law解码失败: {e}")
            return ulaw_data
    
    @staticmethod
    def _pcm_to_ulaw(pcm_data: np.ndarray) -> np.ndarray:
        """PCM转μ-law编码"""
        # μ-law编码表
        MULAW_BIAS = 33
        MULAW_MAX = 32767
        
        # 确保数据类型
        pcm_data = pcm_data.astype(np.int16)
        
        # 应用偏置
        pcm_data = pcm_data + MULAW_BIAS
        
        # 处理负值
        sign = np.sign(pcm_data)
        pcm_data = np.abs(pcm_data)
        
        # 限制最大值
        pcm_data = np.minimum(pcm_data, MULAW_MAX)
        
        # 计算指数和尾数
        exponent = np.floor(np.log2(pcm_data + 1))
        mantissa = np.floor((pcm_data - 2**exponent) / 2**(exponent - 3)) + 1
        
        # 构建μ-law字节
        ulaw_byte = sign * (16 * exponent + mantissa)
        
        # 转换为无符号8位整数
        ulaw_byte = (ulaw_byte + 128).astype(np.uint8)
        
        return ulaw_byte
    
    @staticmethod
    def _ulaw_to_pcm(ulaw_data: np.ndarray) -> np.ndarray:
        """μ-law解码为PCM"""
        # μ-law解码表
        MULAW_BIAS = 33
        
        # 确保数据类型
        ulaw_data = ulaw_data.astype(np.uint8)
        
        # 转换为有符号
        ulaw_signed = ulaw_data.astype(np.int16) - 128
        
        # 提取符号
        sign = np.sign(ulaw_signed)
        ulaw_abs = np.abs(ulaw_signed)
        
        # 提取指数和尾数
        exponent = (ulaw_abs >> 4) & 0x07
        mantissa = ulaw_abs & 0x0F
        
        # 重建PCM值
        pcm_value = sign * ((mantissa << 3) + 0x84) << exponent
        pcm_value = pcm_value - 0x84
        
        # 移除偏置
        pcm_value = pcm_value - MULAW_BIAS
        
        return pcm_value.astype(np.int16)
    
    @staticmethod
    def resample_audio(audio_data: bytes, 
                      from_rate: int, 
                      to_rate: int, 
                      channels: int = 1) -> bytes:
        """重采样音频"""
        try:
            # 将字节转换为numpy数组
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # 计算重采样比例
            ratio = to_rate / from_rate
            
            # 简单的线性插值重采样
            new_length = int(len(audio_array) * ratio)
            indices = np.linspace(0, len(audio_array) - 1, new_length)
            
            # 线性插值
            resampled = np.interp(indices, np.arange(len(audio_array)), audio_array)
            
            # 转换回int16
            resampled = resampled.astype(np.int16)
            
            return resampled.tobytes()
            
        except Exception as e:
            logger.error(f"音频重采样失败: {e}")
            return audio_data
    
    @staticmethod
    def convert_to_wav(audio_data: bytes, 
                      sample_rate: int = 8000, 
                      channels: int = 1) -> bytes:
        """将音频数据转换为WAV格式"""
        try:
            # 创建内存中的WAV文件
            wav_buffer = io.BytesIO()
            
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(channels)
                wav_file.setsampwidth(2)  # 16位
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data)
            
            return wav_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"WAV转换失败: {e}")
            return audio_data
    
    @staticmethod
    def extract_from_wav(wav_data: bytes) -> Tuple[bytes, int, int]:
        """从WAV数据中提取音频信息"""
        try:
            wav_buffer = io.BytesIO(wav_data)
            
            with wave.open(wav_buffer, 'rb') as wav_file:
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                audio_data = wav_file.readframes(wav_file.getnframes())
            
            return audio_data, sample_rate, channels
            
        except Exception as e:
            logger.error(f"WAV提取失败: {e}")
            return wav_data, 8000, 1
    
    @staticmethod
    def normalize_audio(audio_data: bytes, target_level: float = 0.8) -> bytes:
        """音频归一化"""
        try:
            # 转换为numpy数组
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            
            # 归一化到[-1, 1]
            audio_array = audio_array / 32768.0
            
            # 计算当前最大幅度
            max_amplitude = np.max(np.abs(audio_array))
            
            if max_amplitude > 0:
                # 计算缩放因子
                scale_factor = target_level / max_amplitude
                
                # 应用缩放
                audio_array = audio_array * scale_factor
                
                # 限制在[-1, 1]范围内
                audio_array = np.clip(audio_array, -1.0, 1.0)
            
            # 转换回int16
            audio_array = (audio_array * 32767).astype(np.int16)
            
            return audio_array.tobytes()
            
        except Exception as e:
            logger.error(f"音频归一化失败: {e}")
            return audio_data
    
    @staticmethod
    def detect_silence(audio_data: bytes, 
                      threshold: float = 0.01, 
                      min_silence_duration: float = 0.1) -> bool:
        """检测静音"""
        try:
            # 转换为numpy数组
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            
            # 归一化
            audio_array = audio_array / 32768.0
            
            # 计算RMS能量
            rms = np.sqrt(np.mean(audio_array**2))
            
            return rms < threshold
            
        except Exception as e:
            logger.error(f"静音检测失败: {e}")
            return False
    
    @staticmethod
    def split_audio_chunks(audio_data: bytes, 
                          chunk_size: int = 160, 
                          sample_rate: int = 8000) -> list:
        """将音频分割为固定大小的块"""
        try:
            chunks = []
            data_length = len(audio_data)
            
            for i in range(0, data_length, chunk_size):
                chunk = audio_data[i:i + chunk_size]
                
                # 如果最后一个块不足，用静音填充
                if len(chunk) < chunk_size:
                    silence = b'\x00' * (chunk_size - len(chunk))
                    chunk += silence
                
                chunks.append(chunk)
            
            return chunks
            
        except Exception as e:
            logger.error(f"音频分块失败: {e}")
            return [audio_data]
    
    @staticmethod
    def merge_audio_chunks(chunks: list) -> bytes:
        """合并音频块"""
        try:
            return b''.join(chunks)
        except Exception as e:
            logger.error(f"音频块合并失败: {e}")
            return b''


# 全局音频工具实例
audio_utils = AudioUtils() 