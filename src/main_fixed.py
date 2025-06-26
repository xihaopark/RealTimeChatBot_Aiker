#!/usr/bin/env python3
"""
VTX AI Phone System v2.0 - 核心音频修复版主程序
专注解决：1. 生成可用的G.711μ-law音频流  2. 实时人声检测显示
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
from src.audio.fixed_codec import FixedG711Codec, RealTimeVAD
from src.rtp.fixed_handler import FixedRTPHandler
from src.utils.api_manager import api_manager


class FixedAikerPhoneSystem:
    """修复版Aiker电话系统 - 专注核心音频功能"""
    
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
        
        # 核心音频组件
        self.codec = FixedG711Codec()
        self.vad = RealTimeVAD(threshold=0.01)
        self.current_rtp_handler = None
        self.current_call = None
        
        # 设置VAD回调
        self.vad.on_speech_start = lambda: print("🎤 >>> 检测到对方开始说话")
        self.vad.on_speech_end = lambda: print("🔇 >>> 对方停止说话")
        self.vad.on_energy_update = self._display_energy_meter
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = False
        
        print("🎯 修复版Aiker - OneSuite 商业客服机器人")
        print(f"服务器: {settings.vtx.server}:{settings.vtx.port}")
        print(f"域名: {settings.vtx.domain}")
        print(f"DID: {settings.vtx.did_number}")
        print(f"分机: {ext.username}")
        print(f"核心功能: 修复版G.711 + 实时VAD")
        print("-" * 50)
    
    def _signal_handler(self, signum, frame):
        """信号处理"""
        print(f"\n收到信号 {signum}，准备退出...")
        self.running = False
    
    def start(self):
        """启动系统"""
        # 设置来电处理
        self.sip_client.set_incoming_call_handler(self._handle_incoming_call)
        
        # 启动 SIP 客户端
        if not self.sip_client.start():
            print("❌ 系统启动失败")
            return False
        
        print("\n✅ 修复版系统启动成功")
        print(f"📞 等待来电: {settings.vtx.did_number}")
        print("🔧 核心功能: 修复版G.711 + 实时VAD")
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
    
    def _handle_incoming_call(self, call, request):
        """处理来电 - 使用修复版音频处理"""
        print(f"\n📞 来电处理（核心音频修复版）: {call.call_id}")
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
                
                # 创建修复版RTP处理器
                rtp_handler = FixedRTPHandler(
                    self.sip_client.local_ip,
                    local_rtp_port
                )
                call.rtp_handler = rtp_handler
                self.current_rtp_handler = rtp_handler
                
                # 设置 RTP 音频接收回调（包含VAD）
                rtp_handler.set_audio_callback(self._on_rtp_audio_with_vad)
                
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
                
                # 启动修复版RTP
                rtp_handler.start(remote_ip, remote_port)
                
                # 发送修复版测试音频
                self._send_fixed_test_audio()
                
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
    
    def _on_rtp_audio_with_vad(self, audio_data: bytes):
        """带VAD检测的音频接收回调"""
        # VAD检测
        is_speaking = self.vad.process_audio_chunk(audio_data)
        
        # 可以在这里添加其他音频处理逻辑
        # 比如传递给STT引擎等
    
    def _display_energy_meter(self, energy: float):
        """显示能量表"""
        # 每10次更新显示一次，避免刷屏
        if hasattr(self, '_energy_update_count'):
            self._energy_update_count += 1
        else:
            self._energy_update_count = 0
        
        if self._energy_update_count % 10 == 0:
            meter_length = 20
            level = min(int(energy * meter_length * 10), meter_length)  # 放大10倍便于观察
            meter = '█' * level + '░' * (meter_length - level)
            print(f"🎤 对方音频: [{meter}] {energy:.4f}")
    
    def _send_fixed_test_audio(self):
        """发送修复版测试音频"""
        print("🎵 生成并发送修复版测试音频...")
        
        # 生成标准测试音调
        test_audio = self.codec.generate_test_tone_ulaw(
            frequency=800,    # 800Hz更容易听到
            duration=5.0,     # 5秒足够长
            amplitude=0.5     # 适中音量
        )
        
        print(f"📊 生成音频: {len(test_audio)}字节 ({len(test_audio)/8000:.1f}秒)")
        
        # 使用修复版RTP发送
        if self.current_rtp_handler:
            self.current_rtp_handler.send_test_audio_fixed(test_audio)
        else:
            print("❌ RTP处理器不可用")


def main():
    """主函数"""
    print("=" * 60)
    print("修复版Aiker - OneSuite 商业客服机器人 v2.0")
    print("专注解决：1. 生成可用的G.711μ-law音频流")
    print("          2. 实时人声检测显示")
    print("=" * 60)
    
    # 检查依赖
    try:
        import numpy
        print("✅ 核心依赖正常")
    except ImportError as e:
        print(f"❌ 依赖缺失: {e}")
        return 1
    
    print("-" * 60)
    
    try:
        system = FixedAikerPhoneSystem()
        system.start()
    except Exception as e:
        print(f"❌ 系统错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 