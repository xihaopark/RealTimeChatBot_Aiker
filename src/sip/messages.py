"""
SIP 消息构建和解析
"""

import re
import uuid
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class SIPMessage:
    """SIP 消息基类"""
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""
    
    def get_header(self, name: str) -> Optional[str]:
        """获取头部（不区分大小写）"""
        for key, value in self.headers.items():
            if key.lower() == name.lower():
                return value
        return None
    
    def set_header(self, name: str, value: str):
        """设置头部"""
        self.headers[name] = value
    
    def to_string(self) -> str:
        """转换为字符串"""
        raise NotImplementedError


@dataclass
class SIPRequest(SIPMessage):
    """SIP 请求"""
    method: str = ""
    uri: str = ""
    version: str = "SIP/2.0"
    
    def to_string(self) -> str:
        """转换为字符串"""
        lines = [f"{self.method} {self.uri} {self.version}"]
        
        # 添加头部
        for name, value in self.headers.items():
            lines.append(f"{name}: {value}")
        
        # 添加 Content-Length
        content_length = len(self.body) if self.body else 0
        if 'Content-Length' not in self.headers:
            lines.append(f"Content-Length: {content_length}")
        
        # 空行
        lines.append("")
        
        # 添加消息体
        if self.body:
            lines.append(self.body)
        else:
            lines.append("")
        
        return "\r\n".join(lines)


@dataclass
class SIPResponse(SIPMessage):
    """SIP 响应"""
    version: str = "SIP/2.0"
    status_code: int = 200
    reason_phrase: str = "OK"
    
    def to_string(self) -> str:
        """转换为字符串"""
        lines = [f"{self.version} {self.status_code} {self.reason_phrase}"]
        
        # 添加头部
        for name, value in self.headers.items():
            lines.append(f"{name}: {value}")
        
        # 添加 Content-Length
        content_length = len(self.body) if self.body else 0
        if 'Content-Length' not in self.headers:
            lines.append(f"Content-Length: {content_length}")
        
        # 空行
        lines.append("")
        
        # 添加消息体
        if self.body:
            lines.append(self.body)
        else:
            lines.append("")
        
        return "\r\n".join(lines)


class SIPMessageParser:
    """SIP 消息解析器"""
    
    @staticmethod
    def parse(message_text: str) -> Optional[SIPMessage]:
        """
        解析 SIP 消息
        
        Args:
            message_text: 消息文本
            
        Returns:
            SIPRequest 或 SIPResponse 实例
        """
        if not message_text:
            return None
        
        lines = message_text.split('\n')
        if not lines:
            return None
        
        # 解析第一行
        first_line = lines[0].strip()
        
        # 判断是请求还是响应
        if first_line.startswith("SIP/"):
            # 响应: SIP/2.0 200 OK
            return SIPMessageParser._parse_response(lines)
        else:
            # 请求: INVITE sip:user@domain SIP/2.0
            return SIPMessageParser._parse_request(lines)
    
    @staticmethod
    def _parse_request(lines: List[str]) -> Optional[SIPRequest]:
        """解析 SIP 请求"""
        first_line = lines[0].strip()
        parts = first_line.split(' ', 2)
        
        if len(parts) != 3:
            return None
        
        request = SIPRequest(
            method=parts[0],
            uri=parts[1],
            version=parts[2]
        )
        
        # 解析头部和消息体
        SIPMessageParser._parse_headers_and_body(request, lines[1:])
        
        return request
    
    @staticmethod
    def _parse_response(lines: List[str]) -> Optional[SIPResponse]:
        """解析 SIP 响应"""
        first_line = lines[0].strip()
        
        # SIP/2.0 200 OK
        match = re.match(r'(SIP/\d\.\d)\s+(\d+)\s*(.*)', first_line)
        if not match:
            return None
        
        response = SIPResponse(
            version=match.group(1),
            status_code=int(match.group(2)),
            reason_phrase=match.group(3) or ""
        )
        
        # 解析头部和消息体
        SIPMessageParser._parse_headers_and_body(response, lines[1:])
        
        return response
    
    @staticmethod
    def _parse_headers_and_body(message: SIPMessage, lines: List[str]):
        """解析头部和消息体"""
        # 查找空行（分隔头部和消息体）
        body_start = -1
        
        for i, line in enumerate(lines):
            line = line.rstrip('\r')
            
            if not line:  # 空行
                body_start = i + 1
                break
            
            # 解析头部
            if ':' in line:
                name, value = line.split(':', 1)
                message.headers[name.strip()] = value.strip()
        
        # 解析消息体
        if body_start > 0 and body_start < len(lines):
            body_lines = lines[body_start:]
            message.body = '\n'.join(line.rstrip('\r') for line in body_lines)


