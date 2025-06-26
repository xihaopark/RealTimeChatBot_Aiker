#!/usr/bin/env python3
"""
北美VoIP音频修复 - PCMU/μ-law专用方案
针对北美标准的G.711 μ-law编码
"""

import struct
import socket
import time
import math
import audioop
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class NorthAmericaVoIPFix:
    """北美VoIP音频修复"""
    
    # 北美标准常量
    SAMPLE_RATE = 8000      # 8kHz（G.711标准）
    PACKET_MS = 20          # 20ms包
    PACKET_SAMPLES = 160    # 20ms @ 8kHz = 160样本
    PAYLOAD_TYPE = 0        # PCMU (G.711 μ-law)
    
    def __init__(self):
        self.sequence = 0
        self.timestamp = 0
        self.ssrc = 0x12345678
        
    def diagnose_current_issue(self):
        """诊断当前音频问题"""
        print("🔍 北美VoIP音频诊断 (PCMU/μ-law)")
        print("=" * 60)
        
        # 1. 验证μ-law编码
        print("\n1️⃣ 验证μ-law编码...")
        self.verify_ulaw_encoding()
        
        # 2. 生成标准测试音频
        print("\n2️⃣ 生成北美标准测试音频...")
        test_audio = self.generate_standard_test_audio()
        
        # 3. 验证RTP包格式
        print("\n3️⃣ 验证RTP包格式...")
        self.verify_rtp_format(test_audio)
        
        # 4. 提供修复方案
        print("\n4️⃣ 修复方案...")
        self.provide_fix_solution()
        
    def verify_ulaw_encoding(self):
        """验证μ-law编码是否符合北美标准"""
        # 测试关键音频值
        test_values = [
            (0, "静音"),
            (1000, "低音量"),
            (8000, "中音量"), 
            (16383, "高音量"),
            (-16383, "负高音量")
        ]
        
        print("  测试μ-law编码:")
        for pcm_value, desc in test_values:
            # 使用标准audioop编码
            pcm_bytes = struct.pack('h', pcm_value)
            ulaw_byte = audioop.lin2ulaw(pcm_bytes, 2)[0]
            
            # 解码验证
            decoded_bytes = audioop.ulaw2lin(bytes([ulaw_byte]), 2)
            decoded_value = struct.unpack('h', decoded_bytes)[0]
            
            print(f"    {desc:8} PCM:{pcm_value:6} -> μ-law:0x{ulaw_byte:02X} "
                  f"-> PCM:{decoded_value:6} (误差:{abs(pcm_value-decoded_value)})")
        
        # 验证静音值
        silence_ulaw = audioop.lin2ulaw(struct.pack('h', 0), 2)[0]
        print(f"\n  ✅ 北美μ-law静音值: 0x{silence_ulaw:02X} (应该是0xFF)")
        
    def generate_standard_test_audio(self):
        """生成符合北美标准的测试音频"""
        audio_patterns = {}
        
        # 1. 标准DTMF音调 - 使用北美DTMF频率
        print("\n  生成DTMF测试序列'1871':")
        dtmf_sequence = self.generate_dtmf_sequence('1871')
        audio_patterns['dtmf_1871'] = dtmf_sequence
        print(f"    DTMF序列: {len(dtmf_sequence)}字节")
        
        # 2. 标准拨号音（350Hz + 440Hz）
        print("\n  生成北美拨号音:")
        dial_tone = self.generate_dial_tone(duration=1.0)
        audio_patterns['dial_tone'] = dial_tone
        print(f"    拨号音: {len(dial_tone)}字节")
        
        # 3. 单频测试音（1kHz）
        print("\n  生成1kHz测试音:")
        test_tone = self.generate_test_tone(1000, duration=0.5)
        audio_patterns['test_tone'] = test_tone
        print(f"    测试音: {len(test_tone)}字节")
        
        # 验证编码
        for name, audio in audio_patterns.items():
            unique_values = len(set(audio))
            is_silence = all(b == 0xFF for b in audio)
            print(f"\n  {name}验证:")
            print(f"    唯一值数: {unique_values}")
            print(f"    是否静音: {is_silence}")
            print(f"    前10字节: {' '.join(f'0x{b:02X}' for b in audio[:10])}")
        
        return audio_patterns
    
    def generate_dtmf_sequence(self, digits):
        """生成北美标准DTMF序列"""
        # 北美DTMF频率（ANSI标准）
        dtmf_freqs = {
            '1': (697, 1209), '2': (697, 1336), '3': (697, 1477),
            '4': (770, 1209), '5': (770, 1336), '6': (770, 1477),
            '7': (852, 1209), '8': (852, 1336), '9': (852, 1477),
            '*': (941, 1209), '0': (941, 1336), '#': (941, 1477),
        }
        
        sequence = []
        
        for digit in digits:
            if digit in dtmf_freqs:
                # 生成DTMF音调（400ms）
                tone = self.generate_dual_tone(
                    dtmf_freqs[digit][0], 
                    dtmf_freqs[digit][1],
                    duration=0.4
                )
                sequence.append(tone)
                
                # 添加间隔（100ms静音）
                silence = bytes([0xFF] * int(0.1 * self.SAMPLE_RATE))
                sequence.append(silence)
        
        return b''.join(sequence)
    
    def generate_dual_tone(self, freq1, freq2, duration):
        """生成双音多频音调"""
        samples = int(duration * self.SAMPLE_RATE)
        pcm_data = []
        
        for i in range(samples):
            t = i / self.SAMPLE_RATE
            # 双音混合，每个音调振幅0.5
            sample = int(16383 * (
                0.5 * math.sin(2 * math.pi * freq1 * t) +
                0.5 * math.sin(2 * math.pi * freq2 * t)
            ))
            # 限制范围
            sample = max(-32768, min(32767, sample))
            pcm_data.append(sample)
        
        # 转换为PCM字节
        pcm_bytes = struct.pack(f'{len(pcm_data)}h', *pcm_data)
        
        # 编码为μ-law
        return audioop.lin2ulaw(pcm_bytes, 2)
    
    def generate_dial_tone(self, duration=1.0):
        """生成北美拨号音（350Hz + 440Hz）"""
        return self.generate_dual_tone(350, 440, duration)
    
    def generate_test_tone(self, frequency, duration=0.5):
        """生成单频测试音"""
        samples = int(duration * self.SAMPLE_RATE)
        pcm_data = []
        
        for i in range(samples):
            t = i / self.SAMPLE_RATE
            sample = int(16383 * 0.8 * math.sin(2 * math.pi * frequency * t))
            sample = max(-32768, min(32767, sample))
            pcm_data.append(sample)
        
        pcm_bytes = struct.pack(f'{len(pcm_data)}h', *pcm_data)
        return audioop.lin2ulaw(pcm_bytes, 2)
    
    def build_rtp_packet(self, payload, marker=False):
        """构建标准RTP包（北美PCMU）"""
        # RTP头部
        byte0 = 0x80  # V=2, P=0, X=0, CC=0
        byte1 = (int(marker) << 7) | self.PAYLOAD_TYPE  # M bit + PT=0 (PCMU)
        
        header = struct.pack('!BBHII',
                           byte0,
                           byte1,
                           self.sequence,
                           self.timestamp,
                           self.ssrc)
        
        self.sequence = (self.sequence + 1) & 0xFFFF
        self.timestamp = (self.timestamp + self.PACKET_SAMPLES) & 0xFFFFFFFF
        
        return header + payload
    
    def verify_rtp_format(self, audio_patterns):
        """验证RTP包格式"""
        print("\n  验证RTP包格式:")
        
        # 使用DTMF音频创建RTP包
        dtmf_audio = audio_patterns.get('dtmf_1871', b'')
        
        # 创建20ms的包
        packet_size = self.PACKET_SAMPLES  # 160字节
        first_packet = dtmf_audio[:packet_size]
        
        # 确保包大小正确
        if len(first_packet) < packet_size:
            first_packet += bytes([0xFF] * (packet_size - len(first_packet)))
        
        # 构建RTP包
        rtp_packet = self.build_rtp_packet(first_packet)
        
        print(f"    RTP包大小: {len(rtp_packet)}字节")
        print(f"    头部(12字节): {' '.join(f'0x{b:02X}' for b in rtp_packet[:12])}")
        print(f"    负载大小: {len(rtp_packet) - 12}字节")
        print(f"    负载前10字节: {' '.join(f'0x{b:02X}' for b in rtp_packet[12:22])}")
        
        # 验证包结构
        header = struct.unpack('!BBHII', rtp_packet[:12])
        version = (header[0] >> 6) & 0x03
        pt = header[1] & 0x7F
        
        print(f"\n    解析结果:")
        print(f"      版本: {version} (应该是2)")
        print(f"      负载类型: {pt} (应该是0/PCMU)")
        print(f"      序列号: {header[2]}")
        print(f"      时间戳: {header[3]}")
        print(f"      SSRC: 0x{header[4]:08X}")
        
        if version == 2 and pt == 0:
            print("\n    ✅ RTP格式正确!")
        else:
            print("\n    ❌ RTP格式有问题!")
    
    def provide_fix_solution(self):
        """提供修复方案"""
        print("\n🔧 推荐修复方案:")
        print("=" * 60)
        
        print("\n✅ 关键确认:")
        print("  1. 使用G.711 μ-law (PCMU) - 北美标准 ✓")
        print("  2. 负载类型 PT=0 ✓")
        print("  3. 采样率 8000Hz ✓")
        print("  4. 20ms包 = 160字节 ✓")
        print("  5. 静音值 = 0xFF ✓")
        
        print("\n🎯 立即行动:")
        print("  1. 使用Python内置audioop进行μ-law编码")
        print("  2. 确保RTP时间戳每包增加160")
        print("  3. 发送标准DTMF测试序列")
        print("  4. 监控RTP流确认包到达")
        
        print("\n📝 测试步骤:")
        print("  1. 运行修复版本: python north_america_voip_fix.py test")
        print("  2. 拨打14088779998")
        print("  3. 应该听到DTMF音调: 1-8-7-1")
        print("  4. 如果仍无声音，运行: python north_america_voip_fix.py capture")
        
    def run_fixed_audio_test(self):
        """运行修复后的音频测试"""
        print("\n🚀 运行北美VoIP音频测试...")
        
        # 生成测试音频
        dtmf = self.generate_dtmf_sequence('1871')
        
        # 保存为WAV文件验证
        self.save_test_audio(dtmf, 'north_america_test.wav')
        
        print("\n✅ 测试音频已生成!")
        print("   文件: north_america_test.wav")
        print("   内容: DTMF序列 1-8-7-1")
        print("   格式: G.711 μ-law, 8kHz")
        
        return dtmf
    
    def save_test_audio(self, ulaw_data, filename):
        """保存测试音频为WAV文件"""
        import wave
        
        # 解码μ-law为PCM
        pcm_data = audioop.ulaw2lin(ulaw_data, 2)
        
        # 保存WAV
        with wave.open(filename, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(8000)
            wav.writeframes(pcm_data)
    
    def capture_rtp_stream(self, port=10000, duration=10):
        """捕获RTP流进行分析"""
        print(f"\n📡 捕获RTP流 (端口:{port}, 时长:{duration}秒)...")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', port))
        sock.settimeout(0.5)
        
        start_time = time.time()
        packet_count = 0
        payload_types = set()
        
        while (time.time() - start_time) < duration:
            try:
                data, addr = sock.recvfrom(4096)
                packet_count += 1
                
                if len(data) >= 12:
                    # 解析RTP头
                    pt = data[1] & 0x7F
                    payload_types.add(pt)
                    
                    if packet_count <= 5:
                        print(f"  包#{packet_count} 来自{addr}: PT={pt}, "
                              f"大小={len(data)}字节")
                
            except socket.timeout:
                continue
        
        sock.close()
        
        print(f"\n📊 捕获结果:")
        print(f"  总包数: {packet_count}")
        print(f"  负载类型: {payload_types}")
        
        if 0 in payload_types:
            print("  ✅ 检测到PCMU (PT=0)!")
        else:
            print("  ⚠️ 未检测到PCMU包")


def main():
    """主函数"""
    import sys
    
    fixer = NorthAmericaVoIPFix()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'test':
            fixer.run_fixed_audio_test()
        elif sys.argv[1] == 'capture':
            port = int(sys.argv[2]) if len(sys.argv) > 2 else 10000
            fixer.capture_rtp_stream(port)
        elif sys.argv[1] == 'diagnose':
            fixer.diagnose_current_issue()
    else:
        # 默认运行诊断
        fixer.diagnose_current_issue()


if __name__ == "__main__":
    main() 