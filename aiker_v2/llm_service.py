#!/usr/bin/env python3
"""
高性能LLM服务 - 基于Llama.cpp Server
替换Transformers，实现高并发对话生成
"""

import requests
import json
import logging
import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ConversationTurn:
    """对话轮次"""
    user: str
    assistant: str
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class LlamaCppLLMService:
    """Llama.cpp LLM服务类"""
    
    def __init__(self, 
                 server_url: str = "http://127.0.0.1:8080",
                 timeout: int = 30,
                 max_tokens: int = 150,
                 temperature: float = 0.7,
                 system_prompt: str = None):
        """
        初始化Llama.cpp LLM服务
        
        Args:
            server_url: Llama.cpp服务器地址
            timeout: 请求超时时间
            max_tokens: 最大生成token数
            temperature: 生成温度
            system_prompt: 系统提示词
        """
        self.server_url = server_url.rstrip('/')
        self.completion_url = f"{self.server_url}/completion"
        self.health_url = f"{self.server_url}/health"
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # 默认系统提示词
        self.system_prompt = system_prompt or """你是OneSuite的AI客服助手。请遵循以下规则：
1. 用中文回答，语气友好专业
2. 回答要简洁明了，不超过50字
3. 专注于解决客户问题
4. 如遇不清楚的问题，礼貌地询问更多信息"""
        
        # 会话管理
        self.conversations: Dict[str, List[ConversationTurn]] = {}
        self.lock = threading.RLock()
        
        # 检查服务可用性
        self._check_health()
        
        logger.info("LlamaCppLLMService initialized")
    
    def _check_health(self) -> bool:
        """检查Llama.cpp服务器健康状态"""
        try:
            response = requests.get(self.health_url, timeout=5)
            if response.status_code == 200:
                logger.info("Llama.cpp server is healthy")
                return True
            else:
                logger.warning(f"Llama.cpp server health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.warning(f"Llama.cpp server not available: {e}")
            return False
    
    def _format_conversation(self, history: List[ConversationTurn], user_input: str) -> str:
        """格式化对话历史为prompt"""
        prompt_parts = [f"System: {self.system_prompt}"]
        
        # 添加历史对话（最近5轮）
        recent_history = history[-5:] if len(history) > 5 else history
        for turn in recent_history:
            prompt_parts.append(f"User: {turn.user}")
            prompt_parts.append(f"Assistant: {turn.assistant}")
        
        # 添加当前用户输入
        prompt_parts.append(f"User: {user_input}")
        prompt_parts.append("Assistant:")
        
        return "\n".join(prompt_parts)
    
    def generate_response(self, 
                         user_input: str, 
                         conversation_id: str = "default",
                         max_history: int = 10) -> str:
        """
        生成AI回复
        
        Args:
            user_input: 用户输入
            conversation_id: 会话ID
            max_history: 保留的最大历史轮数
            
        Returns:
            AI生成的回复文本
        """
        if not user_input.strip():
            return "请问有什么可以帮助您的吗？"
        
        try:
            with self.lock:
                # 获取或创建会话历史
                if conversation_id not in self.conversations:
                    self.conversations[conversation_id] = []
                
                history = self.conversations[conversation_id]
                
                # 格式化prompt
                prompt = self._format_conversation(history, user_input)
                
                # 构建请求数据
                request_data = {
                    "prompt": prompt,
                    "n_predict": self.max_tokens,
                    "temperature": self.temperature,
                    "stop": ["User:", "\\n\\n", "System:"],
                    "stream": False,
                    "repeat_penalty": 1.1,
                    "top_k": 40,
                    "top_p": 0.9
                }
                
                # 发送请求
                start_time = time.time()
                response = requests.post(
                    self.completion_url,
                    headers={"Content-Type": "application/json"},
                    json=request_data,
                    timeout=self.timeout
                )
                
                response.raise_for_status()
                
                # 解析响应
                result = response.json()
                ai_response = result.get('content', '').strip()
                
                # 清理响应文本
                ai_response = self._clean_response(ai_response)
                
                if not ai_response:
                    ai_response = "抱歉，我现在遇到了一些技术问题，请稍后再试。"
                
                # 保存到会话历史
                turn = ConversationTurn(user=user_input, assistant=ai_response)
                history.append(turn)
                
                # 限制历史长度
                if len(history) > max_history:
                    self.conversations[conversation_id] = history[-max_history:]
                
                elapsed = time.time() - start_time
                logger.debug(f"LLM response generated in {elapsed:.3f}s")
                
                return ai_response
                
        except requests.exceptions.Timeout:
            logger.error("LLM request timeout")
            return "抱歉，处理时间过长，请重新提问。"
        except requests.exceptions.RequestException as e:
            logger.error(f"LLM request error: {e}")
            return "对不起，AI服务暂时不可用，请稍后再试。"
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return "抱歉，我现在遇到了一些问题。"
    
    def _clean_response(self, response: str) -> str:
        """清理AI响应文本"""
        # 移除常见的停止标记
        for stop in ["User:", "System:", "Assistant:"]:
            if stop in response:
                response = response.split(stop)[0]
        
        # 移除多余的换行和空格
        response = response.strip()
        
        # 移除重复的句子
        sentences = response.split('。')
        if len(sentences) > 1:
            unique_sentences = []
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence and sentence not in unique_sentences:
                    unique_sentences.append(sentence)
            response = '。'.join(unique_sentences)
            if response and not response.endswith('。'):
                response += '。'
        
        return response
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """获取会话历史"""
        with self.lock:
            history = self.conversations.get(conversation_id, [])
            return [
                {
                    "user": turn.user,
                    "assistant": turn.assistant,
                    "timestamp": turn.timestamp
                }
                for turn in history
            ]
    
    def clear_conversation(self, conversation_id: str):
        """清除会话历史"""
        with self.lock:
            if conversation_id in self.conversations:
                del self.conversations[conversation_id]
                logger.info(f"Cleared conversation: {conversation_id}")
    
    def is_available(self) -> bool:
        """检查LLM服务是否可用"""
        return self._check_health()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        with self.lock:
            return {
                "active_conversations": len(self.conversations),
                "total_turns": sum(len(history) for history in self.conversations.values()),
                "server_url": self.server_url,
                "is_available": self.is_available()
            }


# 便捷函数
def generate_response(user_input: str, conversation_id: str = "default") -> str:
    """
    快速生成回复的便捷函数
    
    Args:
        user_input: 用户输入
        conversation_id: 会话ID
        
    Returns:
        AI生成的回复
    """
    llm = LlamaCppLLMService()
    return llm.generate_response(user_input, conversation_id)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    llm = LlamaCppLLMService()
    
    if llm.is_available():
        print("Testing LLM service...")
        
        # 测试对话
        test_inputs = [
            "你好，我想了解一下你们的服务",
            "你们的营业时间是什么时候？",
            "如何联系技术支持？"
        ]
        
        for i, test_input in enumerate(test_inputs):
            print(f"\n测试 {i+1}: {test_input}")
            response = llm.generate_response(test_input, "test_conversation")
            print(f"回复: {response}")
        
        # 显示统计信息
        print(f"\n统计信息: {llm.get_stats()}")
    else:
        print("LLM service not available. Please start llama.cpp server first.")