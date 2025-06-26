"""
SIP 认证模块
实现 Digest 认证
"""

import hashlib
import re
from typing import Dict, Optional


class DigestAuth:
    """Digest 认证处理"""
    
    @staticmethod
    def parse_auth_header(auth_header: str) -> Dict[str, str]:
        """
        解析认证头
        
        Args:
            auth_header: 认证头字符串
            
        Returns:
            参数字典
        """
        params = {}
        
        # 匹配 key="value" 或 key=value
        pattern = r'(\w+)=(?:"([^"]+)"|([^,\s]+))'
        matches = re.findall(pattern, auth_header)
        
        for key, quoted_value, unquoted_value in matches:
            value = quoted_value if quoted_value else unquoted_value
            params[key] = value
            
        return params
    
    @staticmethod
    def calculate_response(username: str, password: str, realm: str,
                          nonce: str, uri: str, method: str = "REGISTER",
                          algorithm: str = "MD5", qop: Optional[str] = None,
                          nc: Optional[str] = None, cnonce: Optional[str] = None) -> str:
        """
        计算 Digest 认证响应
        
        Args:
            username: 用户名
            password: 密码
            realm: 认证域
            nonce: 服务器随机数
            uri: 请求 URI
            method: 请求方法
            algorithm: 算法（默认 MD5）
            qop: 质量保护
            nc: nonce 计数
            cnonce: 客户端随机数
            
        Returns:
            响应哈希值
        """
        # 计算 HA1
        if algorithm.upper() == "MD5":
            ha1_str = f"{username}:{realm}:{password}"
            ha1 = hashlib.md5(ha1_str.encode()).hexdigest()
        elif algorithm.upper() == "MD5-SESS":
            ha1_base = hashlib.md5(f"{username}:{realm}:{password}".encode()).hexdigest()
            ha1_str = f"{ha1_base}:{nonce}:{cnonce}"
            ha1 = hashlib.md5(ha1_str.encode()).hexdigest()
        else:
            raise ValueError(f"不支持的算法: {algorithm}")
        
        # 计算 HA2
        ha2_str = f"{method}:{uri}"
        ha2 = hashlib.md5(ha2_str.encode()).hexdigest()
        
        # 计算响应
        if qop and qop.lower() in ['auth', 'auth-int']:
            if not nc or not cnonce:
                raise ValueError("使用 qop 时需要 nc 和 cnonce")
            response_str = f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}"
        else:
            response_str = f"{ha1}:{nonce}:{ha2}"
        
        response = hashlib.md5(response_str.encode()).hexdigest()
        
        return response
    
    @staticmethod
    def build_auth_header(username: str, password: str, realm: str,
                         nonce: str, uri: str, method: str = "REGISTER",
                         algorithm: str = "MD5", opaque: Optional[str] = None,
                         qop: Optional[str] = None, nc: Optional[str] = None,
                         cnonce: Optional[str] = None) -> str:
        """
        构建认证头
        
        Args:
            username: 用户名
            password: 密码
            realm: 认证域
            nonce: 服务器随机数
            uri: 请求 URI
            method: 请求方法
            algorithm: 算法
            opaque: 不透明值
            qop: 质量保护
            nc: nonce 计数
            cnonce: 客户端随机数
            
        Returns:
            完整的认证头字符串
        """
        # 计算响应
        response = DigestAuth.calculate_response(
            username, password, realm, nonce, uri, method,
            algorithm, qop, nc, cnonce
        )
        
        # 构建认证头
        auth_parts = [
            f'Digest username="{username}"',
            f'realm="{realm}"',
            f'nonce="{nonce}"',
            f'uri="{uri}"',
            f'response="{response}"',
            f'algorithm={algorithm}'
        ]
        
        if opaque:
            auth_parts.append(f'opaque="{opaque}"')
        
        if qop:
            auth_parts.append(f'qop={qop}')
            if nc:
                auth_parts.append(f'nc={nc}')
            if cnonce:
                auth_parts.append(f'cnonce="{cnonce}"')
        
        return ', '.join(auth_parts)
    
    @staticmethod
    def extract_challenge(response_text: str) -> Optional[Dict[str, str]]:
        """
        从 401/407 响应中提取认证挑战
        
        Args:
            response_text: 响应文本
            
        Returns:
            认证参数字典或 None
        """
        # 查找认证头
        auth_match = re.search(
            r'(WWW-Authenticate|Proxy-Authenticate):\s*Digest\s+(.+)',
            response_text,
            re.IGNORECASE | re.MULTILINE
        )
        
        if auth_match:
            auth_type = auth_match.group(1)
            auth_params = auth_match.group(2)
            
            params = DigestAuth.parse_auth_header(auth_params)
            params['auth_type'] = auth_type
            
            return params
        
        return None