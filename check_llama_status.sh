#!/bin/bash

# 检查Llama.cpp编译状态

echo "🔍 Checking Llama.cpp compilation status..."
echo "================================================"

cd services/llama.cpp

echo "📁 Project directory:"
pwd

echo -e "\n📊 Build directory status:"
if [ -d "build" ]; then
    echo "✅ Build directory exists"
    echo "📂 Build directory size: $(du -sh build 2>/dev/null | cut -f1)"
    
    echo -e "\n🔍 Looking for compiled binaries:"
    find build -name "*server*" -o -name "llama-server" -o -name "*main*" 2>/dev/null || echo "❌ No server binaries found yet"
    
    echo -e "\n📝 Recent build activity:"
    find build -name "*.o" -o -name "*.so" -newer build/CMakeCache.txt 2>/dev/null | wc -l | xargs echo "Object files created:"
    
    echo -e "\n⚙️ Active compilation processes:"
    ps aux | grep -E "(cmake|make|g\+\+|gcc|nvcc)" | grep -v grep || echo "❌ No active compilation processes"
    
else
    echo "❌ Build directory not found"
fi

echo -e "\n🎯 Expected server location:"
echo "Should be: $(pwd)/server (symlink to build output)"
ls -la server 2>/dev/null || echo "❌ Server binary not ready"

echo -e "\n📋 To manually complete compilation:"
echo "cd services/llama.cpp/build"
echo "cmake --build . --config Release -j\$(nproc)"