#!/usr/bin/env python3
"""
服务器环境检测脚本
全面检测网络、系统、Python环境等
"""

import os
import sys
import subprocess
import socket
import platform
import json
from datetime import datetime
from pathlib import Path

class ServerEnvironmentChecker:
    """服务器环境检测器"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "system": {},
            "network": {},
            "python": {},
            "packages": {},
            "ports": {},
            "recommendations": []
        }
        
        print("🔍 服务器环境检测开始...")
        print("=" * 60)
    
    def run_all_checks(self):
        """运行所有检测"""
        self.check_system_info()
        self.check_network_connectivity()
        self.check_python_environment()
        self.check_package_managers()
        self.check_ports()
        self.generate_recommendations()
        self.save_results()
    
    def check_system_info(self):
        """检测系统信息"""
        print("\n🖥️ 检测系统信息...")
        
        try:
            # 操作系统信息
            self.results["system"]["os"] = platform.system()
            self.results["system"]["os_version"] = platform.version()
            self.results["system"]["architecture"] = platform.machine()
            self.results["system"]["hostname"] = platform.node()
            
            # 内核信息
            try:
                with open('/proc/version', 'r') as f:
                    kernel_info = f.read().strip()
                    self.results["system"]["kernel"] = kernel_info
            except:
                self.results["system"]["kernel"] = "无法读取"
            
            # CPU信息
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    cpu_info = f.read()
                    cpu_count = cpu_info.count('processor')
                    self.results["system"]["cpu_count"] = cpu_count
            except:
                self.results["system"]["cpu_count"] = "无法读取"
            
            # 内存信息
            try:
                with open('/proc/meminfo', 'r') as f:
                    mem_info = f.read()
                    total_mem = None
                    for line in mem_info.split('\n'):
                        if line.startswith('MemTotal:'):
                            total_mem = line.split()[1]
                            break
                    self.results["system"]["total_memory_kb"] = total_mem
            except:
                self.results["system"]["total_memory_kb"] = "无法读取"
            
            # 磁盘信息
            try:
                result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        disk_info = lines[1].split()
                        self.results["system"]["disk_info"] = {
                            "total": disk_info[1],
                            "used": disk_info[2],
                            "available": disk_info[3],
                            "usage_percent": disk_info[4]
                        }
            except:
                self.results["system"]["disk_info"] = "无法读取"
            
            print(f"✅ 操作系统: {self.results['system']['os']} {self.results['system']['os_version']}")
            print(f"✅ 架构: {self.results['system']['architecture']}")
            print(f"✅ 主机名: {self.results['system']['hostname']}")
            
        except Exception as e:
            print(f"❌ 系统信息检测失败: {e}")
    
    def check_network_connectivity(self):
        """检测网络连通性"""
        print("\n🌐 检测网络连通性...")
        
        # 测试目标
        test_targets = [
            ("8.8.8.8", "Google DNS"),
            ("114.114.114.114", "114 DNS"),
            ("223.5.5.5", "阿里DNS"),
            ("pypi.tuna.tsinghua.edu.cn", "清华镜像源"),
            ("mirrors.aliyun.com", "阿里云镜像源"),
            ("pypi.douban.com", "豆瓣镜像源"),
            ("core1-us-lax.myippbx.com", "VTX SIP服务器"),
            ("api.openai.com", "OpenAI API"),
            ("api.deepgram.com", "Deepgram API"),
            ("api.elevenlabs.io", "ElevenLabs API")
        ]
        
        for target, description in test_targets:
            try:
                # DNS解析测试
                try:
                    ip = socket.gethostbyname(target)
                    dns_ok = True
                except:
                    ip = "解析失败"
                    dns_ok = False
                
                # Ping测试
                try:
                    result = subprocess.run(['ping', '-c', '1', '-W', '3', target], 
                                          capture_output=True, text=True, timeout=10)
                    ping_ok = result.returncode == 0
                except:
                    ping_ok = False
                
                # HTTP测试（对于域名）
                http_ok = False
                if dns_ok and not target.replace('.', '').isdigit():
                    try:
                        result = subprocess.run(['curl', '-I', '--connect-timeout', '5', 
                                               f'https://{target}'], 
                                              capture_output=True, text=True, timeout=10)
                        http_ok = result.returncode == 0
                    except:
                        pass
                
                self.results["network"][target] = {
                    "description": description,
                    "dns_resolved": dns_ok,
                    "ip": ip,
                    "ping_ok": ping_ok,
                    "http_ok": http_ok
                }
                
                status = "✅" if dns_ok else "❌"
                print(f"{status} {description}: {ip}")
                
            except Exception as e:
                print(f"❌ {description} 检测失败: {e}")
                self.results["network"][target] = {
                    "description": description,
                    "error": str(e)
                }
    
    def check_python_environment(self):
        """检测Python环境"""
        print("\n🐍 检测Python环境...")
        
        try:
            # Python版本
            self.results["python"]["version"] = sys.version
            self.results["python"]["executable"] = sys.executable
            
            # Python路径
            self.results["python"]["path"] = os.environ.get('PATH', '')
            self.results["python"]["pythonpath"] = os.environ.get('PYTHONPATH', '')
            
            # 检查pip
            try:
                result = subprocess.run([sys.executable, '-m', 'pip', '--version'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    self.results["python"]["pip_version"] = result.stdout.strip()
                    pip_ok = True
                else:
                    pip_ok = False
            except:
                pip_ok = False
                self.results["python"]["pip_version"] = "未安装"
            
            # 检查venv
            try:
                result = subprocess.run([sys.executable, '-m', 'venv', '--help'], 
                                      capture_output=True, text=True)
                venv_ok = result.returncode == 0
            except:
                venv_ok = False
            
            # 检查已安装的包
            if pip_ok:
                try:
                    result = subprocess.run([sys.executable, '-m', 'pip', 'list'], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        packages = []
                        for line in result.stdout.strip().split('\n')[2:]:  # 跳过标题行
                            if line.strip():
                                parts = line.split()
                                if len(parts) >= 2:
                                    packages.append({
                                        "name": parts[0],
                                        "version": parts[1]
                                    })
                        self.results["python"]["installed_packages"] = packages
                except:
                    self.results["python"]["installed_packages"] = []
            
            print(f"✅ Python版本: {sys.version.split()[0]}")
            print(f"✅ Python路径: {sys.executable}")
            print(f"{'✅' if pip_ok else '❌'} pip: {self.results['python']['pip_version']}")
            print(f"{'✅' if venv_ok else '❌'} venv: {'可用' if venv_ok else '不可用'}")
            
        except Exception as e:
            print(f"❌ Python环境检测失败: {e}")
    
    def check_package_managers(self):
        """检测包管理器"""
        print("\n📦 检测包管理器...")
        
        package_managers = [
            ("apt", "apt-get --version"),
            ("yum", "yum --version"),
            ("dnf", "dnf --version"),
            ("pip", "pip --version"),
            ("conda", "conda --version")
        ]
        
        for name, command in package_managers:
            try:
                result = subprocess.run(command.split(), capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    self.results["packages"][name] = {
                        "available": True,
                        "version": result.stdout.strip().split('\n')[0]
                    }
                    print(f"✅ {name}: 可用")
                else:
                    self.results["packages"][name] = {"available": False}
                    print(f"❌ {name}: 不可用")
            except:
                self.results["packages"][name] = {"available": False}
                print(f"❌ {name}: 不可用")
    
    def check_ports(self):
        """检测端口状态"""
        print("\n🔌 检测端口状态...")
        
        # 检查常用端口
        ports_to_check = [
            (22, "SSH"),
            (80, "HTTP"),
            (443, "HTTPS"),
            (5060, "SIP"),
            (8501, "Streamlit"),
            (35122, "Custom")
        ]
        
        for port, service in ports_to_check:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                
                status = "开放" if result == 0 else "关闭"
                self.results["ports"][port] = {
                    "service": service,
                    "status": status
                }
                print(f"{'✅' if result == 0 else '❌'} 端口 {port} ({service}): {status}")
                
            except Exception as e:
                self.results["ports"][port] = {
                    "service": service,
                    "status": "检测失败",
                    "error": str(e)
                }
                print(f"❌ 端口 {port} ({service}): 检测失败")
    
    def generate_recommendations(self):
        """生成建议"""
        print("\n💡 生成建议...")
        
        recommendations = []
        
        # 网络建议
        if not self.results["network"].get("pypi.tuna.tsinghua.edu.cn", {}).get("dns_resolved", False):
            recommendations.append("网络无法访问清华镜像源，建议配置代理或使用其他镜像源")
        
        if not self.results["network"].get("core1-us-lax.myippbx.com", {}).get("dns_resolved", False):
            recommendations.append("无法解析VTX服务器域名，可能影响SIP连接")
        
        # Python建议
        if not self.results["packages"].get("pip", {}).get("available", False):
            recommendations.append("pip不可用，需要安装pip")
        
        if not self.results["packages"].get("apt", {}).get("available", False):
            recommendations.append("apt不可用，可能需要使用其他包管理器")
        
        # 系统建议
        if self.results["system"].get("disk_info"):
            usage = self.results["system"]["disk_info"].get("usage_percent", "0%")
            if usage != "无法读取":
                usage_num = int(usage.replace('%', ''))
                if usage_num > 80:
                    recommendations.append(f"磁盘使用率过高: {usage}，建议清理空间")
        
        self.results["recommendations"] = recommendations
        
        if recommendations:
            print("⚠️ 发现以下问题:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        else:
            print("✅ 环境检查通过，未发现明显问题")
    
    def save_results(self):
        """保存检测结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = f"server_env_check_{timestamp}.json"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📝 检测结果已保存到: {result_file}")
        print("=" * 60)
        print("🔍 环境检测完成！")
        print("=" * 60)


def main():
    """主函数"""
    checker = ServerEnvironmentChecker()
    checker.run_all_checks()


if __name__ == "__main__":
    main() 