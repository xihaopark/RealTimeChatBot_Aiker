#!/usr/bin/env python3
"""
VTX AI Phone System - API密钥管理器
"""

import os
import asyncio
import aiohttp
from pathlib import Path
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class APIKeyManager:
    """API密钥管理器"""
    
    def __init__(self, api_keys_dir: str = "api_keys"):
        self.api_keys_dir = Path(api_keys_dir)
        self.keys = {}
        self._load_keys()
    
    def _load_keys(self):
        """加载所有API密钥"""
        key_files = {
            'deepgram': self.api_keys_dir / 'deepgram.key',
            'elevenlabs': self.api_keys_dir / 'elevenlabs.key',
            'openai': self.api_keys_dir / 'openai.key'
        }
        
        for service, key_file in key_files.items():
            if key_file.exists():
                self.keys[service] = key_file.read_text().strip()
                logger.info(f"✅ 已加载 {service} API密钥")
            else:
                self.keys[service] = None
                logger.warning(f"⚠️ {service} API密钥未找到: {key_file}")
    
    def get_key(self, service: str) -> Optional[str]:
        """获取指定服务的API密钥"""
        return self.keys.get(service)
    
    def has_key(self, service: str) -> bool:
        """检查是否有指定服务的API密钥"""
        return bool(self.keys.get(service))
    
    def get_available_services(self) -> List[str]:
        """获取可用的服务列表"""
        return [service for service, key in self.keys.items() if key]
    
    async def _test_api_key(self, service: str, api_key: str) -> bool:
        """测试API密钥的有效性"""
        try:
            if service == 'deepgram':
                return await self._test_deepgram_key(api_key)
            elif service == 'elevenlabs':
                return await self._test_elevenlabs_key(api_key)
            elif service == 'openai':
                return await self._test_openai_key(api_key)
            else:
                logger.warning(f"未知服务: {service}")
                return False
        except Exception as e:
            logger.error(f"测试 {service} API密钥时出错: {e}")
            return False
    
    async def _test_deepgram_key(self, api_key: str) -> bool:
        """测试Deepgram API密钥"""
        try:
            url = "https://api.deepgram.com/v1/projects"
            headers = {"Authorization": f"Token {api_key}"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Deepgram API测试失败: {e}")
            return False
    
    async def _test_elevenlabs_key(self, api_key: str) -> bool:
        """测试ElevenLabs API密钥"""
        try:
            url = "https://api.elevenlabs.io/v1/voices"
            headers = {"xi-api-key": api_key}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"ElevenLabs API测试失败: {e}")
            return False
    
    async def _test_openai_key(self, api_key: str) -> bool:
        """测试OpenAI API密钥"""
        try:
            url = "https://api.openai.com/v1/models"
            headers = {"Authorization": f"Bearer {api_key}"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"OpenAI API测试失败: {e}")
            return False
    
    async def validate_keys(self) -> Dict[str, bool]:
        """验证所有API密钥的有效性"""
        logger.info("🔍 开始验证API密钥...")
        validation_results = {}
        
        for service, key in self.keys.items():
            if key:
                logger.info(f"测试 {service} API密钥...")
                validation_results[service] = await self._test_api_key(service, key)
            else:
                validation_results[service] = False
        
        return validation_results
    
    def print_status(self, validation_results: Optional[Dict[str, bool]] = None):
        """打印API密钥状态"""
        print("\n🔑 API密钥状态:")
        print("=" * 50)
        
        for service, key in self.keys.items():
            status = "✅ 有效" if validation_results and validation_results.get(service) else "❌ 无效"
            has_key = "已配置" if key else "未配置"
            print(f"{service:12} | {has_key:8} | {status}")
        
        print("=" * 50)
    
    def get_missing_services(self) -> List[str]:
        """获取缺失的服务列表"""
        return [service for service, key in self.keys.items() if not key]
    
    def create_key_file(self, service: str, api_key: str) -> bool:
        """创建API密钥文件"""
        try:
            key_file = self.api_keys_dir / f"{service}.key"
            key_file.write_text(api_key.strip())
            self.keys[service] = api_key.strip()
            logger.info(f"✅ 已创建 {service} API密钥文件")
            return True
        except Exception as e:
            logger.error(f"创建 {service} API密钥文件失败: {e}")
            return False
    
    def get_service_info(self) -> Dict[str, Dict]:
        """获取服务信息"""
        return {
            'deepgram': {
                'name': 'Deepgram',
                'purpose': '流式语音识别',
                'cost': '$0.0043/分钟',
                'url': 'https://deepgram.com/',
                'features': ['低延迟', '高准确率', '多语言支持']
            },
            'elevenlabs': {
                'name': 'ElevenLabs',
                'purpose': '高品质语音合成',
                'cost': '$0.18/1000字符',
                'url': 'https://elevenlabs.io/',
                'features': ['真人级语音', '多语言支持', '情感控制']
            },
            'openai': {
                'name': 'OpenAI',
                'purpose': '智能对话生成',
                'cost': '按使用量计费',
                'url': 'https://platform.openai.com/',
                'features': ['GPT-4o-mini', '高智能', '多轮对话']
            }
        }


# 全局API密钥管理器实例
api_manager = APIKeyManager() 