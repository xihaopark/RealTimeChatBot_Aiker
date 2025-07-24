"""
本地AI系统配置文件
"""

import os
from typing import Dict, Any

# 本地AI配置
LOCAL_AI_CONFIG: Dict[str, Any] = {
    # LLM配置
    "llm": {
        "model_name": "Qwen/Qwen2.5-7B-Instruct",  # 可选: Qwen/Qwen2.5-7B-Instruct, microsoft/DialoGPT-medium, meta-llama/Llama-3.1-8B-Instruct
        "device": "cuda" if os.environ.get("CUDA_AVAILABLE", "true").lower() == "true" else "cpu",
        "max_length": 2048,
        "temperature": 0.7,
        "use_4bit": True,  # 4位量化以节省显存
        "cache_dir": os.path.expanduser("~/.cache/huggingface"),
    },
    
    # STT配置
    "stt": {
        "model": "base",  # tiny, base, small, medium, large
        "language": "zh",  # 语言代码
        "device": "cuda" if os.environ.get("CUDA_AVAILABLE", "true").lower() == "true" else "cpu",
        "mic": False,  # 是否使用麦克风输入
        "compute_type": "float16",  # float16 (GPU) 或 int8 (CPU)
        
        # 语音活动检测参数
        "silero_sensitivity": 0.4,  # Silero VAD敏感度 (0.0-1.0)
        "webrtc_sensitivity": 2,    # WebRTC VAD敏感度 (0-3)
        
        # 音频处理参数
        "post_speech_silence_duration": 0.7,  # 语音后静音持续时间
        "min_length_of_recording": 0.1,       # 最短录音时间
        "min_gap_between_recordings": 0.5,    # 录音间最小间隔
        
        # 实时转录参数
        "enable_realtime_transcription": True,
        "realtime_processing_pause": 0.2,
        
        # 唤醒词配置
        "wake_words": "",  # 空字符串表示不使用唤醒词
        "wake_words_sensitivity": 0.6,
        "wake_word_activation_delay": 0.5,
        "wake_word_timeout": 5,
    },
    
    # TTS配置
    "tts": {
        "engine": "system",  # system, coqui, silero
        "voice": "zh",       # 语音ID或语言代码
        "device": "cuda" if os.environ.get("CUDA_AVAILABLE", "true").lower() == "true" else "cpu",
        "speed": 1.0,        # 语音速度倍率
        
        # Coqui TTS配置
        "coqui": {
            "model_name": "tts_models/multilingual/multi-dataset/xtts_v2",
            "language": "zh",
            "speaker_wav": None,  # 可选：说话人音频文件路径
        },
        
        # 系统TTS配置
        "system": {
            "voice": "zh",
            "rate": 200,  # 语音速率
            "volume": 0.9,
        },
    },
    
    # 音频处理配置
    "audio": {
        "sample_rate_rtp": 8000,   # RTP音频采样率
        "sample_rate_stt": 16000,  # STT输入采样率
        "chunk_size": 160,         # RTP音频块大小 (20ms @ 8kHz)
        "silence_threshold": 0.01, # 静音检测阈值
        "silence_duration": 1.5,   # 静音持续时间 (秒)
        "min_audio_length": 0.5,   # 最小音频长度 (秒)
        "max_audio_length": 10.0,  # 最大音频长度 (秒)
    },
    
    # 性能优化配置
    "performance": {
        "max_concurrent_calls": 5,     # 最大并发通话数
        "audio_buffer_size": 1024,     # 音频缓冲区大小
        "stt_queue_size": 100,         # STT处理队列大小
        "tts_queue_size": 50,          # TTS处理队列大小
        "response_timeout": 30,        # 响应超时时间 (秒)
        "call_timeout": 1800,          # 通话超时时间 (秒)
    },
    
    # 日志配置
    "logging": {
        "level": "INFO",  # DEBUG, INFO, WARNING, ERROR
        "file": "logs/local_ai_system.log",
        "max_file_size": 10 * 1024 * 1024,  # 10MB
        "backup_count": 5,
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    },
    
    # 业务配置
    "business": {
        "welcome_message": "您好，欢迎致电OneSuite，我是您的AI助手，请问有什么可以帮助您的吗？",
        "timeout_message": "抱歉，我没有听到您的回复。如需帮助，请重新拨打电话。",
        "error_message": "抱歉，系统遇到了问题。请稍后再试或联系客服。",
        "business_hours": {
            "enabled": False,  # 是否启用营业时间检查
            "timezone": "Asia/Shanghai",
            "weekdays": {"start": "09:00", "end": "18:00"},
            "weekends": {"start": "10:00", "end": "16:00"},
            "closed_message": "现在是非营业时间，请在工作时间内致电，或留言给我们。"
        }
    }
}

# 环境变量覆盖
def get_config() -> Dict[str, Any]:
    """获取配置，支持环境变量覆盖"""
    config = LOCAL_AI_CONFIG.copy()
    
    # LLM模型名称
    if "LOCAL_AI_LLM_MODEL" in os.environ:
        config["llm"]["model_name"] = os.environ["LOCAL_AI_LLM_MODEL"]
    
    # 设备选择
    if "LOCAL_AI_DEVICE" in os.environ:
        device = os.environ["LOCAL_AI_DEVICE"]
        config["llm"]["device"] = device
        config["stt"]["device"] = device
        config["tts"]["device"] = device
    
    # STT模型大小
    if "LOCAL_AI_STT_MODEL" in os.environ:
        config["stt"]["model"] = os.environ["LOCAL_AI_STT_MODEL"]
    
    # TTS引擎
    if "LOCAL_AI_TTS_ENGINE" in os.environ:
        config["tts"]["engine"] = os.environ["LOCAL_AI_TTS_ENGINE"]
    
    # 日志级别
    if "LOCAL_AI_LOG_LEVEL" in os.environ:
        config["logging"]["level"] = os.environ["LOCAL_AI_LOG_LEVEL"]
    
    return config

# 预设配置模板
PERFORMANCE_PROFILES = {
    "high_quality": {
        "llm": {"model_name": "Qwen/Qwen2.5-14B-Instruct", "use_4bit": False},
        "stt": {"model": "large", "compute_type": "float16"},
        "tts": {"engine": "coqui"}
    },
    
    "balanced": {
        "llm": {"model_name": "Qwen/Qwen2.5-7B-Instruct", "use_4bit": True},
        "stt": {"model": "base", "compute_type": "float16"},
        "tts": {"engine": "system"}
    },
    
    "fast": {
        "llm": {"model_name": "microsoft/DialoGPT-medium", "use_4bit": True},
        "stt": {"model": "tiny", "compute_type": "int8"},
        "tts": {"engine": "system"}
    },
    
    "cpu_only": {
        "llm": {"device": "cpu", "use_4bit": False},
        "stt": {"device": "cpu", "compute_type": "int8"},
        "tts": {"device": "cpu", "engine": "system"}
    }
}

def apply_performance_profile(profile_name: str) -> Dict[str, Any]:
    """应用性能配置模板"""
    config = get_config()
    
    if profile_name in PERFORMANCE_PROFILES:
        profile = PERFORMANCE_PROFILES[profile_name]
        
        # 深度合并配置
        for section, settings in profile.items():
            if section in config:
                config[section].update(settings)
    
    return config