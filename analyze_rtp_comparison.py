#!/usr/bin/env python3
"""
RTP包对比分析工具
分析我们发送的音频包和接收到的音频包之间的差异
"""

import struct
import os
import sys
import math
from collections import defaultdict

def parse_rtp_header(header_data):
    """解析RTP头部"""
    if len(header_data) < 12:
        return None

    byte0, byte1, sequence, timestamp, ssrc = struct.unpack('!BBHII', header_data[:12])

    version = (byte0 >> 6) & 0x03
    padding = (byte0 >> 5) & 0x01
    extension = (byte0 >> 4) & 0x01
    csrc_count = byte0 & 0x0F
    marker = (byte1 >> 7) & 0x01
    payload_type = byte1 & 0x7F

    return {
        'version': version,
        'padding': padding,
        'extension': extension,
        'csrc_count': csrc_count,
        'marker': marker,
        'payload_type': payload_type,
        'sequence_number': sequence,
        'timestamp': timestamp,
        'ssrc': ssrc
    }

def analyze_ulaw_audio(payload_data):
    """分析μ-law音频数据"""
    if not payload_data:
        return {}
    
    # μ-law解码表（简化版）
    ulaw_table = [
        0, 132, 396, 924, 1980, 4092, 8316, 16764,
        255, 387, 915, 1983, 4095, 8319, 16767, 32767
    ]
    
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

def analyze_file(filename):
    """分析单个RTP包文件"""
    print(f"\n🔍 分析文件: {filename}")
    print("=" * 60)
    
    try:
        with open(filename, 'rb') as f:
            data = f.read()
    except Exception as e:
        print(f"❌ 无法读取文件: {e}")
        return None
    
    if len(data) < 12:
        print(f"❌ 文件太小，不是有效的RTP包: {len(data)} 字节")
        return None
    
    # 解析RTP头部
    header = parse_rtp_header(data[:12])
    if not header:
        print("❌ 无法解析RTP头部")
        return None
    
    payload = data[12:]
    
    print(f"📋 RTP头部信息:")
    print(f"  版本: {header['version']}")
    print(f"  填充: {header['padding']}")
    print(f"  扩展: {header['extension']}")
    print(f"  CSRC数量: {header['csrc_count']}")
    print(f"  标记: {header['marker']}")
    print(f"  负载类型: {header['payload_type']}")
    print(f"  序列号: {header['sequence_number']}")
    print(f"  时间戳: {header['timestamp']}")
    print(f"  SSRC: 0x{header['ssrc']:08X}")
    
    print(f"\n📦 负载数据:")
    print(f"  总包大小: {len(data)} 字节")
    print(f"  头部大小: 12 字节")
    print(f"  负载大小: {len(payload)} 字节")
    
    # 分析音频数据
    if header['payload_type'] == 0:  # PCMU
        audio_analysis = analyze_ulaw_audio(payload)
        if audio_analysis:
            print(f"\n🎵 音频分析:")
            print(f"  样本数: {audio_analysis['sample_count']}")
            print(f"  平均能量: {audio_analysis['avg_energy']:.2f}")
            print(f"  过零率: {audio_analysis['zero_crossing_rate']:.4f}")
            print(f"  熵值: {audio_analysis['entropy']:.2f}")
            print(f"  字节范围: {audio_analysis['min_byte']:02X} - {audio_analysis['max_byte']:02X}")
            print(f"  平均字节值: {audio_analysis['avg_byte']:.2f}")
            
            # 显示前32字节的十六进制
            print(f"\n🔢 前32字节 (十六进制):")
            hex_data = ' '.join(f"{b:02X}" for b in payload[:32])
            print(f"  {hex_data}")
            
            # 显示前32字节的ASCII
            ascii_data = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in payload[:32])
            print(f"  ASCII: {ascii_data}")
    
    elif header['payload_type'] == 13:  # CN
        print(f"\n🎵 舒适噪声 (CN):")
        print(f"  负载大小: {len(payload)} 字节")
        if payload:
            print(f"  CN参数: 0x{payload[0]:02X}")
    
    else:
        print(f"\n❓ 未知负载类型: {header['payload_type']}")
        print(f"  前32字节: {' '.join(f'{b:02X}' for b in payload[:32])}")
    
    return {
        'header': header,
        'payload': payload,
        'audio_analysis': audio_analysis if header['payload_type'] == 0 else None
    }

