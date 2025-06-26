"""
SDP 解析器
处理 Session Description Protocol
"""

import time
from typing import Dict, List, Optional, Tuple


class SDPParser:
    """SDP 解析器和生成器"""
    
    @staticmethod
    def parse(sdp_text: str) -> Dict:
        """
        解析 SDP 文本
        
        Args:
            sdp_text: SDP 文本
            
        Returns:
            解析后的 SDP 字典
        """
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
                # 解析 origin: username sess-id sess-version nettype addrtype unicast-address
                parts = value.split()
                if len(parts) >= 6:
                    sdp['origin_parsed'] = {
                        'username': parts[0],
                        'session_id': parts[1],
                        'session_version': parts[2],
                        'network_type': parts[3],
                        'address_type': parts[4],
                        'address': parts[5]
                    }
            elif type_char == 's':
                sdp['session_name'] = value
            elif type_char == 'c':
                # connection: nettype addrtype connection-address
                if current_media:
                    current_media['connection'] = value
                else:
                    sdp['connection'] = value
                    
                # 解析连接信息
                parts = value.split()
                if len(parts) >= 3:
                    conn_info = {
                        'network_type': parts[0],
                        'address_type': parts[1],
                        'address': parts[2]
                    }
                    if current_media:
                        current_media['connection_parsed'] = conn_info
                    else:
                        sdp['connection_parsed'] = conn_info
                        
            elif type_char == 't':
                sdp['time'] = value
            elif type_char == 'm':
                # media: media port proto fmt ...
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
                # 解析常见属性
                if value.startswith('rtpmap:'):
                    # rtpmap:payload_type encoding_name/clock_rate
                    parts = value[7:].split(' ', 1)
                    if len(parts) == 2:
                        payload_type = parts[0]
                        encoding_info = parts[1].split('/')
                        if 'rtpmap' not in current_media:
                            current_media['rtpmap'] = {}
                        current_media['rtpmap'][payload_type] = {
                            'encoding': encoding_info[0],
                            'clock_rate': int(encoding_info[1]) if len(encoding_info) > 1 else 8000
                        }
        
        return sdp
    
    @staticmethod
    def build(local_ip: str, rtp_port: int, session_id: Optional[str] = None, 
              codecs: Optional[List[str]] = None) -> str:
        """
        构建 SDP
        
        Args:
            local_ip: 本地 IP 地址
            rtp_port: RTP 端口
            session_id: 会话 ID
            codecs: 编解码器列表（如 ['0', '8']）
            
        Returns:
            SDP 文本
        """
        if not session_id:
            session_id = str(int(time.time()))
        if not codecs:
            codecs = ['0', '8']  # 默认 PCMU, PCMA
        
        sdp_lines = [
            "v=0",
            f"o=- {session_id} {session_id} IN IP4 {local_ip}",
            "s=VTX AI Phone",
            f"c=IN IP4 {local_ip}",
            "t=0 0",
            f"m=audio {rtp_port} RTP/AVP {' '.join(codecs)}",
        ]
        
        # 添加编解码器映射
        codec_map = {
            '0': 'PCMU/8000',
            '8': 'PCMA/8000',
            '18': 'G729/8000',
            '3': 'GSM/8000',
            '101': 'telephone-event/8000'
        }
        
        for codec in codecs:
            if codec in codec_map:
                sdp_lines.append(f"a=rtpmap:{codec} {codec_map[codec]}")
        
        # 添加 DTMF 支持
        if '101' in codecs:
            sdp_lines.append("a=fmtp:101 0-16")
        
        sdp_lines.append("a=sendrecv")
        
        return '\r\n'.join(sdp_lines)
    
    @staticmethod
    def extract_rtp_info(sdp: Dict) -> Optional[Tuple[str, int, List[str]]]:
        """
        从解析的 SDP 中提取 RTP 信息
        
        Args:
            sdp: 解析后的 SDP 字典
            
        Returns:
            (IP地址, RTP端口, 编解码器列表) 或 None
        """
        if not sdp.get('media'):
            return None
        
        # 查找音频媒体
        for media in sdp['media']:
            if media['type'] == 'audio':
                # 获取连接信息
                conn_info = media.get('connection_parsed') or sdp.get('connection_parsed')
                if conn_info:
                    ip = conn_info['address']
                    port = media['port']
                    codecs = media['formats']
                    return (ip, port, codecs)
        
        return None
    
    @staticmethod
    def validate_sdp(sdp_text: str) -> Tuple[bool, List[str]]:
        """
        验证 SDP 格式
        
        Args:
            sdp_text: SDP 文本
            
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        try:
            sdp = SDPParser.parse(sdp_text)
            
            # 检查必需字段
            if not sdp.get('version'):
                errors.append("缺少版本信息 (v=)")
            elif sdp['version'] != '0':
                errors.append(f"不支持的 SDP 版本: {sdp['version']}")
                
            if not sdp.get('origin'):
                errors.append("缺少源信息 (o=)")
                
            if not sdp.get('session_name'):
                errors.append("缺少会话名称 (s=)")
                
            if not sdp.get('time'):
                errors.append("缺少时间信息 (t=)")
                
            if not sdp.get('media'):
                errors.append("缺少媒体描述 (m=)")
            else:
                # 检查媒体
                for i, media in enumerate(sdp['media']):
                    if media['type'] == 'audio':
                        if not media.get('connection') and not sdp.get('connection'):
                            errors.append(f"媒体 {i} 缺少连接信息 (c=)")
                        if media['port'] == 0:
                            errors.append(f"媒体 {i} 端口为 0（表示禁用）")
                            
        except Exception as e:
            errors.append(f"解析错误: {str(e)}")
        
        return (len(errors) == 0, errors)