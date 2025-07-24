#!/usr/bin/env python3
"""
RTP处理器实现
从main.py提取的RTP音频流处理逻辑
"""

import socket
import struct
import random
import time
import threading
import queue
import math
from typing import Callable, Optional


class G711Codec:
    """G.711编解码器 (μ-law和A-law)"""
    
    @staticmethod
    def pcm_to_mulaw(pcm_data):
        """PCM转μ-law"""
        BIAS = 132
        
        def encode_sample(sample):
            sample = int(sample)
            sample = max(-32635, min(32635, sample))
            
            if sample < 0:
                sample = -sample
                sign = 0x80
            else:
                sign = 0
                
            sample = sample + BIAS
            
            segment = 0
            for i in range(8):
                if sample <= 0xFF:
                    break
                segment += 1
                sample >>= 1
                
            if segment >= 8:
                segment = 7
                
            if segment == 0:
                mantissa = (sample >> 4) & 0x0F
            else:
                mantissa = (sample >> (segment + 3)) & 0x0F
                
            mulaw = ~(sign | (segment << 4) | mantissa)
            return mulaw & 0xFF
        
        if isinstance(pcm_data, (list, tuple)):
            return bytes([encode_sample(sample) for sample in pcm_data])
        else:
            # numpy array or similar
            return bytes([encode_sample(sample) for sample in pcm_data])
    
    @staticmethod
    def mulaw_to_pcm(mulaw_data):
        """μ-law转PCM"""
        exp_lut = [0, 132, 396, 924, 1980, 4092, 8316, 16764]
        
        pcm_data = []
        for mulaw_val in mulaw_data:
            if isinstance(mulaw_val, str):
                mulaw_val = ord(mulaw_val)
            
            mulaw_val = ~mulaw_val
            sign = (mulaw_val & 0x80)
            exponent = (mulaw_val >> 4) & 0x07
            mantissa = mulaw_val & 0x0F
            
            sample = exp_lut[exponent] + (mantissa << (exponent + 3))
            
            if sign == 0:
                sample = -sample
                
            pcm_data.append(sample)
            
        return pcm_data
    
    @staticmethod
    def generate_dtmf(digit, duration=0.1, sample_rate=8000):
        """生成DTMF音频"""
        dtmf_freqs = {
            '1': (697, 1209), '2': (697, 1336), '3': (697, 1477),
            '4': (770, 1209), '5': (770, 1336), '6': (770, 1477),
            '7': (852, 1209), '8': (852, 1336), '9': (852, 1477),
            '*': (941, 1209), '0': (941, 1336), '#': (941, 1477)
        }
        
        if digit not in dtmf_freqs:
            return b''
        
        low_freq, high_freq = dtmf_freqs[digit]
        samples = int(duration * sample_rate)
        
        audio_data = []
        for i in range(samples):
            t = i / sample_rate
            sample = (math.sin(2 * math.pi * low_freq * t) + 
                     math.sin(2 * math.pi * high_freq * t)) * 16383 / 2
            audio_data.append(int(sample))
        
        return G711Codec.pcm_to_mulaw(audio_data)


