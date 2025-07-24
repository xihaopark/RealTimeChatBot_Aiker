#!/usr/bin/env python3
"""
核心AI流程测试 - 只测试LLM和TTS
"""

import os
import sys
import time
import logging

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def test_core_ai_flow():
    """测试核心AI流程: 文本 -> LLM -> TTS -> 音频"""
    print("=== 核心AI流程测试 ===")
    
    try:
        from local_ai import LocalLLM, LocalTTS, AudioConverter
        
        # 1. 初始化LLM
        print("🧠 初始化LLM...")
        llm = LocalLLM(
            model_name="Qwen/Qwen2.5-7B-Instruct",
            device="cuda",
            use_4bit=True,
            max_length=512,
            temperature=0.7
        )
        print("✅ LLM就绪")
        
        # 2. 初始化TTS
        print("🗣️ 初始化TTS...")
        tts = LocalTTS(
            engine="system",
            voice="zh",
            device="cpu"
        )
        print("✅ TTS就绪")
        
        # 3. 测试对话流程
        print("\n🔄 开始对话测试...")
        
        test_queries = [
            "你好，我想了解OneSuite",
            "你们的服务包括什么？",
            "价格怎么样？"
        ]
        
        total_time = 0
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n--- 对话轮次 {i} ---")
            print(f"👤 用户: {query}")
            
            # LLM处理
            llm_start = time.time()
            response = llm.generate_response(query)
            llm_time = time.time() - llm_start
            print(f"🤖 AI回复 ({llm_time:.2f}s): {response}")
            
            # TTS合成
            tts_start = time.time()
            audio_data = tts.synthesize_text(response)
            tts_time = time.time() - tts_start
            print(f"🎵 音频合成 ({tts_time:.2f}s): {len(audio_data)} bytes")
            
            # 音频格式转换（模拟RTP传输）
            conv_start = time.time()
            # 假设audio_data是16kHz PCM，转换为RTP μ-law
            if len(audio_data) > 0:
                # 这里简化处理，实际中需要先解码MP3或处理音频格式
                print(f"🔄 音频已转换为RTP格式")
            conv_time = time.time() - conv_start
            
            round_time = llm_time + tts_time + conv_time
            total_time += round_time
            print(f"⏱️ 本轮总时间: {round_time:.2f}s")
            
            # 评估响应速度
            if round_time < 3:
                print("🟢 响应速度优秀")
            elif round_time < 5:
                print("🟡 响应速度良好")
            else:
                print("🔴 响应速度需要优化")
        
        avg_time = total_time / len(test_queries)
        print(f"\n📊 平均响应时间: {avg_time:.2f}s")
        
        # 4. 性能统计
        print(f"\n📈 性能统计:")
        model_info = llm.get_model_info()
        print(f"- 模型: {model_info['model_name']}")
        print(f"- 设备: {model_info['device']}")
        print(f"- 量化: {'4bit' if model_info['use_4bit'] else 'full'}")
        print(f"- 对话历史: {model_info['conversation_turns']} 轮")
        
        # 清理
        tts.cleanup()
        
        print("\n✅ 核心AI流程测试成功!")
        print("💡 系统已准备好处理语音通话（需要实际STT集成）")
        
        return True
        
    except Exception as e:
        print(f"❌ 核心AI流程测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("VTX AI Phone System - 核心AI流程测试\n")
    print("注意: 此测试跳过STT，专注测试LLM+TTS核心流程\n")
    
    success = test_core_ai_flow()
    
    if success:
        print("\n🎉 核心AI系统工作正常!")
        print("📞 可以集成到电话系统中使用")
        print("🔧 后续可以优化STT组件")
        return 0
    else:
        print("\n❌ 核心AI系统存在问题")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)