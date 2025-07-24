#!/bin/bash

# Vosk STT 自动安装脚本
# 下载Vosk模型文件

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🔧 Setting up Vosk STT...${NC}"

# 创建目录
mkdir -p vosk/models
cd vosk/models

# 下载中文模型
echo -e "${YELLOW}Downloading Chinese model (vosk-model-cn-0.22)...${NC}"
if [ ! -d "vosk-model-cn-0.22" ]; then
    wget -O vosk-model-cn-0.22.zip "https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip"
    unzip vosk-model-cn-0.22.zip
    rm vosk-model-cn-0.22.zip
    echo -e "${GREEN}✅ Chinese model downloaded${NC}"
else
    echo -e "${GREEN}✅ Chinese model already exists${NC}"
fi

# 下载英文模型 (使用较小的模型以节省空间)
echo -e "${YELLOW}Downloading English model (vosk-model-en-us-0.22)...${NC}"
if [ ! -d "vosk-model-en-us-0.22" ]; then
    wget -O vosk-model-en-us-0.22.zip "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip"
    unzip vosk-model-en-us-0.22.zip
    rm vosk-model-en-us-0.22.zip
    echo -e "${GREEN}✅ English model downloaded${NC}"
else
    echo -e "${GREEN}✅ English model already exists${NC}"
fi

# 返回上级目录
cd ..

# 创建测试脚本
cat > test_vosk.py << 'EOF'
#!/usr/bin/env python3
"""测试Vosk STT功能"""

import sys
import os
sys.path.append('../../aiker_v2')

try:
    from stt_service import VoskSTTService
    
    print("Testing Vosk STT Service...")
    
    stt = VoskSTTService()
    
    print(f"Available languages: {stt.get_supported_languages()}")
    print(f"Service stats: {stt.get_stats()}")
    
    if stt.is_available():
        print("✅ Vosk STT Service is working!")
    else:
        print("❌ Vosk STT Service not available")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please install required packages: pip install vosk soundfile numpy")
except Exception as e:
    print(f"❌ Error: {e}")
EOF

chmod +x test_vosk.py

echo -e "${GREEN}🎉 Vosk STT setup completed!${NC}"
echo ""
echo "Models installed:"
echo "  - Chinese: $(pwd)/models/vosk-model-cn-0.22"
echo "  - English: $(pwd)/models/vosk-model-en-us-0.22"
echo ""
echo "To test the installation:"
echo "  cd services/vosk && python test_vosk.py"