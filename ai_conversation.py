#!/usr/bin/env python3
"""
AI对话模块 - 集成STT、LLM、TTS实现智能语音对话
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
    """AI对话管理器"""
    
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
        
        print("🤖 AI对话管理器初始化完成")
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
        print("🎤 开始AI对话...")
        
        # 发送欢迎语
        welcome_text = "您好！我是VTX AI助手，很高兴为您服务。请告诉我您需要什么帮助？"
        self._process_ai_response(welcome_text)
    
    def stop_conversation(self):
        """停止对话"""
        self.is_conversing = False
        print("🔇 停止AI对话")
    
    def process_audio_input(self, audio_data: bytes):
        """处理音频输入（从RTP接收）"""
        if not self.is_conversing:
            return
        
        # 将音频数据放入队列
        self.audio_queue.put(audio_data)
    
    def _process_ai_response(self, text: str):
        """处理AI回复文本"""
        if not self.audio_callback:
            return
        
        print(f"🤖 AI回复: {text}")
        
        # 生成语音
        audio_data = self._text_to_speech(text)
        if audio_data:
            # 通过回调发送音频
            self.audio_callback(audio_data)
    
    def _text_to_speech(self, text: str) -> Optional[bytes]:
        """文本转语音"""
        try:
            # 使用ElevenLabs TTS
            return self._elevenlabs_tts(text)
        except Exception as e:
            print(f"❌ TTS失败: {e}")
            return None
    
    def _elevenlabs_tts(self, text: str) -> Optional[bytes]:
        """ElevenLabs TTS"""
        try:
            import requests
            
            url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                # 将MP3转换为μ-law格式
                return self._convert_mp3_to_ulaw(response.content)
            else:
                print(f"❌ ElevenLabs TTS错误: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ ElevenLabs TTS异常: {e}")
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
        """语音转文本"""
        try:
            # 使用Deepgram STT
            return self._deepgram_stt(audio_data)
        except Exception as e:
            print(f"❌ STT失败: {e}")
            return None
    
    def _deepgram_stt(self, audio_data: bytes) -> Optional[str]:
        """Deepgram STT"""
        try:
            import requests
            
            url = "https://api.deepgram.com/v1/listen?model=nova-2&language=zh-CN&encoding=mulaw&sample_rate=8000"
            
            headers = {
                "Authorization": f"Token {self.deepgram_api_key}",
                "Content-Type": "audio/mulaw"
            }
            
            response = requests.post(url, data=audio_data, headers=headers)
            
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
        """获取AI回复"""
        try:
            import requests
            
            url = "https://api.openai.com/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            # 构建对话历史
            messages = [
                {"role": "system", "content": "你是一个友好的AI助手，请用简洁、自然的中文回复用户。保持对话流畅，回答要实用。"}
            ]
            
            # 添加历史对话
            for msg in self.conversation_history[-4:]:  # 保留最近4轮对话
                messages.append(msg)
            
            # 添加当前用户输入
            messages.append({"role": "user", "content": user_text})
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": messages,
                "max_tokens": 150,
                "temperature": 0.7
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
    
    def process_audio_buffer(self):
        """处理音频缓冲区"""
        if not self.is_conversing:
            return
        
        # 收集音频数据
        audio_buffer = b""
        start_time = time.time()
        
        while time.time() - start_time < 2.0:  # 收集2秒音频
            try:
                audio_data = self.audio_queue.get_nowait()
                audio_buffer += audio_data
            except queue.Empty:
                time.sleep(0.1)
                continue
        
        if len(audio_buffer) > 0:
            # 语音转文本
            text = self._speech_to_text(audio_buffer)
            if text and len(text.strip()) > 0:
                print(f"👤 用户说: {text}")
                
                # 获取AI回复
                ai_response = self._get_ai_response(text)
                
                # 处理AI回复
                self._process_ai_response(ai_response)
    
    def start_audio_processing_thread(self):
        """启动音频处理线程"""
        def audio_processor():
            while self.is_conversing:
                self.process_audio_buffer()
                time.sleep(0.1)
        
        thread = threading.Thread(target=audio_processor, daemon=True)
        thread.start()
        return thread 