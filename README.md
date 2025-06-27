# VTX AI Phone System v2.1

一个基于Python的智能SIP电话系统，集成了AI语音对话功能，支持实时语音识别、AI对话和语音合成。

## 🚀 最新版本 v2.1 特性

### 🎤 完整AI语音对话系统
- **Aiker AI助手** - 智能语音交互助手
- **实时语音识别** - 使用Deepgram API进行高精度STT
- **自然语音合成** - 使用ElevenLabs API生成流畅TTS
- **智能对话管理** - 支持上下文理解和连续对话
- **静音检测** - 智能等待用户说完再回复

### 🎵 音频处理优化
- **中文女声TTS** - Sarah/Aria自然流畅的中文语音
- **音频缓冲优化** - 改进的音频处理逻辑
- **RTP流处理** - 稳定的实时音频传输
- **格式自动转换** - 支持多种音频格式

### 🔧 系统稳定性
- **多API故障转移** - OpenAI、Deepgram、ElevenLabs
- **完整错误处理** - 详细的日志和异常处理
- **模块化架构** - 易于扩展和维护

## 📋 系统要求

- Python 3.8+
- Linux服务器环境
- 稳定的网络连接
- 有效的API密钥

## 🛠️ 安装配置

### 1. 克隆项目
```bash
git clone https://github.com/your-username/vtx-voip.git
cd vtx-voip
```

### 2. 安装依赖
```bash
pip3 install -r requirements.txt
```

### 3. 配置API密钥
复制环境变量模板：
```bash
cp env.example .env
```

编辑 `.env` 文件，填入您的API密钥：
```bash
# OpenAI API (用于AI对话)
OPENAI_API_KEY=your_openai_api_key

# Deepgram API (用于语音识别)
DEEPGRAM_API_KEY=your_deepgram_api_key

# ElevenLabs API (用于语音合成)
ELEVENLABS_API_KEY=your_elevenlabs_api_key
```

### 4. 配置SIP服务器
编辑 `config/sip_config.py`：
```python
SIP_SERVER = "your_sip_server_ip"
SIP_PORT = 5060
USERNAME = "your_username"
PASSWORD = "your_password"
```

## 🚀 快速启动

### 启动AI对话系统
```bash
python3 main.py
```

### 启动基础SIP系统
```bash
python3 main_ai.py
```

## 📞 使用方法

1. **注册分机** - 系统自动注册到SIP服务器
2. **接听来电** - 自动接听并启动AI对话
3. **语音交互** - 与Aiker进行自然语音对话
4. **智能回复** - AI根据上下文提供智能回复

## 🎯 功能特性

### AI对话功能
- ✅ 实时语音识别 (STT)
- ✅ 智能AI对话 (OpenAI GPT)
- ✅ 自然语音合成 (TTS)
- ✅ 中文语音支持
- ✅ 上下文理解
- ✅ 静音检测

### SIP电话功能
- ✅ 自动注册和认证
- ✅ 来电自动接听
- ✅ RTP音频传输
- ✅ 多路通话支持
- ✅ 通话状态管理

### 音频处理
- ✅ G.711音频编解码
- ✅ 实时音频流处理
- ✅ 音频格式转换
- ✅ 音频缓冲管理

## 🔧 配置选项

### AI对话配置
```python
# ai_conversation.py
SYSTEM_PROMPT = "你是Aiker，一个友好的AI助手..."
SILENCE_THRESHOLD = 1.5  # 静音检测阈值(秒)
MAX_AUDIO_LENGTH = 10    # 最大音频长度(秒)
```

### 音频配置
```python
# 音频处理参数
SAMPLE_RATE = 8000
CHUNK_SIZE = 1024
AUDIO_FORMAT = 'ulaw'
```

## 📊 监控和日志

系统提供详细的日志记录：
- 📞 SIP信令日志
- 🎤 音频处理日志
- 🤖 AI对话日志
- ⚠️ 错误和警告日志

日志文件位置：`logs/`

## 🐛 故障排除

### 常见问题

1. **API密钥错误**
   - 检查 `.env` 文件中的API密钥
   - 确认API密钥有效且有足够配额

2. **音频质量问题**
   - 检查网络连接稳定性
   - 调整音频处理参数

3. **AI回复延迟**
   - 检查API响应时间
   - 调整静音检测阈值

### 调试模式
启用详细日志：
```python
DEBUG = True
```

## 📈 性能优化

- 使用SSD存储提升音频处理速度
- 配置足够的内存用于音频缓冲
- 优化网络连接减少延迟
- 定期清理日志文件

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 📞 支持

如有问题，请提交Issue或联系开发团队。

---

**VTX AI Phone System v2.1** - 让AI对话更自然，让语音交互更智能！ 