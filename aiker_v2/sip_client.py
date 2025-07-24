#!/usr/bin/env python3
"""
SIP客户端实现
从main.py提取的SIP协议处理逻辑
"""

import socket
import time
import hashlib
import uuid
import re
import threading
import struct
import random
import queue
from typing import Dict, Callable, Optional, Any


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
            "a=sendrecv"
        ]
        
        for codec in codecs:
            if codec == '0':
                sdp_lines.append("a=rtpmap:0 PCMU/8000")
            elif codec == '8':
                sdp_lines.append("a=rtpmap:8 PCMA/8000")
        
        return '\r\n'.join(sdp_lines) + '\r\n'


class EnhancedSIPClient:
    """增强的SIP客户端"""
    
    def __init__(self, username, password, domain, server, port=5060):
        self.username = username
        self.password = password
        self.domain = domain
        self.server = server
        self.port = port
        
        # 网络设置
        self.sock = None
        self.local_ip = None
        self.local_port = None
        self.running = False
        
        # SIP状态  
        self.cseq = 1
        self.call_id = None
        self.branch = None
        self.from_tag = None
        self.registered = False
        self.auth_info = {}
        
        # 注册响应队列 (关键修复)
        self.register_response_queue = queue.Queue()
        self.waiting_for_register = False
        self.current_cseq = None
        
        # 通话管理
        self.active_calls: Dict[str, Any] = {}
        self.call_tags: Dict[str, str] = {}
        self.rtp_port_pool = list(range(10000, 10500, 2))  # 偶数端口
        self.used_rtp_ports = set()
        
        # 回调函数
        self.call_handler: Optional[Callable] = None
        
        # 线程
        self.receive_thread = None
        self.keepalive_thread = None
        
    def set_call_handler(self, handler: Callable):
        """设置来电处理回调"""
        self.call_handler = handler
        
    def _get_local_ip(self):
        """获取本地IP"""
        try:
            temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp_sock.connect((self.server, self.port))
            local_ip = temp_sock.getsockname()[0]
            temp_sock.close()
            return local_ip
        except:
            return "127.0.0.1"
    
    def _get_next_rtp_port(self):
        """获取下一个可用的RTP端口"""
        for port in self.rtp_port_pool:
            if port not in self.used_rtp_ports:
                self.used_rtp_ports.add(port)
                return port
        
        # 如果所有端口都用完了，重置池
        self.used_rtp_ports.clear()
        port = self.rtp_port_pool[0]
        self.used_rtp_ports.add(port)
        return port
    
    def _release_rtp_port(self, port):
        """释放RTP端口"""
        self.used_rtp_ports.discard(port)
    
    def start(self):
        """启动SIP客户端"""
        try:
            self.local_ip = self._get_local_ip()
            print(f"📡 本地IP: {self.local_ip}")
            
            # 创建socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind(('0.0.0.0', 0))
            self.local_port = self.sock.getsockname()[1]
            print(f"📍 绑定到本地端口: {self.local_port}")
            
            # 启动接收线程
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
                
                print("\n✅ SIP客户端启动成功!")
                self.registered = True
                return True
            else:
                print("❌ 注册失败，无法启动")
                self.running = False
                return False
                
        except Exception as e:
            print(f"❌ 启动失败: {e}")
            return False
    
    def stop(self):
        """停止SIP客户端"""
        print("🛑 正在停止SIP客户端...")
        self.running = False
        self.registered = False
        
        # 结束所有活跃通话
        for call_id in list(self.active_calls.keys()):
            self._handle_call_end(call_id)
        
        if self.sock:
            self.sock.close()
        
        print("✅ SIP客户端已停止")
    
    def initial_register(self):
        """初始注册 - 使用同步等待机制"""
        print("📋 开始SIP注册...")
        
        self.call_id = f"{uuid.uuid4()}@{self.local_ip}"
        self.from_tag = uuid.uuid4().hex[:8]
        self.branch = f"z9hG4bK{uuid.uuid4().hex[:8]}"
        
        try:
            # Step 1: 发送初始REGISTER (无认证)
            self.cseq += 1
            self.current_cseq = self.cseq
            self.waiting_for_register = True
            
            register_msg = self._build_register_message()
            print(f"📤 发送初始REGISTER (CSeq: {self.cseq})")
            self.sock.sendto(register_msg.encode(), (self.server, self.port))
            
            # 等待响应
            try:
                response = self.register_response_queue.get(timeout=10)
                print("📥 收到注册响应")
            except queue.Empty:
                print("❌ 注册超时")
                return False
            finally:
                self.waiting_for_register = False
            
            if "407 Proxy Authentication Required" in response:
                print("🔐 需要认证，处理认证挑战...")
                return self._handle_auth_challenge_sync(response)
            elif "200 OK" in response:
                print("✅ 注册成功 (无需认证)")
                return True
            else:
                print("❌ 注册失败")
                return False
                
        except Exception as e:
            print(f"❌ 注册错误: {e}")
            return False
    
    def _build_register_message(self, auth_header=""):
        """构建REGISTER消息"""
        register_lines = [
            f"REGISTER sip:{self.domain} SIP/2.0",
            f"Via: SIP/2.0/UDP {self.local_ip}:{self.local_port};branch={self.branch};rport",
            f"Max-Forwards: 70",
            f"From: <sip:{self.username}@{self.domain}>;tag={self.from_tag}",
            f"To: <sip:{self.username}@{self.domain}>",
            f"Call-ID: {self.call_id}",
            f"CSeq: {self.cseq} REGISTER",
            f"Contact: <sip:{self.username}@{self.local_ip}:{self.local_port}>",
            f"User-Agent: VTX-AI-System/1.0",
            f"Expires: 60",
            f"Allow: INVITE, ACK, CANCEL, BYE, OPTIONS"
        ]
        
        if auth_header:
            register_lines.append(auth_header)
        
        register_lines.extend(["Content-Length: 0", "", ""])
        
        return '\r\n'.join(register_lines)
    
    def _receive_loop(self):
        """接收循环"""
        while self.running:
            try:
                self.sock.settimeout(1.0)
                data, addr = self.sock.recvfrom(4096)
                message = data.decode('utf-8', errors='ignore')
                
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
                parts = first_line.split(' ', 2)
                status_code = int(parts[1])
                
                if 'REGISTER' in message:
                    # 检查是否是我们等待的注册响应
                    cseq_match = re.search(r'CSeq:\s*(\d+)\s+(\w+)', message)
                    if (cseq_match and 
                        cseq_match.group(2) == "REGISTER" and 
                        self.waiting_for_register and 
                        int(cseq_match.group(1)) == self.current_cseq):
                        # 这是我们等待的注册响应
                        self.register_response_queue.put(message)
                        return
                    else:
                        self._handle_register_response(message, status_code)
                
            elif first_line.startswith('INVITE'):
                # INVITE请求
                call_id = self._extract_call_id(message)
                if call_id:
                    self._handle_invite(message, addr, call_id)
                    
            elif first_line.startswith('BYE'):
                # BYE请求
                call_id = self._extract_call_id(message)
                if call_id:
                    self._handle_bye(message, addr, call_id)
                    
        except Exception as e:
            print(f"⚠️ 消息处理错误: {e}")
    
    def _handle_register_response(self, message, status_code):
        """处理注册响应"""
        if status_code == 401 or status_code == 407:
            # 需要认证
            print("🔐 收到认证挑战")
            self._handle_auth_challenge(message)
            
        elif status_code == 200:
            print("✅ 注册成功")
            self.registered = True
            
        else:
            print(f"❌ 注册失败: {status_code}")
    
    def _handle_auth_challenge_sync(self, response_msg):
        """同步处理认证挑战"""
        try:
            # 解析认证信息
            auth_match = re.search(r'Proxy-Authenticate: Digest (.+)', response_msg)
            if not auth_match:
                print("❌ 无法提取认证信息")
                return False
            
            auth_params = self._parse_auth_header(auth_match.group(1))
            realm = auth_params.get('realm', self.domain) 
            nonce = auth_params.get('nonce', '')
            
            print(f"🔐 Realm: {realm}")
            
            # 保存认证信息
            self.auth_info = {
                'realm': realm,
                'nonce': nonce,
                'method': 'REGISTER',
                'uri': f'sip:{self.domain}'
            }
            
            # Step 2: 发送带认证的REGISTER
            self.cseq += 1
            self.current_cseq = self.cseq
            self.waiting_for_register = True
            
            auth_response = self._generate_auth_response()
            auth_header_line = f'Proxy-Authorization: Digest username="{self.username}", realm="{realm}", nonce="{nonce}", uri="sip:{self.domain}", response="{auth_response}", algorithm=MD5'
            
            self.branch = f"z9hG4bK{uuid.uuid4().hex[:8]}"
            register_msg = self._build_register_message(auth_header_line)
            
            print(f"📤 发送认证REGISTER (CSeq: {self.cseq})")
            self.sock.sendto(register_msg.encode(), (self.server, self.port))
            
            # 等待响应
            try:
                response = self.register_response_queue.get(timeout=10)
            except queue.Empty:
                print("❌ 认证注册超时")
                return False
            finally:
                self.waiting_for_register = False
            
            if "200 OK" in response:
                print("✅ 认证注册成功!")
                return True
            else:
                print("❌ 认证注册失败")
                return False
                
        except Exception as e:
            print(f"❌ 认证处理失败: {e}")
            return False
    
    def _parse_auth_header(self, auth_header):
        """解析认证头"""
        params = {}
        pattern = r'(\w+)=(?:"([^"]+)"|([^,\s]+))'
        matches = re.findall(pattern, auth_header)
        for key, quoted_value, unquoted_value in matches:
            value = quoted_value if quoted_value else unquoted_value
            params[key] = value
        return params
        
    def _handle_auth_challenge(self, message):
        """处理认证挑战 (异步版本，保持兼容)"""
        # 解析WWW-Authenticate或Proxy-Authenticate头
        auth_match = re.search(r'(WWW-Authenticate|Proxy-Authenticate):\s*(.+)', message, re.IGNORECASE)
        if not auth_match:
            return
        
        auth_header = auth_match.group(2)
        
        # 解析认证参数
        realm_match = re.search(r'realm="([^"]+)"', auth_header)
        nonce_match = re.search(r'nonce="([^"]+)"', auth_header)
        
        if not (realm_match and nonce_match):
            return
        
        realm = realm_match.group(1)
        nonce = nonce_match.group(1)
        
        self.auth_info = {
            'realm': realm,
            'nonce': nonce,
            'method': 'REGISTER',
            'uri': f'sip:{self.domain}'
        }
        
        # 生成认证响应
        auth_response = self._generate_auth_response()
        auth_header_line = f'Authorization: Digest username="{self.username}", realm="{realm}", nonce="{nonce}", uri="sip:{self.domain}", response="{auth_response}"'
        
        # 发送带认证的注册
        self.cseq += 1
        self.branch = f"z9hG4bK{uuid.uuid4().hex[:8]}"
        
        register_msg = self._build_register_message(auth_header_line)
        self.sock.sendto(register_msg.encode(), (self.server, self.port))
        print("📤 发送认证REGISTER")
    
    def _generate_auth_response(self):
        """生成认证响应"""
        ha1 = hashlib.md5(f"{self.username}:{self.auth_info['realm']}:{self.password}".encode()).hexdigest()
        ha2 = hashlib.md5(f"{self.auth_info['method']}:{self.auth_info['uri']}".encode()).hexdigest()
        response = hashlib.md5(f"{ha1}:{self.auth_info['nonce']}:{ha2}".encode()).hexdigest()
        return response
    
    def _extract_call_id(self, message):
        """提取Call-ID"""
        match = re.search(r'Call-ID:\s*(.+)', message, re.IGNORECASE)
        return match.group(1).strip() if match else None
    
    def _handle_invite(self, message, addr, call_id):
        """处理INVITE请求"""
        print(f"📞 收到来电: {call_id}")
        
        # 提取来电号码
        from_match = re.search(r'From:\s*(.+)', message, re.IGNORECASE)
        caller = "Unknown"
        if from_match:
            from_header = from_match.group(1)
            num_match = re.search(r'sip:([^@]+)@', from_header)
            if num_match:
                caller = num_match.group(1)
        
        print(f"📞 来电号码: {caller}")
        
        # 生成to_tag
        to_tag = uuid.uuid4().hex[:8]
        self.call_tags[call_id] = to_tag
        
        # 发送100 Trying
        self._send_trying(message, addr)
        
        # 发送180 Ringing
        time.sleep(0.1)
        self._send_ringing(message, addr, to_tag)
        
        # 解析SDP获取RTP信息
        sdp_start = message.find('\r\n\r\n')
        if sdp_start > 0:
            sdp_text = message[sdp_start+4:]
            sdp = SDPParser.parse(sdp_text)
            
            # 获取远程RTP信息
            if sdp['media']:
                audio_media = sdp['media'][0]
                remote_port = audio_media['port']
                
                # 获取远程IP
                connection = audio_media.get('connection') or sdp.get('connection')
                if connection:
                    remote_ip = connection.split()[-1]
                else:
                    remote_ip = addr[0]
                
                print(f"🎵 远程RTP: {remote_ip}:{remote_port}")
                
                # 分配本地RTP端口
                local_rtp_port = self._get_next_rtp_port()
                
                # 延迟接听
                time.sleep(2)
                
                # 发送200 OK with SDP
                self._send_ok_with_sdp(message, addr, to_tag, local_rtp_port)
                
                # 通知应用层处理通话
                if self.call_handler:
                    call_info = {
                        'call_id': call_id,
                        'caller': caller,
                        'remote_ip': remote_ip,
                        'remote_port': remote_port,
                        'local_rtp_port': local_rtp_port
                    }
                    self.call_handler(call_info)
                    
        else:
            # 没有SDP，发送忙音
            time.sleep(2)
            self._send_busy_here(message, addr, to_tag)
    
    def _send_trying(self, request, addr):
        """发送100 Trying"""
        response = self._build_response(request, "100 Trying")
        self.sock.sendto(response.encode(), addr)
        print("📤 发送100 Trying")
    
    def _send_ringing(self, request, addr, to_tag):
        """发送180 Ringing"""
        response = self._build_response(request, "180 Ringing", to_tag)
        self.sock.sendto(response.encode(), addr)
        print("📤 发送180 Ringing")
    
    def _send_ok_with_sdp(self, request, addr, to_tag, rtp_port):
        """发送200 OK with SDP"""
        sdp_body = SDPParser.build(self.local_ip, rtp_port)
        response = self._build_response(request, "200 OK", to_tag, sdp_body)
        self.sock.sendto(response.encode(), addr)
        print("📤 发送200 OK with SDP")
    
    def _send_busy_here(self, request, addr, to_tag):
        """发送486 Busy Here"""
        response = self._build_response(request, "486 Busy Here", to_tag)
        self.sock.sendto(response.encode(), addr)
        print("📤 发送486 Busy Here")
    
    def _build_response(self, request, status_line, to_tag="", body=""):
        """构建SIP响应"""
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
            f"Contact: <sip:{self.username}@{self.local_ip}:{self.local_port}>",
            f"Content-Length: {len(body)}"
        ]
        
        if body:
            response_lines.append("Content-Type: application/sdp")
        
        response_lines.extend(["", body])
        
        return '\r\n'.join(response_lines)
    
    def _handle_bye(self, message, addr, call_id):
        """处理BYE请求"""
        print(f"☎️ 通话结束: {call_id}")
        
        # 发送200 OK
        response = self._build_response(message, "200 OK")
        self.sock.sendto(response.encode(), addr)
        print("📤 发送200 OK (BYE)")
        
        # 清理通话
        self._handle_call_end(call_id)
    
    def _handle_call_end(self, call_id):
        """处理通话结束"""
        if call_id in self.active_calls:
            call_info = self.active_calls[call_id]
            
            # 释放RTP端口
            if 'local_rtp_port' in call_info:
                self._release_rtp_port(call_info['local_rtp_port'])
            
            del self.active_calls[call_id]
        
        if call_id in self.call_tags:
            del self.call_tags[call_id]
        
        print(f"🧹 清理通话: {call_id}")
    
    def _keepalive_loop(self):
        """保活循环"""
        while self.running and self.registered:
            time.sleep(1800)  # 30分钟
            if self.running:
                print("💓 发送保活注册")
                self.cseq += 1
                self.branch = f"z9hG4bK{uuid.uuid4().hex[:8]}"
                
                # 重用现有认证信息
                if self.auth_info:
                    auth_response = self._generate_auth_response()
                    auth_header_line = f'Authorization: Digest username="{self.username}", realm="{self.auth_info["realm"]}", nonce="{self.auth_info["nonce"]}", uri="sip:{self.domain}", response="{auth_response}"'
                    register_msg = self._build_register_message(auth_header_line)
                else:
                    register_msg = self._build_register_message()
                
                try:
                    self.sock.sendto(register_msg.encode(), (self.server, self.port))
                except:
                    pass
    
    @property
    def is_registered(self):
        """检查是否已注册"""
        return self.registered