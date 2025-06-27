"""
对话管理器
整合 STT、TTS 和 LLM，管理完整的对话流程
"""

import time
import threading
import queue
import asyncio
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .stt_engine import STTEngine, STTConfig
from .tts_engine import TTSEngine, TTSConfig
from .llm_handler import LLMHandler, LLMConfig


class ConversationState(Enum):
    """对话状态"""
    IDLE = "idle"                    # 空闲
    LISTENING = "listening"          # 听取用户说话
    PROCESSING = "processing"        # 处理用户输入
    SPEAKING = "speaking"            # 播放 AI 回复
    INTERRUPTED = "interrupted"      # 被打断


@dataclass
class ConversationConfig:
    """对话配置"""
    # 引擎配置
    stt_config: Optional[STTConfig] = None
    tts_config: Optional[TTSConfig] = None
    llm_config: Optional[LLMConfig] = None
    
    # 对话参数
    silence_timeout: float = 2.0     # 静音超时（判定用户说完）
    max_speaking_time: float = 30.0  # 最大说话时间
    interrupt_threshold: float = 0.5 # 打断阈值
    
    # 提示音
    enable_beep: bool = True         # 启用提示音
    beep_on_listening: bool = True   # 开始听取时的提示音
    beep_on_processing: bool = False # 处理时的提示音


