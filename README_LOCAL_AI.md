# VTX AI Phone System - 本地AI版本

基于本地开源模型的实时语音对话系统，使用RealtimeTTS/STT和本地大语言模型，完全替代付费API服务。

## 🚀 主要特性

- **完全本地化**: 无需依赖外部API，数据隐私安全
- **实时对话**: 低延迟语音识别和合成，支持自然对话
- **多模型支持**: 支持Qwen、Llama、Mistral等主流开源模型
- **GPU加速**: 充分利用NVIDIA GPU进行模型推理加速
- **SIP兼容**: 完整的SIP/RTP协议支持，兼容标准IP电话系统

## 🛠️ 系统要求

### 硬件要求
- **GPU**: NVIDIA RTX A5000 (24GB) 或同等级别GPU
- **内存**: 32GB+ RAM 推荐
- **存储**: 20GB+ 可用空间（用于模型存储）
- **网络**: 用于首次下载模型

### 软件要求
- Ubuntu 20.04+ / CentOS 8+
- Python 3.10+
- CUDA 11.8+
- Git

## 📦 安装步骤

### 1. 准备环境
```bash
# 激活GPU虚拟环境
source gpu_env/bin/activate

# 验证CUDA可用性
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
```

### 2. 下载模型
```bash
# 运行模型下载脚本
python download_models.py

# 选择要下载的模型：
# 1. LLM (Qwen2.5-7B) - 约13GB
# 2. Whisper STT - 约1GB
# 3. TTS Models - 约2GB
# 0. 全部下载
```

### 3. 测试系统
```bash
# 运行完整测试
python test_local_ai.py

# 预期输出：
# ✓ Audio Converter tests passed
# ✓ Local LLM tests passed
# ✓ Local TTS tests passed
# ✓ Local STT tests passed
# ✓ Integration test passed
```

### 4. 启动系统
```bash
# 启动本地AI电话系统
python main_local_ai.py

# 日志输出：
# Local AI Phone System started successfully
# SIP client registered
# Waiting for incoming calls...
```

## ⚙️ 配置说明

### 基础配置
编辑 `config/local_ai_config.py`:

```python
LOCAL_AI_CONFIG = {
    "llm": {
        "model_name": "Qwen/Qwen2.5-7B-Instruct",  # LLM模型
        "device": "cuda",                           # 计算设备
        "temperature": 0.7,                         # 生成温度
        "use_4bit": True                           # 4位量化
    },
    "stt": {
        "model": "base",          # Whisper模型大小
        "language": "zh",         # 识别语言
        "device": "cuda"          # 计算设备
    },
    "tts": {
        "engine": "system",       # TTS引擎
        "voice": "zh",           # 语音
        "speed": 1.0             # 语音速度
    }
}
```

### 性能配置模板
```bash
# 使用预设配置
export LOCAL_AI_PROFILE=balanced  # high_quality, balanced, fast, cpu_only
python main_local_ai.py
```

### 环境变量配置
```bash
# 模型选择
export LOCAL_AI_LLM_MODEL="Qwen/Qwen2.5-7B-Instruct"
export LOCAL_AI_STT_MODEL="base"
export LOCAL_AI_TTS_ENGINE="system"

# 设备选择
export LOCAL_AI_DEVICE="cuda"  # 或 "cpu"

# 日志级别
export LOCAL_AI_LOG_LEVEL="INFO"
```

## 🎯 性能优化

### GPU内存优化
1. **4位量化**: 减少50%显存占用
2. **模型选择**: 
   - 快速响应: Qwen2.5-7B + tiny Whisper
   - 平衡性能: Qwen2.5-7B + base Whisper  
   - 高质量: Qwen2.5-14B + large Whisper

### 响应时间优化
- **LLM推理**: 1-3秒 (7B模型)
- **STT转录**: 0.5-1秒 (base模型)
- **TTS合成**: 0.5-1秒 (系统引擎)
- **总响应时间**: 2-5秒

### 并发处理
- 支持最多5个并发通话
- 自动负载均衡
- 内存和GPU资源管理

## 🔧 架构说明

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   SIP Client    │    │   RTP Handler   │    │  Audio Converter│
│                 │────│                 │────│                 │
│ •注册认证       │    │ •音频传输       │    │ •μ-law ↔ PCM   │
│ •呼叫处理       │    │ •包处理         │    │ •重采样         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Local STT     │    │   Local LLM     │    │   Local TTS     │
│                 │    │                 │    │                 │
│ •Whisper模型    │────│ •Qwen/Llama     │────│ •RealtimeTTS    │
│ •实时转录       │    │ •对话生成       │    │ •语音合成       │
│ •语音活动检测   │    │ •业务知识库     │    │ •多引擎支持     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📊 对比分析

| 特性 | API版本 | 本地AI版本 |
|------|---------|------------|
| **成本** | 按使用付费 | 硬件投资后免费 |
| **延迟** | 网络+API延迟 | 本地推理延迟 |
| **隐私** | 数据上传云端 | 完全本地处理 |
| **稳定性** | 依赖网络和服务 | 本地可控 |
| **定制性** | 有限 | 完全可定制 |
| **质量** | 商业级 | 开源模型质量 |

## 🐛 故障排除

### 常见问题

1. **CUDA内存不足**
   ```bash
   # 启用4位量化
   export LOCAL_AI_4BIT=true
   # 或使用更小的模型
   export LOCAL_AI_LLM_MODEL="Qwen/Qwen2.5-3B-Instruct"
   ```

2. **模型下载失败**
   ```bash
   # 使用镜像源
   export HF_ENDPOINT=https://hf-mirror.com
   python download_models.py
   ```

3. **音频质量问题**
   ```bash
   # 使用Coqui TTS引擎
   export LOCAL_AI_TTS_ENGINE="coqui"
   ```

4. **响应速度慢**
   ```bash
   # 使用fast配置
   export LOCAL_AI_PROFILE="fast"
   ```

### 日志检查
```bash
# 查看系统日志
tail -f logs/local_ai_system.log

# 查看错误日志
grep ERROR logs/local_ai_system.log
```

## 📈 监控和维护

### 性能监控
```bash
# GPU监控
nvidia-smi -l 1

# 系统资源监控
htop

# 网络监控
netstat -an | grep 5060  # SIP端口
netstat -an | grep 10000 # RTP端口
```

### 定期维护
- 清理日志文件 (每周)
- 更新模型 (按需)
- 系统资源检查 (每日)
- 备份配置文件 (每月)

## 🚀 升级计划

### 即将支持的功能
- [ ] 多语言支持 (英文、日文等)
- [ ] 语音情感识别
- [ ] 实时语音转换 (变声)
- [ ] 对话记录和分析
- [ ] Web管理界面
- [ ] 集群部署支持

### 模型升级路线
- Qwen2.5-14B-Instruct (更强对话能力)
- Whisper Large-v3 (更高识别准确率)
- XTTS-v2 (更自然的语音合成)

## 📞 技术支持

如遇到问题，请提供：
1. 系统配置信息
2. 错误日志
3. 复现步骤

联系方式：
- GitHub Issues: [项目地址]
- Email: support@example.com

---

**注**: 首次运行会下载大量模型文件，请确保网络连接稳定。建议在业务低峰期进行系统升级和维护。