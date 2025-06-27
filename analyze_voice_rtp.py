#!/usr/bin/env python3
"""
RTP人声包分析工具
专门用于分析包含人声的RTP包
"""

import struct
import sys
import os
import time
from pathlib import Path

def parse_rtp_header(header_data):
    """解析RTP头部"""
    if len(header_data) < 12:
        return None
    
    # RTP头部格式: V=2, P=0, X=0, CC=0, M=1, PT=0, Sequence=2, Timestamp=4, SSRC=4
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

def payload_type_to_codec(payload_type):
    """将payload type转换为编解码器名称"""
    codec_map = {
        0: "PCMU (G.711 μ-law)",
        8: "PCMA (G.711 A-law)",
        13: "CN (Comfort Noise)",
        101: "DTMF",
        110: "PCMU (G.711 μ-law)",
        111: "PCMA (G.711 A-law)"
    }
    return codec_map.get(payload_type, f"未知({payload_type})")

def analyze_voice_activity(payload, payload_type):
    """分析语音活动"""
    if not payload:
        return False, {}
    
    analysis = {}
    
    if payload_type == 0:  # PCMU
        # μ-law解码分析
        energy = sum(abs(b - 0x7F) for b in payload)
        avg_energy = energy / len(payload)
        
        # 检测静音
        silence_count = sum(1 for b in payload if b == 0xFF or b == 0x7F)
        silence_ratio = silence_count / len(payload)
        
        # 检测语音特征
        non_zero_count = sum(1 for b in payload if b != 0xFF and b != 0x7F)
        activity_ratio = non_zero_count / len(payload)
        
        # 计算能量分布
        energy_levels = [0] * 4
        for b in payload:
            if b == 0xFF or b == 0x7F:
                energy_levels[0] += 1  # 静音
            elif abs(b - 0x7F) < 20:
                energy_levels[1] += 1  # 低能量
            elif abs(b - 0x7F) < 50:
                energy_levels[2] += 1  # 中能量
            else:
                energy_levels[3] += 1  # 高能量
        
        analysis = {
            'avg_energy': avg_energy,
            'silence_ratio': silence_ratio,
            'activity_ratio': activity_ratio,
            'energy_distribution': energy_levels,
            'voice_detected': avg_energy > 30 and silence_ratio < 0.7
        }
        
    elif payload_type == 8:  # PCMA
        # A-law解码分析
        energy = sum(abs(b - 0x55) for b in payload)
        avg_energy = energy / len(payload)
        
        analysis = {
            'avg_energy': avg_energy,
            'voice_detected': avg_energy > 30
        }
    
    return analysis.get('voice_detected', False), analysis

def analyze_voice_packet(file_path):
    """分析人声RTP包文件"""
    print(f"\n🎤 分析人声RTP包: {file_path}")
    print("=" * 60)
    
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        
        if len(data) < 12:
            print("❌ 文件太小，不是有效的RTP包")
            return
        
        # 解析RTP头部
        header = parse_rtp_header(data[:12])
        if not header:
            print("❌ 无法解析RTP头部")
            return
        
        payload = data[12:]
        
        print(f"📋 RTP头部信息:")
        print(f"  版本: {header['version']}")
        print(f"  标记: {header['marker']}")
        print(f"  Payload Type: {header['payload_type']} ({payload_type_to_codec(header['payload_type'])})")
        print(f"  序列号: {header['sequence_number']}")
        print(f"  时间戳: {header['timestamp']}")
        print(f"  SSRC: {header['ssrc']}")
        
        print(f"\n🎵 音频负载分析:")
        print(f"  负载大小: {len(payload)} 字节")
        
        # 显示前64字节的十六进制
        hex_data = ' '.join(f'{b:02x}' for b in payload[:64])
        print(f"  前64字节: {hex_data}")
        
        # 语音活动分析
        voice_detected, analysis = analyze_voice_activity(payload, header['payload_type'])
        
        if header['payload_type'] in [0, 8]:  # 音频包
            print(f"\n🔊 语音活动分析:")
            print(f"  检测到语音: {'是' if voice_detected else '否'}")
            
            if 'avg_energy' in analysis:
                print(f"  平均能量: {analysis['avg_energy']:.2f}")
            if 'silence_ratio' in analysis:
                print(f"  静音比例: {analysis['silence_ratio']:.2%}")
            if 'activity_ratio' in analysis:
                print(f"  活动比例: {analysis['activity_ratio']:.2%}")
            if 'energy_distribution' in analysis:
                dist = analysis['energy_distribution']
                total = sum(dist)
                print(f"  能量分布:")
                print(f"    静音: {dist[0]} ({dist[0]/total:.1%})")
                print(f"    低能量: {dist[1]} ({dist[1]/total:.1%})")
                print(f"    中能量: {dist[2]} ({dist[2]/total:.1%})")
                print(f"    高能量: {dist[3]} ({dist[3]/total:.1%})")
            
            # 判断语音质量
            if voice_detected:
                if analysis.get('avg_energy', 0) > 50:
                    print(f"  🔊 强语音信号")
                elif analysis.get('avg_energy', 0) > 20:
                    print(f"  🎤 中等语音信号")
                else:
                    print(f"  🔈 弱语音信号")
                
                if analysis.get('silence_ratio', 1) < 0.3:
                    print(f"  🎵 连续语音")
                elif analysis.get('silence_ratio', 1) < 0.7:
                    print(f"  🎤 混合语音")
                else:
                    print(f"  🔇 主要是静音")
        
        # 保存分析结果
        analysis_file = file_path.replace('.bin', '_analysis.txt')
        with open(analysis_file, 'w', encoding='utf-8') as f:
            f.write(f"RTP人声包分析报告\n")
            f.write(f"文件: {file_path}\n")
            f.write(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"\nRTP头部:\n")
            for key, value in header.items():
                f.write(f"  {key}: {value}\n")
            f.write(f"\n负载大小: {len(payload)} 字节\n")
            f.write(f"语音检测: {'是' if voice_detected else '否'}\n")
            if analysis:
                f.write(f"\n详细分析:\n")
                for key, value in analysis.items():
                    f.write(f"  {key}: {value}\n")
        
        print(f"\n💾 分析结果已保存到: {analysis_file}")
        
    except Exception as e:
        print(f"❌ 分析错误: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python analyze_voice_rtp.py <RTP包文件>")
        print("或者: python analyze_voice_rtp.py --all (分析rtp_samples目录下所有文件)")
        return
    
    if sys.argv[1] == "--all":
        # 分析所有RTP样本文件
        rtp_samples_dir = "rtp_samples"
        if not os.path.exists(rtp_samples_dir):
            print(f"❌ 目录不存在: {rtp_samples_dir}")
            return
        
        voice_files = []
        for file_path in Path(rtp_samples_dir).glob("*.bin"):
            if "voice_sample" in file_path.name:
                voice_files.append(file_path)
        
        if not voice_files:
            print("❌ 未找到人声样本文件")
            return
        
        print(f"🎤 找到 {len(voice_files)} 个人声样本文件")
        for file_path in sorted(voice_files):
            analyze_voice_packet(str(file_path))
            print("\n" + "-" * 60)
    else:
        # 分析单个文件
        file_path = sys.argv[1]
        if not os.path.exists(file_path):
            print(f"❌ 文件不存在: {file_path}")
            return
        
        analyze_voice_packet(file_path)

if __name__ == "__main__":
    main() 