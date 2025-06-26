#!/usr/bin/env python3
"""
最小化SIP/RTP测试 - 极简实现
只关注核心功能：接听电话并检测RTP流
"""

import socket
import time
import struct
import re
import uuid
import threading
import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config.settings import settings
except ImportError:
    print("⚠️ 无法导入配置，使用默认值")
    # 默认配置
    class DefaultSettings:
        class vtx:
            server = "sip.vtxvoip.com"
            port = 5060
            domain = "vtxvoip.com"
            did_number = "14088779998"
        
        def get_extension(self, ext_id):
            class Extension:
                username = "101"
                password = "password"
            return Extension()
    
    settings = DefaultSettings()


class MinimalSIPRTPTest:
    """最小化SIP/RTP测试"""
    
    def __init__(self):
        # 配置
        self.server = settings.vtx.server
        self.port = settings.vtx.port
        self.domain = settings.vtx.domain
        
        ext = settings.get_extension('101')
        self.username = ext.username
        self.password = ext.password
        
        # 网络
        self.local_ip = self._get_local_ip()
        self.sip_sock = None
        self.local_sip_port = None
        
        # SIP参数
        self.call_id = f"{uuid.uuid4()}@{self.local_ip}"
        self.from_tag = uuid.uuid4().hex[:8]
        
        # 状态
        self.running = False
        self.active_calls = {}
        self.rtp_stats = {}
        
        print(f"🔧 最小化SIP/RTP测试")
        print(f"服务器: {self.server}:{self.port}")
        print(f"用户: {self.username}@{self.domain}")
        print(f"本地IP: {self.local_ip}")
        print("-" * 50)
    
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
        """启动测试"""
        try:
            # 创建SIP socket
            self.sip_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sip_sock.settimeout(5)
            self.sip_sock.bind(('0.0.0.0', 0))
            self.local_sip_port = self.sip_sock.getsockname()[1]
            print(f"📍 SIP端口: {self.local_sip_port}")
            
            # 启动接收线程
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_loop)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            print("\n✅ 最小化测试启动成功!")
            print(f"📞 等待来电: {settings.vtx.did_number}")
            print(f"🔍 将检测所有RTP流量")
            return True
            
        except Exception as e:
            print(f"❌ 启动失败: {e}")
            return False
    
    def _receive_loop(self):
        """接收循环"""
        while self.running:
            try:
                data, addr = self.sip_sock.recvfrom(4096)
                message = data.decode('utf-8', errors='ignore')
                
                # 解析消息
                first_line = message.split('\n')[0].strip()
                
                if "INVITE" in first_line:
                    print(f"\n📞 收到INVITE!")
                    self._handle_invite(message, addr)
                
                # 处理其他消息类型...
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"接收错误: {e}")
    
    def _handle_invite(self, message, addr):
        """处理INVITE请求"""
        # 提取信息
        from_match = re.search(r'From:\s*(.+)', message, re.IGNORECASE)
        call_id_match = re.search(r'Call-ID:\s*(.+)', message, re.IGNORECASE)
        
        caller = "Unknown"
        call_id = "unknown"
        
        if from_match:
            from_header = from_match.group(1)
            num_match = re.search(r'sip:([^@]+)@', from_header)
            if num_match:
                caller = num_match.group(1)
        
        if call_id_match:
            call_id = call_id_match.group(1).strip()
        
        print(f"📞 来电: {caller}")
        print(f"   Call-ID: {call_id}")
        
        # 生成tag
        to_tag = uuid.uuid4().hex[:8]
        
        # 发送100 Trying
        self._send_trying(message, addr)
        
        # 发送180 Ringing
        time.sleep(0.1)
        self._send_ringing(message, addr, to_tag)
        
        # 解析SDP
        sdp_start = message.find('\r\n\r\n')
        if sdp_start > 0:
            sdp_text = message[sdp_start+4:]
            sdp = self._parse_simple_sdp(sdp_text)
            
            if sdp:
                remote_ip = sdp.get('ip', addr[0])
                remote_port = sdp.get('port', 10000)
                
                print(f"🎵 远程RTP: {remote_ip}:{remote_port}")
                print(f"   编码: {sdp.get('codecs', ['unknown'])}")
                
                # 分配本地RTP端口
                local_rtp_port = self._get_next_rtp_port()
                
                # 创建RTP监听器
                rtp_listener = RTPListener(local_rtp_port, call_id)
                self.active_calls[call_id] = rtp_listener
                
                # 延迟接听
                time.sleep(2)
                
                # 发送200 OK with SDP
                self._send_ok_with_sdp(message, addr, to_tag, local_rtp_port)
                
                # 启动RTP监听
                rtp_listener.start()
                
                # 发送测试RTP包
                print(f"\n📤 发送测试RTP包到 {remote_ip}:{remote_port}")
                self._send_test_rtp_packets(remote_ip, remote_port, local_rtp_port)
        else:
            # 没有SDP
            time.sleep(2)
            self._send_busy_here(message, addr, to_tag)
    
    def _parse_simple_sdp(self, sdp_text):
        """简单SDP解析"""
        result = {}
        
        for line in sdp_text.split('\n'):
            line = line.strip()
            
            # 连接信息
            if line.startswith('c='):
                parts = line[2:].split()
                if len(parts) >= 3:
                    result['ip'] = parts[2]
            
            # 媒体信息
            elif line.startswith('m=audio'):
                parts = line[8:].split()
                if parts:
                    result['port'] = int(parts[0])
                    if len(parts) > 3:
                        result['codecs'] = parts[3:]
            
            # 负载类型映射
            elif line.startswith('a=rtpmap:'):
                parts = line[9:].split()
                if len(parts) >= 2:
                    pt = parts[0]
                    codec = parts[1].split('/')[0]
                    if 'codec_names' not in result:
                        result['codec_names'] = {}
                    result['codec_names'][pt] = codec
        
        return result
    
    def _send_ok_with_sdp(self, invite_message, addr, to_tag, rtp_port):
        """发送200 OK with SDP"""
        headers = self._extract_headers(invite_message)
        
        # 添加tag到To头部
        to_with_tag = headers['to']
        if 'tag=' not in to_with_tag:
            to_with_tag = f"{to_with_tag};tag={to_tag}"
        
        # 构建SDP（只使用PCMU）
        sdp_lines = [
            "v=0",
            f"o=- {int(time.time())} {int(time.time())} IN IP4 {self.local_ip}",
            "s=Minimal Test",
            f"c=IN IP4 {self.local_ip}",
            "t=0 0",
            f"m=audio {rtp_port} RTP/AVP 0",  # 只提供PCMU (PT=0)
            "a=rtpmap:0 PCMU/8000",
            "a=sendrecv"
        ]
        sdp = "\r\n".join(sdp_lines)
        
        response_lines = [
            "SIP/2.0 200 OK",
            headers['via'],
            headers['from'],
            to_with_tag,
            headers['call_id'],
            headers['cseq'],
            f"Contact: <sip:{self.username}@{self.local_ip}:{self.local_sip_port}>",
            "Content-Type: application/sdp",
            f"Content-Length: {len(sdp)}",
            "",
            sdp
        ]
        
        response = "\r\n".join(response_lines)
        self.sip_sock.sendto(response.encode(), addr)
        print("📤 发送: 200 OK (with PCMU SDP)")
    
    def _send_test_rtp_packets(self, remote_ip, remote_port, local_rtp_port):
        """发送测试RTP包"""
        # 创建发送socket
        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # RTP参数
        ssrc = 0x12345678
        sequence = 0
        timestamp = 0
        
        # 生成测试音频（简单的DTMF音调）
        test_audio = self._generate_test_audio()
        
        print(f"📊 生成测试音频: {len(test_audio)}字节")
        
        # 分包发送（20ms包）
        packet_size = 160  # 20ms @ 8kHz
        packets_sent = 0
        
        for i in range(0, len(test_audio), packet_size):
            packet = test_audio[i:i+packet_size]
            
            # 确保包大小
            if len(packet) < packet_size:
                packet += b'\xFF' * (packet_size - len(packet))
            
            # 构建RTP包
            rtp_packet = self._build_rtp_packet(packet, sequence, timestamp, ssrc)
            
            # 发送
            send_sock.sendto(rtp_packet, (remote_ip, remote_port))
            packets_sent += 1
            
            # 显示进度
            if packets_sent % 50 == 0:
                print(f"📤 已发送{packets_sent}包 ({packets_sent * 0.02:.1f}秒)")
            
            # 更新RTP参数
            sequence = (sequence + 1) & 0xFFFF
            timestamp = (timestamp + 160) & 0xFFFFFFFF
            
            time.sleep(0.02)  # 20ms
        
        send_sock.close()
        print(f"✅ 测试RTP包发送完成: {packets_sent}个包")
    
    def _generate_test_audio(self):
        """生成测试音频"""
        # 简单的DTMF音调（1kHz，0.5秒）
        import math
        
        sample_rate = 8000
        duration = 0.5
        frequency = 1000
        
        samples = int(duration * sample_rate)
        audio_data = []
        
        for i in range(samples):
            t = i / sample_rate
            sample = int(16383 * 0.5 * math.sin(2 * math.pi * frequency * t))
            sample = max(-32768, min(32767, sample))
            audio_data.append(sample)
        
        # 转换为PCM字节
        pcm_data = struct.pack(f'{len(audio_data)}h', *audio_data)
        
        # 编码为μ-law（简单实现）
        ulaw_data = []
        for i in range(0, len(pcm_data), 2):
            pcm_sample = struct.unpack('h', pcm_data[i:i+2])[0]
            ulaw_byte = self._pcm_to_ulaw(pcm_sample)
            ulaw_data.append(ulaw_byte)
        
        return bytes(ulaw_data)
    
    def _pcm_to_ulaw(self, pcm_sample):
        """简单的PCM到μ-law转换"""
        # 简化实现，只用于测试
        if pcm_sample == 0:
            return 0xFF
        
        # 简单的线性映射
        abs_sample = abs(pcm_sample)
        if abs_sample > 16383:
            abs_sample = 16383
        
        # 粗略的μ-law映射
        if abs_sample < 256:
            return 0xFF
        elif abs_sample < 512:
            return 0xFE
        elif abs_sample < 1024:
            return 0xFD
        elif abs_sample < 2048:
            return 0xFC
        elif abs_sample < 4096:
            return 0xFB
        elif abs_sample < 8192:
            return 0xFA
        else:
            return 0xF9
    
    def _build_rtp_packet(self, payload, sequence, timestamp, ssrc):
        """构建RTP包"""
        # RTP头部
        byte0 = 0x80  # V=2, P=0, X=0, CC=0
        byte1 = 0x00  # M=0, PT=0 (PCMU)
        
        # 打包头部
        header = struct.pack('!BBHII',
                           byte0,
                           byte1,
                           sequence,
                           timestamp,
                           ssrc)
        
        return header + payload
    
    def _get_next_rtp_port(self):
        """获取下一个RTP端口"""
        # 简单实现
        return 10000 + (len(self.active_calls) * 2)
    
    def _extract_headers(self, message):
        """提取头部"""
        headers = {}
        patterns = {
            'via': r'^Via:\s*(.+)$',
            'from': r'^From:\s*(.+)$',
            'to': r'^To:\s*(.+)$',
            'call_id': r'^Call-ID:\s*(.+)$',
            'cseq': r'^CSeq:\s*(.+)$'
        }
        
        for line in message.split('\n'):
            line = line.rstrip('\r')
            for key, pattern in patterns.items():
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    headers[key] = line
                    break
        
        return headers
    
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
        self.sip_sock.sendto(response.encode(), addr)
        print("📤 发送: 100 Trying")
    
    def _send_ringing(self, invite_message, addr, to_tag):
        """发送180 Ringing"""
        headers = self._extract_headers(invite_message)
        
        to_with_tag = headers.get('to', '')
        if 'tag=' not in to_with_tag:
            to_with_tag = f"{to_with_tag};tag={to_tag}"
        
        response_lines = [
            "SIP/2.0 180 Ringing",
            headers.get('via', ''),
            headers.get('from', ''),
            to_with_tag,
            headers.get('call_id', ''),
            headers.get('cseq', ''),
            f"Contact: <sip:{self.username}@{self.local_ip}:{self.local_sip_port}>",
            "Content-Length: 0",
            "",
            ""
        ]
        
        response = "\r\n".join(response_lines)
        self.sip_sock.sendto(response.encode(), addr)
        print("📤 发送: 180 Ringing")
    
    def _send_busy_here(self, invite_message, addr, to_tag):
        """发送486 Busy Here"""
        headers = self._extract_headers(invite_message)
        
        to_with_tag = headers.get('to', '')
        if 'tag=' not in to_with_tag:
            to_with_tag = f"{to_with_tag};tag={to_tag}"
        
        response_lines = [
            "SIP/2.0 486 Busy Here",
            headers.get('via', ''),
            headers.get('from', ''),
            to_with_tag,
            headers.get('call_id', ''),
            headers.get('cseq', ''),
            "Content-Length: 0",
            "",
            ""
        ]
        
        response = "\r\n".join(response_lines)
        self.sip_sock.sendto(response.encode(), addr)
        print("📤 发送: 486 Busy Here")
    
    def stop(self):
        """停止测试"""
        print("\n🛑 停止最小化测试...")
        self.running = False
        
        # 停止所有RTP监听器
        for rtp_listener in self.active_calls.values():
            rtp_listener.stop()
        
        if self.sip_sock:
            self.sip_sock.close()
        
        print("✅ 已停止")


