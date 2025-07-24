#!/usr/bin/env python3
"""
本地AI组件分别测试
逐个测试TTS、LLM、STT组件
"""

import os
import sys
import time
import logging

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def test_llm():
    """测试LLM"""
    print("=== 测试本地LLM ===")
    
    try:
        from local_ai import LocalLLM
        
        print("正在初始化LLM...")
        llm = LocalLLM(
            model_name="Qwen/Qwen2.5-7B-Instruct",
            device="cuda",
            use_4bit=True,
            max_length=512,  # 减小长度加快速度
            temperature=0.7
        )
        
        print("✅ LLM初始化成功")
        
        # 测试简单对话
        test_inputs = ["你好", "OneSuite是什么？"]
        
        for user_input in test_inputs:
            print(f"\n用户: {user_input}")
            start_time = time.time()
            response = llm.generate_response(user_input)
            end_time = time.time()
            print(f"AI回复 ({end_time-start_time:.2f}s): {response}")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tts():
    """测试TTS"""
    print("\n=== 测试本地TTS ===")
    
    try:
        from local_ai import LocalTTS
        
        print("正在初始化TTS...")
        tts = LocalTTS(
            engine="system",
            voice="zh",
            device="cpu"  # TTS用CPU就够了
        )
        
        print("✅ TTS初始化成功")
        
        # 测试语音合成
        test_texts = ["你好，欢迎使用OneSuite", "这是语音合成测试"]
        
        for text in test_texts:
            print(f"\n合成文本: {text}")
            start_time = time.time()
            audio_data = tts.synthesize_text(text)
            end_time = time.time()
            print(f"生成音频 ({end_time-start_time:.2f}s): {len(audio_data)} bytes")
        
        tts.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ TTS测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_stt():
    """测试STT"""
    print("\n=== 测试本地STT ===")
    
    try:
        from local_ai import LocalSTT
        
        print("正在初始化STT...")
        stt = LocalSTT(
            model="tiny",  # 使用最小模型快速测试
            language="zh",
            device="cuda",
            mic=False
        )
        
        print("✅ STT初始化成功")
        
        # 简单测试
        stt.test_transcription("STT测试成功")
        
        stt.stop_listening()
        return True
        
    except Exception as e:
        print(f"❌ STT测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_audio_converter():
    """测试音频转换器"""
    print("\n=== 测试音频转换器 ===")
    
    try:
        from local_ai import AudioConverter
        import numpy as np
        
        # 创建测试音频
        test_pcm = np.random.randint(-1000, 1000, 800, dtype=np.int16)
        
        # 测试转换
        mulaw_data = AudioConverter.pcm_to_mulaw(test_pcm)
        recovered_pcm = AudioConverter.mulaw_to_pcm(mulaw_data)
        
        print(f"PCM->μ-law: {len(test_pcm)} -> {len(mulaw_data)}")
        print(f"μ-law->PCM: {len(mulaw_data)} -> {len(recovered_pcm)}")
        
        # 测试RTP转换
        rtp_audio = AudioConverter.convert_pcm16k_to_rtp(test_pcm)  
        rtp_pcm = AudioConverter.convert_rtp_to_pcm16k(rtp_audio)
        
        print(f"PCM->RTP->PCM: {len(test_pcm)} -> {len(rtp_pcm)}")
        
        print("✅ 音频转换器测试成功")
        return True
        
    except Exception as e:
        print(f"❌ 音频转换器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("VTX AI Phone System - AI组件分别测试\n")
    
    tests = [
        ("音频转换器", test_audio_converter),
        ("TTS", test_tts),
        ("LLM", test_llm),
        ("STT", test_stt)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"开始测试: {test_name}")
        print('='*50)
        
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            results[test_name] = False
        
        if results[test_name]:
            print(f"✅ {test_name}测试完成")
        else:
            print(f"❌ {test_name}测试失败")
    
    # 结果汇总
    print(f"\n{'='*50}")
    print("测试结果汇总")
    print('='*50)
    
    passed = 0
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总体结果: {passed}/{len(results)} 组件测试通过")
    
    if passed == len(results):
        print("🎉 所有AI组件测试通过!")
        return 0
    else:
        print("⚠️ 部分组件测试失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)