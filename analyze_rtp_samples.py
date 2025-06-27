#!/usr/bin/env python3
"""
RTP包分析工具
分析保存的RTP包样本，了解对方发送的音频包结构
"""

import os
import struct
import sys
from pathlib import Path

def parse_rtp_header(header_data):
    """解析RTP头部"""
    if len(header_data) < 12:
        return None
    
    byte0, byte1, seq_high, seq_low, ts_0, ts_1, ts_2, ts_3, ssrc_0, ssrc_1, ssrc_2, ssrc_3 = struct.unpack('!BBBBBBBBBBBB', header_data[:12])
    
    version = (byte0 >> 6) & 0x03
    padding = (byte0 >> 5) & 0x01
    extension = (byte0 >> 4) & 0x01
    csrc_count = byte0 & 0x0F
    marker = (byte1 >> 7) & 0x01
    payload_type = byte1 & 0x7F
    
    sequence_number = (seq_high << 8) | seq_low
    timestamp = (ts_0 << 24) | (ts_1 << 16) | (ts_2 << 8) | ts_3
    ssrc = (ssrc_0 << 24) | (ssrc_1 << 16) | (ssrc_2 << 8) | ssrc_3
    
    return {
        'version': version,
        'padding': padding,
        'extension': extension,
        'csrc_count': csrc_count,
        'marker': marker,
        'payload_type': payload_type,
        'sequence_number': sequence_number,
        'timestamp': timestamp,
        'ssrc': ssrc
    }

def payload_type_to_codec(payload_type):
    """将payload type转换为编解码器名称"""
    codec_map = {
        0: "PCMU",
        8: "PCMA", 
        13: "CN",
        126: "动态"
    }
    return codec_map.get(payload_type, f"未知({payload_type})")

def analyze_audio_payload(payload, payload_type):
    """分析音频负载数据"""
    if not payload:
        return
    
    print(f"🎵 音频分析:")
    print(f"  负载大小: {len(payload)} 字节")
    
    # 显示前32字节的十六进制
    hex_data = ' '.join(f'{b:02x}' for b in payload[:32])
    print(f"  前32字节: {hex_data}")
    
    # 分析音频特征
    if payload_type == 0:  # PCMU (μ-law)
        print(f"  编码: μ-law (PCMU)")
        # 计算能量
        energy = sum(abs(b - 0x7F) for b in payload)
        avg_energy = energy / len(payload) if payload else 0
        print(f"  平均能量: {avg_energy:.2f}")
        
        # 检测静音
        silence_count = sum(1 for b in payload if b == 0xFF or b == 0x7F)
        silence_ratio = silence_count / len(payload) if payload else 0
        print(f"  静音比例: {silence_ratio:.2%}")
        
        if silence_ratio > 0.8:
            print(f"  🔇 主要是静音")
        elif avg_energy > 50:
            print(f"  🎤 检测到语音活动")
        else:
            print(f"  🔈 低音量音频")
            
    elif payload_type == 8:  # PCMA (A-law)
        print(f"  编码: A-law (PCMA)")
        # 计算能量
        energy = sum(abs(b - 0x55) for b in payload)
        avg_energy = energy / len(payload) if payload else 0
        print(f"  平均能量: {avg_energy:.2f}")
        
    elif payload_type == 13:  # CN (Comfort Noise)
        print(f"  编码: 舒适噪声 (CN)")
        print(f"  这是舒适噪声包，用于填充静音期间")

def analyze_rtp_file(file_path):
    """分析单个RTP包文件"""
    print(f"\n🔍 分析文件: {file_path}")
    print("=" * 60)
    
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        
        if len(data) < 12:
            print(f"❌ 文件太小，不是有效的RTP包")
            return
        
        # 解析RTP头部
        header = parse_rtp_header(data[:12])
        if not header:
            print(f"❌ 无法解析RTP头部")
            return
        
        print(f"📋 RTP头部信息:")
        print(f"  版本: {header['version']}")
        print(f"  填充: {header['padding']}")
        print(f"  扩展: {header['extension']}")
        print(f"  CSRC数量: {header['csrc_count']}")
        print(f"  标记: {header['marker']}")
        print(f"  负载类型: {header['payload_type']} ({payload_type_to_codec(header['payload_type'])})")
        print(f"  序列号: {header['sequence_number']}")
        print(f"  时间戳: {header['timestamp']}")
        print(f"  SSRC: 0x{header['ssrc']:08X}")
        
        # 分析负载
        payload = data[12:]
        print(f"\n📦 负载数据:")
        print(f"  总包大小: {len(data)} 字节")
        print(f"  头部大小: 12 字节")
        print(f"  负载大小: {len(payload)} 字节")
        
        # 分析音频负载
        if header['payload_type'] in [0, 8, 13]:
            analyze_audio_payload(payload, header['payload_type'])
        
        # 保存负载数据到单独文件（用于进一步分析）
        payload_file = str(file_path).replace('.bin', '_payload.raw')
        with open(payload_file, 'wb') as f:
            f.write(payload)
        print(f"\n💾 负载数据已保存到: {payload_file}")
        
    except Exception as e:
        print(f"❌ 分析文件时出错: {e}")

def main():
    """主函数"""
    rtp_samples_dir = "rtp_samples"
    
    if not os.path.exists(rtp_samples_dir):
        print(f"❌ RTP样本目录不存在: {rtp_samples_dir}")
        print("请先运行VTX系统并接收一些RTP包")
        return
    
    # 查找所有RTP样本文件
    sample_files = list(Path(rtp_samples_dir).glob("*.bin"))
    
    if not sample_files:
        print(f"❌ 未找到RTP样本文件")
        return
    
    print(f"🔍 找到 {len(sample_files)} 个RTP样本文件")
    print("=" * 60)
    
    # 按payload type分组
    payload_groups = {}
    for file_path in sample_files:
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            if len(data) >= 12:
                header = parse_rtp_header(data[:12])
                if header:
                    pt = header['payload_type']
                    if pt not in payload_groups:
                        payload_groups[pt] = []
                    payload_groups[pt].append(file_path)
        except:
            continue
    
    # 显示统计信息
    print(f"📊 RTP包统计:")
    for pt, files in payload_groups.items():
        codec = payload_type_to_codec(pt)
        print(f"  payload_type {pt} ({codec}): {len(files)} 个包")
    
    print("\n" + "=" * 60)
    
    # 分析每个payload type的第一个样本
    for pt, files in payload_groups.items():
        if files:
            analyze_rtp_file(files[0])
    
    print(f"\n✅ 分析完成！")
    print(f"💡 提示: 可以查看保存的负载文件进行进一步分析")

if __name__ == "__main__":
    main() 