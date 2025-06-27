"""
大语言模型处理器
支持 OpenAI API 和兼容接口
"""

import os
import time
import json
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import aiohttp

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("⚠️ OpenAI 库未安装")


class LLMProvider(Enum):
    """LLM 提供商"""
    OPENAI = "openai"
    AZURE = "azure"
    CUSTOM = "custom"  # 自定义 API


@dataclass
class Message:
    """对话消息"""
    role: str  # system, user, assistant
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    api_base: Optional[str] = None  # 自定义 API 地址
    temperature: float = 0.7
    max_tokens: int = 150
    system_prompt: str = """你是一个友好的AI电话助手。请用简洁、自然的语言回答用户问题。
记住这是电话对话，回答要简短明了，避免长篇大论。"""
    timeout: float = 30.0
    base_url: Optional[str] = None


class LLMHandler:
    """LLM 处理器"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """
        初始化 LLM 处理器
        
        Args:
            config: LLM 配置
        """
        self.config = config or LLMConfig()
        
        # 从API密钥管理器获取密钥
        from src.utils.api_keys import get_api_key
        
        if self.config.provider == LLMProvider.OPENAI:
            # 优先使用配置中的密钥，然后尝试API密钥管理器
            api_key = self.config.api_key or get_api_key('openai')
            if not api_key or api_key.startswith('your_'):
                raise ValueError("未设置 OpenAI API 密钥")
            
            # 设置OpenAI客户端
            openai.api_key = api_key
            if self.config.base_url:
                openai.base_url = self.config.base_url
            
            print(f"🤖 LLM 处理器初始化: {self.config.provider.value}")
            print(f"   模型: {self.config.model}")
            print(f"   API密钥: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else '***'}")
        else:
            print(f"🤖 LLM 处理器初始化: {self.config.provider.value}")
        
        # 对话历史
        self.conversation_history: List[Message] = []
        
        # 添加系统提示
        if self.config.system_prompt:
            self.conversation_history.append(
                Message("system", self.config.system_prompt)
            )
        
        # 设置回调
        self.on_response = None
    
    async def generate_response(self, user_input: str) -> Optional[str]:
        """
        生成回复
        
        Args:
            user_input: 用户输入
            
        Returns:
            AI 回复
        """
        # 添加用户消息
        self.add_message("user", user_input)
        
        try:
            # 根据提供商调用 API
            if self.config.provider == LLMProvider.OPENAI:
                response = await self._call_openai()
            elif self.config.provider == LLMProvider.CUSTOM:
                response = await self._call_custom_api()
            else:
                raise NotImplementedError(f"不支持的提供商: {self.config.provider}")
            
            if response:
                # 添加助手消息
                self.add_message("assistant", response)
                
                # 调用回调
                if self.on_response:
                    self.on_response(response)
                
                return response
            
        except Exception as e:
            print(f"❌ LLM 错误: {e}")
            
        return None
    
    async def _call_openai(self) -> Optional[str]:
        """调用 OpenAI API"""
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in self.conversation_history
        ]
        
        try:
            # 使用异步方式调用
            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"❌ OpenAI API 错误: {e}")
            return None
    
    async def _call_custom_api(self) -> Optional[str]:
        """调用自定义 API"""
        if not self.config.api_base:
            raise ValueError("自定义 API 需要设置 api_base")
        
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in self.conversation_history
        ]
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.config.api_base}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        error = await response.text()
                        print(f"❌ API 错误 {response.status}: {error}")
                        return None
                        
            except Exception as e:
                print(f"❌ 自定义 API 错误: {e}")
                return None
    
    def add_message(self, role: str, content: str):
        """添加消息到历史"""
        self.conversation_history.append(Message(role, content))
        
        # 限制历史长度（保留系统提示 + 最近10轮对话）
        if len(self.conversation_history) > 21:  # 1 system + 10*2 messages
            # 保留系统提示
            system_msg = self.conversation_history[0] if self.conversation_history[0].role == "system" else None
            
            # 保留最近的消息
            recent_messages = self.conversation_history[-20:]
            
            # 重建历史
            self.conversation_history = []
            if system_msg:
                self.conversation_history.append(system_msg)
            self.conversation_history.extend(recent_messages)
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history.clear()
        
        # 重新添加系统提示
        if self.config.system_prompt:
            self.conversation_history.append(
                Message("system", self.config.system_prompt)
            )
    
    def set_system_prompt(self, prompt: str):
        """设置系统提示"""
        self.config.system_prompt = prompt
        
        # 更新历史中的系统提示
        if self.conversation_history and self.conversation_history[0].role == "system":
            self.conversation_history[0].content = prompt
        else:
            self.conversation_history.insert(0, Message("system", prompt))
    
    def get_conversation_summary(self) -> str:
        """获取对话摘要"""
        summary = []
        for msg in self.conversation_history:
            if msg.role != "system":
                role = "用户" if msg.role == "user" else "助手"
                summary.append(f"{role}: {msg.content}")
        
        return "\n".join(summary)
    
    def set_callback(self, callback: Callable[[str], None]):
        """设置响应回调"""
        self.on_response = callback


# 预定义的系统提示
SYSTEM_PROMPTS = {
    "客服": """你是一个专业的客服代表。请友好、耐心地解答客户问题。
对于你不确定的信息，请诚实告知并建议客户联系人工客服。
记住保持专业但不失亲切，回答要简洁明了。""",
    
    "销售": """你是一个友好的销售顾问。请热情地介绍产品特点和优势。
倾听客户需求，提供合适的解决方案。避免过度推销，建立信任关系。
回答要简短有力，突出重点。""",
    
    "技术支持": """你是一个技术支持专员。请用简单易懂的语言解释技术问题。
提供清晰的步骤指导，确保用户能够理解和操作。
如果问题复杂，建议安排技术人员上门或远程协助。""",
    
    "助理": """你是一个智能助理。请帮助用户完成各种任务，如查询信息、安排日程等。
保持高效和准确，用简洁的语言提供有用的信息。
对于超出能力范围的请求，请礼貌地说明。""",
    
    "通用": """你是一个友好的AI电话助手。请用简洁、自然的语言回答用户问题。
记住这是电话对话，回答要简短明了，避免长篇大论。
保持友好和专业，让对话流畅自然。"""
}