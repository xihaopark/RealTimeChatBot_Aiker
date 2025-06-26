#!/bin/bash

# VTX AI Phone System - GitHub同步脚本
# 自动提交代码变更并推送到GitHub仓库

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
REPO_URL="https://github.com/xihaopark/RealTimeChatBot_Aiker.git"
BRANCH="main"
COMMIT_MESSAGE=""

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Git是否安装
check_git() {
    if ! command -v git &> /dev/null; then
        log_error "Git未安装，请先安装Git"
        exit 1
    fi
    log_success "Git检查通过"
}

# 检查是否在Git仓库中
check_repo() {
    if [ ! -d ".git" ]; then
        log_error "当前目录不是Git仓库"
        log_info "正在初始化Git仓库..."
        git init
        git remote add origin "$REPO_URL"
        log_success "Git仓库初始化完成"
    fi
    
    # 确保分支名称正确
    local current_branch=$(git branch --show-current 2>/dev/null || echo "master")
    if [ "$current_branch" != "$BRANCH" ]; then
        log_info "当前分支: $current_branch，重命名为: $BRANCH"
        git branch -M "$BRANCH"
    fi
}

# 检查远程仓库连接
check_remote() {
    log_info "检查远程仓库连接..."
    if ! git remote get-url origin &> /dev/null; then
        log_warning "未配置远程仓库，正在添加..."
        git remote add origin "$REPO_URL"
    fi
    
    # 测试连接
    if ! git ls-remote --exit-code origin &> /dev/null; then
        log_error "无法连接到远程仓库，请检查网络连接和仓库URL"
        exit 1
    fi
    log_success "远程仓库连接正常"
}

# 获取变更状态
get_status() {
    log_info "检查代码变更状态..."
    
    # 检查是否有未跟踪的文件
    local untracked_files=$(git ls-files --others --exclude-standard)
    local modified_files=$(git diff --name-only)
    local staged_files=$(git diff --cached --name-only)
    
    # 合并所有变更
    local all_changes=$(echo -e "$untracked_files\n$modified_files\n$staged_files" | grep -v '^$' | sort -u)
    
    if [ -z "$all_changes" ]; then
        log_warning "没有检测到代码变更"
        return 1
    fi
    
    # 显示变更摘要
    log_info "检测到以下变更："
    
    # 显示未跟踪的文件
    if [ -n "$untracked_files" ]; then
        echo "📁 新文件:"
        echo "$untracked_files" | sed 's/^/  + /'
    fi
    
    # 显示已修改的文件
    if [ -n "$modified_files" ]; then
        echo "📝 修改文件:"
        echo "$modified_files" | sed 's/^/  M /'
    fi
    
    # 显示已暂存的文件
    if [ -n "$staged_files" ]; then
        echo "✅ 已暂存:"
        echo "$staged_files" | sed 's/^/  S /'
    fi
    
    return 0
}

# 生成提交信息
generate_commit_message() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # 获取所有变更文件（包括新文件）
    local untracked_files=$(git ls-files --others --exclude-standard)
    local modified_files=$(git diff --name-only)
    local staged_files=$(git diff --cached --name-only)
    
    # 合并所有变更
    local all_changes=$(echo -e "$untracked_files\n$modified_files\n$staged_files" | grep -v '^$' | sort -u)
    
    if [ -z "$COMMIT_MESSAGE" ]; then
        # 自动生成提交信息
        local change_count=$(echo "$all_changes" | wc -l)
        local change_summary=$(echo "$all_changes" | head -3 | tr '\n' ' ' | sed 's/ $//')
        
        if [ "$change_count" -gt 3 ]; then
            change_summary="$change_summary ... 等${change_count}个文件"
        fi
        
        # 根据变更类型生成不同的前缀
        if [ -n "$untracked_files" ]; then
            COMMIT_MESSAGE="Add: $change_summary - $timestamp"
        else
            COMMIT_MESSAGE="Update: $change_summary - $timestamp"
        fi
    fi
}

# 执行同步
sync_to_github() {
    log_info "开始同步到GitHub..."
    
    # 添加所有变更
    log_info "添加文件到暂存区..."
    git add .
    
    # 生成提交信息
    generate_commit_message
    
    # 提交变更
    log_info "提交变更: $COMMIT_MESSAGE"
    git commit -m "$COMMIT_MESSAGE"
    
    # 推送到远程仓库
    log_info "推送到GitHub..."
    if git push origin "$BRANCH"; then
        log_success "代码已成功推送到GitHub"
        log_info "仓库地址: $REPO_URL"
    else
        log_error "推送失败，请检查网络连接和权限"
        exit 1
    fi
}

# 清理临时文件
cleanup() {
    log_info "清理临时文件..."
    
    # 删除Python缓存文件
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    
    # 删除系统文件
    find . -name ".DS_Store" -delete 2>/dev/null || true
    
    log_success "清理完成"
}

# 显示帮助信息
show_help() {
    echo "VTX AI Phone System - GitHub同步脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -m, --message TEXT    指定提交信息"
    echo "  -b, --branch BRANCH   指定分支名称 (默认: main)"
    echo "  -c, --cleanup         清理临时文件"
    echo "  -h, --help            显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                    自动同步所有变更"
    echo "  $0 -m '修复bug'       使用指定信息提交"
    echo "  $0 -c                 仅清理临时文件"
}

# 主函数
main() {
    echo "🚀 VTX AI Phone System - GitHub同步工具"
    echo "=========================================="
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -m|--message)
                COMMIT_MESSAGE="$2"
                shift 2
                ;;
            -b|--branch)
                BRANCH="$2"
                shift 2
                ;;
            -c|--cleanup)
                cleanup
                exit 0
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 执行同步流程
    check_git
    check_repo
    check_remote
    
    # 检查是否有变更
    if ! get_status; then
        log_warning "没有检测到代码变更，跳过同步"
        exit 0
    fi
    
    # 执行同步
    sync_to_github
    
    echo ""
    log_success "🎉 GitHub同步完成！"
    log_info "查看仓库: $REPO_URL"
}

# 错误处理
trap 'log_error "同步过程中发生错误，请检查日志"; exit 1' ERR

# 运行主函数
main "$@" 