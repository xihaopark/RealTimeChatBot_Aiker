#!/usr/bin/env python3
"""
预生成欢迎语音文件
避免每次接电话时都要重新调用TTS API
"""

import os
import sys
import requests
import subprocess
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config.settings import settings

class WelcomeAudioGenerator:
    def __init__(self):
        # ElevenLabs配置
        self.elevenlabs_api_key = self._load_api_key("elevenlabs")
        if not self.elevenlabs_api_key:
            raise ValueError("❌ 未找到 ElevenLabs API密钥")
        
        # 语音ID配置
        self.primary_voice_id = "JBFqnCBsd6RMkjVDRZzb"  # Anna Su - 中文女声
        self.backup_voice_id = "EXAVITQu4vr4xnSDxMaL"   # Sarah - 英文女声
        
        # 输出目录
        self.audio_dir = Path("audio")
        self.audio_dir.mkdir(exist_ok=True)
        
        print("🎵 欢迎语音生成器初始化完成")
        print(f"📁 输出目录: {self.audio_dir}")
    
    def _load_api_key(self, service: str) -> str | None:
        """从api_keys文件夹加载API密钥"""
        try:
            # 先尝试从环境变量获取
            env_key = f"{service.upper()}_API_KEY"
            api_key = os.getenv(env_key)
            if api_key:
                print(f"✅ 从环境变量加载 {service} API密钥")
                return api_key
            
            # 从文件加载
            key_file = f"api_keys/{service}.key"
            if os.path.exists(key_file):
                with open(key_file, 'r') as f:
                    api_key = f.read().strip()
                if api_key:
                    print(f"✅ 从文件加载 {service} API密钥: {key_file}")
                    return api_key
            
            print(f"❌ 未找到 {service} API密钥")
            return None
            
        except Exception as e:
            print(f"❌ 加载 {service} API密钥失败: {e}")
            return None
    
    def generate_welcome_audio(self):
        """生成欢迎语音文件"""
        
        # 欢迎语文本
        welcome_text = "您好！我是Aiker，OneSuite Business的专业客服助手。我们提供最实惠的虚拟电话系统，包括虚拟PBX、短信服务、自动接待员等功能。请问您想了解我们公司的哪些服务？"
        
        print("🎤 开始生成欢迎语音...")
        print(f"📝 文本: {welcome_text}")
        
        # 生成中文欢迎语音
        chinese_audio = self._generate_tts(welcome_text, self.primary_voice_id, "chinese")
        if chinese_audio:
            self._save_audio_file(chinese_audio, "welcome_chinese.mp3")
            
            # 转换为μ-law格式
            self._convert_to_ulaw("welcome_chinese.mp3", "welcome_chinese.ulaw")
            print("✅ 中文欢迎语音生成完成")
        
        # 生成英文备用欢迎语音
        english_text = "Hello! I'm Aiker, your professional customer service assistant from OneSuite Business. We provide the most affordable virtual phone system solutions, including virtual PBX, SMS services, and auto attendant features. How can I help you today?"
        
        english_audio = self._generate_tts(english_text, self.backup_voice_id, "english")
        if english_audio:
            self._save_audio_file(english_audio, "welcome_english.mp3")
            
            # 转换为μ-law格式
            self._convert_to_ulaw("welcome_english.mp3", "welcome_english.ulaw")
            print("✅ 英文欢迎语音生成完成")
        
        print("🎉 所有欢迎语音文件生成完成！")
    
    def _generate_tts(self, text: str, voice_id: str, language: str) -> bytes | None:
        """使用ElevenLabs生成TTS"""
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_api_key
            }
            
            # 针对不同语言优化参数
            if language == "chinese":
                voice_settings = {
                    "stability": 0.5,
                    "similarity_boost": 0.8,
                    "style": 0.3,
                    "use_speaker_boost": True
                }
            else:
                voice_settings = {
                    "stability": 0.6,
                    "similarity_boost": 0.9,
                    "style": 0.2,
                    "use_speaker_boost": True
                }
            
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": voice_settings
            }
            
            print(f"📡 调用ElevenLabs API ({language})...")
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                print(f"✅ TTS生成成功 ({language}): {len(response.content)} 字节")
                return response.content
            else:
                print(f"❌ TTS生成失败 ({language}): {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ TTS生成异常 ({language}): {e}")
            return None
    
    def _save_audio_file(self, audio_data: bytes, filename: str):
        """保存音频文件"""
        try:
            file_path = self.audio_dir / filename
            with open(file_path, 'wb') as f:
                f.write(audio_data)
            print(f"💾 音频文件已保存: {file_path}")
        except Exception as e:
            print(f"❌ 保存音频文件失败: {e}")
    
    def _convert_to_ulaw(self, mp3_file: str, ulaw_file: str):
        """将MP3转换为μ-law格式"""
        try:
            mp3_path = self.audio_dir / mp3_file
            ulaw_path = self.audio_dir / ulaw_file
            
            # 使用ffmpeg转换
            cmd = [
                'ffmpeg', '-y',
                '-i', str(mp3_path),
                '-ar', '8000',           # 8kHz采样率
                '-ac', '1',              # 单声道
                '-acodec', 'pcm_mulaw',  # μ-law编码
                '-f', 'mulaw',           # μ-law格式
                str(ulaw_path)
            ]
            
            print(f"🔄 转换音频格式: {mp3_file} -> {ulaw_file}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ 音频转换成功: {ulaw_path}")
                # 获取文件大小信息
                size = os.path.getsize(ulaw_path)
                duration = size / 8000  # 8kHz采样率
                print(f"📊 文件大小: {size} 字节, 时长: {duration:.2f} 秒")
            else:
                print(f"❌ 音频转换失败: {result.stderr}")
                
        except Exception as e:
            print(f"❌ 音频转换异常: {e}")
    
    def generate_common_responses(self):
        """生成常用回复语音"""
        common_responses = {
            "thinking": "请稍等，让我为您查询一下...",
            "repeat": "抱歉，我没有听清楚，您能再说一遍吗？",
            "goodbye": "感谢您的咨询，再见！",
            "transfer": "我为您转接到人工客服，请稍等...",
            "error": "抱歉，系统出现了一些问题，请稍后再试。"
        }
        
        print("🎵 生成常用回复语音...")
        
        for key, text in common_responses.items():
            print(f"📝 生成: {key} - {text}")
            
            # 生成TTS
            audio_data = self._generate_tts(text, self.primary_voice_id, "chinese")
            if audio_data:
                # 保存MP3
                mp3_filename = f"response_{key}.mp3"
                self._save_audio_file(audio_data, mp3_filename)
                
                # 转换为μ-law
                ulaw_filename = f"response_{key}.ulaw"
                self._convert_to_ulaw(mp3_filename, ulaw_filename)
        
        print("✅ 常用回复语音生成完成")

def main():
    """主函数"""
    print("🎵 VTX AI Phone System - 欢迎语音生成器")
    print("=" * 50)
    
    try:
        generator = WelcomeAudioGenerator()
        
        # 生成欢迎语音
        generator.generate_welcome_audio()
        
        # 生成常用回复
        generator.generate_common_responses()
        
        print("\n🎉 所有音频文件生成完成！")
        print("📁 文件位置: ./audio/")
        print("💡 现在可以启动AI电话系统，将使用预生成的音频文件")
        
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 