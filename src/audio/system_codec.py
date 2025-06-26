#!/usr/bin/env python3
"""
紧急修复：使用系统标准G.711编解码器
解决音频编码根本性错误问题
"""

import audioop
import wave
import struct
import numpy as np
import threading
import time
from typing import Optional, Callable


class SystemG711Codec:
    """使用Python内置audioop的标准G.711编解码器"""
    
    @staticmethod
    def pcm_to_ulaw_system(pcm_data: bytes) -> bytes:
        """使用系统标准的PCM到μ-law转换"""
        try:
            # 使用Python内置的audioop库进行标准转换
            # audioop.lin2ulaw是符合ITU-T G.711标准的实现
            ulaw_data = audioop.lin2ulaw(pcm_data, 2)  # 2 = 16-bit samples
            return ulaw_data
        except Exception as e:
            print(f"❌ 系统G.711编码失败: {e}")
            return b''
    
    @staticmethod
    def ulaw_to_pcm_system(ulaw_data: bytes) -> bytes:
        """使用系统标准的μ-law到PCM转换"""
        try:
            # 使用Python内置的audioop库进行标准转换
            pcm_data = audioop.ulaw2lin(ulaw_data, 2)  # 2 = 16-bit samples
            return pcm_data
        except Exception as e:
            print(f"❌ 系统G.711解码失败: {e}")
            return b''
    
    @staticmethod
    def generate_dtmf_system(digit: str, duration: float = 0.5, sample_rate: int = 8000) -> bytes:
        """生成系统标准的DTMF音调"""
        # DTMF频率表
        dtmf_freqs = {
            '1': (697, 1209), '2': (697, 1336), '3': (697, 1477), 'A': (697, 1633),
            '4': (770, 1209), '5': (770, 1336), '6': (770, 1477), 'B': (770, 1633),
            '7': (852, 1209), '8': (852, 1336), '9': (852, 1477), 'C': (852, 1633),
            '*': (941, 1209), '0': (941, 1336), '#': (941, 1477), 'D': (941, 1633),
        }
        
        if digit not in dtmf_freqs:
            print(f"⚠️ 未知DTMF数字: {digit}")
            return b''
        
        low_freq, high_freq = dtmf_freqs[digit]
        samples = int(duration * sample_rate)
        
        print(f"🎵 生成DTMF音调: {digit} ({low_freq}Hz + {high_freq}Hz)")
        
        # 生成双音频DTMF信号
        t = np.linspace(0, duration, samples, endpoint=False)
        
        # 混合两个频率，使用标准DTMF幅度
        amplitude = 0.4  # DTMF标准幅度
        signal = amplitude * (np.sin(2 * np.pi * low_freq * t) + 
                             np.sin(2 * np.pi * high_freq * t))
        
        # 添加渐入渐出避免咔嗒声
        fade_samples = int(0.01 * sample_rate)  # 10ms
        if fade_samples > 0:
            signal[:fade_samples] *= np.linspace(0, 1, fade_samples)
            signal[-fade_samples:] *= np.linspace(1, 0, fade_samples)
        
        # 转换为16位PCM
        pcm_int16 = (signal * 32767).astype(np.int16)
        pcm_data = pcm_int16.tobytes()
        
        # 使用系统标准编码转换为μ-law
        ulaw_data = SystemG711Codec.pcm_to_ulaw_system(pcm_data)
        
        print(f"✅ DTMF生成完成: {len(pcm_data)}字节PCM -> {len(ulaw_data)}字节μ-law")
        return ulaw_data
    
    @staticmethod
    def generate_test_sequence() -> bytes:
        """生成测试音频序列: "1871"数字DTMF"""
        print("🎵 生成'1871'DTMF测试序列...")
        
        sequence = []
        digits = "1871"
        
        for i, digit in enumerate(digits):
            # 生成数字音调
            dtmf_tone = SystemG711Codec.generate_dtmf_system(digit, duration=0.4)
            sequence.append(dtmf_tone)
            
            # 添加间隔（除了最后一个数字）
            if i < len(digits) - 1:
                silence = SystemG711Codec.generate_silence_ulaw(0.2)
                sequence.append(silence)
        
        # 合并所有音频
        complete_audio = b''.join(sequence)
        total_duration = len(complete_audio) / 8000
        
        print(f"✅ 测试序列生成完成: {len(complete_audio)}字节, {total_duration:.1f}秒")
        return complete_audio
    
    @staticmethod
    def generate_silence_ulaw(duration: float, sample_rate: int = 8000) -> bytes:
        """生成μ-law格式的静音"""
        samples = int(duration * sample_rate)
        # μ-law的静音值是0x7F（不是0x00或0xFF）
        silence_byte = 0x7F
        return bytes([silence_byte] * samples)
    
    @staticmethod
    def validate_ulaw_data(ulaw_data: bytes) -> dict:
        """验证μ-law数据的有效性"""
        if not ulaw_data:
            return {"valid": False, "reason": "空数据"}
        
        # 统计分析
        byte_counts = {}
        for byte_val in ulaw_data:
            byte_counts[byte_val] = byte_counts.get(byte_val, 0) + 1
        
        # 检查是否过于单调（可能编码错误）
        unique_values = len(byte_counts)
        most_common_ratio = max(byte_counts.values()) / len(ulaw_data)
        
        analysis = {
            "valid": True,
            "length": len(ulaw_data),
            "unique_values": unique_values,
            "value_range": f"{min(ulaw_data)}-{max(ulaw_data)}",
            "most_common_ratio": most_common_ratio,
            "duration_seconds": len(ulaw_data) / 8000
        }
        
        # 判断有效性
        if unique_values < 5:
            analysis["valid"] = False
            analysis["reason"] = f"值过于单调，只有{unique_values}个不同值"
        elif most_common_ratio > 0.9:
            analysis["valid"] = False  
            analysis["reason"] = f"单一值占比过高: {most_common_ratio:.1%}"
        
        return analysis


