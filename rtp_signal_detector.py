#!/usr/bin/env python3
"""
RTP信号检测器 - 纯粹的网络层诊断
只检测UDP包，不解码音频，确认网络连通性
"""

import socket
import time
import struct
import binascii
import threading
import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class RTPSignalDetector:
    """RTP信号检测器"""
    
    def __init__(self):
        self.detected_packets = []
        self.running = False
        self.local_ip = self._get_local_ip()
        
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
    
    def quick_scan(self, duration=10):
        """快速扫描 - 检测所有可能的RTP端口"""
        print(f"🔍 RTP信号快速扫描")
        print(f"=" * 60)
        print(f"本地IP: {self.local_ip}")
        print(f"扫描时长: {duration}秒")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\n监听端口范围: 10000-20000")
        print(f"等待RTP包...\n")
        
        # 创建多个socket监听不同端口范围
        sockets = []
        port_ranges = [
            (10000, 10100),   # 常用RTP端口
            (15000, 15100),   # 备用范围
            (20000, 20100),   # 扩展范围
        ]
        
        for start_port, end_port in port_ranges:
            for port in range(start_port, end_port, 2):  # 跳过奇数端口
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.settimeout(0.1)
                    sock.bind(('0.0.0.0', port))
                    sockets.append((sock, port))
                except:
                    continue
        
        print(f"✅ 成功绑定 {len(sockets)} 个端口")
        
        # 开始监听
        start_time = time.time()
        packet_count = 0
        
        while (time.time() - start_time) < duration:
            for sock, port in sockets:
                try:
                    data, addr = sock.recvfrom(4096)
                    packet_count += 1
                    
                    # 分析包
                    self._analyze_packet(data, addr, port, packet_count)
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    continue
        
        # 清理
        for sock, port in sockets:
            sock.close()
        
        # 总结
        self._print_summary(packet_count, duration)
    
    def scan_specific_port(self, port, duration=10):
        """扫描特定端口"""
        print(f"🔍 扫描特定端口: {port}")
        print(f"=" * 60)
        print(f"本地IP: {self.local_ip}")
        print(f"监听端口: {port}")
        print(f"扫描时长: {duration}秒")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\n等待RTP包...\n")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.1)
        sock.bind(('0.0.0.0', port))
        
        start_time = time.time()
        packet_count = 0
        
        while (time.time() - start_time) < duration:
            try:
                data, addr = sock.recvfrom(4096)
                packet_count += 1
                
                # 详细分析包
                self._analyze_packet_detailed(data, addr, port, packet_count)
                
            except socket.timeout:
                continue
            except Exception as e:
                print(f"接收错误: {e}")
        
        sock.close()
        self._print_summary(packet_count, duration)
    
    def full_scan(self, duration=30):
        """完整扫描 - 更全面的检测"""
        print(f"🔍 RTP信号完整扫描")
        print(f"=" * 60)
        print(f"本地IP: {self.local_ip}")
        print(f"扫描时长: {duration}秒")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\n监听所有UDP端口...\n")
        
        # 监听所有可能的端口
        sockets = []
        for port in range(10000, 20000, 2):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(0.1)
                sock.bind(('0.0.0.0', port))
                sockets.append((sock, port))
            except:
                continue
        
        print(f"✅ 成功绑定 {len(sockets)} 个端口")
        
        # 多线程监听
        self.running = True
        threads = []
        
        for sock, port in sockets:
            thread = threading.Thread(target=self._listen_port, args=(sock, port))
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        # 等待
        time.sleep(duration)
        self.running = False
        
        # 清理
        for sock, port in sockets:
            sock.close()
        
        # 总结
        self._print_summary(len(self.detected_packets), duration)
    
    def _listen_port(self, sock, port):
        """监听单个端口（线程函数）"""
        while self.running:
            try:
                data, addr = sock.recvfrom(4096)
                self.detected_packets.append((data, addr, port))
                
                # 分析包
                self._analyze_packet(data, addr, port, len(self.detected_packets))
                
            except socket.timeout:
                continue
            except:
                continue
    
    def _analyze_packet(self, data, addr, port, packet_num):
        """分析RTP包"""
        print(f"📦 包 #{packet_num} 来自 {addr} -> 端口 {port}")
        print(f"   大小: {len(data)} 字节")
        
        # 检查是否是RTP包
        if len(data) >= 12:
            # 解析RTP头
            try:
                header = struct.unpack('!BBHII', data[:12])
                version = (header[0] >> 6) & 0x03
                pt = header[1] & 0x7F
                seq = header[2]
                timestamp = header[3]
                ssrc = header[4]
                
                print(f"   RTP头: V={version}, PT={pt}, Seq={seq}, TS={timestamp}")
                print(f"   SSRC: 0x{ssrc:08X}")
                
                if version == 2:
                    print(f"   ✅ 有效的RTP包")
                    if pt == 0:
                        print(f"   🎵 PCMU (G.711 μ-law)")
                    elif pt == 8:
                        print(f"   🎵 PCMA (G.711 A-law)")
                    else:
                        print(f"   ⚠️ 未知负载类型: {pt}")
                else:
                    print(f"   ❌ 非RTP包 (版本={version})")
                    
            except Exception as e:
                print(f"   ❌ RTP头解析失败: {e}")
        else:
            print(f"   ❌ 包太小，不是RTP")
        
        # 显示前16字节
        hex_data = binascii.hexlify(data[:16]).decode()
        print(f"   前16字节: {hex_data}")
        print("-" * 40)
    
    def _analyze_packet_detailed(self, data, addr, port, packet_num):
        """详细分析包"""
        print(f"📦 包 #{packet_num} 来自 {addr} -> 端口 {port}")
        print(f"   大小: {len(data)} 字节")
        print(f"   时间: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        
        # 显示完整十六进制
        hex_data = binascii.hexlify(data).decode()
        print(f"   完整数据: {hex_data}")
        
        # 分析RTP头
        if len(data) >= 12:
            try:
                header = struct.unpack('!BBHII', data[:12])
                byte0, byte1 = header[0], header[1]
                
                print(f"\n   RTP头分析:")
                print(f"   字节0: 0x{byte0:02X} (V={(byte0>>6)&3}, P={(byte0>>5)&1}, X={(byte0>>4)&1}, CC={byte0&0xF})")
                print(f"   字节1: 0x{byte1:02X} (M={(byte1>>7)&1}, PT={byte1&0x7F})")
                print(f"   序列号: {header[2]}")
                print(f"   时间戳: {header[3]}")
                print(f"   SSRC: 0x{header[4]:08X}")
                
                # 负载分析
                payload = data[12:]
                print(f"\n   负载分析:")
                print(f"   负载大小: {len(payload)} 字节")
                print(f"   负载类型: {self._get_payload_name(header[1] & 0x7F)}")
                
                # 如果是音频负载，分析模式
                if len(payload) > 0:
                    unique_bytes = len(set(payload))
                    print(f"   唯一字节数: {unique_bytes}")
                    
                    if unique_bytes == 1:
                        print(f"   🎵 可能是静音 (所有字节相同)")
                    elif unique_bytes < 10:
                        print(f"   🎵 可能是简单音调")
                    else:
                        print(f"   🎵 可能是语音或复杂音频")
                
            except Exception as e:
                print(f"   ❌ 解析错误: {e}")
        
        print("=" * 60)
    
    def _get_payload_name(self, pt):
        """获取负载类型名称"""
        pt_names = {
            0: "PCMU (G.711 μ-law)",
            8: "PCMA (G.711 A-law)",
            3: "GSM",
            4: "G723",
            9: "G722",
            18: "G729",
            96: "动态",
            101: "telephone-event (DTMF)",
        }
        return pt_names.get(pt, f"未知({pt})")
    
    def _print_summary(self, packet_count, duration):
        """打印总结"""
        print(f"\n" + "=" * 60)
        print(f"📊 扫描总结")
        print(f"=" * 60)
        print(f"扫描时长: {duration}秒")
        print(f"检测到包数: {packet_count}")
        print(f"平均速率: {packet_count/duration:.1f} 包/秒")
        
        if packet_count == 0:
            print(f"\n❌ 未检测到任何RTP包")
            print(f"可能原因:")
            print(f"  1. 防火墙阻止UDP流量")
            print(f"  2. NAT配置问题")
            print(f"  3. 对方未发送RTP包")
            print(f"  4. 端口范围不正确")
        else:
            print(f"\n✅ 检测到RTP流量")
            print(f"网络层正常，可以继续诊断音频编解码")
        
        print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    """主函数"""
    detector = RTPSignalDetector()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'quick':
            detector.quick_scan(10)
        elif sys.argv[1] == 'scan':
            detector.full_scan(30)
        elif sys.argv[1] == 'port':
            port = int(sys.argv[2]) if len(sys.argv) > 2 else 10000
            detector.scan_specific_port(port, 10)
        else:
            print("用法:")
            print("  python rtp_signal_detector.py quick   # 快速扫描")
            print("  python rtp_signal_detector.py scan    # 完整扫描")
            print("  python rtp_signal_detector.py port 10000  # 扫描特定端口")
    else:
        # 默认快速扫描
        detector.quick_scan(10)


if __name__ == "__main__":
    main() 