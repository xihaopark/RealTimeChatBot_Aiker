# VTX AI Phone System V2 - 一体化架构 🚀

## 📋 概述

这是专门为**Vast.ai容器环境**设计的VTX AI电话系统V2一体化版本。与原始的服务分离架构不同，这个版本将所有AI功能（STT、LLM、TTS）整合到单一Python进程中运行，完美适配Vast.ai的容器环境限制。

## 🎯 为什么需要一体化架构？

### Vast.ai环境限制
- **无systemd支持**: 容器环境不支持`systemctl`等系统服务管理
- **无独立服务权限**: 无法启动`dockerd`、`llama.cpp server`等独立后台服务
- **容器化隔离**: 无法修改内核参数或网络配置

### 解决方案
- ✅ **所有AI服务运行在主进程内**: 使用`transformers`、`RealtimeSTT`、`RealtimeTTS`库
- ✅ **无外部依赖**: 不需要启动任何外部服务或守护进程
- ✅ **一键启动**: 单个Python脚本完成所有功能
- ✅ **GPU加速**: 完全支持CUDA加速，充分利用Vast.ai的GPU资源

## 🏗️ 架构对比

| 组件 | V2 分离架构 | V2 一体化架构 (Vast.ai) |
|------|------------|----------------------|
| **LLM** | Llama.cpp Server (HTTP API) | Transformers (进程内加载) |
| **STT** | Vosk Server (WebSocket) | RealtimeSTT (进程内处理) |
| **TTS** | Piper (外部进程调用) | RealtimeTTS (进程内合成) |
| **部署** | 多个服务+主程序 | 单一Python进程 |
| **适用环境** | 完整Linux服务器 | Vast.ai容器环境 |

## 📁 项目结构

```
aiker_v2/                          # V2一体化架构
├── app_integrated.py              # 主程序入口
├── llm_service_integrated.py      # Transformers LLM服务
├── stt_service_integrated.py      # RealtimeSTT语音识别
├── tts_service_integrated.py      # RealtimeTTS语音合成
├── call_handler.py               # 通话处理逻辑
└── audio_converter.py            # 音频格式转换

requirements_v2_integrated.txt     # 一体化版本依赖
start_v2_integrated.sh            # 启动脚本
test_integrated_v2.py             # 测试工具
```

## 🚀 快速开始

### 1. 环境要求

- **Python**: 3.8+
- **GPU**: NVIDIA GPU + CUDA (推荐)
- **内存**: 8GB+ (模型加载需要)
- **存储**: 10GB+ (模型文件)

### 2. 安装依赖

```bash
# 在项目根目录
pip install -r requirements_v2_integrated.txt
```

### 3. 配置SIP参数

编辑 `config/settings.py`:

```python
SIP_CONFIG = {
    'username': 'your_extension',
    'password': 'your_password', 
    'server': 'your.sip.server.com',
    'port': 5060,
    'local_ip': '0.0.0.0'
}
```

### 4. 运行测试

```bash
# 测试所有AI组件
python test_integrated_v2.py
```

### 5. 启动系统

```bash
# 一键启动
./start_v2_integrated.sh
```

## 🔧 核心功能

### 🧠 LLM服务 (Transformers)
- **模型**: Qwen2.5-7B-Instruct (可配置)
- **量化**: 4bit量化节省显存
- **设备**: 自动检测CUDA/CPU
- **特性**: 对话历史管理、上下文保持

### 🎤 STT服务 (RealtimeSTT)
- **模型**: Whisper (tiny/base/small可选)
- **语言**: 中文/英文自动切换
- **模式**: 流式实时识别
- **音频**: 支持8kHz电话音频

### 🎵 TTS服务 (RealtimeTTS)
- **引擎**: Coqui TTS (本地)
- **语音**: 中文huayan/英文ljspeech
- **输出**: 8kHz PCM (RTP兼容)
- **速度**: 实时合成，低延迟

### 📞 通话处理
- **协议**: SIP/RTP (兼容V1)
- **IVR**: 双语语言选择
- **流程**: STT → LLM → TTS 完整链路
- **并发**: 支持多路通话

## ⚡ 性能优化

### GPU内存优化
- **4bit量化**: LLM模型占用减少75%
- **动态加载**: 按需加载语言模型
- **内存管理**: 自动清理GPU缓存

### 音频处理优化
- **流式处理**: 降低延迟
- **格式转换**: 高效PCM/μ-law转换
- **采样率**: 自动重采样适配电话标准

### 并发处理
- **多线程**: 每个通话独立线程
- **资源共享**: AI模型进程内共享
- **负载均衡**: 智能任务分配

## 🛠️ 故障排除

### 常见问题

1. **CUDA内存不足**
   ```bash
   # 使用更小的模型
   model_name = "microsoft/DialoGPT-small"
   # 或者使用CPU模式
   device = "cpu"
   ```

2. **音频设备错误**
   ```bash
   # 环境变量已自动设置
   export SDL_AUDIODRIVER=dummy
   export ALSA_SUPPRESS_WARNINGS=1
   ```

3. **模型下载失败**
   ```bash
   # 设置HuggingFace镜像
   export HF_ENDPOINT=https://hf-mirror.com
   ```

### 日志调试

日志文件位置: `logs/aiker_v2_integrated.log`

```bash
# 实时查看日志
tail -f logs/aiker_v2_integrated.log
```

## 📊 监控与状态

### 系统状态
- 启动后会显示各组件状态
- 定期输出活跃通话统计
- GPU显存使用情况监控

### 性能指标
- **启动时间**: < 60秒 (GPU模式)
- **响应延迟**: < 2秒 (STT+LLM+TTS)
- **并发能力**: 5-10路通话 (取决于GPU显存)
- **资源占用**: 4-8GB GPU显存

## 🔄 与V1版本的兼容性

### 保持兼容
- ✅ SIP/RTP协议完全兼容
- ✅ 配置文件格式不变
- ✅ 业务数据结构保持
- ✅ 音频格式标准一致

### 升级优势
- 🚀 **10x启动速度**: 无需等待多个服务启动
- 🎯 **简化部署**: 单一进程，无服务依赖
- 💾 **资源优化**: 共享内存，减少重复加载
- 🔧 **易于调试**: 统一日志，集中错误处理

## 📈 生产部署建议

### Vast.ai配置推荐
- **GPU**: RTX 4090 / A100 (24GB+ VRAM)
- **CPU**: 8核心以上
- **内存**: 32GB+
- **存储**: 50GB+ SSD

### 性能调优
1. **模型选择**: 根据GPU显存选择合适大小的模型
2. **批处理**: 启用音频批量处理
3. **预热**: 系统启动后进行模型预热
4. **监控**: 实时监控GPU显存和温度

## 🤝 技术支持

- **架构问题**: 查看本文档
- **部署问题**: 运行 `test_integrated_v2.py`
- **性能问题**: 检查GPU状态和日志
- **功能问题**: 参考V1版本文档

---

**🎉 恭喜！您已经掌握了V2一体化架构。这个版本专门为Vast.ai环境优化，让您可以在容器环境中轻松运行高性能AI电话系统！**