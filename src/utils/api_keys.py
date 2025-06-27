#!/usr/bin/env python3
"""
API密钥管理模块
从api_keys文件夹安全加载API密钥
"""

import os
from pathlib import Path
from typing import Optional


class APIKeyManager:
    """API密钥管理器"""
    
    def __init__(self, keys_dir: str = "api_keys"):
        """
        初始化API密钥管理器
        
        Args:
            keys_dir: API密钥文件夹路径
        """
        self.keys_dir = Path(keys_dir)
        self._keys = {}
        self._load_keys()
    
    def _load_keys(self):
        """加载所有API密钥"""
        if not self.keys_dir.exists():
            print(f"⚠️ API密钥目录不存在: {self.keys_dir}")
            return
        
        # 定义密钥文件映射
        key_files = {
            'openai': 'openai.key',
            'deepgram': 'deepgram.key', 
            'elevenlabs': 'elevenlabs.key'
        }
        
        for service, filename in key_files.items():
            key_path = self.keys_dir / filename
            if key_path.exists():
                try:
                    with open(key_path, 'r') as f:
                        key = f.read().strip()
                        if key and not key.startswith('your_'):
                            self._keys[service] = key
                            print(f"✅ 加载 {service} API密钥成功")
                        else:
                            print(f"⚠️ {service} API密钥未配置或使用占位符")
                except Exception as e:
                    print(f"❌ 加载 {service} API密钥失败: {e}")
            else:
                print(f"⚠️ {service} API密钥文件不存在: {key_path}")
    
    def get_key(self, service: str) -> Optional[str]:
        """
        获取指定服务的API密钥
        
        Args:
            service: 服务名称 (openai, deepgram, elevenlabs)
            
        Returns:
            API密钥或None
        """
        return self._keys.get(service)
    
    def has_key(self, service: str) -> bool:
        """
        检查是否有指定服务的API密钥
        
        Args:
            service: 服务名称
            
        Returns:
            是否有密钥
        """
        return service in self._keys
    
    def get_all_keys(self) -> dict:
        """
        获取所有API密钥
        
        Returns:
            所有密钥的字典
        """
        return self._keys.copy()
    
    def validate_keys(self) -> dict:
        """
        验证所有API密钥
        
        Returns:
            验证结果字典
        """
        results = {}
        
        for service in ['openai', 'deepgram', 'elevenlabs']:
            if self.has_key(service):
                results[service] = {
                    'status': 'available',
                    'key_length': len(self.get_key(service))
                }
            else:
                results[service] = {
                    'status': 'missing',
                    'key_length': 0
                }
        
        return results
    
    def print_status(self):
        """打印API密钥状态"""
        print("\n🔐 API密钥状态:")
        print("=" * 40)
        
        validation = self.validate_keys()
        for service, info in validation.items():
            status_icon = "✅" if info['status'] == 'available' else "❌"
            print(f"{status_icon} {service.upper()}: {info['status']}")
        
        print("=" * 40)


# 全局API密钥管理器实例
api_key_manager = APIKeyManager()


def get_api_key(service: str) -> Optional[str]:
    """
    获取API密钥的便捷函数
    
    Args:
        service: 服务名称
        
    Returns:
        API密钥或None
    """
    return api_key_manager.get_key(service)


def has_api_key(service: str) -> bool:
    """
    检查是否有API密钥的便捷函数
    
    Args:
        service: 服务名称
        
    Returns:
        是否有密钥
    """
    return api_key_manager.has_key(service)


if __name__ == "__main__":
    # 测试API密钥加载
    api_key_manager.print_status() 