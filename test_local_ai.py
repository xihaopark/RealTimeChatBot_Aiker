#!/usr/bin/env python3
"""
Local AI服务测试脚本
测试本地STT、TTS和LLM服务的功能
"""

import os
import sys
import logging
import time
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from local_ai import LocalSTT, LocalTTS, LocalLLM, AudioConverter

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_audio_converter():
    """测试音频转换器"""
    print("=== Testing Audio Converter ===")
    
    try:
        # 创建测试音频数据 (模拟8kHz PCM)
        duration = 1.0  # 1秒
        sample_rate = 8000
        frequency = 440  # A4音符
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        pcm_data = (np.sin(frequency * 2 * np.pi * t) * 16383).astype(np.int16)
        
        print(f"Generated test PCM data: {len(pcm_data)} samples")
        
        # 测试PCM to μ-law转换
        mulaw_data = AudioConverter.pcm_to_mulaw(pcm_data)
        print(f"PCM to μ-law: {len(pcm_data)} samples -> {len(mulaw_data)} bytes")
        
        # 测试μ-law to PCM转换
        recovered_pcm = AudioConverter.mulaw_to_pcm(mulaw_data)
        print(f"μ-law to PCM: {len(mulaw_data)} bytes -> {len(recovered_pcm)} samples")
        
        # 测试重采样
        pcm_16k = AudioConverter.resample_audio(pcm_data, 8000, 16000)
        print(f"Resampling 8kHz->16kHz: {len(pcm_data)} -> {len(pcm_16k)} samples")
        
        # 测试RTP转换
        rtp_pcm = AudioConverter.convert_rtp_to_pcm16k(mulaw_data)
        print(f"RTP to PCM16k: {len(mulaw_data)} bytes -> {len(rtp_pcm)} samples")
        
        print("✓ Audio Converter tests passed\n")
        return True
        
    except Exception as e:
        print(f"✗ Audio Converter test failed: {e}\n")
        return False


def test_local_llm():
    """测试本地LLM"""
    print("=== Testing Local LLM ===")
    
    try:
        # 注意：这会下载大模型，需要时间和网络
        print("Initializing Local LLM (this may take a while)...")
        
        llm = LocalLLM(
            model_name="Qwen/Qwen2.5-7B-Instruct",
            device="cuda",
            use_4bit=True
        )
        
        # 测试对话
        test_queries = [
            "你好",
            "OneSuite公司提供什么服务？",
            "电话系统的价格是多少？",
            "今天天气怎么样？"
        ]
        
        for query in test_queries:
            print(f"User: {query}")
            start_time = time.time()
            response = llm.generate_response(query)
            end_time = time.time()
            print(f"Assistant: {response}")
            print(f"Response time: {end_time - start_time:.2f}s\n")
        
        # 获取模型信息
        model_info = llm.get_model_info()
        print(f"Model info: {model_info}")
        
        print("✓ Local LLM tests passed\n")
        return True
        
    except Exception as e:
        print(f"✗ Local LLM test failed: {e}\n")
        return False


def test_local_tts():
    """测试本地TTS"""
    print("=== Testing Local TTS ===")
    
    try:
        print("Initializing Local TTS...")
        
        tts = LocalTTS(
            engine="system",
            voice="zh",
            device="cuda"
        )
        
        # 测试文本列表
        test_texts = [
            "你好，欢迎致电OneSuite。",
            "我是您的AI语音助手。",
            "请问有什么可以帮助您的吗？"
        ]
        
        for text in test_texts:
            print(f"Synthesizing: {text}")
            start_time = time.time()
            audio_data = tts.synthesize_text(text)
            end_time = time.time()
            
            print(f"Generated {len(audio_data)} bytes of audio in {end_time - start_time:.2f}s")
        
        tts.cleanup()
        print("✓ Local TTS tests passed\n")
        return True
        
    except Exception as e:
        print(f"✗ Local TTS test failed: {e}\n")
        return False


def test_local_stt():
    """测试本地STT"""
    print("=== Testing Local STT ===")
    
    try:
        print("Initializing Local STT...")
        
        # 创建STT实例
        stt = LocalSTT(
            model="base",
            language="zh",
            device="cuda",
            mic=False
        )
        
        # 设置回调
        transcriptions = []
        def on_transcription(text):
            transcriptions.append(text)
            print(f"STT Result: {text}")
        
        stt.set_transcription_callback(on_transcription)
        stt.start_listening()
        
        # 测试音频转录（使用测试功能）
        stt.test_transcription("这是一个语音识别测试")
        
        # 等待处理
        time.sleep(2)
        
        stt.stop_listening()
        
        if transcriptions:
            print("✓ Local STT tests passed\n")
            return True
        else:
            print("✗ No transcriptions received\n")
            return False
        
    except Exception as e:
        print(f"✗ Local STT test failed: {e}\n")
        return False


def test_integration():
    """测试组件集成"""
    print("=== Testing Integration ===")
    
    try:
        print("Testing STT -> LLM -> TTS pipeline...")
        
        # 初始化组件
        llm = LocalLLM(model_name="Qwen/Qwen2.5-7B-Instruct", use_4bit=True)
        tts = LocalTTS(engine="system", voice="zh")
        
        # 模拟完整对话流程
        user_input = "你好，请介绍一下OneSuite公司"
        
        print(f"1. User input: {user_input}")
        
        # LLM生成回复
        start_time = time.time()
        ai_response = llm.generate_response(user_input)
        llm_time = time.time() - start_time
        print(f"2. LLM response ({llm_time:.2f}s): {ai_response}")
        
        # TTS合成语音
        start_time = time.time()
        audio_data = tts.synthesize_text(ai_response)
        tts_time = time.time() - start_time
        print(f"3. TTS synthesis ({tts_time:.2f}s): {len(audio_data)} bytes")
        
        total_time = llm_time + tts_time
        print(f"4. Total response time: {total_time:.2f}s")
        
        tts.cleanup()
        
        if total_time < 10.0:  # 期望在10秒内完成
            print("✓ Integration test passed\n")
            return True
        else:
            print(f"✗ Response time too slow: {total_time:.2f}s\n")
            return False
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}\n")
        return False


def main():
    """主测试函数"""
    print("Starting Local AI Services Tests...\n")
    
    results = {
        "Audio Converter": test_audio_converter(),
        "Local LLM": test_local_llm(),
        "Local TTS": test_local_tts(),
        "Local STT": test_local_stt(),
        "Integration": test_integration()
    }
    
    print("=== Test Results ===")
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The local AI system is ready to use.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)