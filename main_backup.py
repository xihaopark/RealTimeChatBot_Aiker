#!/usr/bin/env python3
"""
增强的 SIP 客户端 - 支持音频接听
基于 working_sip_client_v4.py，添加 SDP 和 RTP 支持
"""

import socket
import time
import hashlib
import uuid
import re
import threading
import sys
import os
import queue
import struct
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config.settings import settings

class SDPParser:
    """SDP 解析器"""
    
    @staticmethod
    def parse(sdp_text):
        """解析 SDP"""
        sdp = {
            'version': None,
            'origin': None,
            'session_name': None,
            'connection': None,
            'time': None,
            'media': []
        }
        
        current_media = None
        
        for line in sdp_text.strip().split('\n'):
            line = line.strip()
            if not line or '=' not in line:
                continue
                
            type_char, value = line.split('=', 1)
            
            if type_char == 'v':
                sdp['version'] = value
            elif type_char == 'o':
                sdp['origin'] = value
            elif type_char == 's':
                sdp['session_name'] = value
            elif type_char == 'c':
                if current_media:
                    current_media['connection'] = value
                else:
                    sdp['connection'] = value
            elif type_char == 't':
                sdp['time'] = value
            elif type_char == 'm':
                # m=audio 12345 RTP/AVP 0 8
                parts = value.split()
                current_media = {
                    'type': parts[0],
                    'port': int(parts[1]),
                    'protocol': parts[2],
                    'formats': parts[3:],
                    'attributes': []
                }
                sdp['media'].append(current_media)
            elif type_char == 'a' and current_media:
                current_media['attributes'].append(value)
        
        return sdp
    
    @staticmethod
    def build(local_ip, rtp_port, session_id=None, codecs=None):
        """构建 SDP"""
        if not session_id:
            session_id = str(int(time.time()))
        if not codecs:
            codecs = ['0', '8']  # PCMU, PCMA
        
        sdp_lines = [
            "v=0",
            f"o=- {session_id} {session_id} IN IP4 {local_ip}",
            "s=VTX AI Phone",
            f"c=IN IP4 {local_ip}",
            "t=0 0",
            f"m=audio {rtp_port} RTP/AVP {' '.join(codecs)}",
        ]
        
        # 添加编解码器映射
        if '0' in codecs:
            sdp_lines.append("a=rtpmap:0 PCMU/8000")
        if '8' in codecs:
            sdp_lines.append("a=rtpmap:8 PCMA/8000")
        
        sdp_lines.append("a=sendrecv")
        
        return '\r\n'.join(sdp_lines)


