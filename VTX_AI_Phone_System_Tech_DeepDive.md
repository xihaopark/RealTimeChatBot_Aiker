# VTX AI Phone System 底层通信技术实现细节

## 1. TTS生成与音频格式
- TTS（ElevenLabs）生成音频为MP3格式，采样率44.1kHz。
- 使用`pydub`将MP3解码为PCM，重采样为8kHz，单声道。
- PCM数据通过G.711 μ-law算法编码为8kHz、8bit、单声道μ-law音频流。
- μ-law编码后，音频以160字节为一帧（20ms/帧）进行分片。

**关键代码片段：**
```python
# MP3转μ-law
from pydub import AudioSegment
import numpy as np

audio = AudioSegment.from_mp3(io.BytesIO(mp3_data))
audio = audio.set_frame_rate(8000).set_channels(1)
samples = np.array(audio.get_array_of_samples())
ulaw_samples = linear_to_ulaw(samples)  # G.711 μ-law编码
```

## 2. RTP打包与包结构
- 每帧μ-law音频数据（160字节）被打包进RTP包。
- RTP包结构：
  - 12字节RTP头部
  - 160字节μ-law音频payload
- RTP头部字段：
  - Version: 2 (2 bits)
  - Padding: 0 (1 bit)
  - Extension: 0 (1 bit)
  - CSRC Count: 0 (4 bits)
  - Marker: 0 (1 bit)
  - Payload Type: 0 (PCMU, μ-law)
  - Sequence Number: 16 bits, 每包递增
  - Timestamp: 32 bits, 每帧+160
  - SSRC: 32 bits, 随机生成

**关键代码片段：**
```python
# RTP打包
header = struct.pack('!BBHII', 0x80, payload_type, sequence, timestamp, ssrc)
packet = header + ulaw_payload  # ulaw_payload为160字节
```

## 3. SIP信令流程
- 客户端向101发起呼叫，流程如下：
  1. **INVITE**：携带SDP，声明RTP端口、编解码类型（PCMU/8000）
  2. **101端响应 200 OK**：返回SDP，声明自身RTP端口
  3. **ACK**：确认建立会话
- SDP内容示例：
```
v=0
o=- 1234567890 1234567890 IN IP4 192.168.1.100
s=VTX AI Phone
c=IN IP4 192.168.1.100
t=0 0
m=audio 10000 RTP/AVP 0
a=rtpmap:0 PCMU/8000
a=sendrecv
```

## 4. RTP音频流传输
- 建立会话后，服务器通过UDP将RTP包发送到101的RTP端口。
- 每20ms发送一帧（160字节μ-law），保持实时性。
- 101端收到RTP包后，解包RTP头，提取μ-law音频payload，解码为PCM后播放。

## 5. 电话端（101）回传流程
- 101端采集麦克风音频，编码为μ-law，按20ms一帧打包为RTP包。
- RTP包通过UDP回传到服务器声明的RTP端口。
- 服务器持续监听RTP端口，接收101端回传的RTP包。

## 6. RTP解包与STT前处理
- 服务器收到RTP包，解析12字节头部，提取payload（μ-law音频）。
- 多帧μ-law音频拼接为完整语音片段。
- μ-law音频解码为PCM（8kHz, 16bit, mono），准备送入STT。

**关键代码片段：**
```python
# RTP解包
header = data[:12]
payload = data[12:]
# μ-law解码
def ulaw_to_linear(ulaw_bytes):
    # 反向G.711 μ-law解码
    ...
```

## 7. STT语音识别
- 服务器将PCM音频送入Deepgram STT API。
- Content-Type: audio/mulaw, 8kHz, mono。
- Deepgram返回识别文本。

## 8. 涉及协议与标准
- **SIP (RFC 3261)**：信令控制
- **SDP (RFC 4566)**：会话描述
- **RTP (RFC 3550)**：实时音频传输
- **G.711 μ-law (ITU-T G.711)**：音频编解码
- **UDP**：底层传输协议

## 9. 关键参数
- RTP端口：10000-10500
- Payload Type: 0 (PCMU)
- 采样率：8kHz
- 帧长：20ms/帧
- 音频格式：μ-law, 8bit, mono

## 10. 关键实现要点
- 实时性：每20ms一帧，低延迟传输
- 丢包容忍：RTP天然支持丢包
- 端到端音频链路：TTS→μ-law→RTP→SIP→101→RTP→μ-law→PCM→STT
- 所有音频流量均为UDP包，最大化实时性

---

**本报告仅聚焦于TTS到IP电话101再到STT的底层通信技术实现。** 