# API密钥管理

## 🎯 当前状态
**✅ API密钥已配置完成！**

所有必需的API密钥已正确设置并测试可用：
- ✅ Deepgram STT API密钥
- ✅ ElevenLabs TTS API密钥  
- ✅ OpenAI GPT API密钥

## 📁 文件结构
```
api_keys/
├── README.md              # 本文档
├── .gitignore            # Git忽略规则
├── templates/            # 模板文件（可提交到Git）
│   ├── deepgram.key.template
│   ├── elevenlabs.key.template
│   └── openai.key.template
├── deepgram.key          # 实际密钥文件（本地，不提交）
├── elevenlabs.key        # 实际密钥文件（本地，不提交）
└── openai.key           # 实际密钥文件（本地，不提交）
```

## 🔐 安全配置
- ✅ 所有`.key`文件已添加到`.gitignore`
- ✅ 模板文件不包含真实密钥
- ✅ 本地密钥文件受保护，不会上传到GitHub
- ✅ 密钥格式：纯文本，每行一个密钥

## 🚀 使用方法
1. **复制模板**：`cp templates/deepgram.key.template deepgram.key`
2. **编辑密钥**：将`your_deepgram_api_key_here`替换为真实密钥
3. **验证配置**：运行集成测试验证密钥有效性

## 💰 费用预估
基于当前配置的API服务：

| 服务 | 费率 | 1000分钟通话 | 月费用 |
|------|------|-------------|--------|
| Deepgram STT | $0.0043/分钟 | $4.30 | $4.30 |
| ElevenLabs TTS | $0.18/1000字符 | $5-15 | $5-15 |
| OpenAI GPT | $0.002/1K tokens | $2-8 | $2-8 |
| **总计** | - | **$11-27** | **$11-27** |

## 🔗 申请链接
- **Deepgram**: https://deepgram.com/ (语音识别)
- **ElevenLabs**: https://elevenlabs.io/ (语音合成)
- **OpenAI**: https://platform.openai.com/ (GPT模型)

## 🧪 测试验证
运行以下命令验证API密钥配置：
```bash
python src/tests/integration_test.py
```

## ⚠️ 安全提醒
- 🔒 密钥文件永远不会提交到GitHub
- 🔒 定期检查API使用量和费用
- 🔒 如发现异常使用，立即轮换密钥
- 🔒 生产环境建议使用环境变量

## 📝 更新日志
- **2024-12-19**: 完成所有API密钥配置
- **2024-12-19**: 更新安全配置和文档
- **2024-12-19**: 添加费用预估和使用指南 