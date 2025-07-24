#!/bin/bash

# 检查Vosk模型下载状态

echo "🔍 Checking Vosk STT model download status..."
echo "================================================"

cd services/vosk

echo "📁 Vosk directory:"
pwd

echo -e "\n📊 Models directory status:"
if [ -d "models" ]; then
    echo "✅ Models directory exists"
    echo "📂 Models directory size: $(du -sh models 2>/dev/null | cut -f1)"
    
    echo -e "\n🔍 Downloaded models:"
    ls -la models/ 2>/dev/null || echo "❌ Models directory empty"
    
    echo -e "\n📝 Download files in progress:"
    find . -name "*.zip" -o -name "*download*" -o -name "*.tmp" 2>/dev/null || echo "❌ No active downloads found"
    
    echo -e "\n⚙️ Active download processes:"
    ps aux | grep -E "(wget|curl)" | grep -v grep || echo "❌ No active download processes"
    
    echo -e "\n📏 Expected model sizes:"
    echo "Chinese (vosk-model-cn-0.22): ~1.3GB"
    echo "English (vosk-model-en-us-0.22): ~1.8GB"
    
else
    echo "❌ Models directory not found"
fi

echo -e "\n🎯 Manual download commands:"
echo "cd services/vosk/models"
echo "wget https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip"
echo "wget https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip"
echo "unzip vosk-model-cn-0.22.zip"
echo "unzip vosk-model-en-us-0.22.zip"