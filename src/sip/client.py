"""
SIP 客户端核心
管理 SIP 会话和通话
"""

import socket
import threading
import queue
import time
import uuid
from typing import Dict, Optional, Callable, Tuple
from enum import Enum

from .messages import SIPMessage, SIPRequest, SIPResponse, SIPMessageParser, SIPMessageBuilder
from .auth import DigestAuth
from ..sdp import SDPParser
from ..rtp import RTPHandler


class SIPState(Enum):
    """SIP 客户端状态"""
    IDLE = "idle"
    REGISTERING = "registering"
    REGISTERED = "registered"
    UNREGISTERING = "unregistering"
    FAILED = "failed"


class CallState(Enum):
    """通话状态"""
    IDLE = "idle"
    CALLING = "calling"
    RINGING = "ringing"
    ANSWERED = "answered"
    ENDING = "ending"
    ENDED = "ended"


class Call:
    """通话对象"""
    
    def __init__(self, call_id: str, direction: str = "inbound"):
        self.call_id = call_id
        self.direction = direction  # inbound/outbound
        self.state = CallState.IDLE
        self.local_tag = uuid.uuid4().hex[:8]
        self.remote_tag = None
        self.rtp_handler = None
        self.sdp = None
        self.start_time = time.time()
        self.answer_time = None
        self.end_time = None


