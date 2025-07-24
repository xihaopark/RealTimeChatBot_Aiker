#!/usr/bin/env python3
"""
SIP连接测试脚本 - 不包含AI组件
"""

import os
import sys
import time
import threading
import socket
import hashlib
import random
import uuid
import re

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings

class SIPTester:
    def __init__(self):
        self.config = settings
        self.sip_socket = None
        self.running = False
        self.is_registered = False
        self.call_id = None
        self.cseq = 1
        self.local_ip = None
        self.local_port = None
        
    def start(self):
        print("🧪 SIP连接测试")
        print(f"📞 分机: 101@{self.config.vtx.domain}")
        print(f"🌐 服务器: {self.config.vtx.server}:{self.config.vtx.port}")
        
        if self._connect_sip():
            print("⏳ 等待SIP注册...")
            timeout = 10
            while not self.is_registered and timeout > 0:
                time.sleep(0.5)
                timeout -= 0.5
            
            if self.is_registered:
                print("✅ SIP注册成功！分机101已连接")
                print("📞 系统现在可以接收来电")
                # 保持运行5秒来测试
                time.sleep(5)
            else:
                print("❌ SIP注册超时失败")
        else:
            print("❌ SIP连接失败")
        
        self.stop()
    
    def _connect_sip(self):
        try:
            ext = self.config.extensions['101']
            self.sip_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # 获取本地IP
            self.local_ip = self._get_local_ip()
            self.local_port = random.randint(50000, 60000)
            self.sip_socket.bind((self.local_ip, self.local_port))
            self.sip_socket.settimeout(1.0)
            
            print(f"📍 本地地址: {self.local_ip}:{self.local_port}")
            
            # 生成Call-ID
            self.call_id = str(uuid.uuid4())
            
            # 启动接收线程
            self.running = True
            threading.Thread(target=self._sip_receiver, daemon=True).start()
            
            # 发送初始REGISTER
            self._send_register()
            return True
            
        except Exception as e:
            print(f"❌ SIP连接失败: {e}")
            return False
    
    def _get_local_ip(self):
        """获取本地IP地址"""
        try:
            temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp_sock.connect((self.config.vtx.server, self.config.vtx.port))
            local_ip = temp_sock.getsockname()[0]
            temp_sock.close()
            return local_ip
        except:
            return "127.0.0.1"
    
    def _send_register(self, auth_header=None):
        """发送REGISTER请求"""
        ext = self.config.extensions['101']
        branch = f"z9hG4bK{uuid.uuid4().hex[:8]}"
        tag = uuid.uuid4().hex[:8]
        
        register_lines = [
            f"REGISTER sip:{self.config.vtx.domain} SIP/2.0",
            f"Via: SIP/2.0/UDP {self.local_ip}:{self.local_port};branch={branch}",
            f"Max-Forwards: 70",
            f"From: <sip:{ext.username}@{self.config.vtx.domain}>;tag={tag}",
            f"To: <sip:{ext.username}@{self.config.vtx.domain}>",
            f"Call-ID: {self.call_id}",
            f"CSeq: {self.cseq} REGISTER",
            f"Contact: <sip:{ext.username}@{self.local_ip}:{self.local_port}>",
            f"User-Agent: VTX-SIP-Tester/1.0",
            f"Expires: 3600"
        ]
        
        if auth_header:
            register_lines.insert(-1, auth_header)
        
        register_lines.extend(["Content-Length: 0", ""])
        register_msg = "\r\n".join(register_lines)
        
        self.sip_socket.sendto(register_msg.encode(), (self.config.vtx.server, self.config.vtx.port))
        print(f"📤 发送REGISTER (CSeq: {self.cseq})")
        self.cseq += 1
    
    def _sip_receiver(self):
        while self.running:
            try:
                data, addr = self.sip_socket.recvfrom(4096)
                msg = data.decode('utf-8', errors='ignore')
                self._handle_sip_message(msg, addr)
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"⚠️ SIP接收错误: {e}")
    
    def _handle_sip_message(self, message, addr):
        """处理SIP消息"""
        try:
            lines = message.split('\r\n')
            first_line = lines[0]
            
            print(f"📨 收到SIP消息: {first_line}")
            
            if first_line.startswith('SIP/2.0'):
                # 响应消息
                parts = first_line.split(' ', 2)
                status_code = int(parts[1])
                
                if 'REGISTER' in message:
                    self._handle_register_response(message, status_code)
                    
        except Exception as e:
            print(f"⚠️ SIP消息处理错误: {e}")
    
    def _handle_register_response(self, message, status_code):
        """处理REGISTER响应"""
        if status_code == 401 or status_code == 407:
            print("🔐 需要认证，处理认证挑战")
            self._handle_auth_challenge(message)
        elif status_code == 200:
            print("✅ SIP注册成功!")
            self.is_registered = True
        else:
            print(f"❌ 注册失败，状态码: {status_code}")
    
    def _handle_auth_challenge(self, message):
        """处理认证挑战"""
        try:
            # 解析WWW-Authenticate头
            auth_match = re.search(r'WWW-Authenticate:\s*(.+)', message, re.IGNORECASE)
            if not auth_match:
                return
            
            auth_header = auth_match.group(1)
            
            # 解析realm和nonce
            realm_match = re.search(r'realm="([^"]+)"', auth_header)
            nonce_match = re.search(r'nonce="([^"]+)"', auth_header)
            
            if not (realm_match and nonce_match):
                print("❌ 无法解析认证参数")
                return
            
            realm = realm_match.group(1)
            nonce = nonce_match.group(1)
            
            print(f"🔑 认证参数 - Realm: {realm}")
            
            # 计算认证响应
            ext = self.config.extensions['101']
            uri = f"sip:{self.config.vtx.domain}"
            
            ha1 = hashlib.md5(f"{ext.username}:{realm}:{ext.password}".encode()).hexdigest()
            ha2 = hashlib.md5(f"REGISTER:{uri}".encode()).hexdigest()
            response = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
            
            # 构建Authorization头
            auth_line = f'Authorization: Digest username="{ext.username}", realm="{realm}", nonce="{nonce}", uri="{uri}", response="{response}"'
            
            # 发送认证REGISTER
            self._send_register(auth_line)
            
        except Exception as e:
            print(f"❌ 认证处理失败: {e}")
    
    def stop(self):
        """停止测试"""
        print("🛑 停止SIP测试")
        self.running = False
        if self.sip_socket:
            self.sip_socket.close()

if __name__ == "__main__":
    tester = SIPTester()
    try:
        tester.start()
    except KeyboardInterrupt:
        print("\n🛑 用户中断")
        tester.stop()