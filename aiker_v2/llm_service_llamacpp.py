#!/usr/bin/env python3
"""
LLM服务 - 基于llama-cpp-python (适配Vast.ai容器环境)
在Python进程内直接调用llama.cpp，无需外部server
"""

import json
import logging
import time
import threading
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

try:
    from llama_cpp import Llama
    import torch
except ImportError as e:
    logging.error(f"Missing required packages: {e}")
    logging.error("Please install: pip install llama-cpp-python torch")
    raise

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

class LlamaCppService:
    """llama-cpp-python LLM服务类"""
    
    def __init__(self, 
                 model_path: str = None,
                 n_ctx: int = 2048,
                 n_batch: int = 512,
                 n_threads: int = None,
                 n_gpu_layers: int = -1,  # -1表示全部层放到GPU
                 max_tokens: int = 150,
                 temperature: float = 0.7,
                 system_prompt: str = None):
        """
        初始化llama.cpp LLM服务
        
        Args:
            model_path: GGUF模型文件路径
            n_ctx: 上下文长度
            n_batch: 批处理大小
            n_threads: CPU线程数
            n_gpu_layers: GPU层数(-1=全部)
            max_tokens: 最大生成token数
            temperature: 生成温度
            system_prompt: 系统提示词
        """
        self.model_path = model_path or self._get_default_model_path()
        self.n_ctx = n_ctx
        self.n_batch = n_batch
        self.n_threads = n_threads or os.cpu_count()
        self.n_gpu_layers = n_gpu_layers
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # 模型实例
        self.model: Optional[Llama] = None
        self.model_loaded = False
        
        # 默认系统提示词
        self.system_prompt = system_prompt or """你是OneSuite的AI客服助手。请遵循以下规则：
1. 用中文回答，语气友好专业
2. 回答要简洁明了，不超过50字
3. 专注于解决客户问题
4. 如遇不清楚的问题，礼貌地询问更多信息"""
        
        # 会话管理
        self.conversations: Dict[str, List[ConversationTurn]] = {}
        self.lock = threading.RLock()
        
        # 加载模型
        self._load_model()
        
        logger.info("LlamaCppService initialized")
    
    def _get_default_model_path(self) -> str:
        """获取默认模型路径"""
        # 尝试常见的模型位置
        possible_paths = [
            "/workspace/models/qwen2.5-7b-instruct-q4_k_m.gguf",
            "models/qwen2.5-7b-instruct-q4_k_m.gguf",
            "../models/qwen2.5-7b-instruct-q4_k_m.gguf",
            "services/llama.cpp/models/qwen2.5-7b-instruct-q4_k_m.gguf"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        logger.warning("No default model found, please specify model_path")
        return "models/llama-model.gguf"
    
    def _load_model(self):
        """加载llama.cpp模型"""
        try:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Model file not found: {self.model_path}")
            
            logger.info(f"Loading model: {self.model_path}")
            
            # 检查CUDA可用性
            use_gpu = torch.cuda.is_available() and self.n_gpu_layers != 0
            
            if use_gpu:
                logger.info(f"GPU detected, using {self.n_gpu_layers} layers on GPU")
            else:
                logger.info("Using CPU mode")
                self.n_gpu_layers = 0
            
            # 创建Llama实例
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_batch=self.n_batch,
                n_threads=self.n_threads,
                n_gpu_layers=self.n_gpu_layers,
                verbose=False,  # 减少输出
                seed=-1,  # 随机种子
                f16_kv=True,  # 使用f16键值缓存
                logits_all=False,
                vocab_only=False,
                use_mlock=False,  # 容器环境可能不支持
                embedding=False
            )
            
            self.model_loaded = True
            logger.info("Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.model_loaded = False
            raise
    
    def _format_prompt(self, history: List[ConversationTurn], user_input: str) -> str:
        """格式化对话历史为prompt"""
        # 使用ChatML格式（适用于Qwen等模型）
        prompt_parts = [f"<|im_start|>system\n{self.system_prompt}<|im_end|>"]
        
        # 添加历史对话（最近5轮）
        recent_history = history[-5:] if len(history) > 5 else history
        for turn in recent_history:
            prompt_parts.append(f"<|im_start|>user\n{turn.user}<|im_end|>")
            prompt_parts.append(f"<|im_start|>assistant\n{turn.assistant}<|im_end|>")
        
        # 添加当前用户输入
        prompt_parts.append(f"<|im_start|>user\n{user_input}<|im_end|>")
        prompt_parts.append("<|im_start|>assistant\n")
        
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
        
        if not self.model_loaded:
            return "抱歉，AI服务正在启动中，请稍后再试。"
        
        try:
            with self.lock:
                # 获取或创建会话历史
                if conversation_id not in self.conversations:
                    self.conversations[conversation_id] = []
                
                history = self.conversations[conversation_id]
                
                # 格式化prompt
                prompt = self._format_prompt(history, user_input)
                
                # 生成响应
                start_time = time.time()
                
                response = self.model(
                    prompt,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    top_p=0.9,
                    top_k=40,
                    repeat_penalty=1.1,
                    stop=["<|im_end|>", "<|im_start|>", "\n\n"],
                    echo=False
                )
                
                # 提取生成的文本
                ai_response = response['choices'][0]['text'].strip()
                
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
                
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return "抱歉，我现在遇到了一些问题。"
    
    def _clean_response(self, response: str) -> str:
        """清理AI响应文本"""
        # 移除可能的角色标记
        for marker in ["<|im_end|>", "<|im_start|>", "assistant:", "user:", "system:"]:
            response = response.replace(marker, "")
        
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
        return self.model_loaded and self.model is not None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        with self.lock:
            stats = {
                "active_conversations": len(self.conversations),
                "total_turns": sum(len(history) for history in self.conversations.values()),
                "model_path": self.model_path,
                "n_ctx": self.n_ctx,
                "n_gpu_layers": self.n_gpu_layers,
                "model_loaded": self.model_loaded,
                "is_available": self.is_available()
            }
            
            # 添加模型信息
            if self.model:
                stats["model_n_ctx"] = self.model.n_ctx()
                stats["model_n_vocab"] = self.model.n_vocab()
                
            return stats
    
    def reload_model(self, new_model_path: str = None):
        """重新加载模型"""
        if new_model_path:
            self.model_path = new_model_path
        
        # 清理旧模型
        if self.model:
            del self.model
            self.model = None
        
        # 加载新模型
        self._load_model()


# 便捷函数
def create_llm_service(model_path: str = None, **kwargs) -> LlamaCppService:
    """
    创建LLM服务的便捷函数
    
    Args:
        model_path: 模型文件路径
        **kwargs: 其他参数
        
    Returns:
        LlamaCppService实例
    """
    return LlamaCppService(model_path=model_path, **kwargs)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    llm = LlamaCppService()
    
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
        print("LLM service not available. Please check model installation.")