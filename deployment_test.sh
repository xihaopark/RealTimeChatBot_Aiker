#!/bin/bash

# VTX AI Phone System - 增强版主程序部署测试脚本
# Aiker - OneSuite 商业客服机器人
# 基于100%通过的集成测试，进行实际通话测试

set -e

echo "🚀 Aiker - OneSuite 商业客服机器人 v2.0"
echo "=============================================="

# 1. 环境检查
echo "📋 Step 1: 环境检查..."
source venv/bin/activate

# 检查Python环境
echo "✅ Python环境: $(python --version)"

# 检查关键依赖
echo "📦 检查关键依赖..."
python -c "import asyncio, aiohttp; print('✅ 核心依赖正常')"

# 2. API密钥验证
echo ""
echo "🔑 Step 2: API密钥最终验证..."
python -c "
import sys
sys.path.insert(0, '.')
from src.utils.api_manager import api_manager

available = api_manager.get_available_services()
missing = api_manager.get_missing_services()

print(f'✅ 可用服务: {\",\".join(available)}')
if missing:
    print(f'⚠️ 缺失服务: {\",\".join(missing)}')
else:
    print('✅ 所有API密钥就绪')
"

# 3. 配置验证
echo ""
echo "⚙️ Step 3: 系统配置验证..."
python -c "
import sys
sys.path.insert(0, '.')
from config.settings import settings

print(f'✅ VTX服务器: {settings.vtx.server}:{settings.vtx.port}')
print(f'✅ SIP域: {settings.vtx.domain}')
print(f'✅ DID号码: {settings.vtx.did_number}')

ext = settings.get_extension('101')
if ext:
    print(f'✅ 分机101: {ext.username}')
else:
    print('❌ 分机101未配置')
    exit(1)
"

# 4. 组件状态检查
echo ""
echo "🔧 Step 4: 核心组件状态检查..."
python -c "
import sys, asyncio
sys.path.insert(0, '.')

async def check_components():
    # 检查Deepgram
    from src.ai.providers.deepgram_provider import DeepgramSTTProvider
    deepgram = DeepgramSTTProvider()
    print(f'✅ Deepgram STT: 已初始化')
    
    # 检查ElevenLabs
    from src.ai.providers.elevenlabs_provider import ElevenLabsTTSProvider
    elevenlabs = ElevenLabsTTSProvider()
    print(f'✅ ElevenLabs TTS: 已初始化')
    
    # 检查流式STT引擎
    from src.ai.enhanced.streaming_stt import StreamingSTTEngine
    stt_engine = StreamingSTTEngine()
    print(f'✅ 流式STT引擎: 已初始化')
    
    # 检查欢迎语音频
    from src.audio.welcome_messages import welcome_messages
    print(f'✅ 本地欢迎语音频: 已准备')
    
    print('🎯 所有核心组件就绪')

asyncio.run(check_components())
"

# 5. 启动增强版主程序
echo ""
echo "🚀 Step 5: 启动Aiker商业客服机器人..."
echo "=============================================="
echo "📞 系统即将启动，准备接听来电测试"
echo "📱 请拨打 DID: $(python -c "
import sys
sys.path.insert(0, '.')
from config.settings import settings
print(settings.vtx.did_number)
")"
echo ""
echo "🧪 测试项目:"
echo "  1. 系统启动和SIP注册"
echo "  2. 来电接听和SDP协商"  
echo "  3. RTP音频流建立"
echo "  4. 本地欢迎语播放（快速响应）"
echo "  5. 语音识别功能"
echo "  6. TTS合成和播放"
echo "  7. OneSuite相关回复"
echo "  8. 整体延迟测试"
echo ""
echo "🤖 Aiker功能:"
echo "  - 快速本地欢迎语播放"
echo "  - 智能语音识别"
echo "  - OneSuite商业信息回复"
echo "  - 关键词匹配客服"
echo ""
echo "按 Ctrl+C 可以随时停止测试"
echo "=============================================="
echo ""

# 启动增强版主程序
python src/main_enhanced.py 