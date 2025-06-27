#!/usr/bin/env python3
"""
发送音频包分析工具
分析我们发送的RTP音频包和原始音频文件的差异
"""

import struct
import os
import sys
import math
from collections import defaultdict

def analyze_ulaw_audio(payload_data):
    """分析μ-law音频数据"""
    if not payload_data:
        return {}
    
    samples = []
    energy_sum = 0
    zero_crossings = 0
    prev_sample = 0
    
    for byte in payload_data:
        # 简单的μ-law解码
        if byte == 0:
            sample = 0
        else:
            sign = 1 if (byte & 0x80) == 0 else -1
            exponent = (byte >> 4) & 0x07
            mantissa = byte & 0x0F
            sample = sign * (mantissa << (exponent + 3))
        
        samples.append(sample)
        energy_sum += abs(sample)
        
        # 检测过零点
        if len(samples) > 1 and (prev_sample * sample) < 0:
            zero_crossings += 1
        prev_sample = sample
    
    if not samples:
        return {}
    
    avg_energy = energy_sum / len(samples)
    zero_crossing_rate = zero_crossings / len(samples) if len(samples) > 1 else 0
    
    # 计算频谱特征
    byte_values = list(payload_data)
    byte_freq = defaultdict(int)
    for byte in byte_values:
        byte_freq[byte] += 1
    
    # 计算熵
    entropy = 0
    total_bytes = len(byte_values)
    for count in byte_freq.values():
        if count > 0:
            p = count / total_bytes
            entropy -= p * math.log2(p)
    
    return {
        'sample_count': len(samples),
        'avg_energy': avg_energy,
        'zero_crossing_rate': zero_crossing_rate,
        'entropy': entropy,
        'byte_distribution': dict(byte_freq),
        'min_byte': min(byte_values) if byte_values else 0,
        'max_byte': max(byte_values) if byte_values else 0,
        'avg_byte': sum(byte_values) / len(byte_values) if byte_values else 0
    }

def analyze_sent_rtp_packets():
    """分析我们发送的RTP包"""
    print("📤 分析我们发送的RTP包")
    print("=" * 60)
    
    # 查找我们发送的RTP包（通常包含大量0xFF）
    sent_packets = []
    for filename in os.listdir('rtp_samples'):
        if filename.startswith('sample_payload_0_') and filename.endswith('.bin'):
            filepath = os.path.join('rtp_samples', filename)
            try:
                with open(filepath, 'rb') as f:
                    data = f.read()
                if len(data) >= 12:
                    payload = data[12:]
                    # 检查是否包含大量0xFF（我们发送的特征）
                    ff_count = payload.count(0xFF)
                    if ff_count > len(payload) * 0.3:  # 30%以上是0xFF
                        sent_packets.append((filename, data))
            except:
                continue
    
    print(f"🔍 找到 {len(sent_packets)} 个可能的发送包")
    
    for filename, data in sent_packets[:3]:  # 分析前3个
        print(f"\n📦 分析发送包: {filename}")
        
        # 解析RTP头部
        header_data = data[:12]
        byte0, byte1, sequence, timestamp, ssrc = struct.unpack('!BBHII', header_data)
        
        version = (byte0 >> 6) & 0x03
        marker = (byte1 >> 7) & 0x01
        payload_type = byte1 & 0x7F
        
        payload = data[12:]
        
        print(f"  RTP头部:")
        print(f"    版本: {version}")
        print(f"    标记: {marker}")
        print(f"    负载类型: {payload_type}")
        print(f"    序列号: {sequence}")
        print(f"    时间戳: {timestamp}")
        print(f"    SSRC: 0x{ssrc:08X}")
        
        print(f"  负载数据:")
        print(f"    总大小: {len(data)} 字节")
        print(f"    负载大小: {len(payload)} 字节")
        
        # 分析音频特征
        audio_analysis = analyze_ulaw_audio(payload)
        if audio_analysis:
            print(f"  音频特征:")
            print(f"    平均能量: {audio_analysis['avg_energy']:.2f}")
            print(f"    过零率: {audio_analysis['zero_crossing_rate']:.4f}")
            print(f"    熵值: {audio_analysis['entropy']:.2f}")
            print(f"    字节范围: {audio_analysis['min_byte']:02X} - {audio_analysis['max_byte']:02X}")
            print(f"    平均字节值: {audio_analysis['avg_byte']:.2f}")
        
        # 显示前64字节
        print(f"  前64字节: {' '.join(f'{b:02X}' for b in payload[:64])}")
        
        # 统计0xFF的数量
        ff_count = payload.count(0xFF)
        ff_percent = (ff_count / len(payload)) * 100
        print(f"  0xFF统计: {ff_count}/{len(payload)} ({ff_percent:.1f}%)")

