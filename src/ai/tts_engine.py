"""
语音合成引擎 (Text-to-Speech)
使用 Edge-TTS 或 OpenAI TTS API
"""

import os
import asyncio
import queue
import threading
import tempfile
from typing import Optional, Callable, List
from dataclasses import dataclass
from enum import Enum
import numpy as np

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False
    print("⚠️ Edge-TTS 未安装")

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class TTSProvider(Enum):
    """TTS 提供商"""
    EDGE_TTS = "edge_tts"
    OPENAI = "openai"
    ELEVENLABS = "elevenlabs"


@dataclass
class TTSConfig:
    """TTS 配置"""
    provider: TTSProvider = TTSProvider.EDGE_TTS
    voice: str = "zh-CN-XiaoxiaoNeural"  # Edge-TTS 声音
    openai_voice: str = "alloy"  # OpenAI 声音: alloy, echo, fable, onyx, nova, shimmer
    speed: float = 1.0  # 语速
    pitch: float = 0.0  # 音调
    volume: float = 1.0  # 音量
    sample_rate: int = 16000  # 输出采样率
    api_key: Optional[str] = None  # OpenAI API 密钥


class TTSEngine:
    """语音合成引擎"""
    
    # Edge-TTS 中文语音列表
    CHINESE_VOICES = {
        "晓晓": "zh-CN-XiaoxiaoNeural",
        "云希": "zh-CN-YunxiNeural",
        "云健": "zh-CN-YunjianNeural",
        "晓伊": "zh-CN-XiaoyiNeural",
        "云扬": "zh-CN-YunyangNeural",
        "晓辰": "zh-CN-XiaochenNeural",
        "晓涵": "zh-CN-XiaohanNeural",
        "晓墨": "zh-CN-XiaomoNeural",
        "晓秋": "zh-CN-XiaoqiuNeural",
        "晓睿": "zh-CN-XiaoruiNeural",
        "晓双": "zh-CN-XiaoshuangNeural",
        "晓妍": "zh-CN-XiaoyanNeural",
        "云枫": "zh-CN-YunfengNeural",
        "云皓": "zh-CN-YunhaoNeural",
        "云夏": "zh-CN-YunxiaNeural",
        "云野": "zh-CN-YunyeNeural",
        "云泽": "zh-CN-YunzeNeural"
    }
    
    def __init__(self, config: Optional[TTSConfig] = None):
        """
        初始化 TTS 引擎
        
        Args:
            config: TTS 配置
        """
        self.config = config or TTSConfig()
        
        # 从API密钥管理器获取密钥
        from src.utils.api_keys import get_api_key
        
        if self.config.provider == TTSProvider.EDGE_TTS:
            # Edge-TTS (免费)
            print(f"🔊 TTS 引擎初始化: {self.config.provider.value}")
            print(f"   语音: {self.config.voice}")
            
        elif self.config.provider == TTSProvider.OPENAI:
            # OpenAI TTS
            api_key = self.config.api_key or get_api_key('openai')
            if not api_key or api_key.startswith('your_'):
                raise ValueError("未设置 OpenAI API 密钥")
            
            import openai
            openai.api_key = api_key
            self.openai_client = openai
            
            print(f"🔊 TTS 引擎初始化: {self.config.provider.value}")
            print(f"   语音: {self.config.openai_voice}")
            print(f"   API密钥: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else '***'}")
            
        elif self.config.provider == TTSProvider.ELEVENLABS:
            # ElevenLabs TTS
            api_key = self.config.api_key or get_api_key('elevenlabs')
            if not api_key or api_key.startswith('your_'):
                raise ValueError("未设置 ElevenLabs API 密钥")
            
            try:
                from elevenlabs import generate, set_api_key
                set_api_key(api_key)
                self.elevenlabs_api_key = api_key
                print(f"🔊 TTS 引擎初始化: {self.config.provider.value}")
                print(f"   API密钥: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else '***'}")
            except ImportError:
                raise RuntimeError("ElevenLabs 库未安装，请运行: pip install elevenlabs")
        
        # 任务队列
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        
        # 处理线程
        self.running = False
        self.process_thread = None
        
        # 事件循环
        self.loop = None
        
        # 回调
        self.on_audio_ready = None
    
    def start(self):
        """启动 TTS 引擎"""
        if self.running:
            return
        
        self.running = True
        self.process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self.process_thread.start()
        
        print("🔊 TTS 引擎已启动")
    
    def stop(self):
        """停止 TTS 引擎"""
        self.running = False
        if self.process_thread:
            self.process_thread.join(timeout=2)
        
        print("🔊 TTS 引擎已停止")
    
    def synthesize(self, text: str, priority: bool = False):
        """
        合成语音
        
        Args:
            text: 要合成的文本
            priority: 是否优先处理
        """
        if priority:
            # 清空队列
            while not self.task_queue.empty():
                try:
                    self.task_queue.get_nowait()
                except queue.Empty:
                    break
        
        self.task_queue.put(text)
        print(f"🔊 添加合成任务: {text[:20]}...")
    
    def _process_loop(self):
        """处理循环"""
        # 创建事件循环
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        while self.running:
            try:
                # 获取任务
                text = self.task_queue.get(timeout=0.1)
                
                # 执行合成
                print(f"🔊 开始合成: {text[:20]}...")
                audio_data = self.loop.run_until_complete(self._synthesize_async(text))
                
                if audio_data:
                    # 转换为 μ-law
                    ulaw_data = self._convert_to_ulaw(audio_data)
                    
                    # 添加到结果队列
                    self.result_queue.put((ulaw_data, text))
                    
                    # 调用回调
                    if self.on_audio_ready:
                        self.on_audio_ready(ulaw_data, text)
                    
                    print(f"✅ 合成完成: {len(ulaw_data)} 字节")
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ TTS 错误: {e}")
        
        # 关闭事件循环
        self.loop.close()
    
    async def _synthesize_async(self, text: str) -> Optional[bytes]:
        """
        异步合成语音
        
        Args:
            text: 文本
            
        Returns:
            音频数据 (PCM16)
        """
        if self.config.provider == TTSProvider.EDGE_TTS:
            return await self._synthesize_edge_tts(text)
        elif self.config.provider == TTSProvider.OPENAI:
            return await self._synthesize_openai(text)
        elif self.config.provider == TTSProvider.ELEVENLABS:
            return await self._synthesize_elevenlabs(text)
        else:
            return None
    
    async def _synthesize_edge_tts(self, text: str) -> Optional[bytes]:
        """使用 Edge-TTS 合成"""
        try:
            # 创建通信对象
            communicate = edge_tts.Communicate(
                text,
                self.config.voice,
                rate=f"{int((self.config.speed - 1) * 100):+d}%",
                pitch=f"{int(self.config.pitch * 50):+d}Hz",
                volume=f"{int((self.config.volume - 1) * 100):+d}%"
            )
            
            # 合成到内存
            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])
            
            # 合并音频
            if audio_chunks:
                audio_data = b''.join(audio_chunks)
                
                # Edge-TTS 返回的是 MP3，需要转换
                return self._convert_mp3_to_pcm(audio_data)
            
            return None
            
        except Exception as e:
            print(f"❌ Edge-TTS 错误: {e}")
            return None
    
    async def _synthesize_openai(self, text: str) -> Optional[bytes]:
        """使用 OpenAI TTS 合成"""
        try:
            response = await asyncio.to_thread(
                self.openai_client.Audio.create,
                model="tts-1",
                voice=self.config.openai_voice,
                input=text,
                speed=self.config.speed
            )
            
            # OpenAI 返回 MP3
            return self._convert_mp3_to_pcm(response['data'])
            
        except Exception as e:
            print(f"❌ OpenAI TTS 错误: {e}")
            return None
    
    async def _synthesize_elevenlabs(self, text: str) -> Optional[bytes]:
        """使用 ElevenLabs TTS 合成"""
        try:
            from elevenlabs import generate
            audio_data = generate(text, voice_id=self.elevenlabs_api_key)
            return audio_data
        except Exception as e:
            print(f"❌ ElevenLabs TTS 错误: {e}")
            return None
    
    def _convert_mp3_to_pcm(self, mp3_data: bytes) -> Optional[bytes]:
        """
        将 MP3 转换为 PCM
        
        Args:
            mp3_data: MP3 数据
            
        Returns:
            PCM 数据 (16-bit, 16kHz)
        """
        try:
            import subprocess
            
            # 使用 ffmpeg 转换
            process = subprocess.Popen(
                [
                    'ffmpeg',
                    '-i', 'pipe:0',  # 从标准输入读取
                    '-f', 's16le',   # 16-bit PCM
                    '-ar', str(self.config.sample_rate),  # 采样率
                    '-ac', '1',      # 单声道
                    'pipe:1'         # 输出到标准输出
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )
            
            pcm_data, _ = process.communicate(mp3_data)
            return pcm_data
            
        except Exception as e:
            print(f"❌ 音频转换错误: {e}")
            
            # 备用方案：使用 pydub（如果可用）
            try:
                from pydub import AudioSegment
                import io
                
                audio = AudioSegment.from_mp3(io.BytesIO(mp3_data))
                audio = audio.set_frame_rate(self.config.sample_rate)
                audio = audio.set_channels(1)
                audio = audio.set_sample_width(2)  # 16-bit
                
                return audio.raw_data
                
            except:
                return None
    
    def _convert_to_ulaw(self, pcm_data: bytes) -> bytes:
        """
        将 PCM 转换为 μ-law
        
        Args:
            pcm_data: PCM 数据 (16-bit)
            
        Returns:
            μ-law 数据
        """
        from ..audio import G711Codec
        
        # 如果是 16kHz，需要降采样到 8kHz
        if self.config.sample_rate == 16000:
            # 简单降采样（跳过每隔一个样本）
            pcm_array = np.frombuffer(pcm_data, dtype=np.int16)
            pcm_array = pcm_array[::2]  # 降采样
            pcm_data = pcm_array.tobytes()
        
        return G711Codec.encode_buffer(pcm_data)
    
    def get_audio(self, timeout: float = 0.1) -> Optional[tuple[bytes, str]]:
        """
        获取合成的音频
        
        Args:
            timeout: 超时时间
            
        Returns:
            (音频数据, 文本) 或 None
        """
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def set_callback(self, callback: Callable[[bytes, str], None]):
        """设置音频就绪回调"""
        self.on_audio_ready = callback
    
    def set_voice(self, voice: str):
        """设置语音"""
        if self.config.provider == TTSProvider.EDGE_TTS:
            # 检查是否是预定义的中文语音
            if voice in self.CHINESE_VOICES:
                self.config.voice = self.CHINESE_VOICES[voice]
            else:
                self.config.voice = voice
        elif self.config.provider == TTSProvider.OPENAI:
            self.config.openai_voice = voice
        elif self.config.provider == TTSProvider.ELEVENLABS:
            # ElevenLabs TTS 不需要设置语音
            pass
        
        print(f"🔊 切换语音: {voice}")
    
    def list_voices(self) -> List[str]:
        """列出可用的语音"""
        if self.config.provider == TTSProvider.EDGE_TTS:
            return list(self.CHINESE_VOICES.keys())
        elif self.config.provider == TTSProvider.OPENAI:
            return ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        elif self.config.provider == TTSProvider.ELEVENLABS:
            return []
        else:
            return []