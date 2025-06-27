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

class AIConversationManager:
    """AI对话管理器 - 优化版"""
    
    def __init__(self):
        # 加载API密钥
        self.openai_api_key = self._load_api_key("openai.key")
        self.deepgram_api_key = self._load_api_key("deepgram.key")
        self.elevenlabs_api_key = self._load_api_key("elevenlabs.key")
        
        # 对话状态
        self.is_conversing = False
        self.conversation_history = []
        self.audio_queue = queue.Queue()
        
        # 回调函数
        self.audio_callback = None
        
        # 语音检测参数 - 简化版本
        self.silence_threshold = 1.0  # 静音检测阈值（秒）
        self.min_audio_length = 0.5   # 最小音频长度（秒）
        self.last_speech_time = 0     # 上次说话时间
        
        # 音频缓冲区
        self.audio_buffer = b""
        self.is_processing = False
        
        print("🤖 Aiker AI对话管理器初始化完成")
        print(f"✅ OpenAI API: {'已配置' if self.openai_api_key else '未配置'}")
        print(f"✅ Deepgram API: {'已配置' if self.deepgram_api_key else '未配置'}")
        print(f"✅ ElevenLabs API: {'已配置' if self.elevenlabs_api_key else '未配置'}")
    
    def _load_api_key(self, filename: str) -> str:
        """加载API密钥"""
        try:
            with open(f"api_keys/{filename}", "r") as f:
                return f.read().strip()
        except:
            return ""
    
    def set_audio_callback(self, callback: Callable):
        """设置音频回调函数"""
        self.audio_callback = callback
    
    def start_conversation(self):
        """开始对话"""
        self.is_conversing = True
        self.conversation_history = []
        print("🎤 开始Aiker AI对话...")
        
        # 发送欢迎语
        welcome_text = "您好！我是Aiker，您的AI助手。很高兴为您服务，请告诉我您需要什么帮助？"
        self._process_ai_response(welcome_text)
    
    def stop_conversation(self):
        """停止对话"""
        self.is_conversing = False
        print("🔇 停止Aiker AI对话")
    
    def process_audio_input(self, audio_data: bytes):
        """处理音频输入（从RTP接收）- 简化版本"""
        if not self.is_conversing:
            return
        
        # 将音频数据添加到缓冲区
        self.audio_buffer += audio_data
        self.last_speech_time = time.time()
        
        # 检查音频长度
        audio_duration = len(self.audio_buffer) / 8000  # 8kHz采样率
        
        # 如果音频长度足够，放入队列等待处理
        if audio_duration >= 2.0:  # 收集2秒音频
            if not self.audio_queue.full():
                self.audio_queue.put(self.audio_buffer)
                self.audio_buffer = b""
    
    def _process_audio_buffer(self):
        """处理音频缓冲区"""
        if self.is_processing:
            return
        
        self.is_processing = True
        
        try:
            # 从队列获取音频数据
            audio_data = self.audio_queue.get_nowait()
            
            # 语音转文本
            text = self._speech_to_text(audio_data)
            if text and len(text.strip()) > 0:
                print(f"👤 用户说: {text}")
                
                # 获取AI回复
                ai_response = self._get_ai_response(text)
                
                # 处理AI回复
                self._process_ai_response(ai_response)
            
        except queue.Empty:
            pass
        except Exception as e:
            print(f"❌ 音频处理错误: {e}")
        finally:
            self.is_processing = False
    
    def _process_ai_response(self, text: str):
        """处理AI回复文本"""
        if not self.audio_callback:
            return
        
        print(f"🤖 Aiker回复: {text}")
        
        # 生成语音
        audio_data = self._text_to_speech(text)
        if audio_data:
            # 通过回调发送音频
            self.audio_callback(audio_data)
    
    def _text_to_speech(self, text: str) -> Optional[bytes]:
        """文本转语音"""
        try:
            # 使用ElevenLabs TTS - 使用更好的中文女声
            return self._elevenlabs_tts(text)
        except Exception as e:
            print(f"❌ TTS失败: {e}")
            return None
    
    def _elevenlabs_tts(self, text: str) -> Optional[bytes]:
        """ElevenLabs TTS - 使用Sarah中文女声"""
        try:
            import requests
            
            # 使用Sarah - 年轻女声，支持中文
            url = "https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",  # 使用多语言模型
                "voice_settings": {
                    "stability": 0.6,        # 稳定性
                    "similarity_boost": 0.7,  # 相似度
                    "style": 0.2,            # 风格
                    "use_speaker_boost": True # 说话者增强
                }
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                # 将MP3转换为μ-law格式
                return self._convert_mp3_to_ulaw(response.content)
            else:
                print(f"❌ ElevenLabs TTS错误: {response.status_code}")
                # 尝试备用模型
                return self._elevenlabs_tts_fallback(text)
                
        except Exception as e:
            print(f"❌ ElevenLabs TTS异常: {e}")
            return self._elevenlabs_tts_fallback(text)
    
    def _elevenlabs_tts_fallback(self, text: str) -> Optional[bytes]:
        """ElevenLabs TTS备用方案 - 使用Aria"""
        try:
            import requests
            
            # 使用Aria - 另一个中文女声
            url = "https://api.elevenlabs.io/v1/text-to-speech/9BWtsMINqrJLrRacOk9x"
            
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
                    "similarity_boost": 0.7
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
    
    def _speech_to_text(self, audio_data: bytes) -> Optional[str]:
        """语音转文本 - 优化版本"""
        try:
            # 使用Deepgram STT - 优化参数
            return self._deepgram_stt(audio_data)
        except Exception as e:
            print(f"❌ STT失败: {e}")
            return None
    
    def _deepgram_stt(self, audio_data: bytes) -> Optional[str]:
        """Deepgram STT - 优化参数提高精确度"""
        try:
            import requests
            
            # 优化STT参数
            url = "https://api.deepgram.com/v1/listen"
            
            params = {
                "model": "nova-2",           # 使用最新的Nova-2模型
                "language": "zh-CN",         # 中文识别
                "encoding": "mulaw",         # μ-law编码
                "sample_rate": "8000",       # 8kHz采样率
                "punctuate": "true",         # 添加标点符号
                "utterances": "true",        # 启用话语检测
                "diarize": "false",          # 不进行说话者分离
                "smart_format": "true",      # 智能格式化
                "filler_words": "false",     # 过滤填充词
                "profanity_filter": "false", # 不过滤脏话
                "numerals": "true",          # 数字识别
                "search": "",                # 无搜索词
                "replace": "",               # 无替换词
                "keywords": "",              # 无关键词
                "interim_results": "false",  # 不需要中间结果
                "endpointing": "true",       # 启用端点检测
                "vad_turnoff": "500"         # VAD关闭阈值
            }
            
            headers = {
                "Authorization": f"Token {self.deepgram_api_key}",
                "Content-Type": "audio/mulaw"
            }
            
            response = requests.post(url, params=params, data=audio_data, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                transcript = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
                return transcript.strip()
            else:
                print(f"❌ Deepgram STT错误: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Deepgram STT异常: {e}")
            return None
    
    def _get_ai_response(self, user_text: str) -> str:
        """获取AI回复 - 优化Aiker身份"""
        try:
            import requests
            
            url = "https://api.openai.com/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            # 构建对话历史
            messages = [
                {
                    "role": "system", 
                    "content": "你是Aiker，一个友好、专业的AI助手。请用自然、流畅的中文回复用户，保持对话的连贯性和友好性。你的回复应该简洁明了，但要有帮助性。记住你的名字是Aiker。"
                }
            ]
            
            # 添加历史对话
            for msg in self.conversation_history[-4:]:  # 保留最近4轮对话
                messages.append(msg)
            
            # 添加当前用户输入
            messages.append({"role": "user", "content": user_text})
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": messages,
                "max_tokens": 200,        # 增加回复长度
                "temperature": 0.8,       # 提高创造性
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
        """启动音频处理线程"""
        def audio_processor():
            while self.is_conversing:
                # 处理队列中的音频数据
                if not self.audio_queue.empty():
                    self._process_audio_buffer()
                
                time.sleep(0.1)  # 100ms检查间隔
        
        thread = threading.Thread(target=audio_processor, daemon=True)
        thread.start()
        return thread 