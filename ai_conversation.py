#!/usr/bin/env python3
"""
AI对话模块 - 集成STT、LLM、TTS实现智能语音对话
优化版本：提高识别精度、使用更好TTS、等待用户说完话
"""

import asyncio
import json
import time
import threading
import queue
import websockets
import aiohttp
import numpy as np
from typing import Optional, Callable
import os
import requests

class AIConversationManager:
    """AI对话管理器 - 优化版"""
    
    def __init__(self):
        # 加载API密钥
        self.openai_api_key = self._load_api_key("api_keys/openai.key")
        self.deepgram_api_key = self._load_api_key("api_keys/deepgram.key")
        self.elevenlabs_api_key = self._load_api_key("api_keys/elevenlabs.key")
        
        # 加载OneSuite Business业务数据
        self.onesuite_data = self._load_onesuite_data("onesuite-business-data.json")
        print(f"✅ OneSuite Business 数据加载完成")
        
        # 对话状态
        self.is_conversing = False
        self.conversation_history = []
        self.audio_queue = queue.Queue()
        self.audio_buffer = b""
        self.last_speech_time = 0
        self.silence_threshold = 1.5  # 1.5秒静音检测
        
        # 音频回调函数
        self.audio_callback = None
        
        # 智能音频处理参数
        self.min_audio_length = 2.0  # 最小音频长度（秒）
        self.max_audio_length = 10.0  # 最大音频长度（秒）
        self.is_processing_audio = False  # 防止重复处理
        
        # TTS语音配置 - Anna Su作为主要语音，英文语音作为备用
        self.primary_voice_id = "9lHjugDhwqoxA5MhX0az"  # Anna Su - Casual & Friendly (中文)
        self.fallback_voice_id = "EXAVITQu4vr4xnSDxMaL"  # Sarah - 英文女声 (备用)
        
        print("🤖 Aiker AI对话管理器初始化完成")
        print(f"✅ OpenAI API: {'已配置' if self.openai_api_key else '未配置'}")
        print(f"✅ Deepgram API: {'已配置' if self.deepgram_api_key else '未配置'}")
        print(f"✅ ElevenLabs API: {'已配置' if self.elevenlabs_api_key else '未配置'}")
        print(f"🎭 主要语音: Anna Su (中文)")
        print(f"🎭 备用语音: Sarah (英文)")
    
    def _load_api_key(self, filename: str) -> str:
        """加载API密钥"""
        try:
            with open(filename, "r") as f:
                return f.read().strip()
        except Exception as e:
            print(f"❌ 加载API密钥失败 {filename}: {e}")
            return ""
    
    def _load_onesuite_data(self, filename: str) -> dict:
        """加载业务数据JSON文件"""
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载业务数据失败: {e}")
            return {}
    
    def set_audio_callback(self, callback: Callable):
        """设置音频回调函数"""
        self.audio_callback = callback
    
    def start_conversation(self):
        """开始AI对话"""
        self.is_conversing = True
        self.conversation_history = []
        self.audio_buffer = b""
        self.last_speech_time = time.time()
        
        # 启动音频处理线程
        self.audio_thread = self.start_audio_processing_thread()
        
        print("🎤 开始Aiker AI对话...")
        
        # 发送欢迎消息
        welcome_message = "您好！我是Aiker，OneSuite Business的专业客服助手。我们提供最实惠的虚拟电话系统，包括虚拟PBX、短信服务、自动接待员等功能。请问您想了解我们公司的哪些服务？"
        self._process_ai_response(welcome_message)
    
    def stop_conversation(self):
        """停止对话"""
        self.is_conversing = False
        print("🔇 AI对话已停止")
    
    def process_audio_input(self, audio_data: bytes):
        """处理输入的音频数据 - 智能句子完整性检测"""
        if not self.is_conversing or self.is_processing_audio:
            return
        
        # 添加到音频缓冲区
        self.audio_buffer += audio_data
        self.last_speech_time = time.time()
        
        # 计算当前音频长度
        audio_duration = len(self.audio_buffer) / 8000  # 8kHz采样率
        
        # 智能处理策略：
        # 1. 如果音频太短，继续收集
        # 2. 如果音频足够长且静音，处理
        # 3. 如果音频太长，强制处理
        if audio_duration >= self.min_audio_length:
            # 检查是否静音足够长（句子结束）
            if time.time() - self.last_speech_time > self.silence_threshold:
                self._process_complete_audio()
            # 如果音频太长，强制处理
            elif audio_duration >= self.max_audio_length:
                self._process_complete_audio()

    def _process_complete_audio(self):
        """处理完整的音频片段"""
        if self.is_processing_audio or len(self.audio_buffer) == 0:
            return
        
        self.is_processing_audio = True
        
        try:
            # 语音识别
            text = self._speech_to_text(self.audio_buffer)
            if text and len(text.strip()) > 0:
                print(f"👤 用户说: {text}")
                
                # 获取AI回复
                ai_response = self._get_ai_response(text)
                if ai_response:
                    self._process_ai_response(ai_response)
            
            # 清空缓冲区
            self.audio_buffer = b""
                    
        except Exception as e:
            print(f"❌ 音频处理错误: {e}")
        finally:
            self.is_processing_audio = False

    def _process_audio_buffer_immediate(self, audio_data: bytes):
        """立即处理音频缓冲区 - 不等待静音（备用方法）"""
        try:
            # 语音识别
            text = self._speech_to_text(audio_data)
            if text and len(text.strip()) > 0:
                print(f"👤 用户说: {text}")
                
                # 获取AI回复
                ai_response = self._get_ai_response(text)
                if ai_response:
                    self._process_ai_response(ai_response)
                    
        except Exception as e:
            print(f"❌ 音频处理错误: {e}")

    def _process_audio_buffer(self):
        """处理音频缓冲区 - 静音检测版本（备用）"""
        try:
            # 检查是否静音时间足够长
            if time.time() - self.last_speech_time > self.silence_threshold:
                if not self.audio_queue.empty():
                    audio_data = self.audio_queue.get()
                    self._process_audio_buffer_immediate(audio_data)
                            
        except Exception as e:
            print(f"❌ 音频处理错误: {e}")

    def _process_ai_response(self, text: str):
        """处理AI回复"""
        try:
            print(f"🤖 Aiker回复: {text}")
            
            # 文本转语音
            audio_data = self._text_to_speech(text)
            if audio_data and self.audio_callback:
                self.audio_callback(audio_data)
                
        except Exception as e:
            print(f"❌ AI回复处理错误: {e}")

    def _text_to_speech(self, text: str) -> Optional[bytes]:
        """文本转语音"""
        try:
            # 使用ElevenLabs TTS
            return self._elevenlabs_tts(text)
        except Exception as e:
            print(f"❌ TTS失败: {e}")
            return None

    def _elevenlabs_tts(self, text: str) -> Optional[bytes]:
        """ElevenLabs TTS - 使用Anna Su中文女声"""
        try:
            # 使用Anna Su - Casual & Friendly
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.primary_voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",  # 多语言模型支持中文
                "voice_settings": {
                    "stability": 0.5,        # 稳定性
                    "similarity_boost": 0.75, # 相似度
                    "style": 0.1,            # Casual & Friendly风格
                    "use_speaker_boost": True # 说话者增强
                }
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                # 将MP3转换为μ-law格式
                return self._convert_mp3_to_ulaw(response.content)
            else:
                print(f"❌ ElevenLabs TTS错误: {response.status_code}")
                # 尝试备用语音
                return self._elevenlabs_tts_fallback(text)
                
        except Exception as e:
            print(f"❌ ElevenLabs TTS异常: {e}")
            return self._elevenlabs_tts_fallback(text)
    
    def _elevenlabs_tts_fallback(self, text: str) -> Optional[bytes]:
        """ElevenLabs TTS备用方案 - 使用Sarah"""
        try:
            # 使用Sarah - 备用中文女声
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.fallback_voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.6,
                    "similarity_boost": 0.7,
                    "style": 0.2,
                    "use_speaker_boost": True
                }
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                return self._convert_mp3_to_ulaw(response.content)
            else:
                print(f"❌ 备用TTS也失败: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 备用TTS异常: {e}")
            return None
    
    def _convert_mp3_to_ulaw(self, mp3_data: bytes) -> bytes:
        """将MP3转换为μ-law格式"""
        try:
            import io
            from pydub import AudioSegment
            
            # 加载MP3
            audio = AudioSegment.from_mp3(io.BytesIO(mp3_data))
            
            # 转换为8kHz单声道
            audio = audio.set_frame_rate(8000).set_channels(1)
            
            # 转换为μ-law
            samples = np.array(audio.get_array_of_samples())
            ulaw_samples = self._linear_to_ulaw(samples)
            
            return bytes(ulaw_samples)
            
        except Exception as e:
            print(f"❌ 音频转换失败: {e}")
            return b""
    
    def _linear_to_ulaw(self, samples):
        """线性PCM转μ-law"""
        ulaw_samples = []
        for sample in samples:
            # 简化μ-law编码
            if sample < 0:
                sample = -sample
                sign = 0x80
            else:
                sign = 0
            
            if sample > 32635:
                sample = 32635
            
            sample += 132
            
            # 查找段
            seg = 0
            for i in range(8):
                if sample >= (128 << i):
                    seg = i
            
            # 计算底数
            if seg >= 8:
                uval = 0x7F
            else:
                uval = (seg << 4) | ((sample >> (seg + 3)) & 0x0F)
            
            ulaw_samples.append((sign | uval) ^ 0xFF)
        
        return ulaw_samples
    
    def _speech_to_text(self, audio_data: bytes) -> str:
        """语音转文字 - 使用Deepgram，已修复参数问题"""
        if not self.deepgram_api_key:
            print("❌ Deepgram API密钥未配置")
            return ""
        
        try:
            # 优化Deepgram参数，直接使用μ-law编码
            url = "https://api.deepgram.com/v1/listen"
            headers = {
                "Authorization": f"Token {self.deepgram_api_key}",
                "Content-Type": "audio/mulaw"  # 直接使用μ-law格式
            }
            
            # 优化参数配置 - 移除已弃用的vad_turnoff
            params = {
                "model": "nova-2",  # 使用最新的Nova-2模型
                "language": "zh-CN",  # 中文识别
                "encoding": "mulaw",  # 直接使用μ-law编码，无需转换
                "sample_rate": 8000,  # 采样率
                "punctuate": "true",  # 添加标点符号
                "utterances": "true",  # 启用话语检测
                "interim_results": "false",  # 只返回最终结果
                "endpointing": "500",  # ✅ 正确的端点检测参数
                "diarize": "false",  # 不需要说话人分离
                "smart_format": "true",  # 智能格式化
                "filler_words": "false",  # 过滤填充词
                "profanity_filter": "false"  # 不过滤敏感词
            }
            
            # 直接发送原始的μ-law音频数据，无需转换
            response = requests.post(url, headers=headers, params=params, data=audio_data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if "results" in result and "channels" in result["results"]:
                    transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
                    confidence = result["results"]["channels"][0]["alternatives"][0]["confidence"]
                    
                    # 只返回置信度较高的结果
                    if confidence > 0.3 and transcript.strip():
                        print(f"🎯 语音识别置信度: {confidence:.2f}")
                        return transcript.strip()
                    else:
                        print(f"⚠️ 语音识别置信度过低: {confidence:.2f}")
                        return ""
                else:
                    print("❌ 语音识别结果格式错误")
                    return ""
            else:
                print(f"❌ 语音识别请求失败: {response.status_code}")
                if response.status_code == 400:
                    print(f"🔍 错误详情: {response.text}")
                return ""
                
        except Exception as e:
            print(f"❌ 语音识别错误: {e}")
            return ""

    def _get_ai_response(self, user_text: str) -> str:
        """获取AI回复 - 智能分类和模糊匹配"""
        try:
            url = "https://api.openai.com/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            # 智能分类系统提示语
            system_prompt = (
                "你是 Aiker，OneSuite Business 公司的AI语音客服助手。"
                "你的任务是智能分类用户输入并给出合适的回复：\n\n"
                "1. **业务问题识别**：如果用户询问关于OneSuite Business公司的业务、服务、价格、功能等问题，使用专业客服模式回答。\n"
                "2. **普通聊天**：如果用户只是打招呼、闲聊或询问非业务问题，使用友好自然的聊天模式回答。\n"
                "3. **模糊匹配**：对于业务相关问题，即使不完全匹配，也要尝试找到最接近的信息回答。\n"
                "4. **回答策略**：\n"
                "   - 业务问题：先确认理解，再专业详细回答\n"
                "   - 普通聊天：自然友好，保持对话流畅\n"
                "   - 超出范围：礼貌说明无法回答\n\n"
                "记住：你的输入是用户通过电话说的文字，输出将通过TTS播放，所以回答要自然口语化。"
            )
            
            # 将业务数据整合进用户提问
            prompt_with_context = (
                f"背景知识（OneSuite Business公司信息）：\n"
                f"{json.dumps(self.onesuite_data, ensure_ascii=False, indent=2)}\n\n"
                f"用户输入：'{user_text}'\n\n"
                f"请分析用户输入：\n"
                f"1. 这是业务问题还是普通聊天？\n"
                f"2. 如果是业务问题，找到最相关的信息回答\n"
                f"3. 如果是普通聊天，自然友好回复\n"
                f"4. 如果完全超出范围，礼貌说明无法回答"
            )
            
            # 构建对话历史
            messages = [
                {
                    "role": "system", 
                    "content": system_prompt
                }
            ]
            
            # 添加历史对话
            for msg in self.conversation_history[-4:]:  # 保留最近4轮对话
                messages.append(msg)
            
            # 添加当前用户输入
            messages.append({"role": "user", "content": prompt_with_context})
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": messages,
                "max_tokens": 300,        # 增加回复长度
                "temperature": 0.7,       # 平衡创造性和一致性
                "top_p": 0.9,            # 控制回复多样性
                "frequency_penalty": 0.1, # 减少重复
                "presence_penalty": 0.1   # 鼓励新话题
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                ai_text = result["choices"][0]["message"]["content"].strip()
                
                # 更新对话历史
                self.conversation_history.append({"role": "user", "content": user_text})
                self.conversation_history.append({"role": "assistant", "content": ai_text})
                
                return ai_text
            else:
                print(f"❌ OpenAI API错误: {response.status_code}")
                return "抱歉，我现在无法回答您的问题。"
                
        except Exception as e:
            print(f"❌ OpenAI API异常: {e}")
            return "抱歉，系统出现了一些问题。"
    
    def start_audio_processing_thread(self):
        """启动音频处理线程 - 智能处理版本"""
        def audio_processor():
            while self.is_conversing:
                # 定期检查是否有需要处理的音频
                if len(self.audio_buffer) > 0:
                    audio_duration = len(self.audio_buffer) / 8000
                    # 如果音频足够长且静音，处理
                    if audio_duration >= self.min_audio_length and (time.time() - self.last_speech_time) > self.silence_threshold:
                        self._process_complete_audio()
                
                time.sleep(0.1)  # 100ms检查间隔
        
        thread = threading.Thread(target=audio_processor, daemon=True)
        thread.start()
        return thread 