def analyze_test_audio_file():
    """分析测试音频文件"""
    print(f"\n🎵 分析测试音频文件")
    print("=" * 60)
    
    try:
        with open('test_audio.ulaw', 'rb') as f:
            test_audio = f.read()
        
        print(f"📁 文件信息:")
        print(f"  文件名: test_audio.ulaw")
        print(f"  大小: {len(test_audio)} 字节")
        print(f"  时长: {len(test_audio) / 8000:.2f} 秒 (8kHz)")
        
        # 分析音频特征
        audio_analysis = analyze_ulaw_audio(test_audio)
        if audio_analysis:
            print(f"\n🎵 音频特征:")
            print(f"  样本数: {audio_analysis['sample_count']}")
            print(f"  平均能量: {audio_analysis['avg_energy']:.2f}")
            print(f"  过零率: {audio_analysis['zero_crossing_rate']:.4f}")
            print(f"  熵值: {audio_analysis['entropy']:.2f}")
            print(f"  字节范围: {audio_analysis['min_byte']:02X} - {audio_analysis['max_byte']:02X}")
            print(f"  平均字节值: {audio_analysis['avg_byte']:.2f}")
        
        # 分析字节分布
        byte_freq = defaultdict(int)
        for byte in test_audio:
            byte_freq[byte] += 1
        
        print(f"\n📊 字节分布 (前10个):")
        sorted_bytes = sorted(byte_freq.items(), key=lambda x: x[1], reverse=True)
        for byte, count in sorted_bytes[:10]:
            percent = (count / len(test_audio)) * 100
            print(f"  0x{byte:02X}: {count} 次 ({percent:.1f}%)")
        
        # 显示前128字节
        print(f"\n🔢 前128字节:")
        hex_data = ' '.join(f"{b:02X}" for b in test_audio[:128])
        print(f"  {hex_data}")
        
        # 分析波形特征
        print(f"\n📈 波形分析:")
        # 计算能量变化
        chunk_size = 160  # 20ms @ 8kHz
        energy_chunks = []
        for i in range(0, len(test_audio), chunk_size):
            chunk = test_audio[i:i+chunk_size]
            if chunk:
                energy = sum(abs(b - 0x80) for b in chunk) / len(chunk)
                energy_chunks.append(energy)
        
        if energy_chunks:
            avg_energy = sum(energy_chunks) / len(energy_chunks)
            max_energy = max(energy_chunks)
            min_energy = min(energy_chunks)
            print(f"  平均能量: {avg_energy:.2f}")
            print(f"  最大能量: {max_energy:.2f}")
            print(f"  最小能量: {min_energy:.2f}")
            print(f"  能量变化: {max_energy - min_energy:.2f}")
        
        return test_audio, audio_analysis
        
    except Exception as e:
        print(f"❌ 无法读取测试音频: {e}")
        return None, None

