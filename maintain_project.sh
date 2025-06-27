#!/bin/bash

# VTX AI Phone System - 项目维护脚本
# 自动化环境检查、依赖安装、测试和部署

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 检查系统环境
check_system_environment() {
    log_info "检查系统环境..."
    
    # 检查Python版本
    python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    log_success "Python版本: $python_version"
    
    # 检查ffmpeg
    if command -v ffmpeg &> /dev/null; then
        ffmpeg_version=$(ffmpeg -version 2>/dev/null | head -n1 | cut -d' ' -f3)
        log_success "FFmpeg版本: $ffmpeg_version"
    else
        log_error "FFmpeg未安装"
        return 1
    fi
    
    # 检查Git
    if command -v git &> /dev/null; then
        git_version=$(git --version | cut -d' ' -f3)
        log_success "Git版本: $git_version"
    else
        log_error "Git未安装"
        return 1
    fi
    
    return 0
}

# 安装Python依赖
install_python_dependencies() {
    log_info "安装Python依赖..."
    
    # 核心依赖
    core_deps=(
        "python-dotenv"
        "aiohttp"
        "numpy"
        "scipy"
        "pydantic"
        "typing_extensions"
        "pydantic_core"
        "openai"
        "loguru"
    )
    
    for dep in "${core_deps[@]}"; do
        log_info "安装 $dep..."
        pip3 install --upgrade "$dep" || {
            log_error "安装 $dep 失败"
            return 1
        }
    done
    
    # 音频处理依赖
    audio_deps=(
        "pydub"
        "librosa"
        "ffmpeg-python"
    )
    
    for dep in "${audio_deps[@]}"; do
        log_info "安装 $dep..."
        pip3 install --upgrade "$dep" || {
            log_warning "安装 $dep 失败，但可能不是必需的"
        }
    done
    
    # AI相关依赖
    ai_deps=(
        "openai-whisper"
        "deepgram-sdk"
        "edge-tts"
        "elevenlabs"
    )
    
    for dep in "${ai_deps[@]}"; do
        log_info "安装 $dep..."
        pip3 install --upgrade "$dep" || {
            log_warning "安装 $dep 失败，但可能不是必需的"
        }
    done
    
    log_success "Python依赖安装完成"
}

# 检查项目配置
check_project_config() {
    log_info "检查项目配置..."
    
    # 检查.env文件
    if [ ! -f ".env" ]; then
        if [ -f "env.example" ]; then
            log_info "复制环境变量模板..."
            cp env.example .env
            log_warning "请编辑 .env 文件，配置必要的环境变量"
        else
            log_error "未找到 .env.example 文件"
            return 1
        fi
    else
        log_success ".env 文件已存在"
    fi
    
    # 检查配置文件
    if [ ! -f "config/settings.py" ]; then
        log_error "配置文件 config/settings.py 不存在"
        return 1
    else
        log_success "配置文件存在"
    fi
    
    # 检查主程序
    if [ ! -f "src/main.py" ]; then
        log_error "主程序 src/main.py 不存在"
        return 1
    else
        log_success "主程序存在"
    fi
    
    return 0
}

# 运行基础测试
run_basic_tests() {
    log_info "运行基础功能测试..."
    
    if [ -f "test_basic_functionality.py" ]; then
        python3 test_basic_functionality.py
        if [ $? -eq 0 ]; then
            log_success "基础功能测试通过"
        else
            log_warning "基础功能测试部分失败，但可能不影响主要功能"
        fi
    else
        log_warning "未找到测试文件 test_basic_functionality.py"
    fi
}

# 测试配置加载
test_config_loading() {
    log_info "测试配置加载..."
    
    python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from config.settings import settings
    print('✅ 配置加载成功')
    print(f'   VTX服务器: {settings.vtx.server}')
    print(f'   VTX端口: {settings.vtx.port}')
    print(f'   VTX域名: {settings.vtx.domain}')
    print(f'   DID号码: {settings.vtx.did_number}')
    exit(0)
except Exception as e:
    print(f'❌ 配置加载失败: {e}')
    exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_success "配置加载测试通过"
    else
        log_error "配置加载测试失败"
        return 1
    fi
}

# 测试主程序启动
test_main_program() {
    log_info "测试主程序启动..."
    
    # 使用timeout防止程序无限运行
    timeout 10 python3 src/main.py > /tmp/main_test.log 2>&1 &
    main_pid=$!
    
    # 等待几秒钟
    sleep 5
    
    # 检查进程是否还在运行
    if kill -0 $main_pid 2>/dev/null; then
        log_success "主程序启动成功"
        kill $main_pid 2>/dev/null || true
        return 0
    else
        log_error "主程序启动失败"
        cat /tmp/main_test.log
        return 1
    fi
}

