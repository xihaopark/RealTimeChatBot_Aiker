# OneSuite Business 结构化数据模板说明

## 数据结构概览

这个JSON模板采用树状结构组织OneSuite Business公司信息，专门设计用于语言模型的理解和调用。主要包含以下顶级节点：

### 1. 公司信息 (company)
- 基本信息：名称、成立时间、类型
- 使命愿景：公司使命和标语
- 业务描述：核心业务简介

### 2. 服务体系 (services)
- **核心服务**：虚拟PBX系统及其主要功能
- **目标客户**：三大客户群体定位
- **关键优势**：无需硬件、简单设置等核心卖点

### 3. 功能特性 (features)
详细的功能模块，每个功能包含：
- 名称标识
- 功能描述
- 具体特性列表

主要功能模块：
- 自动接待员 (auto_attendant)
- 自定义问候语 (custom_greetings)
- 语音信箱 (voicemail)
- 呼叫转接 (call_transfer)
- 公司通讯录 (company_directory)
- 来电显示 (caller_id)
- 短信功能 (sms_messaging)
- 号码管理 (number_management)
- 振铃组 (ring_groups)
- 通话记录 (call_records)

### 4. 平台支持 (platforms)
- **移动应用**：OSBPhone Mobile (Android/iOS)
- **网页应用**：OSBPhone Web

### 5. 定价模式 (pricing)
- 计费模式：按需付费
- 基础套餐和附加选项
- 价格特点

### 6. 推荐计划 (programs)
- SuiteTreat推荐奖励机制
- 推荐人和被推荐人的优惠

### 7. 安全隐私 (security_privacy)
- 数据加密
- 存储安全
- 访问控制
- 合规政策

### 8. 客户支持 (support)
- 帮助中心分类
- 联系方式

### 9. 技术信息 (technical_info)
- 设置时间
- 基础设施
- 覆盖范围
- 兼容性

## 使用建议

### 1. 查询示例
```json
// 查询特定功能
query: "features.auto_attendant"

// 查询定价信息
query: "pricing.basic_plan.add_ons"

// 查询平台支持
query: "platforms.mobile_app.platforms"
```

### 2. 语言模型调用场景

**客户咨询场景**：
- 产品介绍：访问 `company` 和 `services` 节点
- 功能询问：访问 `features` 下的具体功能模块
- 价格咨询：访问 `pricing` 节点
- 技术支持：访问 `support` 和 `technical_info` 节点

**销售场景**：
- 竞争优势：访问 `services.key_benefits`
- 目标客户：访问 `services.target_customers`
- 推荐计划：访问 `programs.referral`

### 3. 数据更新维护

建议定期更新以下内容：
- 定价信息（pricing）
- 新功能特性（features）
- 平台兼容性（technical_info.compatibility）
- 推荐计划条款（programs）

### 4. 扩展建议

可以添加的额外信息：
- 客户案例（case_studies）
- 常见问题（faq）
- 竞争对比（competitive_comparison）
- 行业认证（certifications）
- 用户评价（testimonials）

## 最佳实践

1. **保持结构一致性**：新增内容应遵循现有的命名规范和层级结构
2. **使用描述性键名**：便于理解和记忆
3. **适度嵌套**：避免过深的嵌套结构，保持在3-4层以内
4. **数组vs对象**：列表类信息用数组，具有唯一标识的信息用对象
5. **国际化考虑**：可以为多语言支持预留结构