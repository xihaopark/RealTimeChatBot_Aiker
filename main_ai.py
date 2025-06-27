#!/usr/bin/env python3
"""
VTX AI Phone System - 集成AI对话功能
支持SIP注册、RTP音频处理和智能AI对话
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config.settings import settings

# 导入AI对话模块
try:
    from ai_conversation import AIConversationManager
    AI_AVAILABLE = True
    print("✅ AI对话模块加载成功")
except ImportError as e:
    AI_AVAILABLE = False
    print(f"⚠️ AI对话模块加载失败: {e}")

class SDPParser:
    """SDP 解析器"""
    
    @staticmethod
    def parse(sdp_text):
        """解析 SDP"""
        sdp = {'media': []}
        current_media = None
        
        for line in sdp_text.strip().split('\n'):
            line = line.strip()
            if not line or '=' not in line:
                continue
                
            type_char, value = line.split('=', 1)
            
            if type_char == 'm':
                parts = value.split()
                current_media = {
                    'type': parts[0],
                    'port': int(parts[1]),
                    'protocol': parts[2],
                    'formats': parts[3:],
                }
                sdp['media'].append(current_media)
        
        return sdp
    
    @staticmethod
    def build(local_ip, rtp_port, session_id=None, codecs=None):
        """构建 SDP"""
        if not session_id:
            session_id = str(int(time.time()))
        if not codecs:
            codecs = ['0', '8']
        
        sdp_lines = [
            "v=0",
            f"o=- {session_id} {session_id} IN IP4 {local_ip}",
            "s=VTX AI Phone",
            f"c=IN IP4 {local_ip}",
            "t=0 0",
            f"m=audio {rtp_port} RTP/AVP {' '.join(codecs)}",
            "a=rtpmap:0 PCMU/8000",
            "a=rtpmap:8 PCMA/8000",
            "a=sendrecv",
        ]
        
        return '\r\n'.join(sdp_lines)

class RTPHandler:
    """RTP 处理器 - 支持AI对话"""
    
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
        
        # AI对话支持
        self.ai_conversation = None
        
    def set_ai_conversation(self, ai_conversation):
        """设置AI对话管理器"""
        self.ai_conversation = ai_conversation
        
    def start(self, remote_ip, remote_port):
        """启动 RTP"""
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.local_ip, self.local_port))
        self.sock.settimeout(0.1)
        
        self.running = True
        
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
        
        packet = self._build_rtp_packet(audio_data, payload_type)
        self.sock.sendto(packet, (self.remote_ip, self.remote_port))
        
        self.sequence = (self.sequence + 1) & 0xFFFF
        self.timestamp = (self.timestamp + 160) & 0xFFFFFFFF
    
    def _build_rtp_packet(self, payload, payload_type):
        """构建 RTP 包"""
        byte0 = 0x80
        byte1 = payload_type & 0x7F
        
        header = struct.pack('!BBHII',
                           byte0, byte1, self.sequence,
                           self.timestamp, self.ssrc)
        
        return header + payload
    
    def _receive_loop(self):
        """接收循环"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                
                # 解析RTP包
                if len(data) >= 12:
                    payload = data[12:]  # 跳过RTP头部
                    if payload and self.ai_conversation:
                        self.ai_conversation.process_audio_input(payload)
                        
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"RTP 接收错误: {e}")

class G711Codec:
    """G.711 编解码器"""
    
    @staticmethod
    def linear_to_ulaw(sample):
        """线性 PCM 转 μ-law"""
        if sample < 0:
            sample = -sample
            sign = 0x80
        else:
            sign = 0
        
        if sample > 32635:
            sample = 32635
        
        sample += 132
        
        seg = 0
        for i in range(8):
            if sample >= (128 << i):
                seg = i
        
        if seg >= 8:
            uval = 0x7F
        else:
            uval = (seg << 4) | ((sample >> (seg + 3)) & 0x0F)
        
        return (sign | uval) ^ 0xFF
    
    @staticmethod
    def generate_dtmf(digit, duration=0.2, sample_rate=8000):
        """生成 DTMF 音调"""
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
        
        audio_data = bytearray()
        for i in range(samples):
            t = i / sample_rate
            sample = int(16383 * 0.5 * (
                math.sin(2 * math.pi * low_freq * t) +
                math.sin(2 * math.pi * high_freq * t)
            ))
            ulaw = G711Codec.linear_to_ulaw(sample)
            audio_data.append(ulaw)
        
        return bytes(audio_data)

