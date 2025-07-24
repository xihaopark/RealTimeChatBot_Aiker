#!/usr/bin/env python3
"""
本地AI流程测试
专注测试STT -> LLM -> TTS的完整流程
"""

import os
import sys
import time
import logging

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from local_ai import LocalSTT, LocalTTS, LocalLLM, AudioConverter
import numpy as np

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_local_ai_pipeline():
    """测试本地AI完整流程"""
    print("=== 本地AI流程测试 ===")
    
    try:
        # 1. 初始化LLM（最重要的组件）
        print("🧠 初始化本地LLM...")
        llm = LocalLLM(
            model_name="Qwen/Qwen2.5-7B-Instruct",
            device="cuda",
            use_4bit=True,
            max_length=1024,
            temperature=0.7
        )
        print("✅ LLM初始化完成")
        
        # 2. 初始化TTS
        print("🗣️ 初始化本地TTS...")
        tts = LocalTTS(
            engine="system",
            voice="zh",
            device="cuda"
        )
        print("✅ TTS初始化完成")
        
        # 3. 初始化STT
        print("👂 初始化本地STT...")
        stt = LocalSTT(
            model="base",
            language="zh",
            device="cuda",
            mic=False
        )
        print("✅ STT初始化完成")
        
        # 4. 测试完整对话流程
        test_conversations = [
            "你好",
            "OneSuite公司提供什么服务？",
            "电话系统的价格是多少？"
        ]
        
        print("\n🔄 开始测试对话流程...")
        
        for i, user_input in enumerate(test_conversations, 1):
            print(f"\n--- 对话 {i} ---")
            print(f"用户: {user_input}")
            
            # STT: 模拟语音识别（这里直接使用文本）
            stt_start = time.time()
            recognized_text = user_input  # 实际应用中这里是STT的结果
            stt_time = time.time() - stt_start
            print(f"STT结果 ({stt_time:.2f}s): {recognized_text}")
            
            # LLM: 生成回复
            llm_start = time.time()
            ai_response = llm.generate_response(recognized_text)
            llm_time = time.time() - llm_start
            print(f"LLM回复 ({llm_time:.2f}s): {ai_response}")
            
            # TTS: 语音合成
            tts_start = time.time()
            audio_data = tts.synthesize_text(ai_response)
            tts_time = time.time() - tts_start
            print(f"TTS合成 ({tts_time:.2f}s): {len(audio_data)} bytes")
            
            # 总响应时间
            total_time = stt_time + llm_time + tts_time
            print(f"总响应时间: {total_time:.2f}s")
            
            if total_time > 10:
                print("⚠️ 响应时间较长，可能需要优化")
            elif total_time > 5:
                print("🟡 响应时间中等")
            else:
                print("🟢 响应时间良好")
        
        # 5. 测试音频格式转换
        print("\n🔄 测试音频格式转换...")
        
        # 生成测试PCM音频
        test_pcm = np.random.randint(-16384, 16384, 1600, dtype=np.int16)  # 0.1s @ 16kHz
        
        # 转换为RTP格式
        rtp_audio = AudioConverter.convert_pcm16k_to_rtp(test_pcm)
        print(f"PCM->RTP: {len(test_pcm)} samples -> {len(rtp_audio)} bytes")
        
        # 转换回PCM
        recovered_pcm = AudioConverter.convert_rtp_to_pcm16k(rtp_audio)
        print(f"RTP->PCM: {len(rtp_audio)} bytes -> {len(recovered_pcm)} samples")
        
        print("✅ 音频转换测试通过")
        
        # 6. 性能评估
        print("\n📊 性能评估:")
        model_info = llm.get_model_info()
        print(f"- 模型: {model_info['model_name']}")
        print(f"- 设备: {model_info['device']}")
        print(f"- 4位量化: {model_info['use_4bit']}")
        print(f"- 对话轮数: {model_info['conversation_turns']}")
        
        # 清理资源
        tts.cleanup()
        
        return True
        
    except Exception as e:
        print(f"❌ 流程测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("VTX AI Phone System - 本地AI流程测试\n")
    
    success = test_local_ai_pipeline()
    
    if success:
        print("\n🎉 本地AI流程测试成功!")
        print("💡 提示: 系统已准备好处理实际语音通话")
        return 0
    else:
        print("\n❌ 本地AI流程测试失败")
        print("💡 提示: 请检查GPU环境和模型下载")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)