def compare_audio_files():
    """对比音频文件"""
    print("🎵 RTP音频包对比分析")
    print("=" * 60)
    
    # 分析我们发送的测试音频
    print("\n📤 我们发送的音频 (test_audio.ulaw):")
    try:
        with open('test_audio.ulaw', 'rb') as f:
            test_audio = f.read()
        
        test_analysis = analyze_ulaw_audio(test_audio)
        if test_analysis:
            print(f"  总字节数: {len(test_audio)}")
            print(f"  平均能量: {test_analysis['avg_energy']:.2f}")
            print(f"  过零率: {test_analysis['zero_crossing_rate']:.4f}")
            print(f"  熵值: {test_analysis['entropy']:.2f}")
            print(f"  字节范围: {test_analysis['min_byte']:02X} - {test_analysis['max_byte']:02X}")
            print(f"  平均字节值: {test_analysis['avg_byte']:.2f}")
            
            print(f"  前32字节: {' '.join(f'{b:02X}' for b in test_audio[:32])}")
    except Exception as e:
        print(f"❌ 无法读取测试音频: {e}")
        test_analysis = None
    
    # 分析接收到的语音包
    voice_files = [f for f in os.listdir('rtp_samples') if f.startswith('voice_sample_') and f.endswith('.bin')]
    
    if voice_files:
        print(f"\n📥 接收到的语音包分析:")
        for i, filename in enumerate(voice_files[:3]):  # 只分析前3个
            filepath = os.path.join('rtp_samples', filename)
            result = analyze_file(filepath)
            
            if result and result['audio_analysis']:
                print(f"\n  📊 语音包 {i+1} 统计:")
                print(f"    平均能量: {result['audio_analysis']['avg_energy']:.2f}")
                print(f"    过零率: {result['audio_analysis']['zero_crossing_rate']:.4f}")
                print(f"    熵值: {result['audio_analysis']['entropy']:.2f}")
    
    # 对比分析
    if test_analysis and voice_files:
        print(f"\n🔍 对比分析:")
        print(f"  发送音频特征:")
        print(f"    - 平均能量: {test_analysis['avg_energy']:.2f}")
        print(f"    - 过零率: {test_analysis['zero_crossing_rate']:.4f}")
        print(f"    - 熵值: {test_analysis['entropy']:.2f}")
        print(f"    - 字节范围: {test_analysis['min_byte']:02X} - {test_analysis['max_byte']:02X}")
        
        # 分析接收到的语音包的平均特征
        voice_analyses = []
        for filename in voice_files[:5]:  # 分析前5个语音包
            filepath = os.path.join('rtp_samples', filename)
            try:
                with open(filepath, 'rb') as f:
                    data = f.read()
                if len(data) >= 12:
                    payload = data[12:]
                    analysis = analyze_ulaw_audio(payload)
                    if analysis:
                        voice_analyses.append(analysis)
            except:
                continue
        
        if voice_analyses:
            avg_energy = sum(a['avg_energy'] for a in voice_analyses) / len(voice_analyses)
            avg_zero_crossing = sum(a['zero_crossing_rate'] for a in voice_analyses) / len(voice_analyses)
            avg_entropy = sum(a['entropy'] for a in voice_analyses) / len(voice_analyses)
            
            print(f"\n  接收语音特征 (平均):")
            print(f"    - 平均能量: {avg_energy:.2f}")
            print(f"    - 过零率: {avg_zero_crossing:.4f}")
            print(f"    - 熵值: {avg_entropy:.2f}")
            
            print(f"\n  💡 差异分析:")
            energy_diff = abs(test_analysis['avg_energy'] - avg_energy)
            zero_diff = abs(test_analysis['zero_crossing_rate'] - avg_zero_crossing)
            entropy_diff = abs(test_analysis['entropy'] - avg_entropy)
            
            print(f"    - 能量差异: {energy_diff:.2f}")
            print(f"    - 过零率差异: {zero_diff:.4f}")
            print(f"    - 熵值差异: {entropy_diff:.2f}")
            
            if energy_diff > 100:
                print(f"    ⚠️  能量差异较大，可能是编码方式不同")
            if zero_diff > 0.1:
                print(f"    ⚠️  过零率差异较大，可能是音频内容不同")
            if entropy_diff > 1.0:
                print(f"    ⚠️  熵值差异较大，可能是音频复杂度不同")

def analyze_pt73_packets():
    """分析PT=73的异常包"""
    print(f"\n🔍 PT=73包分析:")
    print("=" * 60)
    
    pt73_files = [f for f in os.listdir('rtp_samples') if 'payload_73_' in f and f.endswith('.bin')]
    
    for filename in pt73_files[:2]:  # 只分析前2个
        filepath = os.path.join('rtp_samples', filename)
        print(f"\n📦 分析: {filename}")
        
        try:
            with open(filepath, 'rb') as f:
                data = f.read()
            
            if len(data) >= 12:
                header = parse_rtp_header(data[:12])
                payload = data[12:]
                
                print(f"  RTP版本: {header['version']} (异常，应该是2)")
                print(f"  扩展位: {header['extension']}")
                print(f"  CSRC数量: {header['csrc_count']}")
                print(f"  负载大小: {len(payload)} 字节")
                
                # 尝试解析为文本
                try:
                    text = payload.decode('utf-8', errors='ignore')
                    if 'SIP' in text or 'HTTP' in text:
                        print(f"  📝 检测到SIP/HTTP文本:")
                        lines = text.split('\n')[:3]
                        for line in lines:
                            if line.strip():
                                print(f"    {line.strip()}")
                except:
                    pass
                
                # 显示前64字节的十六进制
                print(f"  🔢 前64字节: {' '.join(f'{b:02X}' for b in payload[:64])}")
        
        except Exception as e:
            print(f"  ❌ 分析失败: {e}")

if __name__ == "__main__":
    print("🎵 VTX RTP包深度分析工具")
    print("=" * 60)
    
    # 检查目录
    if not os.path.exists('rtp_samples'):
        print("❌ rtp_samples目录不存在")
        sys.exit(1)
    
    # 执行分析
    compare_audio_files()
    analyze_pt73_packets()
    
    print(f"\n✅ 分析完成！") 