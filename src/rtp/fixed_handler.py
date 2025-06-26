#!/usr/bin/env python3
"""
VTX AI Phone System - 修复的RTP处理器
专注解决：确保发送标准RTP包格式
"""

import socket
import struct
import threading
import time
from typing import Optional, Callable


class FixedRTPHandler:
    """修复的RTP处理器 - 确保发送标准RTP包"""
    
    def __init__(self, local_ip: str, local_port: int):
        self.local_ip = local_ip
        self.local_port = local_port
        self.remote_ip = None
        self.remote_port = None
        self.sock = None
        
        # RTP参数
        self.ssrc = 0x12345678  # 固定SSRC便于调试
        self.sequence = 1000    # 从1000开始便于识别
        self.timestamp = 0
        
        # 统计
        self.packets_sent = 0
        self.bytes_sent = 0
        
        # 音频回调
        self.audio_callback: Optional[Callable[[bytes], None]] = None
        
        print(f"🎵 修复版RTP处理器初始化: {local_ip}:{local_port}")
    
    def start(self, remote_ip: str, remote_port: int):
        """启动RTP会话"""
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((self.local_ip, self.local_port))
            self.sock.settimeout(0.1)
            
            print(f"✅ RTP会话启动: {self.local_ip}:{self.local_port} -> {remote_ip}:{remote_port}")
            
            # 启动接收线程
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
        except Exception as e:
            print(f"❌ RTP启动失败: {e}")
    
    def stop(self):
        """停止RTP会话"""
        self.running = False
        if self.sock:
            self.sock.close()
        print(f"🔇 RTP会话停止 (发送了{self.packets_sent}个包，{self.bytes_sent}字节)")
    
    def set_audio_callback(self, callback: Callable[[bytes], None]):
        """设置音频接收回调"""
        self.audio_callback = callback
    
    def send_audio_fixed(self, audio_data: bytes, payload_type: int = 0):
        """发送修复版音频数据"""
        if not self.sock or not self.remote_ip:
            print("⚠️ RTP未准备好")
            return
        
        try:
            # 构建标准RTP头部
            rtp_packet = self._build_standard_rtp_packet(audio_data, payload_type)
            
            # 发送数据包
            sent_bytes = self.sock.sendto(rtp_packet, (self.remote_ip, self.remote_port))
            
            # 更新统计
            self.packets_sent += 1
            self.bytes_sent += sent_bytes
            
            # 更新RTP参数
            self.sequence = (self.sequence + 1) & 0xFFFF
            self.timestamp = (self.timestamp + 160) & 0xFFFFFFFF  # 160 samples = 20ms @ 8kHz
            
            # 每50个包显示一次进度
            if self.packets_sent % 50 == 0:
                print(f"📤 RTP发送进度: {self.packets_sent}包 ({sent_bytes}字节/包)")
            
        except Exception as e:
            print(f"❌ RTP发送错误: {e}")
    
    def _build_standard_rtp_packet(self, payload: bytes, payload_type: int) -> bytes:
        """构建标准RTP数据包"""
        # RTP头部固定12字节
        # Byte 0: V(2) P(1) X(1) CC(4) = 10000000 = 0x80
        # Byte 1: M(1) PT(7) = 0 + payload_type
        # Bytes 2-3: 序列号 (网络字节序)
        # Bytes 4-7: 时间戳 (网络字节序)  
        # Bytes 8-11: SSRC (网络字节序)
        
        rtp_header = struct.pack('!BBHII',
            0x80,                    # V=2, P=0, X=0, CC=0
            payload_type & 0x7F,     # M=0, PT=payload_type
            self.sequence,           # 序列号
            self.timestamp,          # 时间戳
            self.ssrc               # SSRC
        )
        
        # 确保payload长度正确（160字节 = 20ms @ 8kHz）
        if len(payload) != 160:
            if len(payload) < 160:
                # 填充静音
                payload = payload + b'\xFF' * (160 - len(payload))
            else:
                # 截断
                payload = payload[:160]
        
        return rtp_header + payload
    
    def _receive_loop(self):
        """接收循环"""
        print("👂 开始监听对方音频...")
        
        while getattr(self, 'running', False):
            try:
                data, addr = self.sock.recvfrom(4096)
                
                if len(data) >= 12:  # 至少包含RTP头部
                    # 提取RTP负载
                    rtp_payload = data[12:]  # 跳过12字节RTP头部
                    
                    # 调用音频回调
                    if self.audio_callback and len(rtp_payload) > 0:
                        self.audio_callback(rtp_payload)
                
            except socket.timeout:
                continue
            except Exception as e:
                if getattr(self, 'running', False):
                    print(f"❌ RTP接收错误: {e}")
    
    def send_test_audio_fixed(self, test_audio: bytes):
        """发送修复版测试音频"""
        print(f"🎵 发送修复版测试音频: {len(test_audio)}字节")
        
        packet_size = 160  # 20ms @ 8kHz
        packets_total = len(test_audio) // packet_size
        
        print(f"📡 RTP发送: {packets_total}个包")
        print("🎧 请注意听测试音调...")
        
        start_time = time.time()
        
        for i in range(0, len(test_audio), packet_size):
            packet = test_audio[i:i+packet_size]
            
            # 发送RTP包
            self.send_audio_fixed(packet, payload_type=0)
            
            # 显示发送进度
            packet_num = (i // packet_size) + 1
            if packet_num % 25 == 0:  # 每0.5秒显示一次
                print(f"📤 发送进度: {packet_num}/{packets_total} ({packet_num*0.02:.1f}s)")
            
            time.sleep(0.02)  # 精确20ms间隔
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ 音频发送完成!")
        print(f"📊 传输统计:")
        print(f"  实际耗时: {duration:.2f}秒")
        print(f"  理论耗时: {packets_total * 0.02:.2f}秒")
        print(f"  发送包数: {self.packets_sent}")
        print(f"  发送字节: {self.bytes_sent}") 