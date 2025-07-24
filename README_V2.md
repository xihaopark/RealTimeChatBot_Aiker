# VTX AI Phone System V2 - 架构说明 🚀

## 📋 概述

VTX AI电话系统V2采用了优化的技术栈组合：**llama-cpp-python + Vosk + Piper**，专门为高性能、低延迟的AI电话服务设计。

## 🎯 技术栈选择

### LLM: llama-cpp-python
- **直接在Python进程内调用llama.cpp**，无需独立server
- **完美适配Vast.ai容器环境**，无需系统权限
- **GPU加速支持**，自动检测并使用CUDA
- **GGUF模型格式**，量化优化，内存占用小

### STT: Vosk
- **轻量级离线语音识别**，启动快速
- **流式识别**，低延迟
- **多语言支持**，中英文效果优秀
- **资源占用低**，适合并发场景

### TTS: Piper
- **极速语音合成**，专为CPU优化
- **高质量输出**，自然流畅
- **多语言多音色**，可扩展性强
- **独立二进制**，性能卓越

## 📁 V2项目结构

```
aiker_v2/                        # V2架构核心目录
├── app_v2.py                   # 主程序入口
├── llm_service_llamacpp.py     # llama-cpp-python LLM服务
├── stt_service.py              # Vosk STT服务
├── tts_service.py              # Piper TTS服务
└── call_handler.py             # 通话处理逻辑

services/                        # AI组件目录
├── piper/                      # Piper TTS
│   ├── piper                   # 二进制可执行文件
│   └── models/                 # TTS模型文件
├── vosk/                       # Vosk STT
│   └── models/                 # STT模型文件
└── llama.cpp/                  # LLM相关
    └── models/                 # GGUF模型文件

requirements_v2.txt             # V2依赖列表
start_v2.sh                    # 启动脚本
test_v2.py                     # 测试工具
```

## 🚀 快速部署

### 1. 安装Python依赖

```bash
pip install -r requirements_v2.txt
```

### 2. 下载AI模型

#### LLM模型（必须）
```bash
# 下载Qwen2.5 7B量化模型（推荐）
cd services/llama.cpp/models
wget https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf
```

### 3. 启动系统

```bash
# 启动V2系统
./start_v2.sh
```

---

**V2架构 = 高性能 + 易部署 + 稳定可靠** 🎉