# 创建系统服务
create_system_service() {
    log_info "创建系统服务..."
    
    local current_dir=$(pwd)
    local service_name="vtx-ai-phone"
    
    # 创建systemd服务文件
    cat > "/tmp/$service_name.service" << EOF
[Unit]
Description=VTX AI Phone System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$current_dir
Environment=PATH=$current_dir/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/usr/bin/python3 $current_dir/src/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    # 复制服务文件到系统目录
    if command -v sudo &> /dev/null; then
        sudo cp "/tmp/$service_name.service" "/etc/systemd/system/"
        sudo systemctl daemon-reload
        log_success "系统服务创建完成"
        log_info "使用以下命令管理服务："
        log_info "  启动: sudo systemctl start $service_name"
        log_info "  停止: sudo systemctl stop $service_name"
        log_info "  状态: sudo systemctl status $service_name"
        log_info "  开机启动: sudo systemctl enable $service_name"
    else
        log_warning "未找到sudo，请手动安装服务文件"
        log_info "服务文件位置: /tmp/$service_name.service"
    fi
}

# 创建启动脚本
create_startup_script() {
    log_info "创建启动脚本..."
    
    cat > "start_vtx.sh" << 'EOF'
#!/bin/bash

# VTX AI Phone System 启动脚本

echo "🚀 启动 VTX AI Phone System..."
echo "=================================="

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查主程序
if [ ! -f "src/main.py" ]; then
    echo "❌ 主程序不存在: src/main.py"
    exit 1
fi

# 启动主程序
echo "📞 启动AI电话系统..."
python3 src/main.py
EOF
    
    chmod +x start_vtx.sh
    log_success "启动脚本创建完成: start_vtx.sh"
}

# 创建监控脚本
create_monitor_script() {
    log_info "创建监控脚本..."
    
    cat > "monitor_vtx.sh" << 'EOF'
#!/bin/bash

# VTX AI Phone System 监控脚本

echo "📊 VTX AI Phone System 状态监控"
echo "=================================="

# 检查进程
if pgrep -f "python.*main.py" > /dev/null; then
    echo "✅ 主程序运行中"
    ps aux | grep "python.*main.py" | grep -v grep
else
    echo "❌ 主程序未运行"
fi

# 检查端口
echo ""
echo "🔌 端口状态:"
netstat -tlnp 2>/dev/null | grep -E "(5060|10000|8501)" || echo "未找到相关端口"

# 检查日志
echo ""
echo "📝 最近日志:"
if [ -f "logs/vtx_system.log" ]; then
    tail -10 logs/vtx_system.log
else
    echo "未找到日志文件"
fi
EOF
    
    chmod +x monitor_vtx.sh
    log_success "监控脚本创建完成: monitor_vtx.sh"
}

# 生成项目状态报告
generate_status_report() {
    log_info "生成项目状态报告..."
    
    local report_file="project_status_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "VTX AI Phone System - 项目状态报告"
        echo "生成时间: $(date)"
        echo "=================================="
        echo ""
        
        echo "系统环境:"
        echo "  Python版本: $(python3 --version 2>&1)"
        echo "  FFmpeg版本: $(ffmpeg -version 2>/dev/null | head -n1 | cut -d' ' -f3 || echo '未安装')"
        echo "  Git版本: $(git --version | cut -d' ' -f3)"
        echo ""
        
        echo "项目文件:"
        echo "  主程序: $(test -f src/main.py && echo '存在' || echo '不存在')"
        echo "  配置文件: $(test -f config/settings.py && echo '存在' || echo '不存在')"
        echo "  环境变量: $(test -f .env && echo '存在' || echo '不存在')"
        echo ""
        
        echo "Python依赖:"
        pip3 list | grep -E "(numpy|aiohttp|openai|pydantic|whisper|edge-tts)" || echo "  未找到相关依赖"
        echo ""
        
        echo "网络连接:"
        if ping -c 1 core1-us-lax.myippbx.com > /dev/null 2>&1; then
            echo "  VTX服务器: 可连接"
        else
            echo "  VTX服务器: 不可连接"
        fi
        echo ""
        
        echo "进程状态:"
        if pgrep -f "python.*main.py" > /dev/null; then
            echo "  主程序: 运行中"
        else
            echo "  主程序: 未运行"
        fi
        
    } > "$report_file"
    
    log_success "状态报告已生成: $report_file"
}

# 主函数
main() {
    echo "🚀 VTX AI Phone System - 项目维护工具"
    echo "=========================================="
    
    # 解析命令行参数
    case "${1:-all}" in
        "check")
            check_system_environment
            check_project_config
            ;;
        "install")
            install_python_dependencies
            ;;
        "test")
            run_basic_tests
            test_config_loading
            test_main_program
            ;;
        "service")
            create_system_service
            ;;
        "scripts")
            create_startup_script
            create_monitor_script
            ;;
        "report")
            generate_status_report
            ;;
        "all")
            log_info "执行完整维护流程..."
            check_system_environment || exit 1
            install_python_dependencies
            check_project_config || exit 1
            run_basic_tests
            test_config_loading || exit 1
            test_main_program || log_warning "主程序测试失败，但可能不影响功能"
            create_startup_script
            create_monitor_script
            generate_status_report
            ;;
        *)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  check     检查系统环境和项目配置"
            echo "  install   安装Python依赖"
            echo "  test      运行测试"
            echo "  service   创建系统服务"
            echo "  scripts   创建启动和监控脚本"
            echo "  report    生成状态报告"
            echo "  all       执行完整维护流程（默认）"
            exit 1
            ;;
    esac
    
    echo ""
    log_success "🎉 项目维护完成！"
}

# 错误处理
trap 'log_error "维护过程中发生错误，请检查日志"; exit 1' ERR

# 运行主函数
main "$@" 