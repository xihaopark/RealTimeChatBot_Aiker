# API密钥管理

## 配置说明
请将各服务的API密钥保存到对应文件中：

- `deepgram.key` - Deepgram语音识别API密钥
- `elevenlabs.key` - ElevenLabs语音合成API密钥  
- `openai.key` - OpenAI GPT API密钥

## 文件格式
每个文件只包含一行，即API密钥字符串，无需额外格式。

## 安全提醒
- 这些文件已被添加到.gitignore，不会提交到代码库
- 请妥善保管API密钥，避免泄露
- 定期检查API使用量和费用

## 申请链接
- **Deepgram**: https://deepgram.com/ (语音识别，$0.0043/分钟)
- **ElevenLabs**: https://elevenlabs.io/ (语音合成，$0.18/1000字符)
- **OpenAI**: https://platform.openai.com/ (已有配置)

## 费用预估
每月1000分钟通话约需 $20-35 