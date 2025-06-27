# VTX AI Phone System v2.0 - AI对话版

一个集成了AI对话功能的智能电话系统，支持SIP注册、RTP音频处理和智能语音对话。

## 🚀 新功能

### AI对话机器人
- **语音识别 (STT)** - 使用Deepgram API实时语音转文字
- **智能对话 (LLM)** - 使用OpenAI ChatGPT生成自然回复
- **语音合成 (TTS)** - 使用ElevenLabs API生成高质量语音
- **流式对话** - 实时语音交互，支持连续对话

### 对话流程
```
用户语音 → Deepgram STT → ChatGPT → ElevenLabs TTS → 播放回复
```

## 📋 系统要求

- Python 3.8+
- 网络连接
- 三个API密钥：
  - OpenAI API Key (ChatGPT)
  - Deepgram API Key (语音识别)
  - ElevenLabs API Key (语音合成)

## 🛠️ 安装

1. **克隆仓库**
```bash
git clone <repository-url>
cd vtx-voip
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置API密钥**
```bash
# 在 api_keys/ 目录下创建密钥文件
echo "your_openai_api_key" > api_keys/openai.key
echo "your_deepgram_api_key" > api_keys/deepgram.key
echo "your_elevenlabs_api_key" > api_keys/elevenlabs.key
```

4. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，填入VTX服务器配置
```

## 🎯 使用方法

### 启动AI对话系统
```bash
python3 main_ai.py
```

### 启动传统音频系统
```bash
python3 main.py
```

## 📞 功能特性

### AI对话功能
- ✅ 实时语音识别
- ✅ 智能对话生成
- ✅ 高质量语音合成
- ✅ 上下文理解
- ✅ 自然语言交互
- ✅ 自动回退机制

### 电话系统功能
- ✅ SIP注册和认证
- ✅ 来电接听
- ✅ RTP音频处理
- ✅ 多分机支持
- ✅ 通话管理

## 🔧 配置说明

### API配置
- **OpenAI**: 用于生成AI回复，支持GPT-3.5-turbo
- **Deepgram**: 用于语音识别，支持中文识别
- **ElevenLabs**: 用于语音合成，支持自然语音

### 系统配置
- **VTX服务器**: SIP服务器地址和端口
- **分机配置**: 用户名、密码和描述
- **RTP端口**: 音频传输端口范围
- **日志级别**: 系统日志详细程度

## 📊 版本历史

### v2.0 - AI对话版 (当前)
- 🆕 集成AI对话功能
- 🆕 支持语音识别和合成
- 🆕 智能对话机器人
- 🆕 流式语音交互

### v1.0 - 基础版
- ✅ SIP注册和认证
- ✅ 来电接听
- ✅ RTP音频处理
- ✅ DTMF音调播放

## 🤖 AI对话示例

```
用户: "你好"
AI: "您好！我是VTX AI助手，很高兴为您服务。请告诉我您需要什么帮助？"

用户: "今天天气怎么样？"
AI: "抱歉，我无法获取实时天气信息，但我可以帮您查找天气预报网站或应用程序。"

用户: "谢谢"
AI: "不客气！如果还有其他问题，随时欢迎找我聊天。祝您愉快！"
```

## 🔍 故障排除

### 常见问题
1. **API密钥错误** - 检查api_keys/目录下的密钥文件
2. **网络连接问题** - 确认服务器地址和端口配置
3. **音频问题** - 检查RTP端口是否被占用
4. **AI功能不可用** - 确认API密钥有效且有足够配额

### 日志查看
系统运行时会输出详细日志，包括：
- SIP注册状态
- 通话建立过程
- AI对话交互
- 错误信息

## 📝 开发说明

### 文件结构
```
vtx-voip/
├── main_ai.py              # AI对话主程序
├── main.py                 # 传统音频主程序
├── ai_conversation.py      # AI对话模块
├── api_keys/               # API密钥目录
├── config/                 # 配置文件
├── requirements.txt        # 依赖包列表
└── README.md              # 说明文档
```

### 扩展开发
- 支持更多AI模型
- 添加多语言支持
- 集成更多TTS服务
- 增加情感分析功能

## 📄 许可证

本项目仅供学习和研究使用。

## 🤝 贡献

欢迎提交Issue和Pull Request来改进项目。

---

**VTX AI Phone System v2.0** - 让电话更智能！🎉 