#!/bin/bash

# 修复后的AI电话系统启动脚本

echo "🚀 启动修复后的AI电话系统..."

# 激活GPU环境
source gpu_env/bin/activate

# 设置环境变量
export CUDA_VISIBLE_DEVICES=0
export ALSA_PCM_CARD=null
export ALSA_PCM_DEVICE=0

# 检查CUDA环境
echo "🔍 检查CUDA环境..."
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('cuDNN available:', torch.backends.cudnn.is_available())"

if [ $? -ne 0 ]; then
    echo "❌ CUDA环境检查失败"
    exit 1
fi

# 创建日志目录
mkdir -p logs

echo "✅ 环境检查完成，启动系统..."

# 测试SIP注册功能
echo "🧪 测试SIP注册..."
python test_sip_fixed.py

if [ $? -eq 0 ]; then
    echo "✅ SIP注册测试通过，启动完整系统..."
    # 启动生产系统
    python production_local_ai.py
else
    echo "❌ SIP注册测试失败，请检查网络和配置"
    exit 1
fi