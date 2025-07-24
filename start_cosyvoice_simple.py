#!/usr/bin/env python3
"""
简化的CosyVoice TTS服务
如果CosyVoice不可用，提供兼容的HTTP API接口
"""

import os
import sys
import logging
from fastapi import FastAPI, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import numpy as np

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Simplified TTS Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"])

# 全局TTS引擎
tts_engine = None

def init_tts_engine():
    """初始化TTS引擎"""
    global tts_engine
    
    try:
        # 尝试导入CosyVoice
        sys.path.append('/workspace/RealTimeChatBot_Aiker-1/CosyVoice')
        sys.path.append('/workspace/RealTimeChatBot_Aiker-1/CosyVoice/third_party/Matcha-TTS')
        
        from cosyvoice.cli.cosyvoice import CosyVoice
        tts_engine = CosyVoice('iic/CosyVoice-300M')
        logger.info("✅ CosyVoice engine loaded successfully")
        return "cosyvoice"
        
    except Exception as e:
        logger.warning(f"CosyVoice failed to load: {e}")
        
        try:
            # 尝试使用espeak作为备选
            import subprocess
            result = subprocess.run(['espeak', '--version'], capture_output=True)
            if result.returncode == 0:
                tts_engine = "espeak"
                logger.info("✅ Using espeak as TTS engine")
                return "espeak"
        except Exception as espeak_error:
            logger.warning(f"Espeak not available: {espeak_error}")
        
        # 最终备选：生成提示音
        tts_engine = "tone_generator"
        logger.info("✅ Using tone generator as TTS engine")
        return "tone_generator"

def generate_cosyvoice_audio(text: str, spk_id: str = "中文女"):
    """使用CosyVoice生成音频"""
    try:
        model_output = tts_engine.inference_sft(text, spk_id)
        for i in model_output:
            tts_audio = (i['tts_speech'].numpy() * (2 ** 15)).astype(np.int16).tobytes()
            yield tts_audio
    except Exception as e:
        logger.error(f"CosyVoice synthesis error: {e}")
        yield generate_fallback_audio(text)

def generate_espeak_audio(text: str):
    """使用espeak生成音频"""
    try:
        import subprocess
        import tempfile
        import wave
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            # 使用espeak生成WAV文件
            subprocess.run([
                'espeak', '-v', 'zh+f3', '-s', '160', '-p', '50', 
                '-a', '100', '-w', tmp_file.name, text
            ], check=True, capture_output=True)
            
            # 读取生成的WAV文件
            with wave.open(tmp_file.name, 'rb') as wav_file:
                frames = wav_file.readframes(wav_file.getnframes())
                return frames
                
    except Exception as e:
        logger.error(f"Espeak synthesis error: {e}")
        return generate_fallback_audio(text)
    finally:
        try:
            os.unlink(tmp_file.name)
        except:
            pass

def generate_fallback_audio(text: str):
    """生成备用提示音"""
    # 基于文本长度生成音频
    duration = max(2.0, len(text) * 0.12)
    sample_rate = 16000
    samples = int(sample_rate * duration)
    
    t = np.linspace(0, duration, samples)
    
    # 生成三音调序列
    tone1 = np.sin(2 * np.pi * 700 * t) * np.exp(-t * 2) * (t < duration/3)
    tone2 = np.sin(2 * np.pi * 550 * (t - duration/3)) * np.exp(-(t - duration/3) * 2) * ((t >= duration/3) & (t < 2*duration/3))
    tone3 = np.sin(2 * np.pi * 400 * (t - 2*duration/3)) * np.exp(-(t - 2*duration/3) * 2) * (t >= 2*duration/3)
    
    audio = (tone1 + tone2 + tone3) * 16383 * 0.6
    return audio.astype(np.int16).tobytes()

def generate_audio_stream(text: str, spk_id: str = "中文女"):
    """生成音频流"""
    logger.info(f"Generating audio for: {text[:50]}...")
    
    if tts_engine.__class__.__name__ == 'CosyVoice':
        # 使用CosyVoice
        yield from generate_cosyvoice_audio(text, spk_id)
    elif tts_engine == "espeak":
        # 使用espeak
        audio_data = generate_espeak_audio(text)
        yield audio_data
    else:
        # 使用备用提示音
        audio_data = generate_fallback_audio(text)
        yield audio_data

@app.get("/")
async def root():
    return {"message": "Simplified TTS Service", "engine": str(type(tts_engine).__name__ if hasattr(tts_engine, '__class__') else tts_engine)}

@app.get("/docs")
async def docs():
    return {"endpoints": ["/inference_sft"], "status": "ready"}

@app.post("/inference_sft")
async def inference_sft(tts_text: str = Form(), spk_id: str = Form("中文女")):
    """SFT推理接口，兼容CosyVoice API"""
    logger.info(f"TTS request: {tts_text[:100]}... (speaker: {spk_id})")
    
    def audio_generator():
        yield from generate_audio_stream(tts_text, spk_id)
    
    return StreamingResponse(
        audio_generator(),
        media_type="audio/wav",
        headers={"Content-Disposition": "attachment; filename=tts_output.wav"}
    )

if __name__ == "__main__":
    # 初始化TTS引擎
    engine_type = init_tts_engine()
    
    print(f"🎤 启动简化TTS服务 (引擎: {engine_type})")
    print("=" * 40)
    
    # 启动FastAPI服务
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=50000,
        log_level="info"
    )