class RTPListener:
    """RTP监听器"""
    
    def __init__(self, port, call_id):
        self.port = port
        self.call_id = call_id
        self.sock = None
        self.running = False
        self.packet_count = 0
        self.start_time = None
        
    def start(self):
        """启动监听"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(0.1)
            self.sock.bind(('0.0.0.0', self.port))
            
            self.running = True
            self.start_time = time.time()
            
            # 启动监听线程
            self.listen_thread = threading.Thread(target=self._listen_loop)
            self.listen_thread.daemon = True
            self.listen_thread.start()
            
            print(f"🎵 RTP监听启动: 端口 {self.port}")
            
        except Exception as e:
            print(f"❌ RTP监听启动失败: {e}")
    
    def _listen_loop(self):
        """监听循环"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                self.packet_count += 1
                
                # 分析RTP包
                self._analyze_rtp_packet(data, addr)
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"RTP接收错误: {e}")
    
    def _analyze_rtp_packet(self, data, addr):
        """分析RTP包"""
        if len(data) >= 12:
            try:
                header = struct.unpack('!BBHII', data[:12])
                version = (header[0] >> 6) & 0x03
                pt = header[1] & 0x7F
                seq = header[2]
                timestamp = header[3]
                ssrc = header[4]
                
                if self.packet_count <= 5:  # 只显示前5个包
                    print(f"📥 RTP包 #{self.packet_count} 来自 {addr}")
                    print(f"   大小: {len(data)}字节, PT={pt}, Seq={seq}")
                    print(f"   时间戳: {timestamp}, SSRC=0x{ssrc:08X}")
                    
                    if version == 2:
                        print(f"   ✅ 有效RTP包")
                    else:
                        print(f"   ❌ 非RTP包")
                
                # 统计
                if self.packet_count % 50 == 0:
                    elapsed = time.time() - self.start_time
                    rate = self.packet_count / elapsed
                    print(f"📊 RTP统计: {self.packet_count}包, 速率: {rate:.1f}包/秒")
                
            except Exception as e:
                print(f"RTP解析错误: {e}")
    
    def stop(self):
        """停止监听"""
        self.running = False
        if self.sock:
            self.sock.close()
        
        # 打印统计
        if self.start_time:
            elapsed = time.time() - self.start_time
            print(f"📊 RTP监听结束: {self.packet_count}包, 时长: {elapsed:.1f}秒")


def main():
    """主函数"""
    print("=" * 60)
    print("最小化SIP/RTP测试")
    print("只关注核心功能：接听电话并检测RTP流")
    print("=" * 60)
    
    test = MinimalSIPRTPTest()
    
    if test.start():
        try:
            print("\n按Ctrl+C退出...\n")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n收到退出信号...")
    
    test.stop()


if __name__ == "__main__":
    main() 