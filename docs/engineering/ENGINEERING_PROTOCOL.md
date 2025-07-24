# Aiker RealTime Chat 工程协议 v1.0

## 1. 协议目的

确保项目在AI辅助开发过程中保持稳定性、一致性和可维护性。通过建立明确的规则和约束，保护核心通信协议不被意外修改，同时支持AI服务的本地化改造。

## 2. 核心原则

### 2.1 最小侵入原则
- 新功能必须通过适配层实现
- 不得直接修改底层通信协议
- 保持向后兼容性
- 使用适配器模式集成新功能

### 2.2 上下文完整性原则
- 每个任务必须有明确的上下文定义
- 上下文必须包含所有相关约束
- 保存任务决策历史
- 维护上下文版本控制

### 2.3 测试驱动原则
- 修改前必须有测试用例
- 新功能必须有对应测试
- 保持测试覆盖率>80%
- 自动化兼容性测试

### 2.4 性能约束原则
- STT延迟 < 500ms
- TTS延迟 < 300ms
- 内存使用 < 2GB
- CPU使用率 < 70%

## 3. 保护机制

### 3.1 绝对保护模块

以下模块绝对不可修改：

#### 3.1.1 SIP信令层（EnhancedSIPClient）
- **保护原因**: 核心SIP协议实现，修改会破坏与VTX PBX的兼容性
- **保护级别**: ABSOLUTE
- **允许操作**: 无
- **文件位置**: `main.py:342-1151`

#### 3.1.2 RTP音频传输（RTPHandler）
- **保护原因**: RTP音频流处理，符合RFC 3550标准
- **保护级别**: ABSOLUTE
- **允许操作**: 无
- **文件位置**: `main.py:100-252`

#### 3.1.3 G.711编解码器（G711Codec）
- **保护原因**: G.711编解码标准实现，电信级标准
- **保护级别**: ABSOLUTE
- **允许操作**: 无
- **文件位置**: `main.py:253-341`

#### 3.1.4 SDP协议解析（SDPParser）
- **保护原因**: SDP协议解析，媒体协商核心组件
- **保护级别**: ABSOLUTE
- **允许操作**: 无
- **文件位置**: `main.py:30-99`

### 3.2 受保护常量

以下常量值不可修改：

| 常量名 | 值 | 保护级别 | 原因 |
|--------|-----|----------|------|
| SAMPLE_RATE | 8000 | ABSOLUTE | 电话标准采样率 |
| FRAME_SIZE | 160 | ABSOLUTE | RTP标准帧大小 |
| SIP_PORT | 5060 | ABSOLUTE | SIP标准端口 |
| ULAW_BIAS | 132 | ABSOLUTE | μ-law编码偏置值 |

### 3.3 受保护接口

以下接口签名必须保持不变：

```python
# STT接口
AIConversationManager._speech_to_text(self, audio_data: bytes) -> str

# TTS接口
AIConversationManager._text_to_speech(self, text: str) -> Optional[bytes]

# LLM接口
AIConversationManager._get_ai_response(self, user_text: str) -> str
```

## 4. 开发流程

### 4.1 任务启动流程

```bash
# 1. 检查保护状态
python scripts/protection_checker.py --mode check

# 2. 创建功能分支
git checkout -b feature/local-stt-implementation

# 3. 加载任务上下文
# 确保.ai/context_map.json中定义了相关上下文
```

### 4.2 开发过程检查清单

在进行任何代码修改前，必须确认：
- [ ] 是否涉及受保护模块？
- [ ] 是否影响SIP/RTP通信？
- [ ] 是否改变音频格式？
- [ ] 是否有对应的测试？
- [ ] 是否创建了适配层？
- [ ] 是否保持接口兼容性？

### 4.3 代码审查流程

1. **自动检查**: 运行保护检查器
2. **兼容性测试**: 验证SIP/RTP通信
3. **性能测试**: 确保满足性能约束
4. **接口测试**: 验证接口兼容性

## 5. 本地化实施策略

### 5.1 实施阶段

#### 阶段1: 环境准备（第1-2周）
- 建立工程协议框架
- 设置保护机制
- 配置开发环境
- 创建基础模板

#### 阶段2: STT本地化（第3-4周）
- 分析现有STT调用链
- 实现本地语音识别引擎
- 创建STT适配器
- 集成测试

#### 阶段3: TTS本地化（第5-6周）
- 实现本地语音合成引擎
- 保持μ-law音频格式输出
- 创建TTS适配器
- 集成测试

#### 阶段4: LLM本地化（第7-8周）
- 实现本地对话引擎
- 集成业务知识库
- 创建LLM适配器
- 集成测试

#### 阶段5: 集成优化（第9-10周）
- 整体性能优化
- 系统集成测试
- 文档更新
- 部署准备

### 5.2 适配器设计模式

```python
class FeatureAdapter:
    def __init__(self, use_local: bool = True):
        if use_local:
            self.engine = LocalEngine()
        else:
            self.engine = APIEngine()
    
    def process(self, *args, **kwargs):
        try:
            return self.engine.process(*args, **kwargs)
        except Exception:
            # 自动回退到备用引擎
            return self.fallback_engine.process(*args, **kwargs)
```

## 6. 质量保证

### 6.1 自动化测试

```bash
# 兼容性测试
python -m pytest tests/test_sip_compatibility.py -v
python -m pytest tests/test_rtp_stream.py -v

# 性能测试
python scripts/benchmark_local_engines.py --engine all

# 保护检查
python scripts/protection_checker.py --mode check
```

### 6.2 持续集成

- 每次提交自动运行保护检查
- 自动化兼容性测试
- 性能回归测试
- 接口兼容性验证

## 7. 紧急情况处理

### 7.1 回滚机制

```bash
# 快速回滚到稳定版本
git checkout stable-baseline

# 恢复上下文
python scripts/context_manager.py --restore stable-baseline
```

### 7.2 故障诊断

1. **检查保护状态**: 运行保护检查器
2. **验证通信**: 测试SIP/RTP连接
3. **检查性能**: 运行性能基准测试
4. **日志分析**: 查看详细错误日志

## 8. 文档维护

### 8.1 必须更新的文档

- 技术规格变更时更新工程协议
- 新增保护模块时更新保护配置
- 接口变更时更新接口文档
- 性能优化时更新性能指标

### 8.2 版本控制

- 工程协议版本与项目版本同步
- 重要变更打标签
- 保持变更历史记录

## 9. 成功标准

### 9.1 技术标准

- [ ] 系统保持与VTX PBX的完全兼容
- [ ] 所有AI服务本地化完成
- [ ] 性能指标达到要求
- [ ] 测试覆盖率>80%

### 9.2 质量标准

- [ ] 代码质量和可维护性提升
- [ ] 文档完整性和准确性
- [ ] 系统稳定性和可靠性
- [ ] 开发效率和协作质量

## 10. 风险控制

### 10.1 技术风险

- **风险**: 修改保护模块导致系统崩溃
- **缓解**: 严格的保护检查和自动化测试
- **应对**: 快速回滚机制

### 10.2 性能风险

- **风险**: 本地化后性能下降
- **缓解**: 性能基准测试和持续监控
- **应对**: 性能优化和回退机制

### 10.3 兼容性风险

- **风险**: 接口变更导致兼容性问题
- **缓解**: 接口版本控制和兼容性测试
- **应对**: 渐进式迁移和适配器模式

---

**本工程协议是确保项目稳定发展的重要保障，所有开发人员和AI助手都必须严格遵守。** 