class RTPHandler:
    """RTP 处理器"""
    
    def __init__(self, local_ip, local_port):
        self.local_ip = local_ip
        self.local_port = local_port
        self.remote_ip = None
        self.remote_port = None
        self.sock = None
        self.ssrc = random.randint(0, 0xFFFFFFFF)
        self.sequence = random.randint(0, 0xFFFF)
        self.timestamp = random.randint(0, 0xFFFFFFFF)
        self.running = False
        self.receive_thread = None
        self.send_queue = queue.Queue()
        self.audio_callback = None  # 音频接收回调
        
    def set_audio_callback(self, callback):
        """设置音频接收回调"""
        self.audio_callback = callback
        
    def start(self, remote_ip, remote_port):
        """启动 RTP"""
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        
        # 创建 UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.local_ip, self.local_port))
        self.sock.settimeout(0.1)
        
        self.running = True
        
        # 启动接收线程
        self.receive_thread = threading.Thread(target=self._receive_loop)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        
        print(f"🎵 RTP 处理器初始化: {self.local_ip}:{self.local_port}")
        print(f"🎵 RTP 会话启动: {self.local_ip}:{self.local_port} <-> {remote_ip}:{remote_port}")
    
    def stop(self):
        """停止 RTP"""
        self.running = False
        if self.sock:
            self.sock.close()
        print("🔇 停止 RTP 会话...")
        if self.receive_thread:
            self.receive_thread.join(timeout=1)
        print("🔇 RTP 会话已停止")
    
    def send_audio(self, audio_data, payload_type=0):
        """发送音频数据"""
        if not self.running or not self.remote_ip:
            return
        
        # 构建 RTP 包
        packet = self._build_rtp_packet(audio_data, payload_type)
        
        # 发送
        try:
            self.sock.sendto(packet, (self.remote_ip, self.remote_port))
            
            # 更新序列号和时间戳
            self.sequence = (self.sequence + 1) & 0xFFFF
            self.timestamp = (self.timestamp + 160) & 0xFFFFFFFF  # 20ms @ 8kHz
        except Exception as e:
            print(f"❌ RTP 发送错误: {e}")
    
    def _build_rtp_packet(self, payload, payload_type):
        """构建 RTP 包"""
        # RTP 头部
        # V=2, P=0, X=0, CC=0, M=1, PT=payload_type (设置标记位为1，与接收包一致)
        byte0 = 0x80  # V=2, P=0, X=0, CC=0
        byte1 = 0x80 | (payload_type & 0x7F)  # 设置标记位为1
        
        # 打包头部
        header = struct.pack('!BBHII',
                           byte0,
                           byte1,
                           self.sequence,
                           self.timestamp,
                           self.ssrc)
        
        return header + payload
    
    def _receive_loop(self):
        """接收循环"""
        print(f"🎧 RTP接收循环启动: 监听 {self.local_ip}:{self.local_port}")
        seen_payload_types = set()
        packet_count = 0
        last_report_time = time.time()
        voice_packet_count = 0
        last_voice_time = 0
        
        # 创建RTP包保存目录
        rtp_samples_dir = "rtp_samples"
        if not os.path.exists(rtp_samples_dir):
            os.makedirs(rtp_samples_dir)
        
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                packet_count += 1
                
                # 解析 RTP 包
                if len(data) >= 12:  # RTP 头部至少 12 字节
                    # 解析RTP头部
                    rtp_header = self._parse_rtp_header(data[:12])
                    payload_type = rtp_header['payload_type']
                    payload = data[12:]
                    
                    # 只在新payload type出现时输出一次详细信息
                    if payload_type not in seen_payload_types:
                        seen_payload_types.add(payload_type)
                        print(f"[RTP分析] 发现新payload_type={payload_type} ({self._payload_type_to_codec(payload_type)})")
                        
                        # 保存前几个包作为样本
                        sample_file = f"{rtp_samples_dir}/sample_payload_{payload_type}_{int(time.time())}.bin"
                        with open(sample_file, 'wb') as f:
                            f.write(data)
                        print(f"[RTP分析] 保存样本到: {sample_file}")
                        
                        # 详细解析并显示包结构
                        self._analyze_rtp_packet(data, payload_type)
                    
                    # 专门检测人声活动
                    if payload_type in [0, 8]:  # PCMU/PCMA音频包
                        voice_detected = self._detect_voice_activity(payload, payload_type)
                        if voice_detected:
                            voice_packet_count += 1
                            current_time = time.time()
                            
                            # 如果距离上次人声检测超过1秒，认为是新的人声片段
                            if current_time - last_voice_time > 1.0:
                                print(f"🎤 检测到人声活动! (第{voice_packet_count}个语音包)")
                                last_voice_time = current_time
                                
                                # 保存人声包样本
                                voice_sample_file = f"{rtp_samples_dir}/voice_sample_{int(current_time)}.bin"
                                with open(voice_sample_file, 'wb') as f:
                                    f.write(data)
                                print(f"💾 保存人声样本: {voice_sample_file}")
                                
                                # 分析人声包
                                self._analyze_voice_packet(data, payload_type)
                    
                    # 每10秒报告一次接收状态（而不是每个包都显示）
                    current_time = time.time()
                    if current_time - last_report_time >= 10:
                        print(f"🎧 RTP接收状态: 已接收 {packet_count} 个包, payload_types: {seen_payload_types}")
                        if voice_packet_count > 0:
                            print(f"🎤 人声检测: 发现 {voice_packet_count} 个语音包")
                        last_report_time = current_time
                        packet_count = 0
                    
                    # 调用音频回调
                    if self.audio_callback and payload:
                        try:
                            self.audio_callback(payload)
                        except Exception as e:
                            print(f"❌ 音频回调错误: {e}")
                else:
                    print(f"⚠️ RTP包过短: {len(data)} 字节")
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"❌ RTP 接收错误: {e}")
                    import traceback
                    traceback.print_exc()
        
        print("🎧 RTP接收循环已停止")
    
    def _parse_rtp_header(self, header_data):
        """解析RTP头部"""
        if len(header_data) < 12:
            return None
        
        # RTP头部格式: V=2, P=0, X=0, CC=0, M=1, PT=0, Sequence=2, Timestamp=4, SSRC=4
        byte0, byte1, sequence, timestamp, ssrc = struct.unpack('!BBHII', header_data[:12])
        
        version = (byte0 >> 6) & 0x03
        padding = (byte0 >> 5) & 0x01
        extension = (byte0 >> 4) & 0x01
        csrc_count = byte0 & 0x0F
        marker = (byte1 >> 7) & 0x01
        payload_type = byte1 & 0x7F
        
        return {
            'version': version,
            'padding': padding,
            'extension': extension,
            'csrc_count': csrc_count,
            'marker': marker,
            'payload_type': payload_type,
            'sequence_number': sequence,
            'timestamp': timestamp,
            'ssrc': ssrc
        }
    
    def _analyze_rtp_packet(self, packet_data, payload_type):
        """分析RTP包结构"""
        print(f"\n🔍 RTP包结构分析 (payload_type={payload_type}):")
        print("=" * 60)
        
        # 解析头部
        header = self._parse_rtp_header(packet_data[:12])
        if header:
            print(f"📋 RTP头部信息:")
            print(f"  版本: {header['version']}")
            print(f"  填充: {header['padding']}")
            print(f"  扩展: {header['extension']}")
            print(f"  CSRC数量: {header['csrc_count']}")
            print(f"  标记: {header['marker']}")
            print(f"  负载类型: {header['payload_type']} ({self._payload_type_to_codec(header['payload_type'])})")
            print(f"  序列号: {header['sequence_number']}")
            print(f"  时间戳: {header['timestamp']}")
            print(f"  SSRC: 0x{header['ssrc']:08X}")
        
        # 分析负载数据
        payload = packet_data[12:]
        print(f"\n📦 负载数据:")
        print(f"  总包大小: {len(packet_data)} 字节")
        print(f"  头部大小: 12 字节")
        print(f"  负载大小: {len(payload)} 字节")
        
        # 显示负载数据的前16字节（十六进制）
        if payload:
            hex_data = ' '.join(f'{b:02x}' for b in payload[:16])
            print(f"  负载前16字节: {hex_data}")
            
            # 如果是音频数据，分析音频特征
            if payload_type in [0, 8]:  # PCMU/PCMA
                print(f"  音频分析:")
                # 计算音频能量
                if payload_type == 0:  # PCMU
                    # μ-law解码（简化）
                    energy = sum(abs(b - 0x7F) for b in payload[:16])
                else:  # PCMA
                    # A-law解码（简化）
                    energy = sum(abs(b - 0x55) for b in payload[:16])
                
                print(f"    能量水平: {energy}")
                if energy > 100:
                    print(f"    🎤 检测到语音活动")
                else:
                    print(f"    🔇 静音或低音量")
        
        print("=" * 60)
    
    def _payload_type_to_codec(self, payload_type):
        """将payload type转换为编解码器名称"""
        codec_map = {
            0: "PCMU (G.711 μ-law)",
            8: "PCMA (G.711 A-law)",
            13: "CN (Comfort Noise)",
            101: "DTMF",
            110: "PCMU (G.711 μ-law)",
            111: "PCMA (G.711 A-law)"
        }
        return codec_map.get(payload_type, f"未知({payload_type})")
    
    def _detect_voice_activity(self, payload, payload_type):
        """检测语音活动"""
        if not payload:
            return False
        
        # 计算音频能量
        if payload_type == 0:  # PCMU
            # μ-law解码（简化）
            energy = sum(abs(b - 0x7F) for b in payload)
            avg_energy = energy / len(payload)
            
            # 检测静音
            silence_count = sum(1 for b in payload if b == 0xFF or b == 0x7F)
            silence_ratio = silence_count / len(payload)
            
            # 语音活动检测条件
            if avg_energy > 30 and silence_ratio < 0.7:  # 能量足够且不是主要静音
                return True
                
        elif payload_type == 8:  # PCMA
            # A-law解码（简化）
            energy = sum(abs(b - 0x55) for b in payload)
            avg_energy = energy / len(payload)
            
            if avg_energy > 30:
                return True
        
        return False
    
    def _analyze_voice_packet(self, packet_data, payload_type):
        """分析人声包"""
        print(f"\n🎤 人声包分析 (payload_type={payload_type}):")
        print("=" * 50)
        
        # 解析头部
        header = self._parse_rtp_header(packet_data[:12])
        if header:
            print(f"📋 RTP头部:")
            print(f"  序列号: {header['sequence_number']}")
            print(f"  时间戳: {header['timestamp']}")
            print(f"  标记: {header['marker']}")
        
        # 分析负载
        payload = packet_data[12:]
        print(f"\n🎵 音频分析:")
        print(f"  负载大小: {len(payload)} 字节")
        
        # 显示前32字节的十六进制
        hex_data = ' '.join(f'{b:02x}' for b in payload[:32])
        print(f"  前32字节: {hex_data}")
        
        # 详细音频分析
        if payload_type == 0:  # PCMU
            energy = sum(abs(b - 0x7F) for b in payload)
            avg_energy = energy / len(payload)
            silence_count = sum(1 for b in payload if b == 0xFF or b == 0x7F)
            silence_ratio = silence_count / len(payload)
            
            print(f"  平均能量: {avg_energy:.2f}")
            print(f"  静音比例: {silence_ratio:.2%}")
            
            # 判断语音特征
            if avg_energy > 50:
                print(f"  🔊 强语音信号")
            elif avg_energy > 20:
                print(f"  🎤 中等语音信号")
            else:
                print(f"  🔈 弱语音信号")
                
            if silence_ratio < 0.3:
                print(f"  🎵 连续语音")
            elif silence_ratio < 0.7:
                print(f"  🎤 混合语音")
            else:
                print(f"  🔇 主要是静音")
        
        print("=" * 50)


