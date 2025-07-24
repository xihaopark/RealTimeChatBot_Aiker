#!/usr/bin/env python3
"""
VTX AI Phone System V2 性能测试脚本
测试新架构的性能和稳定性
"""

import time
import threading
import logging
import json
import statistics
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'aiker_v2'))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PerformanceTestSuite:
    """性能测试套件"""
    
    def __init__(self):
        self.results = {}
        
    def test_tts_performance(self, iterations: int = 10) -> Dict[str, Any]:
        """测试TTS性能"""
        logger.info(f"🎵 Testing TTS performance ({iterations} iterations)...")
        
        try:
            from tts_service import PiperTTSService
            
            tts = PiperTTSService()
            if not tts.is_available():
                return {"error": "TTS service not available"}
            
            # 测试用例
            test_texts = [
                "您好，欢迎致电OneSuite客服中心。",
                "请问有什么可以帮助您的吗？",
                "感谢您的来电，祝您生活愉快。",
                "Hello, welcome to OneSuite customer service.",
                "How may I assist you today?"
            ]
            
            timings = []
            char_counts = []
            
            for i in range(iterations):
                text = test_texts[i % len(test_texts)]
                char_counts.append(len(text))
                
                start_time = time.time()
                audio_data = tts.synthesize_for_rtp(text, 'zh' if i % 2 == 0 else 'en')
                end_time = time.time()
                
                if audio_data:
                    timings.append(end_time - start_time)
                else:
                    logger.warning(f"TTS failed for iteration {i}")
            
            if not timings:
                return {"error": "All TTS attempts failed"}
            
            # 计算性能指标
            avg_time = statistics.mean(timings)
            avg_chars = statistics.mean(char_counts)
            chars_per_second = avg_chars / avg_time
            
            result = {
                "service": "Piper TTS",
                "iterations": len(timings),
                "avg_time_seconds": round(avg_time, 3),
                "min_time_seconds": round(min(timings), 3),
                "max_time_seconds": round(max(timings), 3),
                "chars_per_second": round(chars_per_second, 1),
                "success_rate": len(timings) / iterations
            }
            
            logger.info(f"✅ TTS Performance: {avg_time:.3f}s avg, {chars_per_second:.1f} chars/s")
            return result
            
        except Exception as e:
            logger.error(f"TTS test failed: {e}")
            return {"error": str(e)}
    
    def test_stt_performance(self, iterations: int = 5) -> Dict[str, Any]:
        """测试STT性能"""
        logger.info(f"🎤 Testing STT performance ({iterations} iterations)...")
        
        try:
            from stt_service import VoskSTTService
            
            stt = VoskSTTService()
            if not stt.is_available():
                return {"error": "STT service not available"}
            
            # 创建测试音频数据 (模拟PCM音频)
            import numpy as np
            
            sample_rate = 8000
            duration = 2.0  # 2秒音频
            samples = int(sample_rate * duration)
            
            # 生成测试音频 (正弦波)
            frequency = 440  # A4音符
            t = np.linspace(0, duration, samples, False)
            audio_wave = np.sin(frequency * 2 * np.pi * t)
            audio_pcm = (audio_wave * 32767).astype(np.int16).tobytes()
            
            timings = []
            success_count = 0
            
            for i in range(iterations):
                start_time = time.time()
                
                # 模拟音频块处理
                chunk_size = 1600  # 0.1秒的音频块
                for j in range(0, len(audio_pcm), chunk_size):
                    chunk = audio_pcm[j:j+chunk_size]
                    result = stt.process_audio_chunk(chunk, 'zh')
                    if result:
                        success_count += 1
                        break
                
                end_time = time.time()
                timings.append(end_time - start_time)
            
            avg_time = statistics.mean(timings)
            
            result = {
                "service": "Vosk STT",
                "iterations": iterations,
                "avg_time_seconds": round(avg_time, 3),
                "min_time_seconds": round(min(timings), 3),
                "max_time_seconds": round(max(timings), 3),
                "success_rate": success_count / iterations,
                "audio_duration": duration
            }
            
            logger.info(f"✅ STT Performance: {avg_time:.3f}s avg processing time")
            return result
            
        except Exception as e:
            logger.error(f"STT test failed: {e}")
            return {"error": str(e)}
    
    def test_llm_performance(self, iterations: int = 10) -> Dict[str, Any]:
        """测试LLM性能"""
        logger.info(f"🧠 Testing LLM performance ({iterations} iterations)...")
        
        try:
            from llm_service import LlamaCppLLMService
            
            llm = LlamaCppLLMService()
            if not llm.is_available():
                return {"error": "LLM service not available"}
            
            # 测试问题
            test_questions = [
                "你好，请介绍一下你们的服务。",
                "营业时间是什么时候？",
                "如何联系技术支持？",
                "产品价格是多少？",
                "可以退换货吗？"
            ]
            
            timings = []
            token_counts = []
            success_count = 0
            
            for i in range(iterations):
                question = test_questions[i % len(test_questions)]
                conversation_id = f"test_{i}"
                
                start_time = time.time()
                response = llm.generate_response(question, conversation_id)
                end_time = time.time()
                
                if response and "抱歉" not in response:
                    success_count += 1
                    timings.append(end_time - start_time)
                    token_counts.append(len(response))
                else:
                    logger.warning(f"LLM failed for iteration {i}")
            
            if not timings:
                return {"error": "All LLM attempts failed"}
            
            avg_time = statistics.mean(timings)
            avg_tokens = statistics.mean(token_counts)
            tokens_per_second = avg_tokens / avg_time
            
            result = {
                "service": "Llama.cpp LLM",
                "iterations": len(timings),
                "avg_time_seconds": round(avg_time, 3),
                "min_time_seconds": round(min(timings), 3),
                "max_time_seconds": round(max(timings), 3),
                "tokens_per_second": round(tokens_per_second, 1),
                "avg_response_length": round(avg_tokens, 1),
                "success_rate": success_count / iterations
            }
            
            logger.info(f"✅ LLM Performance: {avg_time:.3f}s avg, {tokens_per_second:.1f} tokens/s")
            return result
            
        except Exception as e:
            logger.error(f"LLM test failed: {e}")
            return {"error": str(e)}
    
    def test_concurrent_load(self, concurrent_calls: int = 5, duration: int = 30) -> Dict[str, Any]:
        """测试并发负载"""
        logger.info(f"⚡ Testing concurrent load ({concurrent_calls} calls for {duration}s)...")
        
        def simulate_call(call_id: int) -> Dict[str, Any]:
            """模拟单个通话"""
            start_time = time.time()
            
            try:
                from tts_service import PiperTTSService
                from llm_service import LlamaCppLLMService
                
                tts = PiperTTSService()
                llm = LlamaCppLLMService()
                
                operations = 0
                errors = 0
                
                end_time = start_time + duration
                
                while time.time() < end_time:
                    try:
                        # 模拟对话流程
                        question = f"这是第{operations + 1}个问题"
                        response = llm.generate_response(question, f"load_test_{call_id}")
                        
                        if response:
                            audio = tts.synthesize_for_rtp(response, 'zh')
                            if audio:
                                operations += 1
                            else:
                                errors += 1
                        else:
                            errors += 1
                        
                        # 模拟通话间隔
                        time.sleep(1)
                        
                    except Exception as e:
                        errors += 1
                        logger.debug(f"Call {call_id} error: {e}")
                
                actual_duration = time.time() - start_time
                
                return {
                    "call_id": call_id,
                    "operations": operations,
                    "errors": errors,
                    "duration": actual_duration,
                    "ops_per_second": operations / actual_duration if actual_duration > 0 else 0
                }
                
            except Exception as e:
                return {
                    "call_id": call_id,
                    "error": str(e)
                }
        
        # 并发执行
        with ThreadPoolExecutor(max_workers=concurrent_calls) as executor:
            futures = [executor.submit(simulate_call, i) for i in range(concurrent_calls)]
            call_results = [future.result() for future in futures]
        
        # 统计结果
        successful_calls = [r for r in call_results if "error" not in r]
        total_operations = sum(r.get("operations", 0) for r in successful_calls)
        total_errors = sum(r.get("errors", 0) for r in successful_calls)
        
        if successful_calls:
            avg_ops_per_second = statistics.mean([r["ops_per_second"] for r in successful_calls])
        else:
            avg_ops_per_second = 0
        
        result = {
            "concurrent_calls": concurrent_calls,
            "duration_seconds": duration,
            "successful_calls": len(successful_calls),
            "total_operations": total_operations,
            "total_errors": total_errors,
            "avg_ops_per_second": round(avg_ops_per_second, 2),
            "success_rate": len(successful_calls) / concurrent_calls
        }
        
        logger.info(f"✅ Concurrent Load: {len(successful_calls)}/{concurrent_calls} calls successful")
        return result
    
    def test_memory_usage(self) -> Dict[str, Any]:
        """测试内存使用情况"""
        logger.info("💾 Testing memory usage...")
        
        try:
            import psutil
            
            process = psutil.Process()
            
            # 获取当前内存使用
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            
            # 获取系统内存信息
            system_memory = psutil.virtual_memory()
            
            result = {
                "process_memory_mb": round(memory_info.rss / 1024 / 1024, 1),
                "process_memory_percent": round(memory_percent, 1),
                "system_memory_total_gb": round(system_memory.total / 1024 / 1024 / 1024, 1),
                "system_memory_available_gb": round(system_memory.available / 1024 / 1024 / 1024, 1),
                "system_memory_percent": system_memory.percent
            }
            
            logger.info(f"✅ Memory Usage: {result['process_memory_mb']}MB ({result['process_memory_percent']}%)")
            return result
            
        except Exception as e:
            logger.error(f"Memory test failed: {e}")
            return {"error": str(e)}
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有性能测试"""
        logger.info("🚀 Starting comprehensive performance tests...")
        
        start_time = time.time()
        
        self.results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tests": {}
        }
        
        # 依次执行各项测试
        test_functions = [
            ("memory_usage", self.test_memory_usage),
            ("tts_performance", self.test_tts_performance),
            ("stt_performance", self.test_stt_performance),
            ("llm_performance", self.test_llm_performance),
            ("concurrent_load", lambda: self.test_concurrent_load(3, 15))  # 减少测试时间
        ]
        
        for test_name, test_func in test_functions:
            logger.info(f"\n--- Running {test_name} test ---")
            try:
                self.results["tests"][test_name] = test_func()
            except Exception as e:
                logger.error(f"Test {test_name} failed: {e}")
                self.results["tests"][test_name] = {"error": str(e)}
        
        total_time = time.time() - start_time
        self.results["total_test_time"] = round(total_time, 2)
        
        logger.info(f"\n✅ All tests completed in {total_time:.2f}s")
        return self.results
    
    def save_results(self, filename: str = None):
        """保存测试结果"""
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"performance_test_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📊 Test results saved to {filename}")
    
    def print_summary(self):
        """打印测试摘要"""
        if not self.results:
            logger.warning("No test results available")
            return
        
        print("\n" + "="*60)
        print("🏆 VTX AI Phone System V2 Performance Test Summary")
        print("="*60)
        
        tests = self.results.get("tests", {})
        
        for test_name, result in tests.items():
            if "error" in result:
                print(f"❌ {test_name}: {result['error']}")
            else:
                print(f"✅ {test_name}:")
                
                if test_name == "tts_performance":
                    print(f"   Average time: {result.get('avg_time_seconds', 'N/A')}s")
                    print(f"   Speed: {result.get('chars_per_second', 'N/A')} chars/s")
                    
                elif test_name == "llm_performance":
                    print(f"   Average time: {result.get('avg_time_seconds', 'N/A')}s")
                    print(f"   Speed: {result.get('tokens_per_second', 'N/A')} tokens/s")
                    
                elif test_name == "concurrent_load":
                    print(f"   Successful calls: {result.get('successful_calls', 'N/A')}")
                    print(f"   Operations/second: {result.get('avg_ops_per_second', 'N/A')}")
                    
                elif test_name == "memory_usage":
                    print(f"   Process memory: {result.get('process_memory_mb', 'N/A')}MB")
                    print(f"   System memory: {result.get('system_memory_percent', 'N/A')}%")
        
        print(f"\nTotal test time: {self.results.get('total_test_time', 'N/A')}s")
        print("="*60)


def main():
    """主函数"""
    print("🧪 VTX AI Phone System V2 Performance Testing")
    print("This will test TTS, STT, LLM, and concurrent performance.")
    print()
    
    # 创建测试套件
    test_suite = PerformanceTestSuite()
    
    try:
        # 运行所有测试
        results = test_suite.run_all_tests()
        
        # 保存结果
        test_suite.save_results()
        
        # 打印摘要
        test_suite.print_summary()
        
    except KeyboardInterrupt:
        logger.info("Testing interrupted by user")
    except Exception as e:
        logger.error(f"Testing failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())