class VTXAIPhoneSystem:
    """VTX AI电话系统"""
    
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
        
        # SIP状态
        self.registered = False
        self.cseq = 0
        self.call_id = str(uuid.uuid4())
        self.tag = str(uuid.uuid4())[:8]
        self.branch = str(uuid.uuid4())[:8]
        
        # 认证
        self.realm = self.domain
        self.nonce = ""
        
        # 通话管理
        self.active_calls = {}
        self.rtp_port_start = 10000
        self.rtp_port_end = 10500
        self.next_rtp_port = self.rtp_port_start
        
        # 注册管理
        self.register_response_queue = queue.Queue()
        self.waiting_for_register = False
        
        print("🚀 VTX AI电话系统初始化完成")
    
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
    
    def start(self):
        """启动系统"""
        print(f"📞 启动VTX AI电话系统...")
        print(f"🌐 服务器: {self.server}:{self.port}")
        print(f"🏠 本地IP: {self.local_ip}")
        print(f"👤 用户名: {self.username}")
        
        # 创建UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.local_ip, 0))
        self.local_port = self.sock.getsockname()[1]
        
        # 注册
        if not self.initial_register():
            print("❌ 注册失败")
            return False
        
        print("✅ 系统启动成功")
        
        # 启动接收循环
        self._receive_loop()
        
        return True
    
    def _handle_invite(self, message, addr, call_id):
        """处理INVITE请求"""
        print(f"📥 收到INVITE: {call_id}")
        
        # 发送100 Trying
        self._send_trying(message, addr)
        
        # 发送180 Ringing
        to_tag = str(uuid.uuid4())[:8]
        self._send_ringing(message, addr, to_tag)
        
        # 等待2秒后发送200 OK
        time.sleep(2)
        
        # 分配RTP端口
        rtp_port = self._get_next_rtp_port()
        
        # 发送200 OK with SDP
        self._send_ok_with_sdp(message, addr, to_tag, rtp_port)
        
        # 启动RTP和AI对话
        self._start_rtp_and_ai(addr, rtp_port, call_id)
    
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
        
        # 修改To头，添加tag
        to_header = headers.get('to', '')
        if ';tag=' not in to_header:
            to_header = to_header.rstrip() + f';tag={to_tag}'
        
        response_lines = [
            "SIP/2.0 180 Ringing",
            headers.get('via', ''),
            headers.get('from', ''),
            to_header,
            headers.get('call_id', ''),
            headers.get('cseq', ''),
            "Content-Length: 0",
            "",
            ""
        ]
        
        response = "\r\n".join(response_lines)
        self.sock.sendto(response.encode(), addr)
        print("📤 发送: 180 Ringing")
    
    def _send_ok_with_sdp(self, invite_message, addr, to_tag, rtp_port):
        """发送200 OK with SDP"""
        headers = self._extract_headers(invite_message)
        
        # 修改To头，添加tag
        to_header = headers.get('to', '')
        if ';tag=' not in to_header:
            to_header = to_header.rstrip() + f';tag={to_tag}'
        
        # 构建SDP
        sdp = SDPParser.build(self.local_ip, rtp_port)
        
        response_lines = [
            "SIP/2.0 200 OK",
            headers.get('via', ''),
            headers.get('from', ''),
            to_header,
            headers.get('call_id', ''),
            headers.get('cseq', ''),
            f"Content-Type: application/sdp",
            f"Content-Length: {len(sdp)}",
            "",
            sdp
        ]
        
        response = "\r\n".join(response_lines)
        self.sock.sendto(response.encode(), addr)
        print("📤 发送: 200 OK with SDP")
    
    def _start_rtp_and_ai(self, addr, rtp_port, call_id):
        """启动RTP和AI对话"""
        print(f"🎵 启动RTP和AI对话: {addr[0]}:{rtp_port}")
        
        # 创建RTP处理器
        rtp_handler = RTPHandler(self.local_ip, rtp_port)
        
        # 解析SDP获取远程RTP端口
        remote_rtp_port = rtp_port + 1  # 简化处理
        
        rtp_handler.start(addr[0], remote_rtp_port)
        
        # 保存通话
        self.active_calls[call_id] = rtp_handler
        
        # 启动AI对话
        if AI_AVAILABLE:
            self._start_ai_conversation(rtp_handler)
        else:
            self._send_default_audio(rtp_handler)
    
    def _start_ai_conversation(self, rtp_handler):
        """启动AI对话"""
        try:
            print("🤖 启动AI对话...")
            
            # 创建AI对话管理器
            ai_conversation = AIConversationManager()
            
            # 设置音频回调
            def audio_callback(audio_data):
                if rtp_handler and rtp_handler.running:
                    packet_size = 160
                    for i in range(0, len(audio_data), packet_size):
                        packet = audio_data[i:i+packet_size]
                        if len(packet) < packet_size:
                            packet += b'\xFF' * (packet_size - len(packet))
                        rtp_handler.send_audio(packet, payload_type=0)
                        time.sleep(0.02)
            
            ai_conversation.set_audio_callback(audio_callback)
            rtp_handler.set_ai_conversation(ai_conversation)
            
            # 启动对话
            ai_conversation.start_conversation()
            ai_conversation.start_audio_processing_thread()
            
            print("✅ AI对话启动成功")
            
        except Exception as e:
            print(f"❌ AI对话启动失败: {e}")
            self._send_default_audio(rtp_handler)
    
    def _send_default_audio(self, rtp_handler):
        """发送默认音频"""
        print("🎵 发送默认音频...")
        
        # 生成DTMF音调
        audio_data = G711Codec.generate_dtmf('1', 0.5)
        audio_data += G711Codec.generate_dtmf('8', 0.5)
        audio_data += G711Codec.generate_dtmf('7', 0.5)
        audio_data += G711Codec.generate_dtmf('1', 0.5)
        
        # 发送音频
        packet_size = 160
        for i in range(0, len(audio_data), packet_size):
            packet = audio_data[i:i+packet_size]
            if len(packet) < packet_size:
                packet += b'\xFF' * (packet_size - len(packet))
            rtp_handler.send_audio(packet, payload_type=0)
            time.sleep(0.02)
        
        print("✅ 默认音频发送完成")
    
    def _get_next_rtp_port(self):
        """获取下一个RTP端口"""
        port = self.next_rtp_port
        self.next_rtp_port += 2
        if self.next_rtp_port > self.rtp_port_end:
            self.next_rtp_port = self.rtp_port_start
        return port
    
    def _handle_bye(self, message, addr):
        """处理BYE请求"""
        call_id_match = re.search(r'Call-ID:\s*(.+)', message, re.IGNORECASE)
        if call_id_match:
            call_id = call_id_match.group(1).strip()
            
            if call_id in self.active_calls:
                rtp_handler = self.active_calls[call_id]
                rtp_handler.stop()
                del self.active_calls[call_id]
                print(f"🔇 停止通话: {call_id}")
        
        # 发送200 OK
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
    
    def _extract_headers(self, message):
        """提取SIP头"""
        headers = {}
        lines = message.split('\r\n')
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.lower().strip()
                value = value.strip()
                
                if key == 'via':
                    headers['via'] = line
                elif key == 'from':
                    headers['from'] = line
                elif key == 'to':
                    headers['to'] = line
                elif key == 'call-id':
                    headers['call_id'] = line
                elif key == 'cseq':
                    headers['cseq'] = line
        
        return headers
    
    def initial_register(self):
        """初始注册"""
        print("📝 执行初始注册...")
        
        try:
            # 发送初始REGISTER
            self.cseq += 1
            self.waiting_for_register = True
            
            register1 = self._build_register()
            print(f"📤 发送初始REGISTER...")
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
            
            # 发送认证REGISTER
            return self.refresh_register()
                
        except Exception as e:
            print(f"❌ 注册错误: {e}")
            return False
    
    def refresh_register(self):
        """刷新注册"""
        try:
            self.cseq += 1
            self.waiting_for_register = True
            
            auth_header = self._build_auth_header()
            register = self._build_register(auth_header=auth_header)
            
            print(f"📤 发送认证REGISTER...")
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
                return True
            else:
                print(f"❌ 注册失败: {response}")
                return False
                
        except Exception as e:
            print(f"❌ 刷新错误: {e}")
            return False
    
    def _build_register(self, auth_header=None):
        """构建REGISTER请求"""
        self.cseq += 1
        
        register_lines = [
            f"REGISTER sip:{self.domain} SIP/2.0",
            f"Via: SIP/2.0/UDP {self.local_ip}:{self.local_port};branch={self.branch}",
            f"From: <sip:{self.username}@{self.domain}>;tag={self.tag}",
            f"To: <sip:{self.username}@{self.domain}>",
            f"Call-ID: {self.call_id}",
            f"CSeq: {self.cseq} REGISTER",
            f"Contact: <sip:{self.username}@{self.local_ip}:{self.local_port}>",
            "Expires: 3600",
            "User-Agent: VTX-AI-Phone/1.0",
            "Content-Length: 0",
            "",
            ""
        ]
        
        if auth_header:
            register_lines.insert(-3, f"Proxy-Authorization: Digest {auth_header}")
        
        return "\r\n".join(register_lines)
    
    def _build_auth_header(self):
        """构建认证头"""
        username = self.username
        password = self.password
        realm = self.realm
        nonce = self.nonce
        uri = f"sip:{self.domain}"
        method = "REGISTER"
        
        # 计算HA1
        ha1 = hashlib.md5(f"{username}:{realm}:{password}".encode()).hexdigest()
        
        # 计算HA2
        ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()
        
        # 计算response
        response = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
        
        auth_header = f'username="{username}", realm="{realm}", nonce="{nonce}", uri="{uri}", response="{response}"'
        return auth_header
    
    def _parse_auth_header(self, auth_header):
        """解析认证头"""
        params = {}
        for param in auth_header.split(','):
            if '=' in param:
                key, value = param.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"')
                params[key] = value
        return params
    
    def _receive_loop(self):
        """接收循环"""
        print("👂 开始监听SIP消息...")
        
        while True:
            try:
                data, addr = self.sock.recvfrom(4096)
                message = data.decode('utf-8', errors='ignore')
                
                # 处理SIP消息
                self._handle_sip_message(message, addr)
                
            except Exception as e:
                print(f"❌ 接收错误: {e}")
    
    def _handle_sip_message(self, message, addr):
        """处理SIP消息"""
        lines = message.split('\r\n')
        if not lines:
            return
        
        first_line = lines[0]
        
        if first_line.startswith('SIP/2.0'):
            # 响应消息
            self._handle_response(message, addr)
        else:
            # 请求消息
            self._handle_request(message, addr, first_line)
    
    def _handle_response(self, message, addr):
        """处理响应消息"""
        if self.waiting_for_register:
            self.register_response_queue.put(message)
        
        if "200 OK" in message and "REGISTER" in message:
            print("✅ 注册响应: 200 OK")
    
    def _handle_request(self, message, addr, first_line):
        """处理请求消息"""
        parts = first_line.split()
        if len(parts) < 3:
            return
        
        method = parts[0]
        
        # 提取Call-ID
        call_id_match = re.search(r'Call-ID:\s*(.+)', message, re.IGNORECASE)
        call_id = call_id_match.group(1).strip() if call_id_match else str(uuid.uuid4())
        
        if method == "INVITE":
            self._handle_invite(message, addr, call_id)
        elif method == "BYE":
            self._handle_bye(message, addr)
        elif method == "OPTIONS":
            self._handle_options(message, addr)
        elif method == "CANCEL":
            self._handle_cancel(message, addr)
    
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
            "Allow: INVITE, ACK, BYE, CANCEL, OPTIONS",
            "Content-Length: 0",
            "",
            ""
        ]
        
        response = "\r\n".join(response_lines)
        self.sock.sendto(response.encode(), addr)
        print("📤 发送: 200 OK (OPTIONS)")
    
    def _handle_cancel(self, message, addr):
        """处理CANCEL请求"""
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
    
    def stop(self):
        """停止系统"""
        print("🛑 停止VTX AI电话系统...")
        
        # 停止所有通话
        for call_id, rtp_handler in self.active_calls.items():
            rtp_handler.stop()
        
        if self.sock:
            self.sock.close()
        
        print("✅ 系统已停止")

def main():
    """主函数"""
    print("🚀 VTX AI Phone System v2.0 - AI对话版")
    print("=" * 50)
    
    # 创建系统实例
    system = VTXAIPhoneSystem()
    
    try:
        # 启动系统
        if system.start():
            print("🎉 系统运行中，按Ctrl+C停止...")
            
            # 保持运行
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n🛑 收到停止信号")
    except Exception as e:
        print(f"❌ 系统错误: {e}")
    finally:
        system.stop()

if __name__ == "__main__":
    main() 