class G711Codec:
    """G.711 编解码器"""
    
    # μ-law 编码表
    ULAW_BIAS = 132
    
    @staticmethod
    def linear_to_ulaw(sample):
        """线性 PCM 转 μ-law"""
        # 简化实现
        if sample < 0:
            sample = -sample
            sign = 0x80
        else:
            sign = 0
        
        if sample > 32635:
            sample = 32635
        
        sample += G711Codec.ULAW_BIAS
        
        # 查找段
        seg = 0
        for i in range(8):
            if sample >= (128 << i):
                seg = i
        
        # 计算底数
        if seg >= 8:
            uval = 0x7F
        else:
            uval = (seg << 4) | ((sample >> (seg + 3)) & 0x0F)
        
        return (sign | uval) ^ 0xFF
    
    @staticmethod
    def generate_dtmf(digit, duration=0.2, sample_rate=8000):
        """生成 DTMF 音调"""
        # DTMF 频率表
        dtmf_freqs = {
            '1': (697, 1209), '2': (697, 1336), '3': (697, 1477),
            '4': (770, 1209), '5': (770, 1336), '6': (770, 1477),
            '7': (852, 1209), '8': (852, 1336), '9': (852, 1477),
            '*': (941, 1209), '0': (941, 1336), '#': (941, 1477),
        }
        
        if digit not in dtmf_freqs:
            return b''
        
        low_freq, high_freq = dtmf_freqs[digit]
        samples = int(duration * sample_rate)
        
        # 生成音调
        audio_data = bytearray()
        for i in range(samples):
            t = i / sample_rate
            # 混合两个频率
            sample = int(16383 * (
                0.5 * (
                    math.sin(2 * math.pi * low_freq * t) +
                    math.sin(2 * math.pi * high_freq * t)
                )
            ))
            # 转换为 μ-law
            ulaw = G711Codec.linear_to_ulaw(sample)
            audio_data.append(ulaw)
        
        return bytes(audio_data)


