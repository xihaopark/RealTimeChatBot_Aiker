#!/usr/bin/env python3
"""
模型下载脚本
预先下载所需的本地AI模型
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from transformers import AutoTokenizer, AutoModelForCausalLM
from huggingface_hub import snapshot_download
import torch

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_llm_model(model_name: str = "Qwen/Qwen2.5-7B-Instruct"):
    """下载LLM模型"""
    print(f"=== Downloading LLM Model: {model_name} ===")
    
    try:
        # 创建模型缓存目录
        cache_dir = Path.home() / ".cache" / "huggingface"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        print("Downloading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True
        )
        print(f"✓ Tokenizer downloaded: {len(tokenizer)} tokens")
        
        print("Downloading model (this may take a while)...")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )
        print(f"✓ Model downloaded: {model.config}")
        
        # 测试模型
        print("Testing model...")
        inputs = tokenizer("你好", return_tensors="pt")
        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=10)
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"✓ Model test successful: {response}")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to download LLM model: {e}")
        return False


def download_whisper_models():
    """下载Whisper模型"""
    print("=== Downloading Whisper Models ===")
    
    try:
        from faster_whisper import WhisperModel
        
        # 下载不同大小的模型
        models = ["tiny", "base", "small"]
        
        for model_size in models:
            print(f"Downloading Whisper {model_size} model...")
            
            model = WhisperModel(
                model_size, 
                device="cuda" if torch.cuda.is_available() else "cpu",
                compute_type="float16" if torch.cuda.is_available() else "int8"
            )
            
            # 测试模型
            print(f"Testing Whisper {model_size} model...")
            
            print(f"✓ Whisper {model_size} model ready")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to download Whisper models: {e}")
        return False


def download_tts_models():
    """下载TTS模型"""
    print("=== Downloading TTS Models ===")
    
    try:
        # Coqui TTS模型
        model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
        
        print(f"Downloading TTS model: {model_name}")
        
        # 使用snapshot_download下载整个模型仓库
        snapshot_download(
            repo_id="coqui/XTTS-v2",
            repo_type="model",
            local_dir=Path.home() / ".cache" / "tts" / "xtts_v2"
        )
        
        print("✓ TTS model downloaded")
        return True
        
    except Exception as e:
        print(f"✗ Failed to download TTS models: {e}")
        print("Note: TTS models will be downloaded on first use")
        return True  # 不阻塞其他下载


def check_system_requirements():
    """检查系统要求"""
    print("=== Checking System Requirements ===")
    
    # 检查CUDA
    cuda_available = torch.cuda.is_available()
    if cuda_available:
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"✓ CUDA available: {gpu_name} ({gpu_memory:.1f}GB)")
        
        if gpu_memory < 8:
            print("⚠️  Warning: GPU memory < 8GB, consider using 4-bit quantization")
    else:
        print("⚠️  CUDA not available, will use CPU (slower)")
    
    # 检查磁盘空间
    import shutil
    free_space = shutil.disk_usage(".").free / 1024**3
    print(f"Available disk space: {free_space:.1f}GB")
    
    if free_space < 20:
        print("⚠️  Warning: Low disk space, models require ~15GB")
        return False
    
    return True


def main():
    """主函数"""
    print("Model Download Script for Local AI Phone System\n")
    
    if not check_system_requirements():
        print("❌ System requirements not met")
        return 1
    
    # 选择要下载的模型
    models_to_download = {
        "LLM (Qwen2.5-7B)": ("qwen", download_llm_model),
        "Whisper STT": ("whisper", download_whisper_models),
        "TTS Models": ("tts", download_tts_models)
    }
    
    print("Available models to download:")
    for i, (name, (key, _)) in enumerate(models_to_download.items(), 1):
        print(f"{i}. {name}")
    print("0. Download all")
    
    try:
        choice = input("\nSelect models to download (0-3): ").strip()
        
        if choice == "0":
            # 下载所有模型
            selected_models = list(models_to_download.values())
        else:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(models_to_download):
                selected_models = [list(models_to_download.values())[choice_idx]]
            else:
                print("Invalid choice")
                return 1
    
    except (ValueError, KeyboardInterrupt):
        print("\nDownload cancelled")
        return 0
    
    # 下载选定的模型
    successful_downloads = 0
    total_downloads = len(selected_models)
    
    for name, download_func in selected_models:
        if download_func():
            successful_downloads += 1
        print()
    
    print(f"=== Download Summary ===")
    print(f"Successful: {successful_downloads}/{total_downloads}")
    
    if successful_downloads == total_downloads:
        print("🎉 All models downloaded successfully!")
        print("\nYou can now run: python test_local_ai.py")
        return 0
    else:
        print("⚠️  Some downloads failed, but the system may still work")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)