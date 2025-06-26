# VTX AI Phone System v2.0

🚀 **基于H100 GPU的高性能AI电话系统** - 在101分机上实现基础AI语音对话功能

## 🎯 项目概述

VTX AI Phone System 是一个集成SIP/RTP协议的智能电话系统，支持实时AI语音对话。系统采用本地服务器+外部API混合架构，在2x H100 GPU环境下运行，目标响应延迟<800ms。

### ✨ 核心特性

- 🎤 **流式语音识别** - Deepgram + Whisper本地备选
- 🔊 **高品质语音合成** - ElevenLabs + Edge-TTS备选  
- 🧠 **智能对话管理** - GPT-4o-mini + 多轮对话
- 📞 **SIP/RTP集成** - 与VTX电话系统无缝对接
- ⚡ **高性能优化** - 目标延迟800ms，支持并发
- 🔧 **模块化架构** - 易于扩展和维护

## 🏗️ 系统架构

```
VTX AI Phone System
├── 📞 SIP/RTP 协议层
├── 🎤 语音识别层 (Deepgram + Whisper)
├── 🧠 AI对话层 (OpenAI GPT)
├── 🔊 语音合成层 (ElevenLabs + Edge-TTS)
└── 🔧 系统管理层 (配置 + 监控)
```

## 📋 开发计划

### Phase 1: 基础架构搭建 ✅
- [x] 项目结构重组
- [x] API密钥管理系统
- [x] 增强配置系统
- [x] 性能监控工具

### Phase 2: 核心组件开发 🔄
- [ ] 流式STT引擎
- [ ] 第三方提供商实现
- [ ] 智能LLM处理器
- [ ] 实时对话管理器

### Phase 3: 系统集成 📋
- [ ] 主程序集成
- [ ] 完整对话流程
- [ ] 错误处理和回退

### Phase 4: 测试验证 📋
- [ ] 单元测试
- [ ] 集成测试
- [ ] 性能测试
- [ ] 实际通话测试

## 🚀 快速开始

### 环境要求

- **硬件**: 2x H100 GPU服务器
- **系统**: Linux/macOS
- **Python**: 3.8+
- **网络**: 稳定的互联网连接

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/xihaopark/RealTimeChatBot_Aiker.git
cd vtx-llm-bot
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置API密钥**
```bash
# 复制模板文件
cp api_keys/templates/*.template api_keys/

# 编辑并填入你的API密钥
# - api_keys/deepgram.key
# - api_keys/elevenlabs.key  
# - api_keys/openai.key
```

5. **配置系统设置**
```bash
cp env.example .env
# 编辑.env文件，配置VTX服务器信息
```

6. **启动系统**
```bash
python src/main.py
```

## 🔑 API服务配置

### 必需的付费API服务

