"""
RTP 数据包格式
"""

import struct
from typing import Optional


class RTPPacket:
    """
    RTP 数据包
    
    RTP 头部格式:
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |V=2|P|X|  CC   |M|     PT      |       sequence number         |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                           timestamp                           |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |           synchronization source (SSRC) identifier            |
    +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+
    |            contributing source (CSRC) identifiers             |
    |                             ....                              |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    """
    
    HEADER_SIZE = 12  # 最小头部大小（不含 CSRC）
    
    def __init__(self, version: int = 2, padding: bool = False,
                 extension: bool = False, cc: int = 0, marker: bool = False,
                 payload_type: int = 0, sequence: int = 0,
                 timestamp: int = 0, ssrc: int = 0):
        """
        初始化 RTP 包
        
        Args:
            version: RTP 版本（通常是 2）
            padding: 是否有填充
            extension: 是否有扩展头
            cc: CSRC 计数
            marker: 标记位
            payload_type: 负载类型（0=PCMU, 8=PCMA 等）
            sequence: 序列号
            timestamp: 时间戳
            ssrc: 同步源标识符
        """
        self.version = version
        self.padding = padding
        self.extension = extension
        self.cc = cc
        self.marker = marker
        self.payload_type = payload_type
        self.sequence = sequence
        self.timestamp = timestamp
        self.ssrc = ssrc
        self.csrc = []  # CSRC 列表
        self.payload = b''
    
    @classmethod
    def parse(cls, data: bytes) -> 'RTPPacket':
        """
        解析 RTP 数据包
        
        Args:
            data: 原始数据包
            
        Returns:
            RTPPacket 实例
        """
        if len(data) < cls.HEADER_SIZE:
            raise ValueError(f"数据包太短: {len(data)} < {cls.HEADER_SIZE}")
        
        # 解析第一个字节
        byte0 = data[0]
        version = (byte0 >> 6) & 0x03
        padding = bool((byte0 >> 5) & 0x01)
        extension = bool((byte0 >> 4) & 0x01)
        cc = byte0 & 0x0F
        
        # 解析第二个字节
        byte1 = data[1]
        marker = bool((byte1 >> 7) & 0x01)
        payload_type = byte1 & 0x7F
        
        # 解析序列号、时间戳和 SSRC
        sequence = struct.unpack('!H', data[2:4])[0]
        timestamp = struct.unpack('!I', data[4:8])[0]
        ssrc = struct.unpack('!I', data[8:12])[0]
        
        # 创建包对象
        packet = cls(
            version=version,
            padding=padding,
            extension=extension,
            cc=cc,
            marker=marker,
            payload_type=payload_type,
            sequence=sequence,
            timestamp=timestamp,
            ssrc=ssrc
        )
        
        # 解析 CSRC（如果有）
        header_len = cls.HEADER_SIZE
        if cc > 0:
            csrc_end = header_len + cc * 4
            if len(data) < csrc_end:
                raise ValueError("数据包太短，无法包含所有 CSRC")
            
            for i in range(cc):
                csrc_start = header_len + i * 4
                csrc = struct.unpack('!I', data[csrc_start:csrc_start + 4])[0]
                packet.csrc.append(csrc)
            
            header_len = csrc_end
        
        # 处理扩展头（如果有）
        if extension:
            if len(data) < header_len + 4:
                raise ValueError("数据包太短，无法包含扩展头")
            
            ext_header = struct.unpack('!HH', data[header_len:header_len + 4])
            ext_len = ext_header[1] * 4
            header_len += 4 + ext_len
        
        # 提取负载
        if len(data) > header_len:
            packet.payload = data[header_len:]
        
        return packet
    
    def serialize(self) -> bytes:
        """
        序列化 RTP 数据包
        
        Returns:
            字节序列
        """
        # 构建第一个字节
        byte0 = (self.version << 6) | (int(self.padding) << 5) | \
                (int(self.extension) << 4) | (self.cc & 0x0F)
        
        # 构建第二个字节
        byte1 = (int(self.marker) << 7) | (self.payload_type & 0x7F)
        
        # 构建固定头部
        header = struct.pack(
            '!BBHII',
            byte0,
            byte1,
            self.sequence,
            self.timestamp,
            self.ssrc
        )
        
        # 添加 CSRC（如果有）
        for csrc in self.csrc[:self.cc]:
            header += struct.pack('!I', csrc)
        
        # 添加负载
        return header + self.payload
    
    def __repr__(self) -> str:
        return (f"RTPPacket(seq={self.sequence}, ts={self.timestamp}, "
                f"pt={self.payload_type}, marker={self.marker}, "
                f"payload_len={len(self.payload)})")
    
    def __str__(self) -> str:
        return self.__repr__()


class RTPStats:
    """RTP 统计信息"""
    
    def __init__(self):
        self.packets_sent = 0
        self.packets_received = 0
        self.bytes_sent = 0
        self.bytes_received = 0
        self.packets_lost = 0
        self.last_sequence = None
        self.jitter_buffer = []
        self.last_timestamp = None
    
    def on_packet_sent(self, packet: RTPPacket):
        """记录发送的包"""
        self.packets_sent += 1
        self.bytes_sent += len(packet.payload) + RTPPacket.HEADER_SIZE
    
    def on_packet_received(self, packet: RTPPacket):
        """记录接收的包"""
        self.packets_received += 1
        self.bytes_received += len(packet.payload) + RTPPacket.HEADER_SIZE
        
        # 检测丢包
        if self.last_sequence is not None:
            expected = (self.last_sequence + 1) & 0xFFFF
            if packet.sequence != expected:
                # 计算丢失的包数
                if packet.sequence > expected:
                    lost = packet.sequence - expected
                else:
                    # 序列号回绕
                    lost = (packet.sequence + 0x10000) - expected
                
                if lost < 100:  # 合理的丢包数
                    self.packets_lost += lost
        
        self.last_sequence = packet.sequence
        
        # 计算抖动
        if self.last_timestamp is not None:
            ts_diff = packet.timestamp - self.last_timestamp
            self.jitter_buffer.append(ts_diff)
            if len(self.jitter_buffer) > 100:
                self.jitter_buffer.pop(0)
        
        self.last_timestamp = packet.timestamp
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        stats = {
            'packets_sent': self.packets_sent,
            'packets_received': self.packets_received,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'packets_lost': self.packets_lost,
            'loss_rate': 0.0,
            'average_jitter': 0.0
        }
        
        # 计算丢包率
        total_expected = self.packets_received + self.packets_lost
        if total_expected > 0:
            stats['loss_rate'] = self.packets_lost / total_expected
        
        # 计算平均抖动
        if self.jitter_buffer:
            stats['average_jitter'] = sum(self.jitter_buffer) / len(self.jitter_buffer)
        
        return stats