def compare_sent_vs_received():
    """对比发送和接收的音频包"""
    print(f"\n🔍 发送 vs 接收对比")
    print("=" * 60)
    
    # 分析测试音频
    test_audio, test_analysis = analyze_test_audio_file()
    
    # 分析接收到的语音包
    voice_files = [f for f in os.listdir('rtp_samples') if f.startswith('voice_sample_') and f.endswith('.bin')]
    
    if voice_files and test_analysis:
        print(f"\n📥 接收到的语音包特征:")
        voice_analyses = []
        
        for filename in voice_files[:5]:  # 分析前5个
            filepath = os.path.join('rtp_samples', filename)
            try:
                with open(filepath, 'rb') as f:
                    data = f.read()
                if len(data) >= 12:
                    payload = data[12:]
                    analysis = analyze_ulaw_audio(payload)
                    if analysis:
                        voice_analyses.append(analysis)
                        print(f"  {filename}: 能量={analysis['avg_energy']:.1f}, 过零率={analysis['zero_crossing_rate']:.3f}")
            except:
                continue
        
        if voice_analyses:
            # 计算平均值
            avg_energy = sum(a['avg_energy'] for a in voice_analyses) / len(voice_analyses)
            avg_zero_crossing = sum(a['zero_crossing_rate'] for a in voice_analyses) / len(voice_analyses)
            avg_entropy = sum(a['entropy'] for a in voice_analyses) / len(voice_analyses)
            
            print(f"\n📊 对比结果:")
            print(f"  发送音频:")
            print(f"    - 平均能量: {test_analysis['avg_energy']:.2f}")
            print(f"    - 过零率: {test_analysis['zero_crossing_rate']:.4f}")
            print(f"    - 熵值: {test_analysis['entropy']:.2f}")
            print(f"    - 字节范围: {test_analysis['min_byte']:02X} - {test_analysis['max_byte']:02X}")
            
            print(f"  接收语音 (平均):")
            print(f"    - 平均能量: {avg_energy:.2f}")
            print(f"    - 过零率: {avg_zero_crossing:.4f}")
            print(f"    - 熵值: {avg_entropy:.2f}")
            
            print(f"\n💡 关键发现:")
            energy_ratio = avg_energy / test_analysis['avg_energy'] if test_analysis['avg_energy'] > 0 else 0
            print(f"  - 能量比例: 接收/发送 = {energy_ratio:.2f}")
            
            if energy_ratio > 5:
                print(f"  ⚠️  接收音频能量远高于发送音频")
                print(f"  💭  可能原因:")
                print(f"    1. 接收的是真实人声，能量更高")
                print(f"    2. 发送的测试音能量过低")
                print(f"    3. 编码方式或增益设置不同")
            
            # 分析字节分布差异
            print(f"\n🔢 字节分布对比:")
            print(f"  发送音频: 范围 {test_analysis['min_byte']:02X}-{test_analysis['max_byte']:02X}")
            print(f"  接收音频: 范围 39-FF (从分析结果)")
            
            if test_analysis['min_byte'] == 0 and test_analysis['max_byte'] == 0xFF:
                print(f"  ✅ 发送音频使用了完整的μ-law范围")
            else:
                print(f"  ⚠️  发送音频范围受限")

def analyze_pt73_issue():
    """分析PT=73问题"""
    print(f"\n🚨 PT=73包问题分析")
    print("=" * 60)
    
    pt73_files = [f for f in os.listdir('rtp_samples') if 'payload_73_' in f and f.endswith('.bin')]
    
    if pt73_files:
        print(f"🔍 发现 {len(pt73_files)} 个PT=73包")
        
        for filename in pt73_files[:2]:
            filepath = os.path.join('rtp_samples', filename)
            try:
                with open(filepath, 'rb') as f:
                    data = f.read()
                
                if len(data) >= 12:
                    # 解析头部
                    byte0, byte1, sequence, timestamp, ssrc = struct.unpack('!BBHII', data[:12])
                    version = (byte0 >> 6) & 0x03
                    extension = (byte0 >> 4) & 0x01
                    csrc_count = byte0 & 0x0F
                    payload = data[12:]
                    
                    print(f"\n📦 {filename}:")
                    print(f"  RTP版本: {version} (异常)")
                    print(f"  扩展位: {extension}")
                    print(f"  CSRC数量: {csrc_count}")
                    print(f"  负载大小: {len(payload)} 字节")
                    
                    # 尝试解析为SIP消息
                    try:
                        text = payload.decode('utf-8', errors='ignore')
                        if 'SIP' in text:
                            print(f"  📝 这是SIP消息，不是RTP包!")
                            print(f"  💡 可能是RTP接收器误将SIP消息当作RTP包处理")
                    except:
                        pass
            except Exception as e:
                print(f"  ❌ 分析失败: {e}")

if __name__ == "__main__":
    print("🎵 VTX发送音频包深度分析")
    print("=" * 60)
    
    # 检查目录
    if not os.path.exists('rtp_samples'):
        print("❌ rtp_samples目录不存在")
        sys.exit(1)
    
    # 执行分析
    analyze_sent_rtp_packets()
    compare_sent_vs_received()
    analyze_pt73_issue()
    
    print(f"\n✅ 分析完成！") 