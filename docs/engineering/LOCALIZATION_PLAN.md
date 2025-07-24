# Aiker RealTimeChat - 本地化改造计划 v1.0

## 1. 改造目标

将项目中依赖外部API的AI服务（STT、TTS、LLM）替换为本地化部署的引擎，以实现以下目标：
- **成本节省**: 显著降低API调用费用。
- **延迟优化**: 减少网络延迟，提升实时对话体验。
- **数据隐私**: 所有数据在本地处理，确保用户隐私和数据安全。
- **系统自主性**: 摆脱对外部服务的依赖，提高系统的稳定性和可控性。

## 2. 实施路线图

本地化改造将分阶段进行，以确保平稳过渡和风险可控。

| 阶段 | 任务 | 时间预估 | 关键产出 |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **环境准备** | 第1-2周 | - 硬件/软件环境就绪<br>- 性能基准测试报告 |
| **Phase 2** | **本地STT替换** | 第3-4周 | - `LocalSTTEngine`<br>- STT适配器<br>- STT性能测试报告 |
| **Phase 3** | **本地TTS替换** | 第5-6周 | - `LocalTTSEngine`<br>- TTS适配器<br>- TTS性能与音质报告 |
| **Phase 4** | **本地LLM替换** | 第7-9周 | - `LocalLLMEngine`<br>- RAG系统<br>- LLM适配器与测试 |
| **Phase 5** | **推理优化** | 第10-11周 | - 量化模型<br>- 推理服务器部署<br>- 优化后的性能报告 |
| **Phase 6** | **系统集成** | 第12周 | - `LocalAIConversationManager`<br>- 统一的后端配置文件 |
| **Phase 7** | **监控与优化** | 持续进行 | - 性能监控面板<br>- 持续优化方案 |

---

## Phase 1: 环境准备（第1-2周）

### 1.1 硬件评估与准备

- **推荐配置**:
  - **GPU**: NVIDIA RTX 4070 Ti (16GB VRAM) 或更高。
  - **CPU**: AMD Ryzen 9 5900X / Intel i9-12900K 或更高。
  - **内存**: 32GB DDR4 或更高。
  - **存储**: 1TB NVMe SSD。
- **最低配置**:
  - **GPU**: NVIDIA RTX 3060 (12GB VRAM)。
- **目标**: 确保硬件环境能支持后续所有模型的本地化部署和调试。

### 1.2 软件环境搭建

- **CUDA**: 安装 CUDA 11.8 或 12.1，并配置 cuDNN 8.9。
- **Python**: 使用 `pyenv` 或 `conda` 创建一个独立的 `Python 3.10` 环境。
- **核心依赖**: 安装 `PyTorch 2.0+`，并验证GPU支持。
- **推理加速**: 安装 `ONNX Runtime` 和 `TensorRT 8.6` (可选)。

---

## Phase 2: 本地STT替换（第3-4周）

### 2.1 技术选型

- **首选方案**: **OpenAI Whisper (large-v3模型)**。
  - **优势**: 业界领先的准确率，良好的多语言支持。
  - **中文优化**: 优先考虑 `belle-whisper-large-v3-zh` 等中文优化版本。
  - **备选模型**: `whisper-medium`（平衡性能与资源），`whisper-base`（用于快速测试）。

### 2.2 实现架构

1.  创建 `src/local_engines/stt_engine.py`。
2.  实现 `LocalSTTEngine` 类，封装 `whisper.load_model()` 和 `model.transcribe()`。
3.  **音频格式处理**: 必须包含从 `μ-law` 到 `PCM` 的转换逻辑，以匹配Whisper的输入要求。
4.  **性能优化**: 使用 `fp16=True` 开启半精度浮点数推理以利用GPU。

### 2.3 性能优化策略

- **VAD预处理**: 集成 `silero-vad` 或 `webrtcvad`，在音频输入到Whisper前进行语音活动检测，去除静音片段，减少无效计算。
- **异步处理**: 实现异步推理队列，避免阻塞主线程。
- **模型量化**: 探索使用 `INT8` 量化来降低显存占用。

---

## Phase 3: 本地TTS替换（第5-6周）

### 3.1 技术选型