class EnhancedSIPClient:
    def __init__(self):
        # 继承原有配置
        self.server = settings.vtx.server
        self.port = settings.vtx.port
        self.domain = settings.vtx.domain
        
        ext = settings.get_extension('101')
        self.username = ext.username
        self.password = ext.password
        
        self.server_ip = socket.gethostbyname(self.server)
        self.local_ip = self._get_local_ip()
        self.sock = None
        self.local_port = None
        
        # SIP 会话参数
        self.call_id = f"{uuid.uuid4()}@{self.local_ip}"
        self.from_tag = uuid.uuid4().hex[:8]
        self.cseq = 0
        
        # 认证参数
        self.realm = None
        self.nonce = None
        self.registered = False
        self.running = False
        self.expires = 60
        
        # 注册响应队列
        self.register_response_queue = queue.Queue()
        self.waiting_for_register = False
        self.current_cseq = None
        
        # 通话管理
        self.active_calls = {}  # Call-ID -> RTPHandler
        self.processed_invites = set()
        self.call_tags = {}
        
        # RTP 端口范围
        self.rtp_port_start = 10000
        self.rtp_port_end = 20000
        self.next_rtp_port = self.rtp_port_start
        
        print(f"🔍 增强 SIP 客户端初始化")
        print(f"服务器: {self.server}:{self.port} ({self.server_ip})")
        print(f"域名: {self.domain}")
        print(f"本地IP: {self.local_ip}")
        print(f"用户名: {self.username}")
        print("-" * 50)
    
    def start(self):
        """启动客户端"""
        try:
            # 创建并绑定socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(5)
            
            # 绑定到随机端口
            self.sock.bind(('0.0.0.0', 0))
            self.local_port = self.sock.getsockname()[1]
            print(f"📍 绑定到本地端口: {self.local_port}")
            
            # 先启动接收线程
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_loop)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            # 执行初始注册
            if self.initial_register():
                # 启动保活线程
                self.keepalive_thread = threading.Thread(target=self._keepalive_loop)
                self.keepalive_thread.daemon = True
                self.keepalive_thread.start()
                
                print("\n✅ 增强 SIP 客户端启动成功!")
                print(f"📞 可以接收来电: {settings.vtx.did_number}")
                print("🎵 支持音频通话")
                return True
            else:
                print("❌ 注册失败，无法启动")
                self.running = False
                return False
                
        except Exception as e:
            print(f"❌ 启动失败: {e}")
            return False
    
    def _handle_invite(self, message, addr, call_id):
        """处理 INVITE 请求（支持音频）"""
        # 提取信息
        from_match = re.search(r'From:\s*(.+)', message, re.IGNORECASE)
        to_match = re.search(r'To:\s*(.+)', message, re.IGNORECASE)
        
        caller = "Unknown"
        if from_match:
            from_header = from_match.group(1)
            num_match = re.search(r'sip:([^@]+)@', from_header)
            if num_match:
                caller = num_match.group(1)
        
        print(f"📞 来电号码: {caller}")
        
        # 生成 tag
        to_tag = uuid.uuid4().hex[:8]
        self.call_tags[call_id] = to_tag
        
        # 发送 100 Trying
        self._send_trying(message, addr)
        
        # 发送 180 Ringing
        time.sleep(0.1)
        self._send_ringing(message, addr, to_tag)
        
        # 解析 SDP
        sdp_start = message.find('\r\n\r\n')
        if sdp_start > 0:
            sdp_text = message[sdp_start+4:]
            sdp = SDPParser.parse(sdp_text)
            
            # 获取远程 RTP 信息
            if sdp['media']:
                audio_media = sdp['media'][0]
                remote_port = audio_media['port']
                
                # 获取远程 IP（从 c= 行）
                connection = audio_media.get('connection') or sdp.get('connection')
                if connection:
                    remote_ip = connection.split()[-1]
                else:
                    remote_ip = addr[0]
                
                print(f"🎵 远程 RTP: {remote_ip}:{remote_port}")
                
                # 分配本地 RTP 端口
                local_rtp_port = self._get_next_rtp_port()
                
                # 创建 RTP 处理器
                rtp_handler = RTPHandler(self.local_ip, local_rtp_port)
                self.active_calls[call_id] = rtp_handler
                
                # 延迟接听
                time.sleep(2)
                
                # 发送 200 OK with SDP
                self._send_ok_with_sdp(message, addr, to_tag, local_rtp_port)
                
                # 启动 RTP
                rtp_handler.start(remote_ip, remote_port)
                
                # 发送测试音频 "1871"
                threading.Thread(target=self._send_test_audio, 
                               args=(rtp_handler,)).start()
        else:
            # 没有 SDP，发送忙音
            time.sleep(2)
            self._send_busy_here(message, addr, to_tag)
    
    def _send_ok_with_sdp(self, invite_message, addr, to_tag, rtp_port):
        """发送 200 OK with SDP"""
        headers = self._extract_headers(invite_message)
        
        # 添加 tag 到 To 头部
        to_with_tag = headers['to']
        if 'tag=' not in to_with_tag:
            to_with_tag = f"{to_with_tag};tag={to_tag}"
        
        # 构建 SDP
        sdp = SDPParser.build(self.local_ip, rtp_port)
        
        response_lines = [
            "SIP/2.0 200 OK",
            headers['via'],
            headers['from'],
            to_with_tag,
            headers['call_id'],
            headers['cseq'],
            f"Contact: <sip:{self.username}@{self.local_ip}:{self.local_port}>",
            "Content-Type: application/sdp",
            f"Content-Length: {len(sdp)}",
            "",
            sdp
        ]
        
        response = "\r\n".join(response_lines)
        self.sock.sendto(response.encode(), addr)
        print("📤 发送: 200 OK (with SDP)")
    
    def _send_test_audio(self, rtp_handler):
        """发送测试音频 1871"""
        print("🎵 开始发送测试音频: 1871")
        
        # 先等待一下，确保对方准备好
        time.sleep(0.5)
        
        # 使用我们生成的测试音频文件
        try:
            with open('test_audio.ulaw', 'rb') as f:
                test_audio = f.read()
            print(f"📊 加载测试音频: {len(test_audio)} 字节, 约 {len(test_audio)/8000:.1f} 秒")
        except FileNotFoundError:
            print("❌ 测试音频文件不存在，生成简单音频")
            # 生成简单的440Hz音频
            test_audio = G711Codec.generate_dtmf('1', duration=3.0)
            print(f"📊 生成简单音频: {len(test_audio)} 字节")
        
        # 分包发送（每包 20ms）
        packet_size = 160  # 20ms @ 8kHz
        packets_sent = 0
        
        for i in range(0, len(test_audio), packet_size):
            packet = test_audio[i:i+packet_size]
            
            # 确保包大小正确
            if len(packet) < packet_size:
                packet += b'\xFF' * (packet_size - len(packet))
            
            rtp_handler.send_audio(packet, payload_type=0)
            packets_sent += 1
            
            # 每秒打印进度
            if packets_sent % 50 == 0:
                print(f"📤 已发送 {packets_sent} 个包 ({packets_sent * 0.02:.1f}秒)")
            
            time.sleep(0.02)  # 20ms
        
        print(f"✅ 测试音频发送完成: {packets_sent} 个包")
    
    def _get_next_rtp_port(self):
        """获取下一个可用的 RTP 端口"""
        port = self.next_rtp_port
        self.next_rtp_port += 2  # RTP 使用偶数端口
        if self.next_rtp_port > self.rtp_port_end:
            self.next_rtp_port = self.rtp_port_start
        return port
    
    def _handle_bye(self, message, addr):
        """处理 BYE 请求"""
        # 提取 Call-ID
        call_id_match = re.search(r'Call-ID:\s*(.+)', message, re.IGNORECASE)
        if call_id_match:
            call_id = call_id_match.group(1).strip()
            
            # 停止 RTP
            if call_id in self.active_calls:
                rtp_handler = self.active_calls[call_id]
                rtp_handler.stop()
                del self.active_calls[call_id]
                print(f"🔇 停止 RTP: {call_id}")
        
        # 发送 200 OK
        headers = self._extract_headers(message)
        
        response_lines = [
            "SIP/2.0 200 OK",
            headers.get('via', ''),
            headers.get('from', ''),
            headers.get('to', ''),
            headers.get('call_id', ''),
            headers.get('cseq', ''),
            "Content-Length: 0",
            "",
            ""
        ]
        
        response = "\r\n".join(response_lines)
        self.sock.sendto(response.encode(), addr)
        print("📤 发送: 200 OK (BYE)")
    
    # 继承其他方法...
    def initial_register(self):
        """初始注册"""
        print("\n🧪 执行初始注册...")
        
        try:
            # Step 1: 发送初始REGISTER
            self.cseq += 1
            self.current_cseq = self.cseq
            self.waiting_for_register = True
            
            register1 = self._build_register()
            print(f"📤 [Step 1] 发送初始REGISTER (CSeq: {self.cseq})...")
            self.sock.sendto(register1.encode(), (self.server_ip, self.port))
            
            # 等待响应
            try:
                response = self.register_response_queue.get(timeout=5)
            except queue.Empty:
                print("❌ 注册超时")
                return False
            finally:
                self.waiting_for_register = False
            
            if "407 Proxy Authentication Required" not in response:
                print(f"❌ 意外的响应")
                return False
            
            print("✅ 收到407，需要认证")
            
            # 提取认证信息
            auth_match = re.search(r'Proxy-Authenticate: Digest (.+)', response)
            if not auth_match:
                print("❌ 无法提取认证信息")
                return False
            
            auth_params = self._parse_auth_header(auth_match.group(1))
            self.realm = auth_params.get('realm', self.domain)
            self.nonce = auth_params.get('nonce', '')
            
            print(f"📋 保存认证参数: realm={self.realm}")
            
            # Step 2: 发送带认证的REGISTER
            return self.refresh_register()
                
        except Exception as e:
            print(f"❌ 注册错误: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def refresh_register(self):
        """刷新注册"""
        try:
            self.cseq += 1
            self.current_cseq = self.cseq
            self.waiting_for_register = True
            
            auth_header = self._build_auth_header()
            register = self._build_register(auth_header=auth_header)
            
            print(f"📤 发送认证REGISTER (CSeq: {self.cseq})...")
            self.sock.sendto(register.encode(), (self.server_ip, self.port))
            
            # 等待响应
            try:
                response = self.register_response_queue.get(timeout=5)
            except queue.Empty:
                print("❌ 刷新超时")
                return False
            finally:
                self.waiting_for_register = False
            
            if "200 OK" in response:
                self.registered = True
                print("✅ 注册成功！")
                
                # 提取过期时间
                expires_match = re.search(r'Expires:\s*(\d+)', response)
                if expires_match:
                    self.expires = int(expires_match.group(1))
                    print(f"📞 注册有效期: {self.expires}秒")
                
                return True
                
            elif "407 Proxy Authentication Required" in response:
                print("⚠️ 需要重新认证")
                auth_match = re.search(r'Proxy-Authenticate: Digest (.+)', response)
                if auth_match:
                    auth_params = self._parse_auth_header(auth_match.group(1))
                    self.nonce = auth_params.get('nonce', '')
                    return self.refresh_register()
                    
            else:
                print(f"❌ 注册失败")
                return False
                
        except Exception as e:
            print(f"❌ 刷新错误: {e}")
            return False
    
    def _receive_loop(self):
        """接收循环"""
        print(f"🎧 RTP接收循环启动: 监听 {self.local_ip}:{self.local_port}")
        seen_payload_types = set()
        packet_count = 0
        last_report_time = time.time()
        voice_packet_count = 0
        last_voice_time = 0
        
        # 创建RTP包保存目录
        rtp_samples_dir = "rtp_samples"
        if not os.path.exists(rtp_samples_dir):
            os.makedirs(rtp_samples_dir)
        
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                packet_count += 1
                
                # 解析 RTP 包
                if len(data) >= 12:  # RTP 头部至少 12 字节
                    # 解析RTP头部
                    rtp_header = self._parse_rtp_header(data[:12])
                    payload_type = rtp_header['payload_type']
                    payload = data[12:]
                    
                    # 只在新payload type出现时输出一次详细信息
                    if payload_type not in seen_payload_types:
                        seen_payload_types.add(payload_type)
                        print(f"[RTP分析] 发现新payload_type={payload_type} ({self._payload_type_to_codec(payload_type)})")
                        
                        # 保存前几个包作为样本
                        sample_file = f"{rtp_samples_dir}/sample_payload_{payload_type}_{int(time.time())}.bin"
                        with open(sample_file, 'wb') as f:
                            f.write(data)
                        print(f"[RTP分析] 保存样本到: {sample_file}")
                        
                        # 详细解析并显示包结构
                        self._analyze_rtp_packet(data, payload_type)
                    
                    # 专门检测人声活动
                    if payload_type in [0, 8]:  # PCMU/PCMA音频包
                        voice_detected = self._detect_voice_activity(payload, payload_type)
                        if voice_detected:
                            voice_packet_count += 1
                            current_time = time.time()
                            
                            # 如果距离上次人声检测超过1秒，认为是新的人声片段
                            if current_time - last_voice_time > 1.0:
                                print(f"🎤 检测到人声活动! (第{voice_packet_count}个语音包)")
                                last_voice_time = current_time
                                
                                # 保存人声包样本
                                voice_sample_file = f"{rtp_samples_dir}/voice_sample_{int(current_time)}.bin"
                                with open(voice_sample_file, 'wb') as f:
                                    f.write(data)
                                print(f"💾 保存人声样本: {voice_sample_file}")
                                
                                # 分析人声包
                                self._analyze_voice_packet(data, payload_type)
                    
                    # 每10秒报告一次接收状态（而不是每个包都显示）
                    current_time = time.time()
                    if current_time - last_report_time >= 10:
                        print(f"🎧 RTP接收状态: 已接收 {packet_count} 个包, payload_types: {seen_payload_types}")
                        if voice_packet_count > 0:
                            print(f"🎤 人声检测: 发现 {voice_packet_count} 个语音包")
                        last_report_time = current_time
                        packet_count = 0
                    
                    # 调用音频回调
                    if self.audio_callback and payload:
                        try:
                            self.audio_callback(payload)
                        except Exception as e:
                            print(f"❌ 音频回调错误: {e}")
                else:
                    print(f"⚠️ RTP包过短: {len(data)} 字节")
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"❌ RTP 接收错误: {e}")
                    import traceback
                    traceback.print_exc()
        
        print("🎧 RTP接收循环已停止")
    
    def _keepalive_loop(self):
        """保活循环"""
        while self.running:
            wait_time = max(self.expires // 2, 20)
            time.sleep(wait_time)
            
            if self.running:
                print(f"\n🔄 刷新注册...")
                if not self.refresh_register():
                    print("⚠️ 刷新失败，尝试重新注册...")
                    self.initial_register()
    
    def _resend_response(self, message, addr, call_id):
        """重发之前的响应"""
        # 获取保存的 tag
        to_tag = self.call_tags.get(call_id)
        if to_tag:
            # 直接发送最终响应（486 Busy）
            self._send_busy_here(message, addr, to_tag)
    
    def _send_trying(self, invite_message, addr):
        """发送 100 Trying"""
        # 提取所有必要的头部
        headers = self._extract_headers(invite_message)
        
        response_lines = [
            "SIP/2.0 100 Trying",
            headers['via'],
            headers['from'],
            headers['to'],  # 100 Trying 不需要 tag
            headers['call_id'],
            headers['cseq'],
            "Content-Length: 0",
            "",
            ""
        ]
        
        response = "\r\n".join(response_lines)
        self.sock.sendto(response.encode(), addr)
        print("📤 发送: 100 Trying")
    
    def _send_ringing(self, invite_message, addr, to_tag):
        """发送 180 Ringing"""
        headers = self._extract_headers(invite_message)
        
        # 添加 tag 到 To 头部
        to_with_tag = headers['to']
        if 'tag=' not in to_with_tag:
            to_with_tag = f"{to_with_tag};tag={to_tag}"
        
        response_lines = [
            "SIP/2.0 180 Ringing",
            headers['via'],
            headers['from'],
            to_with_tag,
            headers['call_id'],
            headers['cseq'],
            f"Contact: <sip:{self.username}@{self.local_ip}:{self.local_port}>",
            "Content-Length: 0",
            "",
            ""
        ]
        
        response = "\r\n".join(response_lines)
        self.sock.sendto(response.encode(), addr)
        print("📤 发送: 180 Ringing")
    
    def _send_busy_here(self, invite_message, addr, to_tag):
        """发送 486 Busy Here"""
        headers = self._extract_headers(invite_message)
        
        # 添加 tag 到 To 头部
        to_with_tag = headers['to']
        if 'tag=' not in to_with_tag:
            to_with_tag = f"{to_with_tag};tag={to_tag}"
        
        response_lines = [
            "SIP/2.0 486 Busy Here",
            headers['via'],
            headers['from'],
            to_with_tag,
            headers['call_id'],
            headers['cseq'],
            "Content-Length: 0",
            "",
            ""
        ]
        
        response = "\r\n".join(response_lines)
        self.sock.sendto(response.encode(), addr)
        print("📤 发送: 486 Busy Here")
    
    def _extract_headers(self, message):
        """提取所有必要的头部（保持原始格式）"""
        headers = {}
        
        # 使用更精确的正则表达式
        patterns = {
            'via': r'^Via:\s*(.+)$',
            'from': r'^From:\s*(.+)$',
            'to': r'^To:\s*(.+)$',
            'call_id': r'^Call-ID:\s*(.+)$',
            'cseq': r'^CSeq:\s*(.+)$'
        }
        
        lines = message.split('\n')
        for line in lines:
            line = line.rstrip('\r')
            for key, pattern in patterns.items():
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    headers[key] = line  # 保持原始的整行
                    break
        
        return headers
    
    def _handle_options(self, message, addr):
        """处理OPTIONS请求"""
        headers = self._extract_headers(message)
        
        response_lines = [
            "SIP/2.0 200 OK",
            headers.get('via', ''),
            headers.get('from', ''),
            headers.get('to', ''),
            headers.get('call_id', ''),
            headers.get('cseq', ''),
            "Allow: INVITE, ACK, CANCEL, BYE, OPTIONS",
            "Accept: application/sdp",
            "Content-Length: 0",
            "",
            ""
        ]
        
        response = "\r\n".join(response_lines)
        self.sock.sendto(response.encode(), addr)
    
    def _handle_cancel(self, message, addr):
        """处理CANCEL请求"""
        # 发送 200 OK for CANCEL
        headers = self._extract_headers(message)
        
        response_lines = [
            "SIP/2.0 200 OK",
            headers.get('via', ''),
            headers.get('from', ''),
            headers.get('to', ''),
            headers.get('call_id', ''),
            headers.get('cseq', ''),
            "Content-Length: 0",
            "",
            ""
        ]
        
        response = "\r\n".join(response_lines)
        self.sock.sendto(response.encode(), addr)
        print("📤 发送: 200 OK (CANCEL)")
        
        # TODO: 发送 487 Request Terminated for original INVITE
    
    def _build_register(self, auth_header=None):
        """构建REGISTER消息"""
        branch = f"z9hG4bK{uuid.uuid4().hex}"
        
        headers = [
            f"REGISTER sip:{self.domain} SIP/2.0",
            f"Via: SIP/2.0/UDP {self.local_ip}:{self.local_port};branch={branch};rport",
            f"From: <sip:{self.username}@{self.domain}>;tag={self.from_tag}",
            f"To: <sip:{self.username}@{self.domain}>",
            f"Call-ID: {self.call_id}",
            f"CSeq: {self.cseq} REGISTER",
            f"Contact: <sip:{self.username}@{self.local_ip}:{self.local_port}>",
            f"Max-Forwards: 70",
            f"User-Agent: VTX-AI-System/1.0",
            f"Expires: {self.expires}",
            f"Allow: INVITE, ACK, CANCEL, BYE, OPTIONS"
        ]
        
        if auth_header:
            headers.append(f"Proxy-Authorization: {auth_header}")
        
        headers.extend(["Content-Length: 0", "", ""])
        
        return "\r\n".join(headers)
    
    def _build_auth_header(self):
        """构建认证头"""
        uri = f"sip:{self.domain}"
        
        ha1 = hashlib.md5(f"{self.username}:{self.realm}:{self.password}".encode()).hexdigest()
        ha2 = hashlib.md5(f"REGISTER:{uri}".encode()).hexdigest()
        response = hashlib.md5(f"{ha1}:{self.nonce}:{ha2}".encode()).hexdigest()
        
        return (
            f'Digest username="{self.username}", '
            f'realm="{self.realm}", '
            f'nonce="{self.nonce}", '
            f'uri="{uri}", '
            f'response="{response}", '
            f'algorithm=MD5'
        )
    
    def _parse_auth_header(self, auth_header):
        """解析认证头"""
        params = {}
        pattern = r'(\w+)=(?:"([^"]+)"|([^,\s]+))'
        matches = re.findall(pattern, auth_header)
        for key, quoted_value, unquoted_value in matches:
            value = quoted_value if quoted_value else unquoted_value
            params[key] = value
        return params
    
    def _get_local_ip(self):
        """获取本地IP"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def stop(self):
        """停止客户端"""
        print("\n🛑 停止 SIP 客户端...")
        self.running = False
        
        # 停止所有 RTP
        for rtp_handler in self.active_calls.values():
            rtp_handler.stop()
        
        if self.sock:
            self.sock.close()
        
        print("✅ 已停止")

    def _parse_rtp_header(self, header_data):
        """解析RTP头部"""
        if len(header_data) < 12:
            return None

        # RTP头部格式: V=2, P=0, X=0, CC=0, M=1, PT=0, Sequence=2, Timestamp=4, SSRC=4
        byte0, byte1, sequence, timestamp, ssrc = struct.unpack('!BBHII', header_data[:12])

        version = (byte0 >> 6) & 0x03
        padding = (byte0 >> 5) & 0x01
        extension = (byte0 >> 4) & 0x01
        csrc_count = byte0 & 0x0F
        marker = (byte1 >> 7) & 0x01
        payload_type = byte1 & 0x7F

        return {
            'version': version,
            'padding': padding,
            'extension': extension,
            'csrc_count': csrc_count,
            'marker': marker,
            'payload_type': payload_type,
            'sequence_number': sequence,
            'timestamp': timestamp,
            'ssrc': ssrc
        }

    def _payload_type_to_codec(self, payload_type):
        """将payload type转换为编解码器名称"""
        codec_map = {
            0: "PCMU (G.711 μ-law)",
            8: "PCMA (G.711 A-law)",
            13: "CN (Comfort Noise)",
            101: "DTMF",
            110: "PCMU (G.711 μ-law)",
            111: "PCMA (G.711 A-law)"
        }
        return codec_map.get(payload_type, f"未知({payload_type})")


# 需要导入 math
import math

# 主程序
if __name__ == "__main__":
    client = EnhancedSIPClient()
    
    if client.start():
        try:
            print("\n按 Ctrl+C 退出...\n")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n收到退出信号...")
    
    client.stop()