class SIPClient:
    """SIP 客户端"""
    
    def __init__(self, server: str, port: int, domain: str,
                 username: str, password: str):
        """
        初始化 SIP 客户端
        
        Args:
            server: SIP 服务器地址
            port: SIP 端口
            domain: SIP 域
            username: 用户名
            password: 密码
        """
        # 配置
        self.server = server
        self.port = port
        self.domain = domain
        self.username = username
        self.password = password
        
        # 网络
        self.server_ip = socket.gethostbyname(server)
        self.local_ip = self._get_local_ip()
        self.local_port = None
        self.sock = None
        
        # 状态
        self.state = SIPState.IDLE
        self.running = False
        
        # SIP 参数
        self.call_id = f"{uuid.uuid4()}@{self.local_ip}"
        self.from_tag = uuid.uuid4().hex[:8]
        self.cseq = 0
        self.expires = 60
        
        # 认证
        self.realm = None
        self.nonce = None
        
        # 线程
        self.receive_thread = None
        self.keepalive_thread = None
        
        # 队列
        self.response_queue = queue.Queue()
        self.request_queue = queue.Queue()
        
        # 通话管理
        self.calls: Dict[str, Call] = {}
        self.processed_invites = set()
        
        # 回调
        self.on_incoming_call: Optional[Callable[[Call, SIPRequest], None]] = None
        
        # RTP 端口范围
        self.rtp_port_start = 10000
        self.rtp_port_end = 20000
        self.next_rtp_port = self.rtp_port_start
        
        print(f"📞 SIP 客户端初始化: {username}@{domain}")
    
    def start(self):
        """启动客户端"""
        try:
            # 创建 socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind(('0.0.0.0', 0))
            self.sock.settimeout(0.5)
            self.local_port = self.sock.getsockname()[1]
            
            print(f"📍 绑定端口: {self.local_port}")
            
            # 启动接收线程
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            # 执行注册
            if self.register():
                # 启动保活线程
                self.keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True)
                self.keepalive_thread.start()
                
                print("✅ SIP 客户端启动成功")
                return True
            else:
                print("❌ 注册失败")
                self.running = False
                return False
                
        except Exception as e:
            print(f"❌ 启动失败: {e}")
            self.running = False
            return False
    
    def stop(self):
        """停止客户端"""
        print("🛑 停止 SIP 客户端...")
        self.running = False
        
        # 结束所有通话
        for call_id in list(self.calls.keys()):
            self.end_call(call_id)
        
        # 关闭 socket
        if self.sock:
            self.sock.close()
        
        print("✅ SIP 客户端已停止")
    
    def register(self) -> bool:
        """执行 SIP 注册"""
        self.state = SIPState.REGISTERING
        self.cseq += 1
        
        # 构建 REGISTER 请求
        request = SIPMessageBuilder.build_register(
            self.username, self.domain, self.server,
            self.local_ip, self.local_port,
            expires=self.expires,
            call_id=self.call_id,
            from_tag=self.from_tag,
            cseq=self.cseq
        )
        
        # 发送请求
        response = self._send_request(request)
        
        if not response:
            self.state = SIPState.FAILED
            return False
        
        # 处理 407 认证要求
        if response.status_code == 407:
            # 提取认证参数
            auth_params = DigestAuth.extract_challenge(response.to_string())
            if not auth_params:
                self.state = SIPState.FAILED
                return False
            
            self.realm = auth_params.get('realm', self.domain)
            self.nonce = auth_params.get('nonce', '')
            
            # 构建认证头
            auth_header = DigestAuth.build_auth_header(
                self.username, self.password, self.realm,
                self.nonce, f"sip:{self.domain}", "REGISTER"
            )
            
            # 重新发送带认证的请求
            self.cseq += 1
            request = SIPMessageBuilder.build_register(
                self.username, self.domain, self.server,
                self.local_ip, self.local_port,
                expires=self.expires,
                call_id=self.call_id,
                from_tag=self.from_tag,
                cseq=self.cseq,
                auth_header=auth_header
            )
            
            response = self._send_request(request)
            
            if not response:
                self.state = SIPState.FAILED
                return False
        
        # 检查注册结果
        if response.status_code == 200:
            self.state = SIPState.REGISTERED
            print("✅ 注册成功")
            
            # 提取过期时间
            expires_header = response.get_header('Expires')
            if expires_header:
                self.expires = int(expires_header)
            
            return True
        else:
            self.state = SIPState.FAILED
            print(f"❌ 注册失败: {response.status_code} {response.reason_phrase}")
            return False
    
    def handle_incoming_call(self, request: SIPRequest):
        """处理来电"""
        call_id = request.get_header('Call-ID')
        if not call_id:
            return
        
        # 创建通话对象
        call = Call(call_id, "inbound")
        self.calls[call_id] = call
        
        # 发送 100 Trying
        self._send_response(request, 100, "Trying")
        
        # 发送 180 Ringing
        time.sleep(0.1)
        self._send_response(request, 180, "Ringing", to_tag=call.local_tag)
        
        # 调用回调
        if self.on_incoming_call:
            self.on_incoming_call(call, request)
        else:
            # 默认拒绝
            time.sleep(2)
            self._send_response(request, 486, "Busy Here", to_tag=call.local_tag)
    
    def answer_call(self, call_id: str, sdp: str):
        """接听电话"""
        call = self.calls.get(call_id)
        if not call:
            return
        
        call.state = CallState.ANSWERED
        call.answer_time = time.time()
        
        # TODO: 发送 200 OK with SDP
    
    def end_call(self, call_id: str):
        """结束通话"""
        call = self.calls.get(call_id)
        if not call:
            return
        
        call.state = CallState.ENDED
        call.end_time = time.time()
        
        # 停止 RTP
        if call.rtp_handler:
            call.rtp_handler.stop()
        
        # 删除通话
        del self.calls[call_id]
    
    def _send_request(self, request: SIPRequest, timeout: float = 5.0) -> Optional[SIPResponse]:
        """发送请求并等待响应"""
        # 清空响应队列
        while not self.response_queue.empty():
            self.response_queue.get()
        
        # 发送请求
        self.sock.sendto(request.to_string().encode(), (self.server_ip, self.port))
        
        # 等待响应
        try:
            response = self.response_queue.get(timeout=timeout)
            return response
        except queue.Empty:
            return None
    
    def _send_response(self, request: SIPRequest, status_code: int,
                      reason_phrase: str, to_tag: Optional[str] = None,
                      body: Optional[str] = None):
        """发送响应"""
        response = SIPMessageBuilder.build_response(
            request, status_code, reason_phrase,
            to_tag=to_tag, body=body
        )
        
        # 获取目标地址
        via = request.get_header('Via')
        if via:
            # 解析 Via 头部获取地址
            # Via: SIP/2.0/UDP 192.168.1.100:5060;branch=...
            import re
            match = re.search(r'(\d+\.\d+\.\d+\.\d+):(\d+)', via)
            if match:
                target_ip = match.group(1)
                target_port = int(match.group(2))
            else:
                target_ip = self.server_ip
                target_port = self.port
        else:
            target_ip = self.server_ip
            target_port = self.port
        
        self.sock.sendto(response.to_string().encode(), (target_ip, target_port))
    
    def _receive_loop(self):
        """接收循环"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                message_text = data.decode('utf-8', errors='ignore')
                
                # 解析消息
                message = SIPMessageParser.parse(message_text)
                if not message:
                    continue
                
                if isinstance(message, SIPResponse):
                    # 响应消息
                    self.response_queue.put(message)
                elif isinstance(message, SIPRequest):
                    # 请求消息
                    self._handle_request(message, addr)
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"接收错误: {e}")
    
    def _handle_request(self, request: SIPRequest, addr: Tuple[str, int]):
        """处理请求"""
        method = request.method
        
        if method == "INVITE":
            self.handle_incoming_call(request)
        elif method == "ACK":
            # ACK 确认
            call_id = request.get_header('Call-ID')
            if call_id in self.calls:
                call = self.calls[call_id]
                if call.state == CallState.ANSWERED:
                    print("✅ 通话已建立")
        elif method == "BYE":
            # 结束通话
            call_id = request.get_header('Call-ID')
            if call_id in self.calls:
                self._send_response(request, 200, "OK")
                self.end_call(call_id)
        elif method == "CANCEL":
            # 取消通话
            self._send_response(request, 200, "OK")
        elif method == "OPTIONS":
            # OPTIONS 请求
            self._send_response(request, 200, "OK")
    
    def _keepalive_loop(self):
        """保活循环"""
        while self.running and self.state == SIPState.REGISTERED:
            # 等待刷新时间
            wait_time = max(self.expires // 2, 20)
            time.sleep(wait_time)
            
            if self.running:
                print("🔄 刷新注册...")
                if not self.register():
                    print("⚠️ 刷新失败")
    
    def _get_local_ip(self) -> str:
        """获取本地 IP"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def _get_next_rtp_port(self) -> int:
        """获取下一个可用的 RTP 端口"""
        port = self.next_rtp_port
        self.next_rtp_port += 2  # RTP 使用偶数端口
        if self.next_rtp_port > self.rtp_port_end:
            self.next_rtp_port = self.rtp_port_start
        return port
    
    def set_incoming_call_handler(self, handler: Callable[[Call, SIPRequest], None]):
        """设置来电处理器"""
        self.on_incoming_call = handler