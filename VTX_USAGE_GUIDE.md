# VTX AI Phone System 使用指南

## 🚀 快速启动

### 主要启动脚本
```bash
./start_vtx.sh
```
这是主要的启动脚本，会自动：
- 检查Python环境
- 检查主程序文件（优先使用 `main.py`）
- 检查配置文件和API密钥
- 停止已运行的旧进程
- 启动VTX AI电话系统

### 系统监控
```bash
./monitor_vtx.sh
```
监控脚本会显示：
- VTX进程状态
- 端口监听状态
- 文件状态
- 网络连接
- 系统资源使用情况

### 测试工具
```bash
./test_vtx.sh
```
交互式测试工具，提供以下功能：
1. 启动VTX系统
2. 停止VTX系统
3. 重启VTX系统
4. 生成测试音频
5. 测试音频播放
6. 检查系统状态
7. 测试网络连接
8. 清理缓存

## 📁 文件结构

### 主程序文件
- `main.py` - **当前使用的主程序**（增强版，包含RTP调试）
- `src/main.py` - 原始AI版本主程序

### 配置文件
- `config/settings.py` - 系统配置
- `api_keys/` - API密钥目录

### 音频文件
- `audio_cache/` - 音频缓存目录
- `audio_cache/welcome_audio.ulaw` - 欢迎语音（μ-law格式）
- `audio_cache/welcome_audio.wav` - 欢迎语音（WAV格式）

### 测试文件
- `test_audio_generation.py` - 生成测试音频
- `test_audio_playback.py` - 测试音频播放
- `test_vtx.sh` - 系统测试工具

## 🎯 使用流程

### 1. 首次启动
```bash
# 启动系统
./start_vtx.sh

# 检查状态
./monitor_vtx.sh
```

### 2. 日常使用
```bash
# 启动系统
./start_vtx.sh

# 等待来电：14088779998
# 系统会自动接听并播放AI欢迎语音
```

### 3. 故障排除
```bash
# 使用测试工具
./test_vtx.sh

# 选择相应选项进行测试
```

## 🔧 常见操作

### 启动系统
```bash
./start_vtx.sh
```

### 停止系统
```bash
pkill -f "python3.*main.py"
```

### 重启系统
```bash
./test_vtx.sh
# 选择选项3：重启VTX系统
```

### 检查状态
```bash
./monitor_vtx.sh
```

### 生成新测试音频
```bash
python3 test_audio_generation.py
```

### 清理缓存
```bash
./test_vtx.sh
# 选择选项8：清理缓存
```

## 📞 测试号码

- **主测试号码**: 14088779998
- **分机**: 101
- **服务器**: core1-us-lax.myippbx.com

## 🎵 音频功能

### 当前音频设置
- **采样率**: 8000Hz
- **编码**: μ-law (PCMU)
- **声道**: 单声道
- **包大小**: 160字节（20ms）

### 音频文件
- 欢迎语音：440Hz正弦波测试音频
- 格式：μ-law (.ulaw) 和 WAV (.wav)

## 🔍 调试信息

当前版本包含详细的RTP调试信息：
- RTP包接收状态
- 音频数据解析
- Payload type识别
- 音频发送状态

## ⚠️ 注意事项

1. **主程序文件**: 当前使用 `main.py`（根目录），不是 `src/main.py`
2. **API密钥**: 确保 `api_keys/` 目录中有正确的API密钥文件
3. **网络连接**: 确保能访问VTX服务器
4. **端口**: 系统会自动分配RTP端口（10000-20000范围）

## 🆘 故障排除

### 系统无法启动
1. 检查Python环境：`python3 --version`
2. 检查依赖：`pip3 list`
3. 检查配置文件：`ls -la config/`

### 听不到音频
1. 检查音频缓存：`ls -la audio_cache/`
2. 重新生成测试音频：`python3 test_audio_generation.py`
3. 查看调试信息：启动时会有详细的RTP日志

### 网络连接问题
1. 测试服务器连接：`ping core1-us-lax.myippbx.com`
2. 检查DNS解析：`nslookup core1-us-lax.myippbx.com`
3. 检查防火墙设置

### 进程管理
- 查看进程：`ps aux | grep python3`
- 停止进程：`pkill -f "python3.*main.py"`
- 重启系统：使用 `./test_vtx.sh` 选项3 