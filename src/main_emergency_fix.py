#!/usr/bin/env python3
"""
VTX AI Phone System v2.1 - 紧急修复版主程序
使用系统标准G.711编解码器解决音频编码根本性错误
"""

import sys
import os
import time
import signal
import threading
import asyncio
from typing import Optional

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from src.sip import SIPClient
from src.sdp import SDPParser
from src.rtp import RTPHandler
from src.audio.system_codec import SystemG711Codec, SystemRTPSender


class EmergencyFixedAikerSystem:
    """紧急修复版Aiker系统 - 使用系统标准G.711编解码器"""
    
    def __init__(self):
        # 获取配置
        ext = settings.get_extension('101')
        if not ext:
            raise ValueError("分机 101 未配置")
        
        # 创建 SIP 客户端
        self.sip_client = SIPClient(
            server=settings.vtx.server,
            port=settings.vtx.port,
            domain=settings.vtx.domain,
            username=ext.username,
            password=ext.password
        )
        
        # 系统标准音频组件
        self.system_codec = SystemG711Codec()
        self.current_rtp_handler = None
        self.current_call = None
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = False
        
        print("🚨 紧急修复版Aiker - OneSuite 商业客服机器人")
        print("🔧 使用系统标准G.711编解码器")
        print(f"服务器: {settings.vtx.server}:{settings.vtx.port}")
        print(f"域名: {settings.vtx.domain}")
        print(f"DID: {settings.vtx.did_number}")
        print(f"分机: {ext.username}")
        print(f"核心修复: 系统标准audioop库")
        print("-" * 50)
    
    def _signal_handler(self, signum, frame):
        """信号处理"""
        print(f"\n收到信号 {signum}，准备退出...")
        self.running = False
    
    def start(self):
        """启动系统"""
        # 设置来电处理
        self.sip_client.set_incoming_call_handler(self._handle_incoming_call_emergency_fix)
        
        # 启动 SIP 客户端
        if not self.sip_client.start():
            print("❌ 系统启动失败")
            return False
        
        print("\n✅ 紧急修复版系统启动成功")
        print(f"📞 等待来电: {settings.vtx.did_number}")
        print("🔧 核心修复: 系统标准G.711编解码器")
        print("🎧 预期听到: 清晰的DTMF音调 1-8-7-1")
        print("按 Ctrl+C 退出...\n")
        
        self.running = True
        
        # 主循环
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        
        # 停止系统
        self.stop()
        
        return True
    
    def stop(self):
        """停止系统"""
        print("\n🛑 停止系统...")
        
        # 停止 RTP
        if self.current_rtp_handler:
            self.current_rtp_handler.stop()
        
        # 停止 SIP
        self.sip_client.stop()
        
        print("✅ 系统已停止")
    
    def _handle_incoming_call_emergency_fix(self, call, request):
        """紧急修复版来电处理 - 使用系统标准G.711编解码器"""
        print(f"\n📞 紧急修复版来电处理: {call.call_id}")
        print("🚨 使用系统标准G.711编解码器")
        self.current_call = call
        
        # 提取来电信息
        from_header = request.get_header('From')
        if from_header:
            import re
            match = re.search(r'sip:([^@]+)@', from_header)
            if match:
                caller = match.group(1)
                print(f"   来电号码: {caller}")
        
        # 解析 SDP
        body = request.body
        if body:
            sdp = SDPParser.parse(body)
            rtp_info = SDPParser.extract_rtp_info(sdp)
            
            if rtp_info:
                remote_ip, remote_port, codecs = rtp_info
                print(f"   远程 RTP: {remote_ip}:{remote_port}")
                print(f"   编解码器: {', '.join(codecs)}")
                
                # 分配本地 RTP 端口
                local_rtp_port = self.sip_client._get_next_rtp_port()
                
                # 创建RTP处理器
                rtp_handler = RTPHandler(
                    self.sip_client.local_ip,
                    local_rtp_port
                )
                call.rtp_handler = rtp_handler
                self.current_rtp_handler = rtp_handler
                
                # 构建响应 SDP
                response_sdp = SDPParser.build(
                    self.sip_client.local_ip,
                    local_rtp_port,
                    codecs=codecs
                )
                
                # 接听电话
                time.sleep(2)  # 模拟振铃
                self.sip_client._send_response(
                    request, 200, "OK",
                    to_tag=call.local_tag,
                    body=response_sdp
                )
                
                # 启动RTP
                rtp_handler.start(remote_ip, remote_port)
                
                # 发送系统标准测试音频
                self._send_system_standard_audio()
                
            else:
                print("⚠️ 无法解析 RTP 信息")
                # 发送忙音
                time.sleep(2)
                self.sip_client._send_response(
                    request, 486, "Busy Here",
                    to_tag=call.local_tag
                )
        else:
            print("⚠️ 没有 SDP")
            # 发送忙音
            time.sleep(2)
            self.sip_client._send_response(
                request, 486, "Busy Here",
                to_tag=call.local_tag
            )
    
    def _send_system_standard_audio(self):
        """发送系统标准测试音频"""
        print("🎵 生成系统标准DTMF序列: 1871")
        
        # 生成系统标准测试音频
        test_audio = self.system_codec.generate_test_sequence()
        
        # 验证音频有效性
        validation = self.system_codec.validate_ulaw_data(test_audio)
        if validation['valid']:
            print(f"✅ 音频验证通过: {validation['unique_values']}个不同值")
            print(f"   时长: {validation['duration_seconds']:.1f}秒")
            print(f"   范围: {validation['value_range']}")
            
            # 创建系统RTP发送器
            system_sender = SystemRTPSender(self.current_rtp_handler)
            
            # 发送系统标准音频
            system_sender.send_system_audio(test_audio)
        else:
            print(f"❌ 音频验证失败: {validation['reason']}")
            print("⚠️ 使用备用音频生成方法")
            self._send_fallback_audio()
    
    def _send_fallback_audio(self):
        """发送备用音频（如果系统音频生成失败）"""
        print("🔄 使用备用音频生成方法...")
        
        # 生成简单的440Hz音调
        sample_rate = 8000
        duration = 3.0
        frequency = 440
        
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        pcm_wave = 0.3 * np.sin(2 * np.pi * frequency * t)
        pcm_int16 = (pcm_wave * 32767).astype(np.int16)
        pcm_data = pcm_int16.tobytes()
        
        # 使用系统标准编码
        ulaw_data = self.system_codec.pcm_to_ulaw_system(pcm_data)
        
        if ulaw_data:
            print(f"✅ 备用音频生成: {len(ulaw_data)}字节")
            
            # 分包发送
            packet_size = 160  # 20ms @ 8kHz
            total_packets = len(ulaw_data) // packet_size
            
            print(f"📊 发送计划: {total_packets}个包")
            print("🎧 请听440Hz测试音调")
            
            for i in range(0, len(ulaw_data), packet_size):
                packet = ulaw_data[i:i+packet_size]
                
                # 确保包大小正确
                if len(packet) < packet_size:
                    packet += b'\x7F' * (packet_size - len(packet))
                
                # 发送RTP包
                self.current_rtp_handler.send_audio(packet, payload_type=0)
                
                # 进度显示
                packet_num = (i // packet_size) + 1
                if packet_num % 25 == 0:
                    print(f"📤 发送进度: {packet_num}/{total_packets} ({packet_num*0.02:.1f}s)")
                
                time.sleep(0.02)  # 精确20ms
            
            print("✅ 备用音频发送完成!")
        else:
            print("❌ 备用音频生成失败")


def main():
    """主函数"""
    print("=" * 60)
    print("紧急修复版Aiker - OneSuite 商业客服机器人 v2.1")
    print("🔧 使用系统标准G.711编解码器")
    print("🎯 解决音频编码根本性错误问题")
    print("=" * 60)
    
    # 检查依赖
    try:
        import audioop
        import numpy
        print("✅ 核心依赖正常")
    except ImportError as e:
        print(f"❌ 依赖缺失: {e}")
        return 1
    
    print("-" * 60)
    
    try:
        system = EmergencyFixedAikerSystem()
        system.start()
    except Exception as e:
        print(f"❌ 系统错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 