class SystemAudioTester:
    """使用系统标准库的音频测试器"""
    
    def __init__(self):
        self.codec = SystemG711Codec()
    
    def test_system_codec(self):
        """测试系统编解码器"""
        print("\n🧪 测试系统标准G.711编解码器...")
        
        # 生成测试PCM数据
        sample_rate = 8000
        duration = 1.0
        frequency = 440  # A音符
        
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        pcm_wave = 0.3 * np.sin(2 * np.pi * frequency * t)
        pcm_int16 = (pcm_wave * 32767).astype(np.int16)
        pcm_data = pcm_int16.tobytes()
        
        print(f"  生成PCM测试数据: {len(pcm_data)}字节")
        
        # 测试编码
        ulaw_data = self.codec.pcm_to_ulaw_system(pcm_data)
        print(f"  PCM->μ-law编码: {len(ulaw_data)}字节")
        
        # 测试解码
        decoded_pcm = self.codec.ulaw_to_pcm_system(ulaw_data)
        print(f"  μ-law->PCM解码: {len(decoded_pcm)}字节")
        
        # 验证数据有效性
        validation = self.codec.validate_ulaw_data(ulaw_data)
        print(f"  数据验证: {'✅有效' if validation['valid'] else '❌无效'}")
        if validation['valid']:
            print(f"    长度: {validation['length']}字节")
            print(f"    不同值: {validation['unique_values']}个")
            print(f"    范围: {validation['value_range']}")
            print(f"    时长: {validation['duration_seconds']:.2f}秒")
        else:
            print(f"    错误: {validation['reason']}")
        
        return ulaw_data
    
    def test_dtmf_generation(self):
        """测试DTMF生成"""
        print("\n🧪 测试DTMF生成...")
        
        # 测试单个数字
        for digit in "1871":
            dtmf_audio = self.codec.generate_dtmf_system(digit, duration=0.3)
            validation = self.codec.validate_ulaw_data(dtmf_audio)
            status = "✅" if validation['valid'] else "❌"
            print(f"  DTMF '{digit}': {status} {len(dtmf_audio)}字节")
        
        # 测试完整序列
        sequence = self.codec.generate_test_sequence()
        validation = self.codec.validate_ulaw_data(sequence)
        print(f"  完整序列: {'✅有效' if validation['valid'] else '❌无效'} {len(sequence)}字节")
        
        return sequence
    
    def save_audio_for_analysis(self, audio_data: bytes, filename: str):
        """保存音频用于外部分析"""
        try:
            # 保存原始μ-law数据
            with open(f"debug_{filename}.ulaw", "wb") as f:
                f.write(audio_data)
            
            # 解码并保存为WAV文件便于播放验证
            pcm_data = self.codec.ulaw_to_pcm_system(audio_data)
            if pcm_data:
                with wave.open(f"debug_{filename}.wav", "wb") as wav_file:
                    wav_file.setnchannels(1)  # 单声道
                    wav_file.setsampwidth(2)  # 16位
                    wav_file.setframerate(8000)  # 8kHz
                    wav_file.writeframes(pcm_data)
                
                print(f"📁 音频已保存: debug_{filename}.ulaw 和 debug_{filename}.wav")
                print(f"   可以播放WAV文件验证音频是否正确")
            
        except Exception as e:
            print(f"❌ 保存音频失败: {e}")
    
    def run_complete_test(self):
        """运行完整的系统音频测试"""
        print("🎯 系统标准G.711编解码器测试")
        print("=" * 50)
        
        # 1. 测试基础编解码
        print("1️⃣ 基础编解码测试...")
        basic_audio = self.test_system_codec()
        self.save_audio_for_analysis(basic_audio, "basic_tone")
        
        # 2. 测试DTMF
        print("2️⃣ DTMF生成测试...")
        dtmf_audio = self.test_dtmf_generation()
        self.save_audio_for_analysis(dtmf_audio, "dtmf_1871")
        
        print("\n✅ 系统音频测试完成!")
        print("📋 下一步:")
        print("  1. 检查生成的WAV文件是否能正常播放")
        print("  2. 将系统编解码器集成到RTP发送中")
        print("  3. 重新测试实际通话")
        
        return dtmf_audio


