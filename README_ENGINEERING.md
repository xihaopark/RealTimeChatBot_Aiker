# VTX AI Phone System - 工程环境使用指南

## 🎯 概述

本指南介绍如何使用已构建的工程环境，包括AI助手的限制机制、保护规则和开发流程。

## 📁 工程环境结构

```
vtx-voip/
├── .ai/                          # AI工程协议目录
│   ├── system_prompt.md          # 系统级提示词
│   ├── protected_modules.yaml    # 受保护模块清单
│   ├── context_map.json          # 上下文映射
│   └── templates/                # 代码模板
│       ├── local_engine.py.tmpl  # 本地引擎模板
│       └── adapter.py.tmpl       # 适配器模板
├── docs/engineering/             # 工程文档
│   └── ENGINEERING_PROTOCOL.md   # 工程协议
├── scripts/                      # 工具脚本
│   └── protection_checker.py     # 保护检查器
├── src/                          # 源代码
│   ├── local_engines/           # 本地引擎
│   └── adapters/                # 适配器
└── tests/                        # 测试代码
    ├── compatibility/           # 兼容性测试
    ├── performance/             # 性能测试
    └── integration/             # 集成测试
```

## 🛡️ 保护机制

### 绝对保护模块（不可修改）
- **SIP信令层**: `main.py:EnhancedSIPClient`
- **RTP音频传输**: `main.py:RTPHandler`
- **G.711编解码器**: `main.py:G711Codec`
- **SDP协议解析**: `main.py:SDPParser`

### 受保护常量
- `SAMPLE_RATE = 8000` (电话标准采样率)
- `FRAME_SIZE = 160` (RTP标准帧大小)
- `SIP_PORT = 5060` (SIP标准端口)
- `ULAW_BIAS = 132` (μ-law编码偏置值)

## 🔧 使用方法

### 1. 检查保护状态

```bash
# 运行保护检查器
python scripts/protection_checker.py --mode check

# 生成详细报告
python scripts/protection_checker.py --mode report --output protection_report.json
```

### 2. 开发新功能

#### 步骤1: 检查约束
在开始任何开发前，确认：
- [ ] 是否涉及受保护模块？
- [ ] 是否影响SIP/RTP通信？
- [ ] 是否改变音频格式？
- [ ] 是否有对应的测试？
- [ ] 是否创建了适配层？

#### 步骤2: 使用模板生成代码
```bash
# 使用模板生成本地引擎
cp .ai/templates/local_engine.py.tmpl src/local_engines/stt_engine.py

# 使用模板生成适配器
cp .ai/templates/adapter.py.tmpl src/adapters/stt_adapter.py
```

#### 步骤3: 实现功能
- 使用适配器模式集成新功能
- 保持接口兼容性
- 遵循性能约束

#### 步骤4: 测试验证
```bash
# 兼容性测试
python -m pytest tests/compatibility/ -v

# 性能测试
python -m pytest tests/performance/ -v

# 集成测试
python -m pytest tests/integration/ -v
```

## 🤖 AI助手使用规则

### 对AI助手的约束
1. **绝对禁止**修改受保护模块
2. **必须**使用适配器模式集成新功能
3. **必须**保持接口兼容性
4. **必须**遵循性能约束
5. **必须**创建对应的测试

### AI助手的帮助功能
1. **代码生成**: 基于模板生成标准化代码
2. **架构设计**: 提供适配器设计建议
3. **性能优化**: 在约束范围内优化性能
4. **测试生成**: 自动生成测试用例
5. **文档更新**: 同步更新相关文档

## 📋 开发检查清单

### 开发前检查
- [ ] 阅读工程协议文档
- [ ] 运行保护检查器
- [ ] 确认任务上下文
- [ ] 准备测试用例

### 开发中检查
- [ ] 使用适配器模式
- [ ] 保持接口兼容性
- [ ] 遵循性能约束
- [ ] 编写单元测试

### 开发后检查
- [ ] 运行所有测试
- [ ] 检查性能指标
- [ ] 验证兼容性
- [ ] 更新文档

## 🚨 紧急情况处理

### 如果意外修改了受保护模块
1. 立即停止开发
2. 运行保护检查器确认影响
3. 回滚到最近的稳定版本
4. 重新评估开发方案

### 如果系统出现兼容性问题
1. 检查SIP/RTP通信状态
2. 验证音频格式是否正确
3. 检查接口签名是否匹配
4. 运行兼容性测试套件

## 📊 性能监控

### 性能指标
- STT延迟: < 500ms
- TTS延迟: < 300ms
- 内存使用: < 2GB
- CPU使用率: < 70%

### 监控方法
```bash
# 运行性能基准测试
python scripts/benchmark_local_engines.py --engine all

# 监控系统资源
htop  # 或者 top
```

## 🔄 本地化实施步骤

### 阶段1: STT本地化
1. 分析现有STT调用链
2. 选择合适的本地STT引擎（Whisper/FunASR/WeNet）
3. 实现本地STT引擎
4. 创建STT适配器
5. 集成测试

### 阶段2: TTS本地化
1. 分析现有TTS调用链
2. 选择合适的本地TTS引擎
3. 实现本地TTS引擎（确保输出μ-law格式）
4. 创建TTS适配器
5. 集成测试

### 阶段3: LLM本地化
1. 分析现有LLM调用链
2. 选择合适的本地LLM引擎
3. 集成业务知识库
4. 创建LLM适配器
5. 集成测试

## 📖 相关文档

- [工程协议](docs/engineering/ENGINEERING_PROTOCOL.md)
- [系统提示词](.ai/system_prompt.md)
- [受保护模块配置](.ai/protected_modules.yaml)
- [上下文映射](.ai/context_map.json)

## 💡 最佳实践

1. **始终使用适配器模式**: 不要直接修改现有代码
2. **保持接口稳定**: 新功能通过扩展而非修改实现
3. **性能优先**: 在满足功能的前提下追求最佳性能
4. **测试驱动**: 先写测试，再实现功能
5. **文档同步**: 及时更新相关文档

## ⚠️ 注意事项

1. **严格遵守保护规则**: 绝不修改受保护模块
2. **保持音频格式**: 确保音频处理链的格式一致性
3. **性能约束**: 本地化不应显著降低性能
4. **兼容性第一**: 保持与VTX PBX的完全兼容

---

**通过遵循这些规则和流程，可以确保项目在AI辅助开发过程中保持稳定和可控。** 