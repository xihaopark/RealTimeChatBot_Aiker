# GitHub同步操作指南

本指南将帮助你将VTX AI Phone System项目同步到GitHub仓库 `https://github.com/xihaopark/RealTimeChatBot_Aiker`。

## 🚀 快速同步（推荐）

### 方法1：使用自动同步脚本

1. **确保脚本有执行权限**
```bash
chmod +x sync_to_github.sh
```

2. **执行自动同步**
```bash
./sync_to_github.sh
```

脚本会自动：
- 检查Git环境
- 初始化仓库（如果需要）
- 添加所有文件
- 生成提交信息
- 推送到GitHub

### 方法2：指定提交信息
```bash
./sync_to_github.sh -m "重构AI模块，优化对话管理"
```

### 方法3：仅清理缓存文件
```bash
./sync_to_github.sh -c
```

## 📋 手动同步步骤

### 1. 初始化Git仓库（如果未初始化）

```bash
# 检查是否已初始化
ls -la | grep .git

# 如果未初始化，执行以下命令
git init
git remote add origin https://github.com/xihaopark/RealTimeChatBot_Aiker.git
```

### 2. 配置Git用户信息

```bash
git config user.name "xihaopark"
git config user.email "your-email@example.com"
```

### 3. 添加文件到暂存区

```bash
# 添加所有文件
git add .

# 或者选择性添加
git add src/
git add config/
git add *.md
git add *.sh
git add requirements.txt
```

### 4. 提交变更

```bash
# 使用自动生成的提交信息
git commit -m "Update: VTX AI Phone System v2.0 - 重构AI模块架构"

# 或者使用详细提交信息
git commit -m "feat: 重构AI模块架构

- 添加完整的对话管理器
- 优化语音识别和合成流程
- 改进错误处理机制
- 添加GitHub同步脚本
- 完善项目文档"
```

### 5. 推送到GitHub

```bash
# 推送到main分支
git push origin main

# 如果是第一次推送，可能需要设置上游分支
git push -u origin main
```

## 🔧 常见问题解决

### 问题1：权限错误
```bash
# 错误信息：Permission denied (publickey)
# 解决方案：配置SSH密钥或使用HTTPS

# 使用HTTPS（推荐）
git remote set-url origin https://github.com/xihaopark/RealTimeChatBot_Aiker.git

# 或者配置SSH密钥
ssh-keygen -t rsa -b 4096 -C "your-email@example.com"
# 然后将公钥添加到GitHub账户
```

### 问题2：分支冲突
```bash
# 如果远程有更新，先拉取
git pull origin main

# 如果有冲突，解决后重新提交
git add .
git commit -m "解决合并冲突"
git push origin main
```

### 问题3：大文件问题
```bash
# 如果文件太大，使用Git LFS
git lfs install
git lfs track "*.wav"
git lfs track "*.mp3"
git add .gitattributes
git commit -m "配置Git LFS"
```

## 📁 项目文件结构确认

同步前请确认以下文件结构：

```
vtx-llm-bot/
├── 📁 src/                          # 源代码
│   ├── 📁 ai/                       # AI模块
│   ├── 📁 audio/                    # 音频模块
│   ├── 📁 rtp/                      # RTP协议
│   ├── 📁 sdp/                      # SDP协议
│   ├── 📁 sip/                      # SIP协议
│   ├── 📁 utils/                    # 工具模块
│   └── main.py                      # 主程序
├── 📁 config/                       # 配置
│   └── settings.py                  # 配置管理
├── 📄 README.md                     # 项目说明
├── 📄 requirements.txt              # 依赖包
├── 📄 sync_to_github.sh             # 同步脚本
├── 📄 deploy.sh                     # 部署脚本
├── 📄 .gitignore                    # Git忽略文件
├── 📄 env.example                   # 环境变量模板
└── 📄 LICENSE                       # 许可证
```

## 🔄 持续同步策略

### 1. 开发工作流

```bash
# 日常开发流程
./sync_to_github.sh -m "feat: 添加新功能"
```

### 2. 版本发布

```bash
# 创建版本标签
git tag -a v2.0.0 -m "Release version 2.0.0"
git push origin v2.0.0
```

### 3. 分支管理

```bash
# 创建功能分支
git checkout -b feature/new-feature
# 开发完成后合并
git checkout main
git merge feature/new-feature
git push origin main
```

## 📊 同步状态检查

### 检查本地状态
```bash
git status
git log --oneline -5
```

### 检查远程状态
```bash
git remote -v
git fetch origin
git log --oneline origin/main -5
```

### 检查文件差异
```bash
git diff --cached
git diff HEAD~1
```

## 🛠️ 高级配置

### 1. 配置Git别名
```bash
# 添加到 ~/.gitconfig
[alias]
    sync = !./sync_to_github.sh
    status = status --short
    log = log --oneline --graph
```

### 2. 设置自动同步钩子
```bash
# 创建pre-commit钩子
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# 自动清理缓存文件
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
EOF
chmod +x .git/hooks/pre-commit
```

### 3. 配置GitHub Actions（可选）

创建 `.github/workflows/sync.yml`：

```yaml
name: Auto Sync
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Run tests
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        python -m pytest
```

## 📞 技术支持

如果在同步过程中遇到问题：

1. **检查网络连接**
2. **确认GitHub账户权限**
3. **查看错误日志**
4. **联系项目维护者**

---

**注意**: 首次同步前请确保：
- GitHub仓库已创建
- 本地代码已测试通过
- 敏感信息已从代码中移除
- 所有必要的文件都已包含

**仓库地址**: https://github.com/xihaopark/RealTimeChatBot_Aiker 