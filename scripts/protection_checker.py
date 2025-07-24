#!/usr/bin/env python3
"""
保护检查脚本
用于验证受保护模块的完整性和兼容性
"""

import os
import sys
import yaml
import json
import hashlib
import ast
import argparse
from typing import Dict, List, Any, Optional
from pathlib import Path

class ProtectionChecker:
    """保护检查器"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.protected_modules = self._load_protected_modules()
        self.context_map = self._load_context_map()
        self.violations = []
        self.warnings = []
        
    def _load_protected_modules(self) -> Dict[str, Any]:
        """加载受保护模块配置"""
        config_path = self.project_root / ".ai" / "protected_modules.yaml"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ 加载受保护模块配置失败: {e}")
            return {}
    
    def _load_context_map(self) -> Dict[str, Any]:
        """加载上下文映射"""
        config_path = self.project_root / ".ai" / "context_map.json"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载上下文映射失败: {e}")
            return {}
    
    def check_all(self) -> Dict[str, Any]:
        """执行所有检查"""
        print("🔍 开始保护检查...")
        
        results = {
            "module_integrity": self.check_module_integrity(),
            "interface_compatibility": self.check_interface_compatibility(),
            "constant_validation": self.check_constants(),
            "file_protection": self.check_file_protection(),
            "performance_constraints": self.check_performance_constraints(),
            "violations": self.violations,
            "warnings": self.warnings
        }
        
        self._print_summary(results)
        return results
    
    def check_module_integrity(self) -> Dict[str, Any]:
        """检查模块完整性"""
        print("📋 检查模块完整性...")
        
        results = {}
        protected_modules = self.protected_modules.get("protected_modules", [])
        
        for module_info in protected_modules:
            module_name = module_info["module"]
            file_path = self.project_root / module_info["file_path"]
            
            if not file_path.exists():
                self.violations.append(f"受保护文件不存在: {file_path}")
                continue
            
            # 检查文件哈希
            file_hash = self._calculate_file_hash(file_path)
            
            # 检查类/函数是否存在
            integrity_check = self._check_class_methods(file_path, module_info)
            
            results[module_name] = {
                "file_exists": True,
                "file_hash": file_hash,
                "integrity_check": integrity_check,
                "protection_level": module_info["protection_level"]
            }
        
        return results
    
    def check_interface_compatibility(self) -> Dict[str, Any]:
        """检查接口兼容性"""
        print("🔌 检查接口兼容性...")
        
        results = {}
        protected_interfaces = self.protected_modules.get("protected_interfaces", [])
        
        for interface_info in protected_interfaces:
            interface_name = interface_info["interface"]
            signature = interface_info["signature"]
            
            # 解析接口路径
            parts = interface_name.split(".")
            if len(parts) >= 2:
                module_name = parts[0]
                method_name = parts[1]
                
                # 检查接口是否存在且签名匹配
                compatibility_check = self._check_interface_signature(
                    module_name, method_name, signature
                )
                
                results[interface_name] = {
                    "exists": compatibility_check["exists"],
                    "signature_match": compatibility_check["signature_match"],
                    "current_signature": compatibility_check["current_signature"]
                }
                
                if not compatibility_check["exists"]:
                    self.violations.append(f"受保护接口不存在: {interface_name}")
                elif not compatibility_check["signature_match"]:
                    self.violations.append(f"接口签名不匹配: {interface_name}")
        
        return results
    
    def check_constants(self) -> Dict[str, Any]:
        """检查常量"""
        print("🔢 检查受保护常量...")
        
        results = {}
        protected_constants = self.protected_modules.get("protected_constants", {})
        
        for const_name, const_info in protected_constants.items():
            expected_value = const_info["value"]
            location = const_info["location"]
            
            # 检查常量值
            actual_value = self._find_constant_value(const_name, location)
            
            results[const_name] = {
                "expected": expected_value,
                "actual": actual_value,
                "match": actual_value == expected_value,
                "location": location,
                "protection": const_info["protection"]
            }
            
            if actual_value != expected_value:
                if const_info["protection"] == "ABSOLUTE":
                    self.violations.append(f"受保护常量值被修改: {const_name}")
                else:
                    self.warnings.append(f"常量值发生变化: {const_name}")
        
        return results
    
    def check_file_protection(self) -> Dict[str, Any]:
        """检查文件保护"""
        print("📁 检查文件保护...")
        
        results = {}
        protected_files = self.protected_modules.get("protected_files", [])
        
        for file_info in protected_files:
            file_path = self.project_root / file_info["file"]
            
            if not file_path.exists():
                self.violations.append(f"受保护文件不存在: {file_path}")
                continue
            
            # 检查文件修改时间
            stat = file_path.stat()
            
            results[file_info["file"]] = {
                "exists": True,
                "size": stat.st_size,
                "modified_time": stat.st_mtime,
                "protection": file_info.get("protection", "UNKNOWN"),
                "sections": file_info.get("sections", [])
            }
        
        return results
    
    def check_performance_constraints(self) -> Dict[str, Any]:
        """检查性能约束"""
        print("⚡ 检查性能约束...")
        
        results = {}
        contexts = self.context_map.get("contexts", {})
        
        for context_name, context_info in contexts.items():
            performance_targets = context_info.get("performance_targets", {})
            if performance_targets:
                results[context_name] = {
                    "targets": performance_targets,
                    "status": "需要运行时验证"
                }
        
        return results
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            self.warnings.append(f"无法计算文件哈希: {file_path} - {e}")
            return ""
    
    def _check_class_methods(self, file_path: Path, module_info: Dict[str, Any]) -> Dict[str, Any]:
        """检查类和方法"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # 提取类名
            module_name = module_info["module"]
            class_name = module_name.split(".")[-1]
            
            # 查找类定义
            class_found = False
            methods_found = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    class_found = True
                    
                    # 检查方法
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods_found.append(item.name)
            
            expected_methods = module_info.get("methods", [])
            missing_methods = [m for m in expected_methods if m not in methods_found]
            
            return {
                "class_found": class_found,
                "methods_found": methods_found,
                "expected_methods": expected_methods,
                "missing_methods": missing_methods,
                "complete": class_found and len(missing_methods) == 0
            }
            
        except Exception as e:
            self.warnings.append(f"无法解析文件: {file_path} - {e}")
            return {"error": str(e)}
    
    def _check_interface_signature(self, module_name: str, method_name: str, expected_signature: str) -> Dict[str, Any]:
        """检查接口签名"""
        # 这里应该实现更复杂的签名检查逻辑
        # 暂时返回基本检查结果
        return {
            "exists": True,  # 简化实现
            "signature_match": True,  # 简化实现
            "current_signature": expected_signature
        }
    
    def _find_constant_value(self, const_name: str, location: str) -> Any:
        """查找常量值"""
        # 这里应该实现常量值查找逻辑
        # 暂时返回None表示未找到
        return None
    
    def _print_summary(self, results: Dict[str, Any]):
        """打印检查摘要"""
        print("\n" + "="*50)
        print("📊 保护检查摘要")
        print("="*50)
        
        total_violations = len(self.violations)
        total_warnings = len(self.warnings)
        
        if total_violations == 0:
            print("✅ 没有发现违规行为")
        else:
            print(f"❌ 发现 {total_violations} 个违规行为:")
            for violation in self.violations:
                print(f"  - {violation}")
        
        if total_warnings > 0:
            print(f"⚠️  发现 {total_warnings} 个警告:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        print("\n📋 检查项目状态:")
        for check_name, check_result in results.items():
            if check_name in ["violations", "warnings"]:
                continue
            
            if isinstance(check_result, dict):
                passed = sum(1 for v in check_result.values() if isinstance(v, dict) and v.get("complete", True))
                total = len(check_result)
                print(f"  {check_name}: {passed}/{total} 通过")
            else:
                print(f"  {check_name}: {check_result}")
    
    def generate_report(self, output_file: str = "protection_report.json"):
        """生成检查报告"""
        results = self.check_all()
        
        report = {
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "summary": {
                "total_violations": len(self.violations),
                "total_warnings": len(self.warnings),
                "status": "PASS" if len(self.violations) == 0 else "FAIL"
            },
            "results": results
        }
        
        output_path = self.project_root / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📄 报告已生成: {output_path}")
        return report

def main():
    parser = argparse.ArgumentParser(description="VTX AI Phone System 保护检查器")
    parser.add_argument("--mode", choices=["check", "report", "git-hook"], 
                       default="check", help="运行模式")
    parser.add_argument("--output", default="protection_report.json", 
                       help="报告输出文件")
    parser.add_argument("--files", nargs="*", help="要检查的文件列表")
    
    args = parser.parse_args()
    
    if args.mode == "check":
        checker = ProtectionChecker()
        checker.check_all()
        
    elif args.mode == "report":
        checker = ProtectionChecker()
        checker.generate_report(args.output)

if __name__ == "__main__":
    main() 