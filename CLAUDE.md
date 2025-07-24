# VTX AI Phone System - Claude Memory

## 项目概述
这是一个基于本地AI的实时电话客服系统，集成了SIP协议、RTP音频传输、STT语音识别、TTS语音合成和LLM对话功能。

## 核心架构
- **SIP客户端**: 处理IP电话协议，注册分机和接听电话
- **RTP处理器**: 处理实时音频流传输
- **本地AI服务**: 
  - STT: 使用RealtimeSTT + Whisper进行语音识别
  - TTS: 使用RealtimeTTS进行语音合成
  - LLM: 使用Transformers + Qwen2.5-7B进行对话生成

## 主要文件结构
```
├── main_local_ai.py          # 本地AI版本主程序
├── production_local_ai.py    # 生产版本主程序
├── sip_client.py            # SIP客户端实现
├── rtp_handler.py           # RTP音频处理
├── config/
│   ├── settings.py          # 统一配置管理
│   └── local_ai_config.py   # 本地AI配置
├── local_ai/
│   ├── local_stt.py         # 本地语音识别
│   ├── local_tts.py         # 本地语音合成
│   ├── local_llm.py         # 本地大语言模型
│   └── audio_converter.py   # 音频格式转换
└── logs/                    # 日志目录
```

## 已解决问题
1. ✅ **cuDNN依赖问题**: 通过创建符号链接修复
2. ✅ **ALSA音频问题**: 配置虚拟音频设备解决
3. ✅ **SIP注册失败**: 修复同步注册机制
4. ✅ **TTS音频生成警告**: 优化音频流处理
5. ✅ **Transformers生成参数**: 移除不兼容参数

## 技术栈
- Python 3.10
- CUDA/cuDNN (GPU加速)
- PyTorch + Transformers
- RealtimeSTT/RealtimeTTS
- SIP协议栈
- RTP音频传输

## 配置要求
- VTX SIP服务器: core1-us-lax.myippbx.com:5060
- 支持CUDA的GPU环境
- 音频设备支持 (ALSA)

## 启动脚本
- `start_local_ai.sh`: 启动本地AI版本
- `start_production.sh`: 启动生产版本

## 关键技术实现

### SIP注册机制 (至关重要)
**必须使用同步注册流程**，异步注册会导致注册失败！

#### 关键组件：
1. **响应队列机制**: `register_response_queue = queue.Queue()`
2. **同步等待**: `waiting_for_register = True`
3. **CSeq匹配**: 确保注册响应与请求匹配

#### 注册流程：
```python
# Step 1: 发送初始REGISTER (无认证)
self.cseq += 1
self.current_cseq = self.cseq
self.waiting_for_register = True

# Step 2: 同步等待响应 
response = self.register_response_queue.get(timeout=10)

# Step 3: 处理407认证挑战，发送带认证的REGISTER  
# Step 4: 再次同步等待200 OK
```

#### 关键注册头部字段：
```sip
Via: SIP/2.0/UDP {local_ip}:{local_port};branch={branch};rport
From: <sip:{username}@{domain}>;tag={from_tag}
Call-ID: {uuid}@{local_ip}
Contact: <sip:{username}@{local_ip}:{local_port}>
User-Agent: VTX-AI-System/1.0
Expires: 60
```

### 音频编码/解码

#### G.711 μ-law编码 (RTP Payload Type 0)
- **采样率**: 8kHz
- **包大小**: 160字节 (20ms音频)  
- **编码公式**: PCM16 -> μ-law压缩
- **RTP时间戳增量**: 160 (每20ms包)

#### 音频处理流程：
```python
# 接收音频: RTP -> μ-law -> PCM16
rtp_packet = parse_rtp_packet(data)
mulaw_audio = rtp_packet['payload'] 
pcm_audio = G711Codec.mulaw_to_pcm(mulaw_audio)

# 发送音频: PCM16/AI生成音频 -> μ-law -> RTP
ai_audio = tts_service.synthesize_text(text)
mulaw_data = AudioConverter.convert_pcm16k_to_rtp(ai_audio)  
send_rtp_packet(mulaw_data, payload_type=0)
```

#### 音频同步：
- **包间隔**: 20ms (time.sleep(0.02))
- **序列号**: 每包递增1
- **时间戳**: 每包递增160 (@8kHz)

### RTP处理关键点
```python
# RTP头部构建
header = struct.pack('!BBHII',
    0x80,           # V=2, P=0, X=0, CC=0  
    payload_type,   # 0=PCMU, 8=PCMA
    sequence,       # 包序列号
    timestamp,      # 时间戳
    ssrc)           # 同步源标识

# 音频分包发送 (160字节/包)
chunk_size = 160
for i in range(0, len(audio_data), chunk_size):
    chunk = audio_data[i:i+chunk_size]
    if len(chunk) < chunk_size:
        chunk += b'\\x7f' * (chunk_size - len(chunk))  # 填充
    rtp_handler.send_audio(chunk)
    time.sleep(0.02)  # 20ms间隔
```

## 故障排除

### SIP注册失败
1. **检查同步机制**: 确保使用`register_response_queue`
2. **验证认证参数**: realm, nonce, 用户名密码
3. **检查网络**: 防火墙，NAT设置
4. **调试CSeq匹配**: 确保响应CSeq与请求匹配

### 音频问题  
1. **ALSA错误**: 
   ```bash
   # 安装必要的ALSA插件
   apt-get install -y libasound2-plugins
   
   # 配置虚拟音频设备
   echo 'pcm.!default { type null }' > /etc/alsa/conf.d/99-null.conf
   ```

2. **cuDNN缺失**: 
   ```bash
   sudo ln -sf /usr/lib/x86_64-linux-gnu/libcudnn_cnn_infer.so.8 \
               /usr/lib/x86_64-linux-gnu/libcudnn_graph.so.9.1.0
   ```

3. **TTS音频生成警告**: 
   - 设置环境变量: `SDL_AUDIODRIVER=dummy`
   - 使用 `play_realtime=False` 禁用实时播放
   - 改进音频流超时处理机制

4. **Transformers生成警告**:
   ```python
   # 移除不兼容的参数
   outputs = model.generate(
       max_new_tokens=150,
       temperature=0.7,
       repetition_penalty=1.1
       # 不使用: length_penalty, early_stopping
   )
   ```

## 常用命令
```bash
# 检查CUDA环境
nvidia-smi

# 检查cuDNN
python -c "import torch; print(torch.backends.cudnn.is_available())"

# 一键环境设置（推荐）
./setup_environment.sh

# 使用修复版启动脚本
./start_ai_fixed.sh

# 测试SIP注册功能
python test_sip_fixed.py

# 调试SIP注册
tcpdump -i any -n port 5060

# 调试RTP音频  
tcpdump -i any -n portrange 10000-10500

# 静音Transformers警告
export TRANSFORMERS_VERBOSITY=error
```