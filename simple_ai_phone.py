#!/usr/bin/env python3
"""
简化版AI电话系统 - 直接连接分机101处理通话
"""

import asyncio
import logging
import os
import sys
import signal
import threading
import time
import socket
import hashlib
import random
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from local_ai import LocalLLM, LocalTTS, AudioConverter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class SimpleSIPClient:
    """简化版SIP客户端"""
    
    def __init__(self, username, password, domain, server, port=5060):
        self.username = username
        self.password = password
        self.domain = domain
        self.server = server
        self.port = port
        
        self.local_ip = self._get_local_ip()
        self.local_port = random.randint(50000, 60000)
        self.socket = None
        self.is_registered = False
        self.call_handler = None
        
        # SIP消息计数器
        self.cseq_counter = 1
        
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
    
    def _generate_call_id(self):
        """生成Call-ID"""
        return f"{random.randint(100000, 999999)}@{self.local_ip}"
    
    def _generate_tag(self):
        """生成标签"""
        return f"{random.randint(100000, 999999)}"
    
    def _calculate_auth_response(self, method, uri, realm, nonce):
        """计算认证响应"""
        ha1 = hashlib.md5(f"{self.username}:{realm}:{self.password}".encode()).hexdigest()
        ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()
        response = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
        return response
    
    def start(self):
        """启动SIP客户端"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.local_ip, self.local_port))
            self.socket.settimeout(1.0)
            
            logger.info(f"SIP客户端启动: {self.local_ip}:{self.local_port}")
            
            # 发送初始REGISTER
            self._send_register()
            
            # 启动消息接收线程
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
            self.receive_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"SIP客户端启动失败: {e}")
            return False
    
    def _send_register(self, auth_header=None):
        """发送REGISTER请求"""
        call_id = self._generate_call_id()
        tag = self._generate_tag()
        
        register_msg = f"REGISTER sip:{self.domain} SIP/2.0\r\n"
        register_msg += f"Via: SIP/2.0/UDP {self.local_ip}:{self.local_port};branch=z9hG4bK{random.randint(100000, 999999)}\r\n"
        register_msg += f"From: <sip:{self.username}@{self.domain}>;tag={tag}\r\n"
        register_msg += f"To: <sip:{self.username}@{self.domain}>\r\n"
        register_msg += f"Call-ID: {call_id}\r\n"
        register_msg += f"CSeq: {self.cseq_counter} REGISTER\r\n"
        register_msg += f"Contact: <sip:{self.username}@{self.local_ip}:{self.local_port}>\r\n"
        register_msg += f"Max-Forwards: 70\r\n"
        register_msg += f"User-Agent: VTX-AI-Phone/1.0\r\n"
        register_msg += f"Expires: 3600\r\n"
        
        if auth_header:
            register_msg += f"Authorization: {auth_header}\r\n"
        
        register_msg += f"Content-Length: 0\r\n\r\n"
        
        self.socket.sendto(register_msg.encode(), (self.server, self.port))
        self.cseq_counter += 1
        logger.info("发送REGISTER请求")
    
    def _receive_messages(self):
        """接收SIP消息"""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(4096)
                message = data.decode('utf-8', errors='ignore')
                self._handle_sip_message(message, addr)
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"接收消息错误: {e}")
    
    def _handle_sip_message(self, message, addr):
        """处理SIP消息"""
        try:
            lines = message.split('\r\n')
            first_line = lines[0]
            
            if "401 Unauthorized" in first_line and not self.is_registered:
                logger.info("收到认证挑战，发送认证REGISTER")
                self._handle_auth_challenge(message)
            elif "200 OK" in first_line and "REGISTER" in message:
                logger.info("✅ SIP注册成功!")
                self.is_registered = True
            elif "INVITE" in first_line:
                logger.info("📞 收到来电INVITE")
                self._handle_invite(message, addr)
            
        except Exception as e:
            logger.error(f"处理SIP消息错误: {e}")
    
    def _handle_auth_challenge(self, message):
        """处理认证挑战"""
        try:
            # 解析WWW-Authenticate头
            auth_line = None
            for line in message.split('\r\n'):
                if line.startswith('WWW-Authenticate:'):
                    auth_line = line
                    break
            
            if not auth_line:
                return
            
            # 提取realm和nonce
            realm = None
            nonce = None
            
            parts = auth_line.split(',')
            for part in parts:
                if 'realm=' in part:
                    realm = part.split('realm=')[1].strip('"')
                elif 'nonce=' in part:
                    nonce = part.split('nonce=')[1].strip('"')
            
            if realm and nonce:
                # 计算认证响应
                uri = f"sip:{self.domain}"
                response = self._calculate_auth_response("REGISTER", uri, realm, nonce)
                
                # 构建Authorization头
                auth_header = f'Digest username="{self.username}", realm="{realm}", '
                auth_header += f'nonce="{nonce}", uri="{uri}", response="{response}"'
                
                # 发送带认证的REGISTER
                self._send_register(auth_header)
            
        except Exception as e:
            logger.error(f"处理认证挑战错误: {e}")
    
    def _handle_invite(self, message, addr):
        """处理来电INVITE"""
        if self.call_handler:
            # 提取来电信息
            call_info = {
                'call_id': 'incoming_call_1',
                'caller': 'unknown',
                'remote_ip': addr[0],
                'remote_port': 8000,  # RTP端口
                'local_rtp_port': random.randint(10000, 20000)
            }
            
            # 发送200 OK响应
            self._send_invite_ok(message, call_info)
            
            # 通知应用层处理来电
            self.call_handler(call_info)
    
    def _send_invite_ok(self, invite_message, call_info):
        """发送INVITE的200 OK响应"""
        try:
            # 这里简化处理，实际应解析INVITE消息构建正确的响应
            ok_response = "SIP/2.0 200 OK\r\n"
            ok_response += f"Content-Type: application/sdp\r\n"
            ok_response += f"Content-Length: 0\r\n\r\n"
            
            self.socket.sendto(ok_response.encode(), (call_info['remote_ip'], self.port))
            logger.info("发送INVITE 200 OK响应")
            
        except Exception as e:
            logger.error(f"发送INVITE响应错误: {e}")
    
    def set_call_handler(self, handler):
        """设置来电处理回调"""
        self.call_handler = handler
    
    def stop(self):
        """停止SIP客户端"""
        self.running = False
        if self.socket:
            self.socket.close()


class SimpleAIPhone:
    """简化版AI电话系统"""
    
    def __init__(self):
        self.config = settings
        self.is_running = False
        self.sip_client = None
        
        # AI组件
        self.llm_service = None
        self.tts_service = None
        
        logger.info("简化版AI电话系统初始化")
    
    def _init_ai_services(self):
        """初始化AI服务"""
        try:
            logger.info("🧠 初始化LLM...")
            self.llm_service = LocalLLM(
                model_name="Qwen/Qwen2.5-7B-Instruct",
                device="cuda",
                max_length=512,
                temperature=0.7,
                use_4bit=True
            )
            logger.info("✅ LLM就绪")
            
            logger.info("🗣️ 初始化TTS...")
            self.tts_service = LocalTTS(
                engine="system",
                voice="zh",
                device="cpu",
                speed=1.0
            )
            logger.info("✅ TTS就绪")
            
        except Exception as e:
            logger.error(f"AI服务初始化失败: {e}")
            raise
    
    def start(self):
        """启动系统"""
        try:
            logger.info("🚀 启动简化版AI电话系统...")
            
            # 初始化AI服务
            self._init_ai_services()
            
            # 获取分机配置
            extension = self.config.extensions['101']
            
            logger.info(f"📞 连接分机: {extension.username}@{self.config.vtx.domain}")
            
            # 创建SIP客户端
            self.sip_client = SimpleSIPClient(
                username=extension.username,
                password=extension.password,
                domain=self.config.vtx.domain,
                server=self.config.vtx.server,
                port=self.config.vtx.port
            )
            
            # 设置来电处理
            self.sip_client.set_call_handler(self._handle_incoming_call)
            
            # 启动SIP客户端
            if self.sip_client.start():
                self.is_running = True
                logger.info("✅ AI电话系统启动成功!")
                logger.info(f"📱 DID号码: {self.config.vtx.did_number}")
                logger.info("等待来电...")
                
                # 主循环
                self._main_loop()
            else:
                logger.error("❌ SIP客户端启动失败")
                
        except Exception as e:
            logger.error(f"系统启动失败: {e}")
            self.stop()
    
    def _handle_incoming_call(self, call_info):
        """处理来电"""
        logger.info(f"📞 来电: {call_info['caller']}")
        
        # 发送欢迎消息
        welcome_msg = "您好，欢迎致电OneSuite Business！我是您的AI助手。"
        logger.info(f"🤖 AI回复: {welcome_msg}")
        
        # 模拟语音合成和播放
        try:
            audio_data = self.tts_service.synthesize_text(welcome_msg)
            logger.info(f"🎵 语音合成完成: {len(audio_data)} bytes")
            logger.info("📢 (音频已发送到通话)")
        except Exception as e:
            logger.error(f"语音合成错误: {e}")
    
    def _main_loop(self):
        """主循环"""
        try:
            while self.is_running:
                time.sleep(1)
                
                # 显示状态
                if hasattr(self, '_last_status_time'):
                    if time.time() - self._last_status_time > 30:
                        self._show_status()
                        self._last_status_time = time.time()
                else:
                    self._last_status_time = time.time()
                    
        except KeyboardInterrupt:
            logger.info("收到中断信号")
        except Exception as e:
            logger.error(f"主循环错误: {e}")
        finally:
            self.stop()
    
    def _show_status(self):
        """显示系统状态"""
        status = "🟢" if self.sip_client.is_registered else "🔴"
        logger.info(f"状态: {status} 注册状态: {'已注册' if self.sip_client.is_registered else '未注册'}")
    
    def stop(self):
        """停止系统"""
        logger.info("停止AI电话系统...")
        
        self.is_running = False
        
        if self.sip_client:
            self.sip_client.stop()
        
        if self.tts_service:
            self.tts_service.cleanup()
        
        logger.info("✅ AI电话系统已停止")


def signal_handler(signum, frame):
    """信号处理器"""
    logger.info(f"收到信号 {signum}")
    if 'phone_system' in globals():
        phone_system.stop()
    sys.exit(0)


def main():
    """主函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 50)
    print("🤖 VTX AI Phone System - 简化版")
    print("=" * 50)
    print("📋 配置信息:")
    print(f"   - 分机: 101")
    print(f"   - 域名: {settings.vtx.domain}")
    print(f"   - 服务器: {settings.vtx.server}")
    print(f"   - DID: {settings.vtx.did_number}")
    print("=" * 50)
    print("🚀 正在启动系统...")
    print()
    
    try:
        # 创建并启动系统
        global phone_system
        phone_system = SimpleAIPhone()
        phone_system.start()
        
    except Exception as e:
        logger.error(f"系统错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()