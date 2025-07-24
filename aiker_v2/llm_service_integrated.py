#!/usr/bin/env python3
"""
一体化LLM服务 - 基于Transformers (适配Vast.ai容器环境)
直接加载模型到进程内，无需外部服务
"""

import json
import logging
import time
import threading
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    import gc
except ImportError as e:
    logging.error(f"Missing required packages: {e}")
    logging.error("Please install: pip install torch transformers bitsandbytes")
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

class TransformersLLMService:
    """Transformers一体化LLM服务类"""
    
    def __init__(self, 
                 model_name: str = "Qwen/Qwen2.5-7B-Instruct",
                 device: str = "auto",
                 max_tokens: int = 150,
                 temperature: float = 0.7,
                 system_prompt: str = None,
                 use_4bit: bool = True):
        """
        初始化Transformers LLM服务
        
        Args:
            model_name: 模型名称或路径
            device: 设备 (auto, cuda, cpu)
            max_tokens: 最大生成token数
            temperature: 生成温度
            system_prompt: 系统提示词
            use_4bit: 是否使用4bit量化
        """
        self.model_name = model_name
        self.device = device
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.use_4bit = use_4bit
        
        # 模型和分词器
        self.model = None
        self.tokenizer = None
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
        
        logger.info("TransformersLLMService initialized")
    
    def _load_model(self):
        """加载Transformers模型"""
        try:
            logger.info(f"Loading model: {self.model_name}")
            
            # 设置设备
            if self.device == "auto":
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            
            logger.info(f"Using device: {self.device}")
            
            # 配置量化 (如果使用GPU)
            quantization_config = None
            if self.use_4bit and self.device == "cuda":
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                )
                logger.info("Using 4-bit quantization")
            
            # 加载分词器
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                padding_side="left"
            )
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # 加载模型
            model_kwargs = {
                "trust_remote_code": True,
                "torch_dtype": torch.float16 if self.device == "cuda" else torch.float32,
            }
            
            if quantization_config:
                model_kwargs["quantization_config"] = quantization_config
                model_kwargs["device_map"] = "auto"
            else:
                model_kwargs["device_map"] = self.device
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                **model_kwargs
            )
            
            self.model.eval()
            self.model_loaded = True
            
            # 显存清理
            if self.device == "cuda":
                torch.cuda.empty_cache()
            gc.collect()
            
            logger.info("Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.model_loaded = False
            raise
    
    def _format_conversation(self, history: List[ConversationTurn], user_input: str) -> List[Dict[str, str]]:
        """格式化对话历史为messages格式"""
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # 添加历史对话（最近5轮）
        recent_history = history[-5:] if len(history) > 5 else history
        for turn in recent_history:
            messages.append({"role": "user", "content": turn.user})
            messages.append({"role": "assistant", "content": turn.assistant})
        
        # 添加当前用户输入
        messages.append({"role": "user", "content": user_input})
        
        return messages
    
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
                # 检查模型是否已加载
                if not self.model_loaded:
                    raise RuntimeError("Model not loaded")
                
                # 获取或创建会话历史
                if conversation_id not in self.conversations:
                    self.conversations[conversation_id] = []
                
                history = self.conversations[conversation_id]
                
                # 格式化对话
                messages = self._format_conversation(history, user_input)
                
                # 使用分词器应用聊天模板
                prompt = self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
                
                # 编码输入
                start_time = time.time()
                inputs = self.tokenizer.encode(
                    prompt,
                    return_tensors="pt",
                    truncation=True,
                    max_length=2048
                ).to(self.model.device)
                
                # 生成响应
                with torch.no_grad():
                    outputs = self.model.generate(
                        inputs,
                        max_new_tokens=self.max_tokens,
                        temperature=self.temperature,
                        do_sample=True,
                        top_p=0.9,
                        top_k=40,
                        repetition_penalty=1.1,
                        pad_token_id=self.tokenizer.pad_token_id,
                        eos_token_id=self.tokenizer.eos_token_id,
                    )
                
                # 解码生成的文本
                generated_tokens = outputs[0][inputs.shape[1]:]
                ai_response = self.tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
                
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
                
                # 清理GPU缓存
                if self.device == "cuda":
                    torch.cuda.empty_cache()
                
                return ai_response
                
        except torch.cuda.OutOfMemoryError:
            logger.error("GPU out of memory")
            if self.device == "cuda":
                torch.cuda.empty_cache()
            return "抱歉，处理能力不足，请稍后再试。"
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
        return self.model_loaded and self.model is not None and self.tokenizer is not None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        with self.lock:
            stats = {
                "active_conversations": len(self.conversations),
                "total_turns": sum(len(history) for history in self.conversations.values()),
                "model_name": self.model_name,
                "device": self.device,
                "model_loaded": self.model_loaded,
                "is_available": self.is_available()
            }
            
            # 添加GPU信息
            if self.device == "cuda" and torch.cuda.is_available():
                stats["gpu_memory_allocated"] = torch.cuda.memory_allocated() / 1024**3  # GB
                stats["gpu_memory_reserved"] = torch.cuda.memory_reserved() / 1024**3   # GB
            
            return stats
    
    def cleanup(self):
        """清理资源"""
        if self.model is not None:
            del self.model
            self.model = None
        
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        
        if self.device == "cuda":
            torch.cuda.empty_cache()
        
        gc.collect()
        self.model_loaded = False
        logger.info("Model resources cleaned up")


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
    llm = TransformersLLMService()
    return llm.generate_response(user_input, conversation_id)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    llm = TransformersLLMService()
    
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