| 服务 | 用途 | 费用 | 申请链接 |
|------|------|------|----------|
| **Deepgram** | 流式语音识别 | $0.0043/分钟 | [申请](https://deepgram.com/) |
| **ElevenLabs** | 高品质语音合成 | $0.18/1000字符 | [申请](https://elevenlabs.io/) |
| **OpenAI** | 智能对话生成 | 按使用量计费 | [申请](https://platform.openai.com/) |

### 预估成本
- **每月1000分钟通话**: $20-35
- **Deepgram**: $4.30
- **ElevenLabs**: $15-30 (取决于回复长度)

## 📁 项目结构

```
vtx-llm-bot/
├── 📁 api_keys/                 # API密钥管理
│   ├── .gitignore              # 保护敏感文件
│   ├── README.md               # 密钥管理说明
│   └── templates/              # 密钥模板
├── 📁 config/                  # 配置管理
│   ├── settings.py             # 基础配置
│   └── enhanced/               # 增强配置
│       └── conversation_config.py
├── 📁 src/                     # 源代码
│   ├── 📁 ai/                  # AI模块
│   │   ├── enhanced/           # 增强AI模块
│   │   ├── providers/          # 第三方提供商
│   │   └── ...                 # 原有AI模块
│   ├── 📁 utils/               # 工具模块
│   │   ├── api_manager.py      # API密钥管理
│   │   ├── performance_monitor.py # 性能监控
│   │   └── audio_utils.py      # 音频工具
│   ├── 📁 sip/                 # SIP协议
│   ├── 📁 rtp/                 # RTP协议
│   ├── 📁 sdp/                 # SDP协议
│   └── main.py                 # 主程序
├── 📁 docs/                    # 文档
│   ├── COLLABORATION_GUIDE.md  # 协作协议
│   ├── design-decisions.md     # 设计决策
│   └── feedback-log.md         # 反馈日志
├── 📁 logs/                    # 日志文件
├── 📁 temp/                    # 临时文件
├── requirements.txt            # 依赖包
├── sync_to_github.sh          # 同步脚本
└── README.md                   # 项目说明
```

## 🔧 配置说明

### 基础配置 (config/settings.py)
```python
# VTX服务器配置
VTX_SERVER = "your_vtx_server"
VTX_PORT = 5060
VTX_DOMAIN = "your_domain"
DID_NUMBER = "your_did_number"

# 分机配置
EXTENSIONS = {
    "101": {
        "username": "101",
        "password": "your_password"
    }
}
```

### 增强配置 (configs/enhanced/conversation_config.py)
```python
# 性能配置
target_latency = 0.8  # 目标延迟800ms
enable_streaming = True
enable_local_fallback = True

# AI服务配置
stt_primary = "deepgram"
tts_primary = "elevenlabs"
llm_primary = "gpt-4o-mini"
```

## 📊 性能指标

### 目标性能
- **响应延迟**: <800ms
- **语音识别准确率**: >95%
- **语音合成质量**: 接近真人
- **系统可用性**: >99.9%

### 监控指标
- 实时响应时间
- STT/TTS延迟
- 错误率和成功率
- 系统资源使用

## 🤝 协作开发

本项目采用**用户决策 + Claude设计 + Cursor执行**的协作模式：

- **用户**: 项目目标、功能需求、优先级决策
- **Claude**: 技术方案设计、架构规划、可行性分析  
- **Cursor**: 代码实现、环境配置、调试部署

详细协作协议请参考 [docs/COLLABORATION_GUIDE.md](docs/COLLABORATION_GUIDE.md)

## 🧪 测试

### 运行测试
```bash
# 单元测试
pytest src/tests/

# 集成测试
pytest src/tests/integration/

# 性能测试
python -m pytest src/tests/ -k "performance"
```

### 测试覆盖
- 语音识别准确性
- 语音合成质量
- 对话流程完整性
- 性能指标达标
- 错误处理机制

## 📈 部署

### 生产环境部署
```bash
# 1. 环境准备
./deploy.sh prepare

# 2. 安装依赖
./deploy.sh install

# 3. 配置服务
./deploy.sh configure

# 4. 启动服务
./deploy.sh start
```

### 监控和维护
```bash
# 查看性能报告
python -c "from src.utils.performance_monitor import performance_monitor; performance_monitor.print_performance_report()"

# 检查API状态
python -c "from src.utils.api_manager import api_manager; api_manager.print_status()"
```

## 📝 更新日志

### v2.0.0 (2024-01-XX)
- 🎉 全新架构设计
- 🚀 集成Deepgram + ElevenLabs
- 📊 性能监控系统
- 🔧 模块化重构
- 📚 完善文档体系

### v1.0.0 (2024-01-XX)
- 🎯 基础SIP/RTP集成
- 🎤 Whisper语音识别
- 🔊 Edge-TTS语音合成
- 🤖 OpenAI对话集成

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🤝 贡献

欢迎提交Issue和Pull Request！

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 📞 支持

- 📧 邮箱: [your-email@example.com]
- 🐛 Issues: [GitHub Issues](https://github.com/xihaopark/RealTimeChatBot_Aiker/issues)
- 📚 文档: [项目Wiki](https://github.com/xihaopark/RealTimeChatBot_Aiker/wiki)

---

**VTX AI Phone System** - 让AI电话更智能，让沟通更自然 🚀