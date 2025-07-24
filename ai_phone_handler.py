#!/usr/bin/env python3
"""
AI电话处理器 - 集成STT, LLM, TTS完整对话流
"""

import io
import wave
import threading
import queue
import time
import numpy as np
from typing import Optional, Callable

class AIPhoneHandler:
    """AI电话处理器 - 处理完整的语音对话流程"""
    
    def __init__(self):
        self.stt_service = None
        self.llm_service = None
        self.tts_service = None
        
        # 音频缓冲
        self.audio_buffer = queue.Queue()
        self.audio_samples = []
        self.sample_rate = 8000
        self.is_processing = False
        
        # 语音活动检测
        self.vad_threshold = 500  # 简单的音量阈值
        self.silence_duration = 1.5  # 1.5秒静音后处理
        self.last_audio_time = 0
        
        # 回调函数
        self.audio_callback = None
        
        # 处理线程
        self.processing_thread = None
        self.running = False
        
        # 对话状态显示
        self.conversation_state = "等待来电"
        self.last_activity_time = time.time()
        self.status_display_count = 0
        
    def initialize_ai_services(self):
        """初始化AI服务"""
        try:
            # 尝试导入本地AI服务
            from local_ai import LocalLLM, LocalTTS, LocalSTT
            
            print("🧠 初始化LLM服务...")
            self.llm_service = LocalLLM(
                model_name="Qwen/Qwen2.5-7B-Instruct",
                device="cuda",
                use_4bit=True
            )
            print("✅ LLM就绪")
            
            print("🗣️ 初始化TTS服务...")
            self.tts_service = LocalTTS()
            print("✅ TTS就绪")
            
            print("🎤 初始化STT服务...")
            self.stt_service = LocalSTT(
                model="small",  # 使用small模型平衡速度和准确度
                language="zh",
                device="cuda"
            )
            # 设置 STT 转录回调
            self.stt_service.set_transcription_callback(self._on_speech_recognized)
            self.stt_service.start_listening()
            print("✅ STT就绪")
            
            return True
            
        except Exception as e:
            print(f"❌ AI服务初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def set_audio_callback(self, callback: Callable):
        """设置音频输出回调"""
        self.audio_callback = callback
    
    def start(self):
        """启动AI处理器"""
        if not self.initialize_ai_services():
            return False
            
        self.running = True
        # 不再需要处理线程，使用实时STT回调
        
        print("🤖 AI电话处理器已启动")
        return True
    
    def stop(self):
        """停止AI处理器"""
        self.running = False
        if self.stt_service:
            self.stt_service.stop_listening()
        print("🤖 AI电话处理器已停止")
    
    def process_audio_chunk(self, audio_data: bytes, payload_type: int):
        """处理接收到的音频块"""
        try:
            # 将μ-law音频转换为PCM
            from working_sip_client import G711Codec
            pcm_data = G711Codec.mulaw_to_pcm(audio_data)
            
            # 转换为numpy数组用于处理
            samples = np.frombuffer(pcm_data, dtype=np.int16)
            
            # 简单的语音活动检测
            audio_level = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
            
            # 直接将音频数据发送给STT服务
            if self.stt_service:
                self.stt_service.feed_audio(audio_data)
            
            # 显示语音活动状态（减少日志）
            if audio_level > self.vad_threshold:
                if not self.is_processing and len(self.audio_samples) == 0:
                    self._update_conversation_state("🎤 正在听取语音...")
                # 积累音频数据用于备用处理
                self.audio_samples.extend(samples)
                self.last_audio_time = time.time()
                    
        except Exception as e:
            print(f"❌ 音频处理错误: {e}")
    
    def _process_accumulated_audio(self):
        """处理积累的音频数据"""
        if not self.audio_samples or self.is_processing:
            return
            
        self.is_processing = True
        
        try:
            # 将音频样本加入处理队列
            audio_array = np.array(self.audio_samples, dtype=np.int16)
            self.audio_buffer.put(audio_array)
            
            print(f"🎤 语音结束，处理 {len(self.audio_samples)} 个样本 ({len(self.audio_samples)/self.sample_rate:.1f}秒)")
            
            # 清空缓冲区
            self.audio_samples = []
            
        except Exception as e:
            print(f"❌ 音频积累处理错误: {e}")
        finally:
            self.is_processing = False
    
    # 不再需要循环处理，因为使用实时STT回调
    # def _processing_loop 已移除
    
    # 不再需要，因为使用实时STT回调
    # def _process_conversation 已移除
    
    def _on_speech_recognized(self, text: str):
        """语音识别回调函数"""
        try:
            if text and text.strip():
                self._update_conversation_state(f"🎤 用户: {text}")
                
                # 生成回复
                self._update_conversation_state("🧠 AI思考中...")
                response = self._generate_response(text)
                if response:
                    self._update_conversation_state(f"🤖 AI: {response}")
                    
                    # 文字转语音
                    self._update_conversation_state("🗣️ 正在合成语音...")
                    audio_response = self._text_to_speech(response)
                    if audio_response:
                        # 发送音频回复
                        self._send_audio_response(audio_response)
                        self._update_conversation_state("📞 等待用户说话...")
                        
        except Exception as e:
            print(f"❌ 语音识别回调错误: {e}")
    
    def _generate_response(self, user_text: str) -> Optional[str]:
        """生成LLM回复"""
        try:
            if not self.llm_service:
                # 使用默认回复
                return f"感谢您说'{user_text}'。我是OneSuite Business的AI助手，很高兴为您服务！"
            
            # 构建对话prompt
            prompt = f"""你是OneSuite Business的专业AI客服助手。你需要用中文回复。

用户说: "{user_text}"

请提供一个简短、专业、友好的中文回复（不超过25字）。只返回回复内容，不要其他解释。"""
            
            response = self.llm_service.generate_response(prompt)
            
            # 限制回复长度并清理格式
            response = response.strip()
            if len(response) > 40:
                response = response[:37] + "..."
                
            return response
            
        except Exception as e:
            print(f"❌ LLM生成错误: {e}")
            return "抱歉，我现在无法理解您的问题，请稍后再试。"
    
    def _text_to_speech(self, text: str) -> Optional[bytes]:
        """文字转语音"""
        try:
            if not self.tts_service:
                print("⚠️ TTS服务不可用，跳过语音合成")
                return None
                
            print(f"🗣️ 开始TTS合成: '{text}'")
            
            # 生成语音
            audio_data = self.tts_service.synthesize_text(text)
            
            if audio_data and len(audio_data) > 0:
                print(f"✅ TTS成功生成 {len(audio_data)} bytes μ-law音频")
                return audio_data
            else:
                print("❌ TTS未生成有效音频数据")
                return None
                
        except Exception as e:
            print(f"❌ TTS处理错误: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _send_audio_response(self, audio_data: bytes):
        """发送音频回复"""
        try:
            if not self.audio_callback:
                print("⚠️ 没有音频回调函数")
                return
                
            print(f"📫 开始发送音频: {len(audio_data)} bytes")
            
            # TTS已经返回了μ-law格式的数据，直接使用
            mulaw_data = audio_data
            
            # 分包发送 (每包160字节，20ms)
            chunk_size = 160
            packets_sent = 0
            
            for i in range(0, len(mulaw_data), chunk_size):
                chunk = mulaw_data[i:i+chunk_size]
                if len(chunk) == chunk_size:  # 只发送完整的包
                    self.audio_callback(chunk, payload_type=0)  # μ-law
                    packets_sent += 1
                    time.sleep(0.02)  # 20ms间隔
                elif len(chunk) > 0:  # 对于最后一个不完整的包，填充至160字节
                    padded_chunk = chunk + b'\x7f' * (chunk_size - len(chunk))  # 用静音值填充
                    self.audio_callback(padded_chunk, payload_type=0)
                    packets_sent += 1
                    time.sleep(0.02)
            
            print(f"✅ 音频发送完成: {packets_sent} 个 RTP 包")
            
        except Exception as e:
            print(f"❌ 音频发送错误: {e}")
            import traceback
            traceback.print_exc()
    
    def send_welcome_message(self):
        """发送欢迎消息"""
        welcome_text = "您好！欢迎致电OneSuite Business，我是您的AI助手，请问有什么可以帮助您的？"
        
        self._update_conversation_state("🎉 发送欢迎消息...")
        
        # 直接生成并发送欢迎语音
        audio_data = self._text_to_speech(welcome_text)
        if audio_data:
            self._send_audio_response(audio_data)
            self._update_conversation_state("📞 等待用户说话...")
        else:
            print("🤖 " + welcome_text)
            self._update_conversation_state("❌ 欢迎消息发送失败")
    
    def _update_conversation_state(self, new_state: str):
        """更新对话状态显示"""
        self.conversation_state = new_state
        self.last_activity_time = time.time()
        
        # 在同一行更新状态，避免刷屏
        print(f"\r💬 对话状态: {new_state}", end="", flush=True)
        
        # 如果状态是最终状态（用户说话或等待），则换行
        if "用户:" in new_state or "等待" in new_state:
            print()  # 换行