"""
RTP 处理器
管理 RTP 会话的收发
"""

import socket
import threading
import queue
import time
import random
from typing import Optional, Callable, Tuple

from .packet import RTPPacket, RTPStats


class RTPHandler:
    """RTP 处理器"""
    
    def __init__(self, local_ip: str, local_port: int):
        """
        初始化 RTP 处理器
        
        Args:
            local_ip: 本地 IP 地址
            local_port: 本地 RTP 端口
        """
        self.local_ip = local_ip
        self.local_port = local_port
        self.remote_ip = None
        self.remote_port = None
        
        # Socket
        self.sock = None
        
        # RTP 参数
        self.ssrc = random.randint(0, 0xFFFFFFFF)
        self.sequence = random.randint(0, 0xFFFF)
        self.timestamp = random.randint(0, 0xFFFFFFFF)
        self.payload_type = 0  # 默认 PCMU
        
        # 控制标志
        self.running = False
        
        # 线程
        self.receive_thread = None
        self.send_thread = None
        
        # 队列
        self.send_queue = queue.Queue()
        self.receive_queue = queue.Queue()
        
        # 回调
        self.on_audio_received: Optional[Callable[[bytes], None]] = None
        
        # 统计
        self.stats = RTPStats()
        
        # 时间戳增量（20ms @ 8kHz = 160）
        self.timestamp_increment = 160
        
        print(f"🎵 RTP 处理器初始化: {local_ip}:{local_port}")
    
    def start(self, remote_ip: str, remote_port: int):
        """
        启动 RTP 会话
        
        Args:
            remote_ip: 远程 IP 地址
            remote_port: 远程 RTP 端口
        """
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        
        # 创建 UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.local_ip, self.local_port))
        self.sock.settimeout(0.1)
        
        self.running = True
        
        # 启动接收线程
        self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.receive_thread.start()
        
        # 启动发送线程
        self.send_thread = threading.Thread(target=self._send_loop, daemon=True)
        self.send_thread.start()
        
        print(f"🎵 RTP 会话启动: {self.local_ip}:{self.local_port} <-> {remote_ip}:{remote_port}")
    
    def stop(self):
        """停止 RTP 会话"""
        print("🔇 停止 RTP 会话...")
        self.running = False
        
        # 等待线程结束
        if self.receive_thread:
            self.receive_thread.join(timeout=1)
        if self.send_thread:
            self.send_thread.join(timeout=1)
        
        # 关闭 socket
        if self.sock:
            self.sock.close()
            self.sock = None
        
        print("🔇 RTP 会话已停止")
    
    def send_audio(self, audio_data: bytes, payload_type: Optional[int] = None,
                   marker: bool = False):
        """
        发送音频数据
        
        Args:
            audio_data: 音频数据（通常是 160 字节，20ms @ 8kHz）
            payload_type: 负载类型（默认使用初始化时的值）
            marker: 标记位（用于标记重要帧）
        """
        if not self.running or not self.remote_ip:
            return
        
        # 添加到发送队列
        self.send_queue.put((audio_data, payload_type, marker))
    
    def _send_loop(self):
        """发送线程主循环"""
        while self.running:
            try:
                # 从队列获取数据（超时避免阻塞）
                audio_data, payload_type, marker = self.send_queue.get(timeout=0.1)
                
                # 构建 RTP 包
                packet = self._build_rtp_packet(audio_data, payload_type, marker)
                
                # 发送
                if self.sock and self.remote_ip:
                    self.sock.sendto(packet.serialize(), (self.remote_ip, self.remote_port))
                    self.stats.on_packet_sent(packet)
                
                # 更新序列号和时间戳
                self.sequence = (self.sequence + 1) & 0xFFFF
                self.timestamp = (self.timestamp + self.timestamp_increment) & 0xFFFFFFFF
                
            except queue.Empty:
                continue
            except Exception as e:
                if self.running:
                    print(f"❌ RTP 发送错误: {e}")
    
    def _receive_loop(self):
        """接收线程主循环"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                
                # 解析 RTP 包
                try:
                    packet = RTPPacket.parse(data)
                    self.stats.on_packet_received(packet)
                    
                    # 处理音频数据
                    if packet.payload and self.on_audio_received:
                        self.on_audio_received(packet.payload)
                    
                    # 添加到接收队列（供其他处理使用）
                    self.receive_queue.put(packet)
                    
                except ValueError as e:
                    print(f"⚠️ RTP 包解析错误: {e}")
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"❌ RTP 接收错误: {e}")
    
    def _build_rtp_packet(self, payload: bytes, payload_type: Optional[int] = None,
                         marker: bool = False) -> RTPPacket:
        """
        构建 RTP 包
        
        Args:
            payload: 负载数据
            payload_type: 负载类型
            marker: 标记位
            
        Returns:
            RTPPacket 实例
        """
        if payload_type is None:
            payload_type = self.payload_type
        
        packet = RTPPacket(
            version=2,
            padding=False,
            extension=False,
            cc=0,
            marker=marker,
            payload_type=payload_type,
            sequence=self.sequence,
            timestamp=self.timestamp,
            ssrc=self.ssrc
        )
        
        packet.payload = payload
        
        return packet
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return self.stats.get_stats()
    
    def set_payload_type(self, payload_type: int):
        """设置默认负载类型"""
        self.payload_type = payload_type
    
    def set_audio_callback(self, callback: Callable[[bytes], None]):
        """设置音频接收回调"""
        self.on_audio_received = callback


class RTPSession:
    """RTP 会话管理器（管理多个 RTP 流）"""
    
    def __init__(self):
        self.sessions = {}  # call_id -> RTPHandler
        
    def create_session(self, call_id: str, local_ip: str, local_port: int) -> RTPHandler:
        """创建新的 RTP 会话"""
        if call_id in self.sessions:
            raise ValueError(f"会话 {call_id} 已存在")
        
        handler = RTPHandler(local_ip, local_port)
        self.sessions[call_id] = handler
        return handler
    
    def get_session(self, call_id: str) -> Optional[RTPHandler]:
        """获取 RTP 会话"""
        return self.sessions.get(call_id)
    
    def end_session(self, call_id: str):
        """结束 RTP 会话"""
        if call_id in self.sessions:
            handler = self.sessions[call_id]
            handler.stop()
            del self.sessions[call_id]
    
    def end_all_sessions(self):
        """结束所有会话"""
        for call_id in list(self.sessions.keys()):
            self.end_session(call_id)