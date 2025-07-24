#!/bin/bash

# VTX AI电话系统环境设置脚本
# 一键修复所有已知问题

echo "🔧 VTX AI电话系统环境设置"
echo "=" * 50

# 1. 安装必要的系统包
echo "📦 安装系统依赖..."
apt-get update
apt-get install -y alsa-utils pulseaudio-utils libasound2-plugins

# 2. 修复cuDNN依赖
echo "🔗 修复cuDNN符号链接..."
if [ ! -f "/usr/lib/x86_64-linux-gnu/libcudnn_graph.so.9.1.0" ]; then
    ln -sf /usr/lib/x86_64-linux-gnu/libcudnn_cnn_infer.so.8 /usr/lib/x86_64-linux-gnu/libcudnn_graph.so.9.1.0
    ln -sf /usr/lib/x86_64-linux-gnu/libcudnn_cnn_infer.so.8 /usr/lib/x86_64-linux-gnu/libcudnn_graph.so.9.1
    ln -sf /usr/lib/x86_64-linux-gnu/libcudnn_cnn_infer.so.8 /usr/lib/x86_64-linux-gnu/libcudnn_graph.so.9
    ln -sf /usr/lib/x86_64-linux-gnu/libcudnn_cnn_infer.so.8 /usr/lib/x86_64-linux-gnu/libcudnn_graph.so
    echo "✅ cuDNN符号链接已创建"
else
    echo "✅ cuDNN符号链接已存在"
fi

# 3. 配置ALSA虚拟音频设备
echo "🎵 配置ALSA虚拟音频设备..."
mkdir -p /etc/alsa/conf.d
cat > /etc/alsa/conf.d/99-null.conf << 'EOF'
# Null audio device configuration for container environments
pcm.!default {
    type null
}

ctl.!default {
    type null
}

# Dummy devices for compatibility
pcm.cards {
    type null
}
pcm.dmix {
    type null
}
pcm.pulse {
    type null
}
EOF
echo "✅ ALSA配置已更新"

# 4. 设置环境变量
echo "🌐 设置环境变量..."
cat >> ~/.bashrc << 'EOF'

# VTX AI电话系统环境变量
export ALSA_PCM_CARD=null
export ALSA_PCM_DEVICE=0
export SDL_AUDIODRIVER=dummy
export CUDA_VISIBLE_DEVICES=0
export TRANSFORMERS_VERBOSITY=error
EOF

# 5. 应用当前会话环境变量
export ALSA_PCM_CARD=null
export ALSA_PCM_DEVICE=0
export SDL_AUDIODRIVER=dummy
export CUDA_VISIBLE_DEVICES=0
export TRANSFORMERS_VERBOSITY=error

echo "✅ 环境变量已设置"

# 6. 验证CUDA环境
echo "🧪 验证CUDA环境..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    echo "✅ CUDA环境正常"
else
    echo "⚠️ CUDA不可用（非GPU环境）"
fi

# 7. 创建必要目录
echo "📁 创建必要目录..."
mkdir -p logs recordings data

echo ""
echo "🎉 环境设置完成！"
echo ""
echo "💡 使用以下命令启动系统："
echo "   ./start_ai_fixed.sh"
echo ""
echo "🔍 测试SIP注册："
echo "   python test_sip_fixed.py"
echo ""