class SIPMessageBuilder:
    """SIP 消息构建器"""
    
    @staticmethod
    def build_register(username: str, domain: str, server: str,
                      local_ip: str, local_port: int,
                      expires: int = 3600, call_id: Optional[str] = None,
                      from_tag: Optional[str] = None, cseq: int = 1,
                      auth_header: Optional[str] = None) -> SIPRequest:
        """
        构建 REGISTER 请求
        
        Args:
            username: 用户名
            domain: SIP 域
            server: 服务器地址
            local_ip: 本地 IP
            local_port: 本地端口
            expires: 过期时间
            call_id: Call-ID
            from_tag: From 标签
            cseq: CSeq 号
            auth_header: 认证头
            
        Returns:
            SIPRequest 实例
        """
        if not call_id:
            call_id = f"{uuid.uuid4()}@{local_ip}"
        if not from_tag:
            from_tag = uuid.uuid4().hex[:8]
        
        request = SIPRequest(
            method="REGISTER",
            uri=f"sip:{domain}",
            version="SIP/2.0"
        )
        
        # 设置头部
        branch = f"z9hG4bK{uuid.uuid4().hex}"
        
        request.headers = {
            "Via": f"SIP/2.0/UDP {local_ip}:{local_port};branch={branch};rport",
            "From": f"<sip:{username}@{domain}>;tag={from_tag}",
            "To": f"<sip:{username}@{domain}>",
            "Call-ID": call_id,
            "CSeq": f"{cseq} REGISTER",
            "Contact": f"<sip:{username}@{local_ip}:{local_port}>",
            "Max-Forwards": "70",
            "User-Agent": "VTX-AI-System/1.0",
            "Expires": str(expires),
            "Allow": "INVITE, ACK, CANCEL, BYE, OPTIONS"
        }
        
        if auth_header:
            request.headers["Proxy-Authorization"] = auth_header
        
        return request
    
    @staticmethod
    def build_response(request: SIPRequest, status_code: int,
                      reason_phrase: str, to_tag: Optional[str] = None,
                      body: Optional[str] = None,
                      extra_headers: Optional[Dict[str, str]] = None) -> SIPResponse:
        """
        构建 SIP 响应
        
        Args:
            request: 原始请求
            status_code: 状态码
            reason_phrase: 原因短语
            to_tag: To 标签
            body: 消息体
            extra_headers: 额外头部
            
        Returns:
            SIPResponse 实例
        """
        response = SIPResponse(
            status_code=status_code,
            reason_phrase=reason_phrase
        )
        
        # 复制必要的头部
        for header in ['Via', 'From', 'To', 'Call-ID', 'CSeq']:
            value = request.get_header(header)
            if value:
                response.headers[header] = value
        
        # 添加 To 标签
        if to_tag and 'To' in response.headers:
            to_header = response.headers['To']
            if 'tag=' not in to_header:
                response.headers['To'] = f"{to_header};tag={to_tag}"
        
        # 添加额外头部
        if extra_headers:
            response.headers.update(extra_headers)
        
        # 设置消息体
        if body:
            response.body = body
            if 'Content-Type' not in response.headers:
                response.headers['Content-Type'] = 'application/sdp'
        
        return response
    
    @staticmethod
    def build_invite_response(request: SIPRequest, status_code: int,
                            local_ip: str, local_port: int,
                            to_tag: Optional[str] = None,
                            sdp: Optional[str] = None) -> SIPResponse:
        """构建 INVITE 响应"""
        extra_headers = {}
        
        # 添加 Contact（200 OK 需要）
        if status_code == 200:
            username = SIPMessageBuilder._extract_username(request.get_header('To'))
            if username:
                extra_headers['Contact'] = f"<sip:{username}@{local_ip}:{local_port}>"
        
        # 获取状态短语
        reason_phrases = {
            100: "Trying",
            180: "Ringing",
            200: "OK",
            486: "Busy Here",
            487: "Request Terminated",
            603: "Decline"
        }
        reason_phrase = reason_phrases.get(status_code, "Unknown")
        
        return SIPMessageBuilder.build_response(
            request, status_code, reason_phrase,
            to_tag=to_tag,
            body=sdp,
            extra_headers=extra_headers
        )
    
    @staticmethod
    def _extract_username(uri_header: Optional[str]) -> Optional[str]:
        """从 URI 头部提取用户名"""
        if not uri_header:
            return None
        
        match = re.search(r'sip:([^@]+)@', uri_header)
        if match:
            return match.group(1)
        
        return None