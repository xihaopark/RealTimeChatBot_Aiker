# Aiker RealTimeChat 项目改造计划 v1.0

## 1. 项目目标

本项目旨在将Aiker实时语音对话系统中的核心AI服务（STT, TTS, LLM）从依赖云端API全面转向本地化部署。目标是显著降低运营成本、优化响应延迟、保障数据隐私，并确保系统核心的底层通信协议（SIP/RTP）在此过程中保持绝对稳定。

## 2. 核心原则

- **协议稳定性第一**: 任何改造都不得影响底层通信协议的稳定性和兼容性。
- **渐进式本地化**: 逐一替换AI服务模块，确保每个阶段系统的可用性。
- **性能导向**: 本地化方案的性能（延迟、资源占用）需满足或优于API方案。
- **可维护性**: 新增模块需遵循统一的工程规范，易于维护和扩展。

---

## 第一部分：底层通信协议保护规范

### 1.1.《底层协议工程守则》

此守则是本项目不可逾越的红线，所有开发人员及AI助手必须严格遵守。

#### 1.1.1. 不可修改的核心模块 ⚠️

以下模块及其核心逻辑**严禁任何形式的修改**：
- **SIP信令层**: `main.py`中的`EnhancedSIPClient`类，特别是`_build_register`, `_build_auth_header`, `_parse_auth_header`等方法。
- **RTP音频传输层**: `main.py`中的`RTPHandler`类，特别是RTP包结构（12字节头部）、序列号和时间戳的递增逻辑、SSRC生成机制。
- **音频编解码器**: `main.py`中的`G711Codec`类，特别是`linear_to_ulaw`算法和`ULAW_BIAS`常量。
- **SDP协议处理**: `main.py`中的`SDPParser`类，特别是SDP媒体描述格式。

#### 1.1.2. 关键参数锁定 🔒

以下参数已在`config/protocol_constants.yaml`中锁定，**严禁修改**：
- **SIP端口**: `5060`
- **RTP端口范围**: `10000-10500`
- **音频采样率**: `8000` Hz
- **音频帧大小**: `160` 字节
- **音频编码**: `mulaw`

#### 1.1.3. 自动化保护

- **静态检查**: `scripts/protection_checker.py`脚本已集成到开发流程中，用于在代码提交前自动检查是否触犯保护规则。
- **版本控制**: 核心协议文件已在版本控制中被重点监控。

---

## 第二部分：AI服务本地化改造计划

### Phase 1: 环境准备（第1-2周）

- **任务**: 准备本地化所需的软硬件环境。
- **硬件评估**:
  - **GPU**: 推荐NVIDIA RTX 4070 Ti (16GB VRAM)或更高。
  - **内存**: 32GB DDR4以上。
  - **存储**: 1TB NVMe SSD。
- **软件搭建**:
  - **OS**: Ubuntu 22.04 LTS
  - **CUDA**: 12.1 + cuDNN 8.9
  - **Python**: 3.10
  - **核心依赖**: PyTorch 2.0+, Transformers, ONNX Runtime, VAD, aiohttp等。

### Phase 2: 本地STT替换（第3-4周）

- **目标**: 使用本地Whisper模型替换Deepgram API。
- **技术选型**:
  - **模型**: `whisper-large-v3`（或其中文优化版`belle-whisper-large-v3-zh`）。
  - **VAD**: `silero-vad`用于端点检测，减少不必要的计算。
- **实施步骤**:
  1. 在`src/local_engines/stt_engine.py`中实现`LocalSTTEngine`。
     - 实现`_ulaw_to_pcm`转换。
     - 集成VAD进行语音活动检测。
     - 调用Whisper模型进行推理。
  2. 在`src/adapters/stt_adapter.py`中完善`STTAdapter`。
     - 实现对本地引擎的调用。
     - (可选)保留对Deepgram API的调用作为回退方案。
  3. 在`ai_conversation.py`中，通过`STTAdapter`调用STT服务。