class RTPHandler:
    """RTP处理器"""
    
    def __init__(self, local_ip="0.0.0.0", local_port=0):
        self.local_ip = local_ip
        self.local_port = local_port
        self.remote_ip = None
        self.remote_port = None
        
        # RTP参数
        self.ssrc = random.randint(0, 0xFFFFFFFF)
        self.sequence = random.randint(0, 0xFFFF)
        self.timestamp = random.randint(0, 0xFFFFFFFF)
        
        # 网络
        self.sock = None
        self.running = False
        
        # 线程
        self.receive_thread = None
        self.send_thread = None
        
        # 队列
        self.send_queue = queue.Queue()
        self.receive_queue = queue.Queue()
        
        # 回调
        self.audio_callback: Optional[Callable[[bytes], None]] = None
        
        print(f"🎵 RTP Handler created: {local_ip}:{local_port}")
    
    def set_audio_callback(self, callback: Callable[[bytes], None]):
        """设置音频接收回调"""
        self.audio_callback = callback
    
    def start(self, remote_ip=None, remote_port=None):
        """启动RTP处理"""
        if remote_ip:
            self.remote_ip = remote_ip
        if remote_port:
            self.remote_port = remote_port
            
        try:
            # 创建UDP socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((self.local_ip, self.local_port))
            self.sock.settimeout(0.1)  # 100ms超时
            
            # 获取实际绑定的端口
            if self.local_port == 0:
                self.local_port = self.sock.getsockname()[1]
            
            self.running = True
            
            # 启动接收线程
            self.receive_thread = threading.Thread(target=self._receive_loop)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            # 启动发送线程
            self.send_thread = threading.Thread(target=self._send_loop)
            self.send_thread.daemon = True
            self.send_thread.start()
            
            print(f"🎵 RTP启动: {self.local_ip}:{self.local_port} <-> {self.remote_ip}:{self.remote_port}")
            return True
            
        except Exception as e:
            print(f"❌ RTP启动失败: {e}")
            return False
    
    def stop(self):
        """停止RTP处理"""
        print("🛑 停止RTP处理器...")
        self.running = False
        
        if self.sock:
            self.sock.close()
        
        # 等待线程结束
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=1.0)
        if self.send_thread and self.send_thread.is_alive():
            self.send_thread.join(timeout=1.0)
        
        print("✅ RTP处理器已停止")
    
    def send_audio(self, audio_data: bytes):
        """发送音频数据"""
        if not self.running or not self.remote_ip or not self.remote_port:
            return
        
        try:
            self.send_queue.put(audio_data, timeout=0.1)
        except queue.Full:
            print("⚠️ RTP发送队列已满")
    
    def _receive_loop(self):
        """接收循环"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                
                if len(data) >= 12:  # RTP头部至少12字节
                    # 解析RTP头部
                    rtp_header = struct.unpack('!BBHII', data[:12])
                    version = (rtp_header[0] >> 6) & 0x03
                    payload_type = rtp_header[1] & 0x7F
                    sequence = rtp_header[2]
                    timestamp = rtp_header[3]
                    ssrc = rtp_header[4]
                    
                    # 提取音频数据
                    audio_data = data[12:]
                    
                    if self.audio_callback and audio_data:
                        self.audio_callback(audio_data)
                        
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"⚠️ RTP接收错误: {e}")
    
    def _send_loop(self):
        """发送循环"""
        while self.running:
            try:
                # 从队列获取音频数据
                audio_data = self.send_queue.get(timeout=0.1)
                
                if not self.remote_ip or not self.remote_port:
                    continue
                
                # 构建RTP包
                rtp_packet = self._build_rtp_packet(audio_data)
                
                # 发送
                self.sock.sendto(rtp_packet, (self.remote_ip, self.remote_port))
                
                # 更新序列号和时间戳
                self.sequence = (self.sequence + 1) & 0xFFFF
                self.timestamp = (self.timestamp + 160) & 0xFFFFFFFF  # 20ms @ 8kHz
                
            except queue.Empty:
                continue
            except Exception as e:
                if self.running:
                    print(f"⚠️ RTP发送错误: {e}")
    
    def _build_rtp_packet(self, audio_data: bytes) -> bytes:
        """构建RTP数据包"""
        # RTP头部
        version = 2
        padding = 0
        extension = 0
        csrc_count = 0
        marker = 0
        payload_type = 0  # PCMU
        
        # 构建第一个字节
        byte1 = (version << 6) | (padding << 5) | (extension << 4) | csrc_count
        
        # 构建第二个字节
        byte2 = (marker << 7) | payload_type
        
        # 打包RTP头部
        rtp_header = struct.pack('!BBHII', 
                                byte1, byte2, 
                                self.sequence, 
                                self.timestamp, 
                                self.ssrc)
        
        return rtp_header + audio_data
    
    def send_dtmf(self, digit: str, duration: float = 0.1):
        """发送DTMF音频"""
        dtmf_audio = G711Codec.generate_dtmf(digit, duration)
        
        # 分成160字节的块发送
        chunk_size = 160
        for i in range(0, len(dtmf_audio), chunk_size):
            chunk = dtmf_audio[i:i + chunk_size]
            if len(chunk) < chunk_size:
                # 填充最后一个块
                chunk += b'\x7f' * (chunk_size - len(chunk))
            
            self.send_audio(chunk)
            time.sleep(0.02)  # 20ms间隔
    
    def get_stats(self) -> dict:
        """获取RTP统计信息"""
        return {
            'local_endpoint': f"{self.local_ip}:{self.local_port}",
            'remote_endpoint': f"{self.remote_ip}:{self.remote_port}" if self.remote_ip else "未连接",
            'running': self.running,
            'ssrc': hex(self.ssrc),
            'sequence': self.sequence,
            'timestamp': self.timestamp,
            'send_queue_size': self.send_queue.qsize() if self.send_queue else 0
        }