class SystemRTPSender:
    """使用系统标准编解码器的RTP发送器"""
    
    def __init__(self, rtp_handler):
        self.rtp_handler = rtp_handler
        self.codec = SystemG711Codec()
    
    def send_system_audio(self, audio_data: bytes):
        """使用系统标准格式发送音频"""
        print(f"📡 发送系统标准音频: {len(audio_data)}字节")
        
        # 验证音频数据
        validation = self.codec.validate_ulaw_data(audio_data)
        if not validation['valid']:
            print(f"❌ 音频数据无效: {validation['reason']}")
            return
        
        print(f"✅ 音频验证通过: {validation['unique_values']}个不同值")
        
        # 分包发送
        packet_size = 160  # 20ms @ 8kHz
        total_packets = len(audio_data) // packet_size
        
        print(f"📊 发送计划: {total_packets}个包")
        print("🎧 请仔细听DTMF音调: 1-8-7-1")
        
        for i in range(0, len(audio_data), packet_size):
            packet = audio_data[i:i+packet_size]
            
            # 确保包大小正确
            if len(packet) < packet_size:
                # 用μ-law静音填充
                packet += b'\x7F' * (packet_size - len(packet))
            
            # 发送RTP包
            self.rtp_handler.send_audio(packet, payload_type=0)
            
            # 进度显示
            packet_num = (i // packet_size) + 1
            if packet_num % 25 == 0:
                print(f"📤 发送进度: {packet_num}/{total_packets} ({packet_num*0.02:.1f}s)")
            
            time.sleep(0.02)  # 精确20ms
        
        print("✅ 系统标准音频发送完成!")


if __name__ == "__main__":
    tester = SystemAudioTester()
    tester.run_complete_test() 