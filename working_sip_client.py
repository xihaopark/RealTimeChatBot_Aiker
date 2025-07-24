#!/usr/bin/env python3
"""
从GitHub工作版本提取的SIP客户端实现
直接复制可用的SIP连接逻辑
"""

import socket
import time
import hashlib
import uuid
import re
import threading
import queue
import struct
import random
import math
from typing import Dict, Any, Optional, Callable

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
                
            return (sign | (segment << 4) | mantissa) ^ 0xFF
        
        if isinstance(pcm_data, bytes):
            # 假设是16-bit PCM
            samples = struct.unpack('<' + 'h' * (len(pcm_data) // 2), pcm_data)
        else:
            samples = pcm_data
            
        return bytes([encode_sample(sample) for sample in samples])
    
    @staticmethod
    def mulaw_to_pcm(mulaw_data):
        """μ-law转PCM"""
        def decode_sample(mulaw):
            mulaw = mulaw ^ 0xFF
            sign = mulaw & 0x80
            segment = (mulaw >> 4) & 0x07
            mantissa = mulaw & 0x0F
            
            sample = (mantissa << 4) + 132
            
            if segment > 0:
                sample = (sample + 256) << (segment - 1)
            
            sample -= 132
            
            if sign:
                sample = -sample
                
            return max(-32635, min(32635, sample))
        
        if isinstance(mulaw_data, bytes):
            samples = [decode_sample(b) for b in mulaw_data]
        else:
            samples = [decode_sample(sample) for sample in mulaw_data]
            
        return struct.pack('<' + 'h' * len(samples), *samples)


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
        
        # 音频回调
        self.audio_callback = None
        
    def set_audio_callback(self, callback):
        """设置音频回调函数"""
        self.audio_callback = callback
        
    def start(self, remote_ip, remote_port):
        """启动 RTP"""
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        
        try:
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
            return True
        except Exception as e:
            print(f"❌ RTP启动失败: {e}")
            return False
    
    def stop(self):
        """停止 RTP"""
        self.running = False
        if self.sock:
            self.sock.close()
        print("🎵 RTP已停止")
    
    def send_audio(self, audio_data, payload_type=0):
        """发送音频数据"""
        if not self.running or not self.remote_ip:
            return
        
        # 构建 RTP 包
        packet = self._build_rtp_packet(audio_data, payload_type)
        
        try:
            # 发送
            self.sock.sendto(packet, (self.remote_ip, self.remote_port))
            
            # 更新序列号和时间戳
            self.sequence = (self.sequence + 1) & 0xFFFF
            self.timestamp = (self.timestamp + 160) & 0xFFFFFFFF  # 20ms @ 8kHz
        except Exception as e:
            print(f"⚠️ RTP发送错误: {e}")
    
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
    
    def _parse_rtp_packet(self, data):
        """解析RTP包"""
        if len(data) < 12:  # RTP头部至少12字节
            return None
            
        # 解析RTP头部
        header = struct.unpack('!BBHII', data[:12])
        version = (header[0] >> 6) & 0x03
        payload_type = header[1] & 0x7F
        sequence = header[2]
        timestamp = header[3]
        ssrc = header[4]
        
        # 提取音频数据
        payload = data[12:]
        
        return {
            'version': version,
            'payload_type': payload_type,
            'sequence': sequence,
            'timestamp': timestamp,
            'ssrc': ssrc,
            'payload': payload
        }
    
    def _receive_loop(self):
        """接收循环"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                
                # 解析RTP包
                rtp_packet = self._parse_rtp_packet(data)
                if rtp_packet:
                    # 减少RTP包日志，只显示重要信息
                    self.packet_count = getattr(self, 'packet_count', 0) + 1
                    if self.packet_count % 100 == 1:  # 每100个包显示一次
                        print(f"🎧 RTP音频流活跃: {len(rtp_packet['payload'])} bytes (第{self.packet_count}包)")
                    
                    # 如果有音频回调，处理接收到的音频
                    if self.audio_callback:
                        self.audio_callback(rtp_packet['payload'], rtp_packet['payload_type'])
                        
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"⚠️ RTP接收错误: {e}")


class WorkingSIPClient:
    """从GitHub复制的工作版本SIP客户端"""
    
    def __init__(self, username, password, domain, server, port=5060):
        self.server = server
        self.port = port
        self.domain = domain
        self.username = username
        self.password = password
        
        self.server_ip = socket.gethostbyname(self.server)
        self.local_ip = self._get_local_ip()  # 内网IP，用于绑定socket
        self.public_ip = self._get_public_ip()  # 公网IP，用于SIP消息
        self.sock = None
        self.local_port = None
        
        # SIP 会话参数
        self.call_id = f"{uuid.uuid4()}@{self.public_ip}"
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
        
        # 回调函数
        self.call_handler = None
        
        print(f"🔍 SIP 客户端初始化")
        print(f"服务器: {self.server}:{self.port} ({self.server_ip})")
        print(f"域名: {self.domain}")
        print(f"内网IP: {self.local_ip} (用于绑定)")
        print(f"公网IP: {self.public_ip} (用于SIP消息)")
        print(f"用户名: {self.username}")
        print("-" * 50)
    
    def _get_local_ip(self):
        """获取本地IP（内网IP用于绑定）"""
        try:
            # 连接到服务器以获取正确的本地IP
            temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp_sock.connect((self.server, self.port))
            local_ip = temp_sock.getsockname()[0]
            temp_sock.close()
            return local_ip
        except Exception:
            return "127.0.0.1"
    
    def _get_public_ip(self):
        """获取公网IP用于SIP消息"""
        try:
            import urllib.request
            response = urllib.request.urlopen('http://ifconfig.me', timeout=3)
            public_ip = response.read().decode('utf-8').strip()
            return public_ip
        except Exception:
            # 如果无法获取公网IP，尝试使用STUN
            return self._get_stun_ip()
    
    def _get_stun_ip(self):
        """使用STUN获取公网IP"""
        try:
            import struct
            # 简单的STUN实现
            stun_server = 'stun.l.google.com'
            stun_port = 19302
            
            # STUN Binding Request
            msg_type = 0x0001  # Binding Request
            msg_length = 0x0000
            magic_cookie = 0x2112A442
            transaction_id = random.randint(0, 0xFFFFFFFFFFFFFFFFFFFFFFFF)
            
            # 构建STUN请求
            stun_request = struct.pack('!HHI', msg_type, msg_length, magic_cookie)
            stun_request += struct.pack('!III', 
                                      (transaction_id >> 64) & 0xFFFFFFFF,
                                      (transaction_id >> 32) & 0xFFFFFFFF, 
                                      transaction_id & 0xFFFFFFFF)
            
            # 发送STUN请求
            stun_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            stun_sock.settimeout(3)
            stun_sock.sendto(stun_request, (stun_server, stun_port))
            
            # 接收响应
            data, addr = stun_sock.recvfrom(1024)
            stun_sock.close()
            
            # 解析STUN响应（简化版）
            if len(data) >= 20:
                # 查找MAPPED-ADDRESS属性
                offset = 20  # 跳过STUN头部
                while offset < len(data):
                    if offset + 4 > len(data):
                        break
                    attr_type, attr_length = struct.unpack('!HH', data[offset:offset+4])
                    if attr_type == 0x0001:  # MAPPED-ADDRESS
                        if attr_length >= 8:
                            family, port = struct.unpack('!xBH', data[offset+4:offset+8])
                            if family == 1:  # IPv4
                                ip_bytes = data[offset+8:offset+12]
                                ip = '.'.join(str(b) for b in ip_bytes)
                                return ip
                    offset += 4 + attr_length
            
            return self.local_ip
        except Exception:
            return self.local_ip
    
    def set_call_handler(self, handler):
        """设置来电处理回调"""
        self.call_handler = handler
    
    def start(self):
        """启动客户端"""
        try:
            # 创建并绑定socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(5)
            
            # 尝试绑定到标准5060端口，如果失败则使用随机端口
            try:
                self.sock.bind(('0.0.0.0', 5060))
                self.local_port = 5060
                print("🎯 成功绑定到标准5060端口")
            except:
                self.sock.bind(('0.0.0.0', 0))
                self.local_port = self.sock.getsockname()[1]
                print(f"🎲 使用随机端口: {self.local_port}")
            print(f"📍 本地端口: {self.local_port}")
            
            # 先启动接收线程
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_loop)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            # 执行初始注册
            if self.initial_register():
                print("\n✅ SIP 客户端启动成功!")
                return True
            else:
                print("❌ 注册失败，无法启动")
                self.running = False
                return False
                
        except Exception as e:
            print(f"❌ 启动失败: {e}")
            return False
    
    def initial_register(self):
        """初始注册"""
        print("📋 开始 SIP 注册...")
        
        # 发送初始 REGISTER（无认证）
        self.cseq += 1
        self.current_cseq = self.cseq
        self.waiting_for_register = True
        
        register_msg = self._build_register_message()
        
        try:
            print(f"📤 发送到: {self.server_ip}:{self.port}")
            print(f"📝 REGISTER消息预览:")
            print(register_msg[:200] + "..." if len(register_msg) > 200 else register_msg)
            self.sock.sendto(register_msg.encode('utf-8'), (self.server_ip, self.port))
            print("📤 发送初始 REGISTER 请求")
            
            # 等待响应
            try:
                print("⏳ 等待注册响应... (最多等10秒)")
                response_data = self.register_response_queue.get(timeout=10)
                response_code, response_msg = response_data
                
                if response_code == 200:
                    self.registered = True
                    print("✅ 注册成功 (无需认证)")
                    return True
                elif response_code in [401, 407]:
                    print("🔐 需要认证，处理认证挑战...")
                    return self._handle_auth_challenge(response_msg)
                else:
                    print(f"❌ 注册失败，状态码: {response_code}")
                    return False
                    
            except queue.Empty:
                print("❌ 注册超时 - 未收到任何服务器响应")
                print(f"🔍 请检查: 1) 网络连接 2) 防火墙设置 3) NAT配置")
                return False
                
        except Exception as e:
            print(f"❌ 发送注册失败: {e}")
            return False
    
    def _build_register_message(self, auth_header=None):
        """构建 REGISTER 消息"""
        message = f"REGISTER sip:{self.domain} SIP/2.0\r\n"
        message += f"Via: SIP/2.0/UDP {self.public_ip}:{self.local_port};branch=z9hG4bK{uuid.uuid4().hex[:8]}\r\n"
        message += f"Max-Forwards: 70\r\n"
        message += f"From: <sip:{self.username}@{self.domain}>;tag={self.from_tag}\r\n"
        message += f"To: <sip:{self.username}@{self.domain}>\r\n"
        message += f"Call-ID: {self.call_id}\r\n"
        message += f"CSeq: {self.cseq} REGISTER\r\n"
        message += f"Contact: <sip:{self.username}@{self.public_ip}:{self.local_port}>\r\n"
        message += f"Expires: {self.expires}\r\n"
        
        if auth_header:
            message += f"{auth_header}\r\n"
        
        message += f"Content-Length: 0\r\n\r\n"
        
        return message
    
    def _receive_loop(self):
        """接收循环"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                message = data.decode('utf-8', errors='ignore')
                first_line = message.split('\r\n')[0]
                # 只显示重要的SIP消息
                if any(keyword in first_line for keyword in ['INVITE', 'BYE', '200 OK', '407']):
                    print(f"📨 SIP: {first_line}")
                self._handle_message(message, addr)
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"⚠️ 接收错误: {e}")
                    
    def _handle_message(self, message, addr):
        """处理接收到的消息"""
        try:
            lines = message.split('\r\n')
            first_line = lines[0]
            
            if first_line.startswith('SIP/2.0'):
                # 响应消息
                status_match = re.match(r'SIP/2.0\s+(\d+)\s+(.*)', first_line)
                if status_match:
                    status_code = int(status_match.group(1))
                    status_text = status_match.group(2)
                    
                    if 'REGISTER' in message and self.waiting_for_register:
                        # 获取CSeq来匹配请求
                        cseq_match = re.search(r'CSeq:\s*(\d+)', message, re.IGNORECASE)
                        if cseq_match and int(cseq_match.group(1)) == self.current_cseq:
                            self.register_response_queue.put((status_code, message))
                            self.waiting_for_register = False
                
            elif first_line.startswith('INVITE'):
                # 来电请求
                call_id = self._extract_call_id(message)
                if call_id and call_id not in self.processed_invites:
                    self.processed_invites.add(call_id)
                    self._handle_invite(message, addr, call_id)
                    
            elif first_line.startswith('BYE'):
                # 结束通话
                call_id = self._extract_call_id(message)
                if call_id:
                    self._handle_bye(message, addr, call_id)
                    
        except Exception as e:
            print(f"⚠️ 消息处理错误: {e}")
    
    def _handle_auth_challenge(self, response_msg):
        """处理认证挑战"""
        try:
            # 减少认证响应详情日志
            print(f"🔑 处理认证响应...")
            
            # 解析 WWW-Authenticate 或 Proxy-Authenticate 头
            auth_match = re.search(r'(WWW-Authenticate|Proxy-Authenticate):\s*Digest (.+)', response_msg, re.IGNORECASE)
            if not auth_match:
                print("❌ 找不到认证头")
                return False
            
            auth_type = auth_match.group(1)
            auth_params = auth_match.group(2)
            # 减少认证类型日志
            
            # 解析 realm 和 nonce
            realm_match = re.search(r'realm="([^"]+)"', auth_params)
            nonce_match = re.search(r'nonce="([^"]+)"', auth_params)
            
            if not (realm_match and nonce_match):
                print("❌ 无法解析认证参数")
                return False
            
            self.realm = realm_match.group(1)
            self.nonce = nonce_match.group(1)
            
            print(f"🔑 Realm: {self.realm}")
            print(f"🔑 Nonce: {self.nonce[:20]}...")
            
            # 发送带认证的 REGISTER
            self.cseq += 1
            self.current_cseq = self.cseq
            self.waiting_for_register = True
            
            auth_response = self._calculate_auth_response()
            print(f"✅ 认证响应生成成功")
            
            # 根据Proxy-Authenticate还是WWW-Authenticate使用不同头部
            if 'Proxy-Authenticate' in response_msg:
                auth_header = f'Proxy-Authorization: Digest username="{self.username}", realm="{self.realm}", nonce="{self.nonce}", uri="sip:{self.domain}", response="{auth_response}"'
            else:
                auth_header = f'Authorization: Digest username="{self.username}", realm="{self.realm}", nonce="{self.nonce}", uri="sip:{self.domain}", response="{auth_response}"'
            
            print(f"🔑 认证头: {auth_header[:100]}...")
            register_msg = self._build_register_message(auth_header)
            
            self.sock.sendto(register_msg.encode('utf-8'), (self.server_ip, self.port))
            print("📤 发送认证 REGISTER 请求")
            
            # 等待响应
            try:
                response_data = self.register_response_queue.get(timeout=10)
                response_code, response_msg = response_data
                
                if response_code == 200:
                    self.registered = True
                    print("✅ 认证注册成功!")
                    return True
                elif response_code == 407:
                    print(f"❌ 认证失败 - 可能是用户名或密码错误")
                    print(f"🔑 请检查分机101的认证信息")
                    return False
                else:
                    print(f"❌ 认证注册失败，状态码: {response_code}")
                    return False
                    
            except queue.Empty:
                print("❌ 认证注册超时")
                return False
                
        except Exception as e:
            print(f"❌ 认证处理失败: {e}")
            return False
    
    def _calculate_auth_response(self):
        """计算认证响应"""
        ha1 = hashlib.md5(f"{self.username}:{self.realm}:{self.password}".encode()).hexdigest()
        ha2 = hashlib.md5(f"REGISTER:sip:{self.domain}".encode()).hexdigest()
        response = hashlib.md5(f"{ha1}:{self.nonce}:{ha2}".encode()).hexdigest()
        return response
    
    def _extract_call_id(self, message):
        """提取 Call-ID"""
        match = re.search(r'Call-ID:\s*(.+)', message, re.IGNORECASE)
        return match.group(1).strip() if match else None
    
    def _handle_invite(self, message, addr, call_id):
        """处理 INVITE 请求"""
        print(f"📞 收到来电: Call-ID {call_id}")
        
        # 提取来电号码
        from_match = re.search(r'From:\s*(.+)', message, re.IGNORECASE)
        caller = "Unknown"
        if from_match:
            from_header = from_match.group(1)
            num_match = re.search(r'sip:([^@]+)@', from_header)
            if num_match:
                caller = num_match.group(1)
        
        print(f"📞 来电号码: {caller}")
        
        # 生成 to_tag
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
            if sdp_text.strip():
                sdp = SDPParser.parse(sdp_text)
                
                # 获取远程 RTP 信息
                if sdp['media']:
                    audio_media = sdp['media'][0]
                    remote_port = audio_media['port']
                    
                    # 获取远程 IP
                    connection = audio_media.get('connection') or sdp.get('connection')
                    if connection:
                        remote_ip = connection.split()[-1]
                    else:
                        remote_ip = addr[0]
                    
                    print(f"🎵 远程 RTP: {remote_ip}:{remote_port}")
                    
                    # 分配本地 RTP 端口
                    local_rtp_port = random.randint(10000, 20000)
                    
                    # 延迟接听
                    time.sleep(1)
                    
                    # 发送 200 OK with SDP
                    self._send_ok_with_sdp(message, addr, to_tag, local_rtp_port)
                    
                    # 启动RTP处理器
                    rtp_handler = RTPHandler(self.local_ip, local_rtp_port)
                    rtp_handler.set_audio_callback(self._handle_received_audio)
                    
                    if rtp_handler.start(remote_ip, remote_port):
                        self.active_calls[call_id] = rtp_handler
                        print(f"✅ RTP会话已建立: {call_id}")
                        
                        # 发送欢迎音频
                        self._send_welcome_audio(rtp_handler)
                    
                    # 通知应用层
                    if self.call_handler:
                        call_info = {
                            'call_id': call_id,
                            'caller': caller,
                            'remote_ip': remote_ip,
                            'remote_port': remote_port,
                            'local_rtp_port': local_rtp_port,
                            'rtp_handler': rtp_handler
                        }
                        self.call_handler(call_info)
                        
                else:
                    # 没有 SDP，发送 486 Busy Here
                    time.sleep(1)
                    self._send_busy_here(message, addr, to_tag)
            else:
                # 没有 SDP，发送 486 Busy Here
                time.sleep(1)
                self._send_busy_here(message, addr, to_tag)
    
    def _send_trying(self, request, addr):
        """发送 100 Trying"""
        response = self._build_response(request, "100 Trying")
        self.sock.sendto(response.encode(), addr)
        print("📤 发送 100 Trying")
    
    def _send_ringing(self, request, addr, to_tag):
        """发送 180 Ringing"""
        response = self._build_response(request, "180 Ringing", to_tag)
        self.sock.sendto(response.encode(), addr)
        print("📤 发送 180 Ringing")
    
    def _send_ok_with_sdp(self, request, addr, to_tag, rtp_port):
        """发送 200 OK with SDP"""
        sdp_body = SDPParser.build(self.public_ip, rtp_port)
        response = self._build_response(request, "200 OK", to_tag, sdp_body)
        self.sock.sendto(response.encode(), addr)
        print("📤 发送 200 OK with SDP")
    
    def _send_busy_here(self, request, addr, to_tag):
        """发送 486 Busy Here"""
        response = self._build_response(request, "486 Busy Here", to_tag)
        self.sock.sendto(response.encode(), addr)
        print("📤 发送 486 Busy Here")
    
    def _build_response(self, request, status_line, to_tag="", body=""):
        """构建 SIP 响应"""
        lines = request.split('\r\n')
        
        # 提取必要的头部
        via_line = ""
        from_line = ""
        to_line = ""
        call_id_line = ""
        cseq_line = ""
        
        for line in lines:
            if line.startswith('Via:'):
                via_line = line
            elif line.startswith('From:'):
                from_line = line
            elif line.startswith('To:'):
                to_line = line
                if to_tag and 'tag=' not in to_line:
                    to_line += f';tag={to_tag}'
            elif line.startswith('Call-ID:'):
                call_id_line = line
            elif line.startswith('CSeq:'):
                cseq_line = line
        
        response_lines = [
            f"SIP/2.0 {status_line}",
            via_line,
            from_line,
            to_line,
            call_id_line,
            cseq_line,
            f"Contact: <sip:{self.username}@{self.public_ip}:{self.local_port}>",
            f"Content-Length: {len(body)}"
        ]
        
        if body:
            response_lines.append("Content-Type: application/sdp")
        
        response_lines.extend(["", body])
        
        return '\r\n'.join(response_lines)
    
    def _handle_bye(self, message, addr, call_id):
        """处理 BYE 请求"""
        print(f"☎️ 通话结束: {call_id}")
        
        # 发送 200 OK
        response = self._build_response(message, "200 OK")
        self.sock.sendto(response.encode(), addr)
        print("📤 发送 200 OK (BYE)")
        
        # 停止RTP处理器
        if call_id in self.active_calls:
            rtp_handler = self.active_calls[call_id]
            rtp_handler.stop()
            del self.active_calls[call_id]
            print(f"🎵 RTP会话已结束: {call_id}")
            
        if call_id in self.call_tags:
            del self.call_tags[call_id]
    
    def _handle_received_audio(self, audio_data, payload_type):
        """处理接收到的音频数据"""
        try:
            if payload_type == 0:  # PCMU (μ-law)
                pcm_data = G711Codec.mulaw_to_pcm(audio_data)
                # 减少μ-law解码日志刷屏
                pass
                # 这里可以进一步处理PCM音频，比如传递给语音识别
            elif payload_type == 8:  # PCMA (A-law)
                # TODO: 实现A-law解码
                # 减少A-law音频日志
                pass
            elif payload_type == 13:  # Comfort Noise (CN)
                # 减少静音包日志
                pass
                # CN包通常很小(1字节)，表示静音期间的背景噪声
                # 可以忽略或用于VAD(语音活动检测)
            elif payload_type == 101:  # Telephone Event (DTMF)
                # 减少DTMF事件日志
                pass
            else:
                print(f"⚠️ 不支持的音频格式: payload_type={payload_type}, size={len(audio_data)}")
        except Exception as e:
            print(f"❌ 音频解码错误: {e}")
    
    def _send_welcome_audio(self, rtp_handler):
        """发送欢迎音频"""
        try:
            # 生成更真实的欢迎音频 (多频率组合，模拟语音)
            sample_rate = 8000
            duration = 2.0  # 2秒
            
            samples = []
            for i in range(int(sample_rate * duration)):
                t = i / sample_rate
                
                # 组合多个频率模拟语音特征
                # 基频 + 谐波
                f1 = 200 * math.sin(2 * math.pi * 200 * t)  # 基频
                f2 = 150 * math.sin(2 * math.pi * 400 * t)  # 第二谐波
                f3 = 100 * math.sin(2 * math.pi * 800 * t)  # 第三谐波
                
                # 添加包络以避免突然开始/结束
                envelope = 1.0
                if t < 0.1:  # 淡入
                    envelope = t / 0.1
                elif t > duration - 0.1:  # 淡出
                    envelope = (duration - t) / 0.1
                
                amplitude = int((f1 + f2 + f3) * envelope)
                samples.append(max(-32767, min(32767, amplitude)))
            
            # 转换为μ-law
            mulaw_data = G711Codec.pcm_to_mulaw(samples)
            
            print(f"🎵 准备发送欢迎音频: {len(mulaw_data)} bytes")
            
            # 异步发送音频以避免阻塞
            def send_audio_chunks():
                chunk_size = 160
                for i in range(0, len(mulaw_data), chunk_size):
                    if not rtp_handler.running:
                        break
                    chunk = mulaw_data[i:i+chunk_size]
                    if len(chunk) == chunk_size:  # 只发送完整的包
                        rtp_handler.send_audio(chunk, payload_type=0)
                        time.sleep(0.02)  # 20ms间隔
                print("🎵 欢迎音频发送完成")
            
            # 在新线程中发送音频
            audio_thread = threading.Thread(target=send_audio_chunks)
            audio_thread.daemon = True
            audio_thread.start()
            
        except Exception as e:
            print(f"❌ 发送欢迎音频失败: {e}")
    
    def stop(self):
        """停止客户端"""
        print("🛑 停止 SIP 客户端...")
        self.running = False
        self.registered = False
        
        # 停止所有RTP会话
        for call_id, rtp_handler in self.active_calls.items():
            rtp_handler.stop()
        self.active_calls.clear()
        
        if self.sock:
            self.sock.close()
        
        print("✅ SIP 客户端已停止")
    
    @property
    def is_registered(self):
        """检查是否已注册"""
        return self.registered