- **性能优化**: 探索使用`distil-whisper`或INT8量化以降低资源占用。
- **验收标准**: STT延迟<500ms，识别准确率>95%。

### Phase 3: 本地TTS替换（第5-6周）

- **目标**: 使用本地TTS引擎替换ElevenLabs API。
- **技术选型**:
  - **首选**: **Coqui XTTS-v2**，因其强大的声音克隆能力，可以完美复刻`Anna Su`的音色。
  - **备选**: `Edge-TTS`本地版（`piper-tts`），延迟极低，音质优秀。
- **实施步骤**:
  1. 准备`Anna Su`的声音样本（3-5分钟高质量录音）。
  2. 在`src/local_engines/tts_engine.py`中实现`LocalTTSEngine`。
     - 使用XTTS-v2进行声音克隆和模型微调。
     - 实现TTS推理逻辑。
     - 实现`_pcm_to_ulaw`转换，确保输出格式兼容。
  3. 在`src/adapters/tts_adapter.py`中完善`TTSAdapter`。
- **验收标准**: 合成音频为8000Hz μ-law格式，端到端延迟<300ms。

### Phase 4: 本地LLM替换（第7-9周）

- **目标**: 使用本地大语言模型替换OpenAI GPT-3.5 API。
- **技术选型**:
  - **首选**: **ChatGLM3-6B**，中文能力强，支持工具调用，社区成熟。
  - **备选**: `Qwen-14B-Chat`，长文本能力更强。
  - **RAG嵌入模型**: `BAAI/bge-large-zh-v1.5`。
- **实施步骤**:
  1. 在`src/local_engines/llm_engine.py`中实现`LocalLLMEngine`。
     - 集成ChatGLM3-6B模型。
     - 实现RAG系统，使用ChromaDB和嵌入模型处理`onesuite-business-data.json`。
     - 构建增强提示（`augmented prompt`）逻辑。
  2. 在`src/adapters/llm_adapter.py`中完善`LLMAdapter`。
- **验收标准**: LLM首字延迟<1s，能正确回答与业务数据相关的问题。

### Phase 5: 推理优化与部署（第10-11周）

- **目标**: 优化本地AI服务的性能和吞吐量。
- **技术选型**:
  - **推理服务器**: **vLLM**，利用PagedAttention等技术提升LLM吞吐量。
  - **模型量化**: **GPTQ 4-bit**量化，显著降低LLM显存占用。
- **实施步骤**:
  1. 将量化后的ChatGLM模型部署到vLLM服务器。
  2. 将STT和TTS服务封装为独立的、可异步调用的工作者（Worker）。
  3. 创建`scripts/inference_server.py`，模拟完整的异步处理流程。
- **验收标准**: 系统能支持至少10路并发通话，GPU利用率<80%。

### Phase 6: 系统总成与测试（第12周）

- **目标**: 将所有本地化模块集成到主程序中，并进行端到端测试。
- **实施步骤**:
  1. 创建`ai_conversation_local.py`，继承`AIConversationManager`，并使用本地适配器替换API调用。
  2. 利用`config/ai_backend.yaml`中的`mode`参数实现`api`和`local`模式的无缝切换。
  3. 进行完整的兼容性测试、性能压力测试和用户体验测试。
- **验收标准**: 本地化后的系统功能与API版本一致，性能指标达标，且稳定运行超过72小时。

---

## 3. 总结与展望

此计划提供了一个清晰、分阶段的路径，以在保护核心系统稳定性的前提下，完成AI服务的全面本地化。

- **预期收益**: 成本显著降低、延迟优化、数据隐私得到保障。
- **技术栈升级**:
  - **STT**: Deepgram API -> **Whisper Large-v3**
  - **TTS**: ElevenLabs API -> **Coqui XTTS-v2**
  - **LLM**: OpenAI GPT-3.5 -> **ChatGLM3-6B + RAG**
- **下一步**: **立即启动Phase 1**，进行详细的硬件和软件环境配置。 