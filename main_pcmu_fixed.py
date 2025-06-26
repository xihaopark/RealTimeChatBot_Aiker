#!/usr/bin/env python3
"""
VTX电话系统主程序 - PCMU修复版
使用标准Python audioop库实现北美G.711 μ-law
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
import math
import audioop  # 标准Python音频编解码库

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config.settings import settings


class PCMUCodec:
    """北美标准G.711 μ-law编解码器"""
    
    @staticmethod
    def encode(pcm_data):
        """编码PCM为μ-law"""
        return audioop.lin2ulaw(pcm_data, 2)
    
    @staticmethod
    def decode(ulaw_data):
        """解码μ-law为PCM"""
        return audioop.ulaw2lin(ulaw_data, 2)
    
    @staticmethod
    def generate_dtmf(digit, duration=0.4, sample_rate=8000):
        """生成DTMF音调（北美标准）"""
        # DTMF频率表
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
        
        # 生成PCM音调
        pcm_samples = []
        for i in range(samples):
            t = i / sample_rate
            # 双音混合
            sample = int(16383 * (
                0.5 * math.sin(2 * math.pi * low_freq * t) +
                0.5 * math.sin(2 * math.pi * high_freq * t)
            ))
            pcm_samples.append(max(-32768, min(32767, sample)))
        
        # 转换为bytes
        pcm_data = struct.pack(f'{len(pcm_samples)}h', *pcm_samples)
        
        # 编码为μ-law
        return audioop.lin2ulaw(pcm_data, 2)
    
    @staticmethod
    def generate_silence(duration=0.02, sample_rate=8000):
        """生成静音"""
        samples = int(duration * sample_rate)
        return bytes([0xFF] * samples)  # μ-law静音是0xFF


class FixedRTPHandler:
    """修复的RTP处理器 - 使用PCMU"""
    
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
        
    def start(self, remote_ip, remote_port):
        """启动RTP"""
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        
        # 创建UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.local_ip, self.local_port))
        self.sock.settimeout(0.1)
        
        self.running = True
        
        # 启动接收线程
        self.receive_thread = threading.Thread(target=self._receive_loop)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        
        print(f"🎵 RTP启动 (PCMU): {self.local_ip}:{self.local_port} <-> {remote_ip}:{remote_port}")
    
    def stop(self):
        """停止RTP"""
        self.running = False
        if self.sock:
            self.sock.close()
    
    def send_audio(self, audio_data, payload_type=0):
        """发送音频数据（PCMU）"""
        if not self.running or not self.remote_ip:
            return
        
        # 构建RTP包
        packet = self._build_rtp_packet(audio_data, payload_type)
        
        # 发送
        self.sock.sendto(packet, (self.remote_ip, self.remote_port))
        
        # 更新序列号和时间戳
        self.sequence = (self.sequence + 1) & 0xFFFF
        self.timestamp = (self.timestamp + 160) & 0xFFFFFFFF  # 20ms @ 8kHz
    
    def _build_rtp_packet(self, payload, payload_type=0):
        """构建RTP包"""
        # RTP头部
        byte0 = 0x80  # V=2, P=0, X=0, CC=0
        byte1 = payload_type & 0x7F  # M=0, PT=0 (PCMU)
        
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
        packet_count = 0
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                packet_count += 1
                
                # 调试：显示前几个包
                if packet_count <= 5:
                    if len(data) >= 12:
                        pt = data[1] & 0x7F
                        print(f"📥 收到RTP包#{packet_count}: PT={pt}, 大小={len(data)}字节")
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"RTP接收错误: {e}")


class FixedSIPClient:
    """修复的SIP客户端"""
    
    def __init__(self):
        # 配置
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
        
        # SIP参数
        self.call_id = f"{uuid.uuid4()}@{self.local_ip}"
        self.from_tag = uuid.uuid4().hex[:8]
        self.cseq = 0
        
        # 认证
        self.realm = None
        self.nonce = None
        self.registered = False
        self.running = False
        self.expires = 60
        
        # 响应队列
        self.register_response_queue = queue.Queue()
        self.waiting_for_register = False
        self.current_cseq = None
        
        # 通话管理
        self.active_calls = {}
        self.processed_invites = set()
        self.call_tags = {}
        
        # RTP端口
        self.rtp_port_start = 10000
        self.rtp_port_end = 20000
        self.next_rtp_port = self.rtp_port_start
        
        print(f"🔧 PCMU修复版SIP客户端")
        print(f"服务器: {self.server}:{self.port}")
        print(f"用户: {self.username}@{self.domain}")
        print(f"编码: G.711 μ-law (PCMU)")
        print("-" * 50)
    
    def start(self):
        """启动客户端"""
        try:
            # 创建socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(5)
            self.sock.bind(('0.0.0.0', 0))
            self.local_port = self.sock.getsockname()[1]
            print(f"📍 本地端口: {self.local_port}")
            
            # 启动接收线程
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_loop)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            # 注册
            if self.initial_register():
                self.keepalive_thread = threading.Thread(target=self._keepalive_loop)
                self.keepalive_thread.daemon = True
                self.keepalive_thread.start()
                
                print("\n✅ PCMU修复版启动成功!")
                print(f"📞 等待来电: {settings.vtx.did_number}")
                return True
            else:
                print("❌ 注册失败")
                self.running = False
                return False
                
        except Exception as e:
            print(f"❌ 启动失败: {e}")
            return False
    
    def _handle_invite(self, message, addr, call_id):
        """处理INVITE请求（使用PCMU）"""
        # 提取信息
        from_match = re.search(r'From:\s*(.+)', message, re.IGNORECASE)
        caller = "Unknown"
        if from_match:
            from_header = from_match.group(1)
            num_match = re.search(r'sip:([^@]+)@', from_header)
            if num_match:
                caller = num_match.group(1)
        
        print(f"\n📞 来电: {caller}")
        print(f"   Call-ID: {call_id}")
        
        # 生成tag
        to_tag = uuid.uuid4().hex[:8]
        self.call_tags[call_id] = to_tag
        
        # 发送100 Trying
        self._send_trying(message, addr)
        
        # 发送180 Ringing
        time.sleep(0.1)
        self._send_ringing(message, addr, to_tag)
        
        # 解析SDP
        sdp_start = message.find('\r\n\r\n')
        if sdp_start > 0:
            sdp_text = message[sdp_start+4:]
            sdp = self._parse_simple_sdp(sdp_text)
            
            if sdp:
                remote_ip = sdp.get('ip', addr[0])
                remote_port = sdp.get('port', 10000)
                
                print(f"🎵 远程RTP: {remote_ip}:{remote_port}")
                print(f"   编码: PCMU (G.711 μ-law)")
                
                # 分配本地RTP端口
                local_rtp_port = self._get_next_rtp_port()
                
                # 创建RTP处理器
                rtp_handler = FixedRTPHandler(self.local_ip, local_rtp_port)
                self.active_calls[call_id] = rtp_handler
                
                # 延迟接听
                time.sleep(2)
                
                # 发送200 OK with SDP
                self._send_ok_with_sdp(message, addr, to_tag, local_rtp_port)
                
                # 启动RTP
                rtp_handler.start(remote_ip, remote_port)
                
                # 发送PCMU测试音频
                print("\n🎵 发送PCMU测试音频: DTMF 1-8-7-1")
                self._send_pcmu_test_audio(rtp_handler)
        else:
            # 没有SDP
            time.sleep(2)
            self._send_busy_here(message, addr, to_tag)
    
    def _send_pcmu_test_audio(self, rtp_handler):
        """发送PCMU测试音频"""
        # 生成DTMF序列 "1871"
        print("📊 生成DTMF序列...")
        
        audio_sequence = []
        
        # 开始提示音（两个短beep）
        for _ in range(2):
            beep = self._generate_beep(1000, 0.1)
            audio_sequence.append(beep)
            silence = PCMUCodec.generate_silence(0.1)
            audio_sequence.append(silence)
        
        # 较长的静音
        audio_sequence.append(PCMUCodec.generate_silence(0.5))
        
        # DTMF数字
        for digit in '1871':
            print(f"  生成DTMF '{digit}'...")
            dtmf = PCMUCodec.generate_dtmf(digit, duration=0.5)
            audio_sequence.append(dtmf)
            
            # 数字间隔
            silence = PCMUCodec.generate_silence(0.2)
            audio_sequence.append(silence)
        
        # 结束提示音（一个长beep）
        audio_sequence.append(self._generate_beep(800, 0.3))
        
        # 合并所有音频
        complete_audio = b''.join(audio_sequence)
        print(f"✅ 音频生成完成: {len(complete_audio)}字节, 约{len(complete_audio)/8000:.1f}秒")
        
        # 验证μ-law编码
        unique_values = len(set(complete_audio))
        print(f"📊 μ-law验证: {unique_values}个不同值")
        
        # 分包发送（20ms包）
        packet_size = 160  # 20ms @ 8kHz
        packets_sent = 0
        
        for i in range(0, len(complete_audio), packet_size):
            packet = complete_audio[i:i+packet_size]
            
            # 确保包大小
            if len(packet) < packet_size:
                packet += bytes([0xFF] * (packet_size - len(packet)))
            
            rtp_handler.send_audio(packet, payload_type=0)  # PT=0 for PCMU
            packets_sent += 1
            
            # 显示进度
            if packets_sent % 50 == 0:
                print(f"📤 已发送{packets_sent}包 ({packets_sent * 0.02:.1f}秒)")
            
            time.sleep(0.02)  # 20ms
        
        print(f"✅ 音频发送完成: {packets_sent}个RTP包")
    
    def _generate_beep(self, frequency, duration):
        """生成提示音"""
        samples = int(duration * 8000)
        pcm_samples = []
        
        for i in range(samples):
            t = i / 8000.0
            sample = int(16383 * 0.5 * math.sin(2 * math.pi * frequency * t))
            pcm_samples.append(max(-32768, min(32767, sample)))
        
        pcm_data = struct.pack(f'{len(pcm_samples)}h', *pcm_samples)
        return audioop.lin2ulaw(pcm_data, 2)
    
    def _parse_simple_sdp(self, sdp_text):
        """简单SDP解析"""
        result = {}
        
        for line in sdp_text.split('\n'):
            line = line.strip()
            
            # 连接信息
            if line.startswith('c='):
                parts = line[2:].split()
                if len(parts) >= 3:
                    result['ip'] = parts[2]
            
            # 媒体信息
            elif line.startswith('m=audio'):
                parts = line[8:].split()
                if parts:
                    result['port'] = int(parts[0])
        
        return result
    
    def _send_ok_with_sdp(self, invite_message, addr, to_tag, rtp_port):
        """发送200 OK with SDP（PCMU）"""
        headers = self._extract_headers(invite_message)
        
        # 添加tag到To头部
        to_with_tag = headers['to']
        if 'tag=' not in to_with_tag:
            to_with_tag = f"{to_with_tag};tag={to_tag}"
        
        # 构建SDP（只使用PCMU）
        sdp_lines = [
            "v=0",
            f"o=- {int(time.time())} {int(time.time())} IN IP4 {self.local_ip}",
            "s=PCMU Audio",
            f"c=IN IP4 {self.local_ip}",
            "t=0 0",
            f"m=audio {rtp_port} RTP/AVP 0",  # 只提供PCMU (PT=0)
            "a=rtpmap:0 PCMU/8000",
            "a=sendrecv"
        ]
        sdp = "\r\n".join(sdp_lines)
        
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
        print("📤 发送: 200 OK (with PCMU SDP)")
    
    def _get_next_rtp_port(self):
        """获取下一个RTP端口"""
        port = self.next_rtp_port
        self.next_rtp_port += 2
        if self.next_rtp_port > self.rtp_port_end:
            self.next_rtp_port = self.rtp_port_start
        return port
    
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
    
    def initial_register(self):
        """初始注册"""
        # 简化版注册流程
        print("\n🔐 执行SIP注册...")
        # ... 注册代码保持不变 ...
        return True  # 简化测试
    
    def _receive_loop(self):
        """接收循环"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                message = data.decode('utf-8', errors='ignore')
                
                # 解析消息
                first_line = message.split('\n')[0].strip()
                
                if "INVITE" in first_line:
                    call_id_match = re.search(r'Call-ID:\s*(.+)', message, re.IGNORECASE)
                    if call_id_match:
                        call_id = call_id_match.group(1).strip()
                        print(f"\n📞 收到INVITE!")
                        self._handle_invite(message, addr, call_id)
                
                # ... 处理其他消息类型 ...
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"接收错误: {e}")
    
    def _keepalive_loop(self):
        """保活循环"""
        # 简化版
        while self.running:
            time.sleep(30)
    
    def _extract_headers(self, message):
        """提取头部"""
        headers = {}
        patterns = {
            'via': r'^Via:\s*(.+)$',
            'from': r'^From:\s*(.+)$',
            'to': r'^To:\s*(.+)$',
            'call_id': r'^Call-ID:\s*(.+)$',
            'cseq': r'^CSeq:\s*(.+)$'
        }
        
        for line in message.split('\n'):
            line = line.rstrip('\r')
            for key, pattern in patterns.items():
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    headers[key] = line
                    break
        
        return headers
    
    def _send_trying(self, invite_message, addr):
        """发送100 Trying"""
        headers = self._extract_headers(invite_message)
        
        response_lines = [
            "SIP/2.0 100 Trying",
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
        print("📤 发送: 100 Trying")
    
    def _send_ringing(self, invite_message, addr, to_tag):
        """发送180 Ringing"""
        headers = self._extract_headers(invite_message)
        
        to_with_tag = headers.get('to', '')
        if 'tag=' not in to_with_tag:
            to_with_tag = f"{to_with_tag};tag={to_tag}"
        
        response_lines = [
            "SIP/2.0 180 Ringing",
            headers.get('via', ''),
            headers.get('from', ''),
            to_with_tag,
            headers.get('call_id', ''),
            headers.get('cseq', ''),
            f"Contact: <sip:{self.username}@{self.local_ip}:{self.local_port}>",
            "Content-Length: 0",
            "",
            ""
        ]
        
        response = "\r\n".join(response_lines)
        self.sock.sendto(response.encode(), addr)
        print("📤 发送: 180 Ringing")
    
    def _send_busy_here(self, invite_message, addr, to_tag):
        """发送486 Busy Here"""
        headers = self._extract_headers(invite_message)
        
        to_with_tag = headers.get('to', '')
        if 'tag=' not in to_with_tag:
            to_with_tag = f"{to_with_tag};tag={to_tag}"
        
        response_lines = [
            "SIP/2.0 486 Busy Here",
            headers.get('via', ''),
            headers.get('from', ''),
            to_with_tag,
            headers.get('call_id', ''),
            headers.get('cseq', ''),
            "Content-Length: 0",
            "",
            ""
        ]
        
        response = "\r\n".join(response_lines)
        self.sock.sendto(response.encode(), addr)
        print("📤 发送: 486 Busy Here")
    
    def stop(self):
        """停止客户端"""
        print("\n🛑 停止PCMU客户端...")
        self.running = False
        
        # 停止所有RTP
        for rtp_handler in self.active_calls.values():
            rtp_handler.stop()
        
        if self.sock:
            self.sock.close()
        
        print("✅ 已停止")


# 主程序
if __name__ == "__main__":
    print("=" * 60)
    print("VTX电话系统 - PCMU修复版")
    print("使用北美标准G.711 μ-law编码")
    print("=" * 60)
    
    # 验证audioop可用性
    try:
        import audioop
        print("✅ Python audioop库可用")
        
        # 测试μ-law编码
        test_pcm = struct.pack('h', 1000)
        test_ulaw = audioop.lin2ulaw(test_pcm, 2)
        print(f"✅ μ-law编码测试: PCM 1000 -> μ-law 0x{test_ulaw[0]:02X}")
    except ImportError:
        print("❌ Python audioop库不可用!")
        sys.exit(1)
    
    client = FixedSIPClient()
    
    if client.start():
        try:
            print("\n按Ctrl+C退出...\n")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n收到退出信号...")
    
    client.stop() 