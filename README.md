# VTX AI Phone System - 实时AI电话机器人

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-xihaopark/RealTimeChatBot_Aiker-blue.svg)](https://github.com/xihaopark/RealTimeChatBot_Aiker)

一个基于Python的智能AI电话系统，能够通过VTX IP电话系统接听和处理电话，集成了实时语音识别(STT)、语音合成(TTS)和大语言模型(LLM)，实现完整的AI电话对话功能。

## 🚀 功能特性

- ✅ **SIP/RTP协议支持** - 兼容标准IP电话系统
- ✅ **实时语音识别** - 支持OpenAI Whisper和本地Whisper模型
- ✅ **智能语音合成** - 支持Edge-TTS和OpenAI TTS
- ✅ **AI智能对话** - 集成OpenAI GPT模型，支持上下文对话
- ✅ **自动NAT穿透** - STUN/TURN支持，解决网络连接问题
- ✅ **多分机支持** - 支持多个分机同时工作
- ✅ **通话录音** - 自动录制和分析通话内容
- ✅ **实时监控** - 完整的系统监控和日志记录
- ✅ **配置管理** - 灵活的环境变量配置系统

## 📁 项目结构

```
vtx-llm-bot/
├── 📁 src/                          # 源代码目录
│   ├── 📁 ai/                       # AI处理模块
│   │   ├── __init__.py              # AI模块初始化
│   │   ├── conversation_manager.py  # 对话管理器
│   │   ├── stt_engine.py            # 语音识别引擎
│   │   ├── tts_engine.py            # 语音合成引擎
│   │   └── llm_handler.py           # 大语言模型处理器
│   ├── 📁 audio/                    # 音频处理模块
│   │   ├── __init__.py              # 音频模块初始化
│   │   ├── codec.py                 # 音频编解码器
│   │   └── generator.py             # 音频生成器
│   ├── 📁 rtp/                      # RTP协议处理
│   │   ├── __init__.py              # RTP模块初始化
│   │   ├── handler.py               # RTP处理器
│   │   └── packet.py                # RTP数据包处理
│   ├── 📁 sdp/                      # SDP协议处理
│   │   ├── __init__.py              # SDP模块初始化
│   │   └── parser.py                # SDP解析器
│   ├── 📁 sip/                      # SIP协议处理
│   │   ├── __init__.py              # SIP模块初始化
│   │   ├── auth.py                  # SIP认证
│   │   ├── client.py                # SIP客户端
│   │   └── messages.py              # SIP消息处理
│   ├── 📁 utils/                    # 工具模块
│   ├── __init__.py                  # 源代码包初始化
│   └── main.py                      # 主程序入口
├── 📁 config/                       # 配置目录
│   └── settings.py                  # 系统配置管理
├── 📁 venv/                         # Python虚拟环境
├── 📄 requirements.txt              # Python依赖包
├── 📄 .gitignore                    # Git忽略文件
├── 📄 sync_to_github.sh             # GitHub同步脚本
├── 📄 deploy.sh                     # 部署脚本
└── 📄 README.md                     # 项目说明文档
```

## 🔧 核心模块详解

### 🤖 AI模块 (`src/ai/`)

#### `conversation_manager.py`
- **功能**: 管理完整的AI对话流程
- **核心类**: `ConversationManager`, `ConversationConfig`
- **职责**: 
  - 协调STT、TTS、LLM三个引擎
  - 管理对话状态和上下文
  - 处理音频输入输出流
  - 实现打断检测和静音超时

#### `stt_engine.py`
- **功能**: 语音识别引擎
- **核心类**: `STTEngine`, `STTConfig`, `AudioBuffer`
- **支持**: 
  - OpenAI Whisper API
  - 本地Whisper模型
  - 实时音频流处理
  - 语音活动检测(VAD)

#### `tts_engine.py`
- **功能**: 语音合成引擎
- **核心类**: `TTSEngine`, `TTSConfig`
- **支持**:
  - Edge-TTS (微软)
  - OpenAI TTS
  - 多种中文语音
  - 实时音频流输出

#### `llm_handler.py`
- **功能**: 大语言模型处理器
- **核心类**: `LLMHandler`, `LLMConfig`, `Message`
- **支持**:
  - OpenAI GPT系列
  - 自定义API端点
  - 对话历史管理
  - 上下文保持

### 🔊 音频模块 (`src/audio/`)

#### `codec.py`
- **功能**: 音频编解码器
- **核心类**: `G711Codec`
- **支持**:
  - μ-law编码/解码
  - A-law编码/解码
  - PCM格式转换

#### `generator.py`
- **功能**: 音频生成器
- **核心类**: `AudioGenerator`
- **支持**:
  - 测试音频生成
  - 提示音生成
  - 音频格式转换

### 🌐 网络协议模块

#### SIP模块 (`src/sip/`)
- **client.py**: SIP客户端实现
- **auth.py**: SIP认证处理
- **messages.py**: SIP消息解析和构建

#### RTP模块 (`src/rtp/`)
- **handler.py**: RTP数据流处理
- **packet.py**: RTP数据包封装

#### SDP模块 (`src/sdp/`)
- **parser.py**: SDP会话描述协议解析

### ⚙️ 配置模块 (`config/`)

#### `settings.py`
- **功能**: 统一配置管理
- **核心类**: `Settings`, `VTXConfig`, `AIConfig`, `SystemConfig`
- **支持**:
  - 环境变量配置
  - 多分机配置
  - 网络参数配置
  - AI模型配置

## 🚀 快速开始

### 环境要求

- **Python**: 3.8+
- **操作系统**: Linux/macOS/Windows
- **网络**: 支持UDP的网络环境
- **VTX账户**: 有效的VTX IP电话系统账户

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/xihaopark/RealTimeChatBot_Aiker.git
cd RealTimeChatBot_Aiker
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的配置信息
```

5. **运行系统**
```bash
python src/main.py
```

### 环境变量配置

创建 `.env` 文件并配置以下变量：

```env
# VTX服务器配置
VTX_SERVER=core1-us-lax.myippbx.com
VTX_PORT=5060
VTX_DOMAIN=aiker.myippbx.com
VTX_DID=14088779998

# 分机配置
EXTENSION_101_USERNAME=your_username
EXTENSION_101_PASSWORD=your_password
EXTENSION_101_DESCRIPTION=AI Assistant

# AI配置
OPENAI_API_KEY=your_openai_api_key
STT_PROVIDER=whisper
TTS_PROVIDER=edge-tts
LLM_PROVIDER=openai

# 网络配置
SIP_PORT=5060
RTP_PORT_START=10000
RTP_PORT_END=10500
USE_STUN=true
```

## 🔄 GitHub同步机制

### 自动同步脚本

项目包含自动同步到GitHub的脚本：

```bash
# 执行同步
./sync_to_github.sh
```

### 同步脚本功能

- 自动提交代码变更
- 推送到GitHub仓库
- 生成提交日志
- 错误处理和回滚

### 手动同步

```bash
# 添加所有文件
git add .

# 提交变更
git commit -m "Update: 描述你的变更"

# 推送到GitHub
git push origin main
```

## 📊 监控和日志

### 日志系统
- 使用 `loguru` 进行日志管理
- 支持多级别日志输出
- 自动日志轮转

### 系统监控
- 实时通话状态监控
- 性能指标收集
- 健康检查机制

## 🧪 测试

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_sip.py

# 生成覆盖率报告
pytest --cov=src
```

## 🚀 部署

### 生产环境部署
```bash
# 使用部署脚本
./deploy.sh

# 或手动部署
python src/main.py --production
```

### Docker部署
```bash
# 构建镜像
docker build -t vtx-ai-phone .

# 运行容器
docker run -d --name vtx-ai-phone vtx-ai-phone
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持

如果你遇到问题或有建议，请：

1. 查看 [Issues](https://github.com/xihaopark/RealTimeChatBot_Aiker/issues)
2. 创建新的 Issue
3. 联系项目维护者

## 🔄 更新日志

### v2.0.0 (2024-01-XX)
- ✅ 重构AI模块架构
- ✅ 添加完整的对话管理
- ✅ 优化音频处理流程
- ✅ 改进错误处理机制
- ✅ 添加GitHub同步脚本

### v1.0.0 (2024-01-XX)
- ✅ 基础SIP/RTP功能
- ✅ 语音识别和合成
- ✅ AI对话功能

---

**项目维护者**: [xihaopark](https://github.com/xihaopark)  
**项目地址**: [https://github.com/xihaopark/RealTimeChatBot_Aiker](https://github.com/xihaopark/RealTimeChatBot_Aiker)