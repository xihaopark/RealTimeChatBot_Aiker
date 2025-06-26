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
        
        print(f"🎵 RTP 启动: {self.local_ip}:{self.local_port} <-> {remote_ip}:{remote_port}")
    
    def stop(self):
        """停止 RTP"""
        self.running = False
        if self.sock:
            self.sock.close()
    
    def send_audio(self, audio_data, payload_type=0):
        """发送音频数据"""
        if not self.running or not self.remote_ip:
            return
        
        # 构建 RTP 包
        packet = self._build_rtp_packet(audio_data, payload_type)
        
        # 发送
        self.sock.sendto(packet, (self.remote_ip, self.remote_port))
        
        # 更新序列号和时间戳
        self.sequence = (self.sequence + 1) & 0xFFFF
        self.timestamp = (self.timestamp + 160) & 0xFFFFFFFF  # 20ms @ 8kHz
    
    def _build_rtp_packet(self, payload, payload_type):
        """构建 RTP 包"""
        # RTP 头部
        # V=2, P=0, X=0, CC=0, M=0, PT=payload_type
        byte0 = 0x80  # V=2, P=0, X=0, CC=0
        byte1 = payload_type & 0x7F
        
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
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                # TODO: 处理接收到的 RTP 包
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"RTP 接收错误: {e}")


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
        
        # 生成完整的测试音频
        test_audio = G711Codec.generate_test_pattern()
        print(f"📊 生成音频: {len(test_audio)} 字节, 约 {len(test_audio)/8000:.1f} 秒")
        
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
        print("👂 开始监听...")
        
        self.sock.settimeout(0.5)
        
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                message = data.decode('utf-8', errors='ignore')
                
                # 解析消息类型
                first_line = message.split('\n')[0].strip()
                
                # 判断消息类型
                if first_line.startswith("SIP/2.0"):
                    # 这是一个响应
                    self._handle_response(message, addr)
                else:
                    # 这是一个请求
                    self._handle_request(message, addr, first_line)
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"接收错误: {e}")
    
    def _handle_response(self, message, addr):
        """处理SIP响应"""
        # 检查是否是注册响应
        cseq_match = re.search(r'CSeq:\s*(\d+)\s+(\w+)', message)
        if cseq_match:
            cseq_num = int(cseq_match.group(1))
            method = cseq_match.group(2)
            
            if method == "REGISTER" and self.waiting_for_register and cseq_num == self.current_cseq:
                # 这是我们等待的注册响应
                self.register_response_queue.put(message)
                return
        
        # 其他响应
        status_line = message.split('\n')[0].strip()
        if "OPTIONS" not in message:  # 不显示 OPTIONS 响应
            print(f"\n📥 收到响应: {status_line}")
    
    def _handle_request(self, message, addr, first_line):
        """处理SIP请求"""
        if "INVITE" in first_line:
            # 提取 Call-ID 和 CSeq
            call_id_match = re.search(r'Call-ID:\s*(.+)', message, re.IGNORECASE)
            cseq_match = re.search(r'CSeq:\s*(\d+)\s+(\w+)', message, re.IGNORECASE)
            
            if call_id_match and cseq_match:
                call_id = call_id_match.group(1).strip()
                cseq_num = cseq_match.group(1)
                invite_id = f"{call_id}:{cseq_num}"
                
                # 检查是否已处理过
                if invite_id not in self.processed_invites:
                    self.processed_invites.add(invite_id)
                    print(f"\n📞 收到新来电从 {addr}!")
                    print(f"Call-ID: {call_id}")
                    print(f"CSeq: {cseq_num} INVITE")
                    self._handle_invite(message, addr, call_id)
                else:
                    # 重发的 INVITE，再次发送相同的响应
                    print(f"🔄 收到重发的 INVITE (Call-ID: {call_id}, CSeq: {cseq_num})")
                    self._resend_response(message, addr, call_id)
            
        elif "OPTIONS" in first_line:
            # OPTIONS请求，静默处理
            self._handle_options(message, addr)
            
        elif "BYE" in first_line:
            print("📴 收到挂断请求")
            self._handle_bye(message, addr)
            
        elif "ACK" in first_line:
            print("✅ 收到 ACK 确认")
            # 清理相关的 Call-ID
            call_id_match = re.search(r'Call-ID:\s*(.+)', message, re.IGNORECASE)
            if call_id_match:
                call_id = call_id_match.group(1).strip()
                # 清理已处理的 INVITE 记录
                self.processed_invites = {inv for inv in self.processed_invites if not inv.startswith(call_id)}
            
        elif "CANCEL" in first_line:
            print("🚫 收到取消请求")
            self._handle_cancel(message, addr)
    
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