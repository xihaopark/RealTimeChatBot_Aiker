#!/usr/bin/env python3
"""
VTX AI Phone System V2 快速测试
不依赖大模型下载，验证核心架构
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'aiker_v2'))

def test_piper_tts():
    """测试Piper TTS"""
    print("🎵 Testing Piper TTS...")
    try:
        from tts_service import PiperTTSService
        tts = PiperTTSService()
        
        if tts.is_available():
            print("✅ Piper TTS service available")
            
            # 测试合成
            audio = tts.synthesize("测试", 'zh')
            if audio:
                print(f"✅ TTS synthesis successful: {len(audio)} bytes")
            else:
                print("❌ TTS synthesis failed")
        else:
            print("❌ Piper TTS not available")
            
    except Exception as e:
        print(f"❌ TTS test failed: {e}")

def test_llm_service():
    """测试LLM服务"""
    print("\n🧠 Testing LLM service...")
    try:
        from llm_service import LlamaCppLLMService
        llm = LlamaCppLLMService()
        
        if llm.is_available():
            print("✅ LLM service available")
            
            response = llm.generate_response("你好", "test")
            if response:
                print(f"✅ LLM response: {response}")
            else:
                print("❌ LLM response failed")
        else:
            print("❌ LLM service not available (server not running)")
            
    except Exception as e:
        print(f"❌ LLM test failed: {e}")

def test_stt_service():
    """测试STT服务"""
    print("\n🎤 Testing STT service...")
    try:
        from stt_service import VoskSTTService
        stt = VoskSTTService()
        
        if stt.is_available():
            print("✅ STT service available")
            print(f"✅ Supported languages: {stt.get_supported_languages()}")
        else:
            print("❌ STT service not available (models not downloaded)")
            
    except Exception as e:
        print(f"❌ STT test failed: {e}")

def test_core_architecture():
    """测试核心架构"""
    print("\n🏗️ Testing core architecture...")
    try:
        from call_handler import CallManager, CallInfo
        
        # 创建通话管理器
        manager = CallManager()
        print("✅ CallManager created successfully")
        
        # 测试呼叫信息
        call_info = CallInfo(
            call_id="test_001",
            remote_ip="127.0.0.1", 
            remote_port=5060,
            local_rtp_port=10000
        )
        print("✅ CallInfo structure working")
        
    except Exception as e:
        print(f"❌ Core architecture test failed: {e}")

def main():
    """主测试函数"""
    print("🧪 VTX AI Phone System V2 - Quick Test")
    print("=" * 50)
    
    # 测试各个组件
    test_piper_tts()
    test_llm_service() 
    test_stt_service()
    test_core_architecture()
    
    print("\n" + "=" * 50)
    print("🎯 Quick test completed!")
    print("\n📋 Next steps:")
    print("1. Wait for model downloads to complete")
    print("2. Start LLM server: cd services/llama.cpp && ./start_server.sh")  
    print("3. Run full system: ./start_aiker_v2.sh")

if __name__ == "__main__":
    main()