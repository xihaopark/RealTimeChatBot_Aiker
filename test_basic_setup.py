#!/usr/bin/env python3
"""
基础设置测试脚本
验证配置、导入和基本功能
"""

import os
import sys
import logging

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_imports():
    """测试模块导入"""
    print("=== 测试模块导入 ===")
    
    try:
        from config.settings import settings
        print("✓ 配置模块导入成功")
        
        from sip_client import EnhancedSIPClient, SDPParser
        print("✓ SIP客户端模块导入成功")
        
        from rtp_handler import RTPHandler, G711Codec
        print("✓ RTP处理器模块导入成功")
        
        from local_ai import LocalSTT, LocalTTS, LocalLLM, AudioConverter
        print("✓ 本地AI模块导入成功")
        
        return True
        
    except Exception as e:
        print(f"✗ 模块导入失败: {e}")
        return False


def test_configuration():
    """测试配置"""
    print("\n=== 测试配置 ===")
    
    try:
        from config.settings import settings
        
        print(f"VTX服务器: {settings.vtx.server}:{settings.vtx.port}")
        print(f"VTX域名: {settings.vtx.domain}")
        print(f"DID号码: {settings.vtx.did_number}")
        
        print(f"SIP端口: {settings.network.sip_port}")
        print(f"RTP端口范围: {settings.network.rtp_port_start}-{settings.network.rtp_port_end}")
        
        print(f"分机列表: {list(settings.extensions.keys())}")
        
        if not settings.extensions:
            print("⚠️ 警告: 没有配置分机，请检查环境变量")
            return False
        
        extension_id = list(settings.extensions.keys())[0]
        extension = settings.extensions[extension_id]
        print(f"使用分机: {extension.username} ({extension.description})")
        
        return True
        
    except Exception as e:
        print(f"✗ 配置测试失败: {e}")
        return False


def test_gpu_environment():
    """测试GPU环境"""
    print("\n=== 测试GPU环境 ===")
    
    try:
        import torch
        print(f"PyTorch版本: {torch.__version__}")
        print(f"CUDA可用: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"CUDA版本: {torch.version.cuda}")
            print(f"GPU数量: {torch.cuda.device_count()}")
            print(f"GPU名称: {torch.cuda.get_device_name(0)}")
            print(f"GPU内存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
        else:
            print("⚠️ CUDA不可用，将使用CPU模式")
        
        return True
        
    except Exception as e:
        print(f"✗ GPU环境测试失败: {e}")
        return False


def test_audio_converter():
    """测试音频转换器"""
    print("\n=== 测试音频转换器 ===")
    
    try:
        from local_ai import AudioConverter
        import numpy as np
        
        # 创建测试音频数据
        sample_rate = 8000
        duration = 0.1  # 100ms
        samples = int(sample_rate * duration)
        
        # 生成440Hz正弦波
        t = np.linspace(0, duration, samples, False)
        pcm_data = (np.sin(2 * np.pi * 440 * t) * 16383).astype(np.int16)
        
        print(f"生成测试PCM数据: {len(pcm_data)} 采样点")
        
        # 测试PCM to μ-law转换
        mulaw_data = AudioConverter.pcm_to_mulaw(pcm_data)
        print(f"PCM->μ-law: {len(pcm_data)} samples -> {len(mulaw_data)} bytes")
        
        # 测试μ-law to PCM转换
        recovered_pcm = AudioConverter.mulaw_to_pcm(mulaw_data)
        print(f"μ-law->PCM: {len(mulaw_data)} bytes -> {len(recovered_pcm)} samples")
        
        # 测试重采样
        pcm_16k = AudioConverter.resample_audio(pcm_data, 8000, 16000)
        print(f"重采样8k->16k: {len(pcm_data)} -> {len(pcm_16k)} samples")
        
        return True
        
    except Exception as e:
        print(f"✗ 音频转换器测试失败: {e}")
        return False


def test_sip_client_creation():
    """测试SIP客户端创建"""
    print("\n=== 测试SIP客户端创建 ===")
    
    try:
        from config.settings import settings
        from sip_client import EnhancedSIPClient
        
        # 获取分机配置
        extension_id = list(settings.extensions.keys())[0]
        extension = settings.extensions[extension_id]
        
        # 创建SIP客户端（不启动）
        sip_client = EnhancedSIPClient(
            username=extension.username,
            password=extension.password,
            domain=settings.vtx.domain,
            server=settings.vtx.server,
            port=settings.vtx.port
        )
        
        print(f"✓ SIP客户端创建成功: {extension.username}@{settings.vtx.domain}")
        print(f"  服务器: {settings.vtx.server}:{settings.vtx.port}")
        
        return True
        
    except Exception as e:
        print(f"✗ SIP客户端创建失败: {e}")
        return False


def test_rtp_handler_creation():
    """测试RTP处理器创建"""
    print("\n=== 测试RTP处理器创建 ===")
    
    try:
        from rtp_handler import RTPHandler
        
        # 创建RTP处理器
        rtp_handler = RTPHandler("127.0.0.1", 10000)
        
        print(f"✓ RTP处理器创建成功: {rtp_handler.local_ip}:{rtp_handler.local_port}")
        print(f"  SSRC: {hex(rtp_handler.ssrc)}")
        
        return True
        
    except Exception as e:
        print(f"✗ RTP处理器创建失败: {e}")
        return False


def test_port_management():
    """测试端口管理"""
    print("\n=== 测试端口管理 ===")
    
    try:
        import socket
        from config.settings import settings
        
        # 测试SIP端口
        sip_port = settings.network.sip_port
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind(('0.0.0.0', sip_port))
            print(f"✓ SIP端口 {sip_port} 可用")
            sock.close()
        except OSError as e:
            print(f"⚠️ SIP端口 {sip_port} 被占用: {e}")
        
        # 测试RTP端口范围
        rtp_start = settings.network.rtp_port_start
        rtp_end = min(settings.network.rtp_port_end, rtp_start + 10)  # 只测试前10个
        
        available_ports = 0
        for port in range(rtp_start, rtp_end, 2):  # 偶数端口
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.bind(('0.0.0.0', port))
                available_ports += 1
                sock.close()
            except OSError:
                pass
        
        print(f"✓ RTP端口可用: {available_ports}/{(rtp_end-rtp_start)//2}")
        
        return True
        
    except Exception as e:
        print(f"✗ 端口管理测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("VTX AI Phone System - 基础设置测试\n")
    
    tests = [
        ("模块导入", test_imports),
        ("配置管理", test_configuration),
        ("GPU环境", test_gpu_environment),
        ("音频转换", test_audio_converter),
        ("SIP客户端", test_sip_client_creation),
        ("RTP处理器", test_rtp_handler_creation),
        ("端口管理", test_port_management)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"✗ {test_name}测试异常: {e}")
            results[test_name] = False
    
    # 显示结果
    print("\n=== 测试结果汇总 ===")
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总体结果: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有基础测试通过! 可以尝试启动系统")
        return 0
    else:
        print("⚠️ 某些测试失败，请检查配置和环境")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)