- **方案A (推荐)**: **Coqui TTS (XTTS-v2模型)**
  - **优势**: 优秀的跨语言声音克隆能力，情感表达丰富。
  - **劣势**: 延迟相对较高（~500ms），资源占用大（~6GB VRAM）。
- **方案B (备选)**: **Edge-TTS 本地版 (piper-tts)**
  - **优势**: 极低的延迟（~100ms）和资源占用，声音质量高。
  - **劣势**: 声音定制能力较弱。
- **方案C (备选)**: **PaddleSpeech (FastSpeech2模型)**
  - **优势**: 中文原生支持，延迟较低（~200ms）。

### 3.2 实现架构

1.  创建 `src/local_engines/tts_engine.py`。
2.  实现 `LocalTTSEngine` 类，根据选型封装相应模型的TTS逻辑。
3.  **音频格式处理**: 输出的音频必须被转换为 `μ-law` 格式，以符合RTP传输要求。
4.  **声音定制**: 实现声音克隆流程，使用 `anna_su.wav` 作为基础音色进行微调。

---

## Phase 4: 本地LLM替换（第7-9周）

### 4.1 技术选型

- **方案A (推荐)**: **ChatGLM系列 (GLM-4-9B)**
  - **优势**: 最新的开源模型，强大的中文能力和工具调用功能。
- **方案B (备选)**: **Qwen系列 (Qwen-14B-Chat)**
  - **优势**: 强大的中文对话能力和长文本支持。
- **方案C (备选)**: **Baichuan系列 (Baichuan2-13B-Chat)**
  - **优势**: 商业友好，推理速度快。

### 4.2 实现架构

1.  创建 `src/local_engines/llm_engine.py`。
2.  实现 `LocalLLMEngine` 类，封装 `AutoModel` 和 `AutoTokenizer` 的加载与生成逻辑。
3.  **RAG集成**:
    - 创建 `src/local_engines/rag_system.py`。
    - 使用 `ChromaDB` 作为向量数据库。
    - 使用 `BAAI/bge-large-zh-v1.5` 作为嵌入模型。
    - 实现加载 `onesuite-business-data.json` 并构建知识库的逻辑。
    - 将检索到的上下文整合到LLM的prompt中。

---

## Phase 5: 推理优化（第10-11周）

### 5.1 模型量化

- **技术**: 优先采用 `GPTQ` 进行4-bit量化，目标是将显存占用降低75%。
- **实现**: 使用 `auto-gptq` 库加载量化后的模型。

### 5.2 推理服务器

- **推荐方案**: **vLLM**
  - **优势**: 通过PagedAttention等技术实现高吞吐量，支持多GPU并行。
- **备选方案**: **TGI (Text Generation Inference)** 或 **llama.cpp** (适用于CPU/GPU混合推理)。

---

## Phase 6: 系统集成（第12周）

### 6.1 适配层设计

- 创建 `src/adapters/` 目录。
- 为STT, TTS, LLM分别创建 `stt_adapter.py`, `tts_adapter.py`, `llm_adapter.py`。
- 适配器内部应封装对本地引擎的调用，并保持与 `AIConversationManager` 中原有接口的兼容性。

### 6.2 配置切换

- 在 `config/settings.py` (或新的 `ai_backend.yaml`) 中增加配置项，用于在 `api`, `local`, `hybrid` 模式间切换。
- `AIConversationManager` (或其子类 `LocalAIConversationManager`) 根据配置动态加载API或本地引擎。

---

## Phase 7: 性能监控与优化（持续）

### 7.1 监控指标

- **延迟**: STT < 500ms, TTS < 300ms, LLM首字延迟 < 1s。
- **资源**: GPU利用率 < 80%, 显存占用 < 16GB。

### 7.2 优化方向

- **批处理 (Batching)**: 聚合多个请求进行批处理，提高GPU利用率。
- **模型缓存**: 缓存常用模型以加速加载。
- **流式生成 (Streaming)**: 对TTS和LLM采用流式输出，降低感知延迟。

---

## 预期成果

- **成本**: API费用降为零，仅剩硬件和电力成本。
- **延迟**: 端到端（用户说话到听到AI回复）延迟从3-5秒优化至1-2秒。
- **隐私**: 100%数据本地化处理，符合最高数据安全标准。
- **自主性**: 系统完全自主可控，不受外部API服务商影响。 