class ConversationManager:
    """对话管理器"""
    
    def __init__(self, config: Optional[ConversationConfig] = None):
        """
        初始化对话管理器
        
        Args:
            config: 对话配置
        """
        self.config = config or ConversationConfig()
        
        # 创建引擎
        self.stt_engine = STTEngine(self.config.stt_config)
        self.tts_engine = TTSEngine(self.config.tts_config)
        self.llm_handler = LLMHandler(self.config.llm_config)
        
        # 状态
        self.state = ConversationState.IDLE
        self.running = False
        
        # 音频队列
        self.audio_input_queue = queue.Queue()   # 输入音频
        self.audio_output_queue = queue.Queue()  # 输出音频
        
        # 时间跟踪
        self.last_speech_time = 0
        self.speaking_start_time = 0
        
        # 回调
        self.on_state_change: Optional[Callable[[ConversationState], None]] = None
        self.on_transcription: Optional[Callable[[str], None]] = None
        self.on_response: Optional[Callable[[str], None]] = None
        self.on_audio_output: Optional[Callable[[bytes], None]] = None
        
        # 线程
        self.process_thread = None
        
        # 设置引擎回调
        self._setup_callbacks()
        
        print("💬 对话管理器初始化完成")
    
    def _setup_callbacks(self):
        """设置引擎回调"""
        # STT 回调
        self.stt_engine.set_callback(self._on_stt_result)
        
        # TTS 回调
        self.tts_engine.set_callback(self._on_tts_ready)
        
        # LLM 回调
        self.llm_handler.set_callback(self._on_llm_response)
    
    def start(self):
        """启动对话管理器"""
        if self.running:
            return
        
        self.running = True
        
        # 启动引擎
        self.stt_engine.start()
        self.tts_engine.start()
        
        # 启动处理线程
        self.process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self.process_thread.start()
        
        # 开始监听
        self._change_state(ConversationState.LISTENING)
        
        print("💬 对话管理器已启动")
    
    def stop(self):
        """停止对话管理器"""
        self.running = False
        
        # 停止引擎
        self.stt_engine.stop()
        self.tts_engine.stop()
        
        if self.process_thread:
            self.process_thread.join(timeout=2)
        
        print("💬 对话管理器已停止")
    
    def add_audio_input(self, audio_data: bytes, format: str = "ulaw"):
        """
        添加输入音频
        
        Args:
            audio_data: 音频数据
            format: 音频格式
        """
        # 添加到 STT 引擎
        self.stt_engine.add_audio(audio_data, format)
        
        # 检测是否有语音活动
        if self.state == ConversationState.SPEAKING:
            # TODO: 实现打断检测
            pass
    
    def _process_loop(self):
        """处理循环"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while self.running:
            try:
                # 根据状态处理
                if self.state == ConversationState.LISTENING:
                    # 检查是否有静音超时
                    if time.time() - self.last_speech_time > self.config.silence_timeout:
                        if self.last_speech_time > 0:  # 确实有说话
                            self._change_state(ConversationState.PROCESSING)
                
                elif self.state == ConversationState.PROCESSING:
                    # 处理已经在回调中进行
                    pass
                
                elif self.state == ConversationState.SPEAKING:
                    # 检查是否说完
                    if self.audio_output_queue.empty():
                        # 回到监听状态
                        self._change_state(ConversationState.LISTENING)
                
                # 短暂休眠
                time.sleep(0.1)
                
            except Exception as e:
                print(f"❌ 处理循环错误: {e}")
        
        loop.close()
    
    def _change_state(self, new_state: ConversationState):
        """改变状态"""
        if self.state == new_state:
            return
        
        old_state = self.state
        self.state = new_state
        
        print(f"📍 状态变化: {old_state.value} -> {new_state.value}")
        
        # 状态转换逻辑
        if new_state == ConversationState.LISTENING:
            # 清空 STT 缓冲区
            self.stt_engine.clear_buffer()
            self.last_speech_time = 0
            
            # 播放提示音
            if self.config.enable_beep and self.config.beep_on_listening:
                self._play_beep()
        
        elif new_state == ConversationState.PROCESSING:
            # 停止监听
            pass
        
        elif new_state == ConversationState.SPEAKING:
            self.speaking_start_time = time.time()
        
        # 调用回调
        if self.on_state_change:
            self.on_state_change(new_state)
    
    def _on_stt_result(self, text: str, duration: float):
        """STT 结果回调"""
        print(f"🎤 识别结果: {text}")
        
        # 更新最后说话时间
        self.last_speech_time = time.time()
        
        # 调用回调
        if self.on_transcription:
            self.on_transcription(text)
        
        # 如果在监听状态，处理输入
        if self.state == ConversationState.LISTENING:
            self._change_state(ConversationState.PROCESSING)
            
            # 在新线程中运行异步任务
            threading.Thread(
                target=self._run_async_response,
                args=(text,),
                daemon=True
            ).start()
    
    def _run_async_response(self, user_input: str):
        """在新线程中运行异步响应生成"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 运行异步任务
            loop.run_until_complete(self._generate_response(user_input))
            
        except Exception as e:
            print(f"❌ 异步响应生成错误: {e}")
            self._change_state(ConversationState.LISTENING)
        finally:
            # 清理事件循环
            try:
                loop.close()
            except:
                pass
    
    async def _generate_response(self, user_input: str):
        """生成并播放回复"""
        try:
            # 生成 LLM 回复
            response = await self.llm_handler.generate_response(user_input)
            
            if response:
                # 合成语音
                self.tts_engine.synthesize(response, priority=True)
                
                # 切换到说话状态
                self._change_state(ConversationState.SPEAKING)
            else:
                # 回到监听状态
                self._change_state(ConversationState.LISTENING)
                
        except Exception as e:
            print(f"❌ 生成回复错误: {e}")
            self._change_state(ConversationState.LISTENING)
    
    def _on_llm_response(self, response: str):
        """LLM 响应回调"""
        print(f"🤖 AI 回复: {response}")
        
        if self.on_response:
            self.on_response(response)
    
    def _on_tts_ready(self, audio_data: bytes, text: str):
        """TTS 音频就绪回调"""
        # 添加到输出队列
        self.audio_output_queue.put(audio_data)
        
        # 分包输出
        self._stream_audio_output(audio_data)
    
    def _stream_audio_output(self, audio_data: bytes):
        """流式输出音频"""
        # 分成 20ms 的包
        packet_size = 160  # 20ms @ 8kHz
        
        for i in range(0, len(audio_data), packet_size):
            packet = audio_data[i:i+packet_size]
            
            # 确保包大小
            if len(packet) < packet_size:
                packet += b'\xFF' * (packet_size - len(packet))
            
            # 输出音频
            if self.on_audio_output:
                self.on_audio_output(packet)
            
            # 模拟实时播放
            time.sleep(0.02)  # 20ms
    
    def _play_beep(self):
        """播放提示音"""
        from ..audio import AudioGenerator
        
        # 生成短促的提示音
        beep = AudioGenerator.generate_beep(frequency=800, duration=0.1)
        
        # 输出
        if self.on_audio_output:
            self.on_audio_output(beep)
    
    def interrupt(self):
        """打断当前对话"""
        if self.state == ConversationState.SPEAKING:
            print("🛑 对话被打断")
            
            # 清空输出队列
            while not self.audio_output_queue.empty():
                try:
                    self.audio_output_queue.get_nowait()
                except queue.Empty:
                    break
            
            # 停止 TTS
            while not self.tts_engine.task_queue.empty():
                try:
                    self.tts_engine.task_queue.get_nowait()
                except queue.Empty:
                    break
            
            # 切换状态
            self._change_state(ConversationState.INTERRUPTED)
            time.sleep(0.1)
            self._change_state(ConversationState.LISTENING)
    
    def set_audio_output_callback(self, callback: Callable[[bytes], None]):
        """设置音频输出回调"""
        self.on_audio_output = callback
    
    def set_callbacks(self, **callbacks):
        """设置各种回调"""
        for name, callback in callbacks.items():
            if hasattr(self, f"on_{name}"):
                setattr(self, f"on_{name}", callback)