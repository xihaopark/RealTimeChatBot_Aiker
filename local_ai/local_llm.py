import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import json
import logging
from typing import List, Dict, Optional
import time


class LocalLLM:
    """本地大语言模型服务，支持Mistral、Qwen、Llama等模型"""
    
    def __init__(self,
                 model_name: str = "Qwen/Qwen2.5-7B-Instruct",
                 device: str = "cuda",
                 max_length: int = 2048,
                 temperature: float = 0.7,
                 use_4bit: bool = True):
        """
        初始化本地LLM
        Args:
            model_name: 模型名称
            device: 计算设备
            max_length: 最大生成长度
            temperature: 生成温度
            use_4bit: 是否使用4bit量化
        """
        self.model_name = model_name
        self.device = device
        self.max_length = max_length
        self.temperature = temperature
        self.use_4bit = use_4bit
        
        # 对话历史
        self.conversation_history = []
        
        # 业务知识库（简化版）
        self.business_knowledge = self._load_business_knowledge()
        
        # 初始化模型和分词器
        self._init_model()
        
        logging.info(f"LocalLLM initialized: {model_name} on {device}")
    
    def _init_model(self):
        """初始化模型和分词器"""
        try:
            # 量化配置
            quantization_config = None
            if self.use_4bit and self.device == "cuda":
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
            
            # 加载分词器
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                padding_side="left"
            )
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # 加载模型
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                quantization_config=quantization_config,
                device_map="auto" if self.device == "cuda" else None,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            if not quantization_config:
                self.model = self.model.to(self.device)
            
            self.model.eval()
            
        except Exception as e:
            logging.error(f"Model initialization error: {e}")
            raise
    
    def _load_business_knowledge(self) -> Dict:
        """加载业务知识库"""
        try:
            with open('data/onesuite-business-data.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"Failed to load business knowledge: {e}")
            return {
                "company": {
                    "name": "OneSuite Business",
                    "description": "虚拟电话系统服务提供商"
                },
                "services": ["虚拟PBX系统", "商务电话线路", "语音信箱"],
                "pricing": {"model": "按需付费"}
            }
    
    def _is_business_query(self, text: str) -> bool:
        """判断是否为业务相关查询"""
        business_keywords = [
            "价格", "费用", "收费", "服务", "产品", "功能", "如何", "怎么",
            "电话", "通话", "系统", "onesuite", "客服", "技术支持",
            "购买", "咨询", "了解", "介绍"
        ]
        return any(keyword in text.lower() for keyword in business_keywords)
    
    def _create_system_prompt(self, is_business: bool = False) -> str:
        """创建系统提示"""
        if is_business:
            company = self.business_knowledge.get('company', {})
            services = self.business_knowledge.get('services', {})
            pricing = self.business_knowledge.get('pricing', {})
            
            return f"""你是OneSuite Business的AI客服助手。请根据以下信息回答客户问题：

公司信息：
- 公司名称：{company.get('name', 'OneSuite Business')}
- 成立时间：{company.get('established', '1999')}
- 公司定位：{company.get('type', '虚拟电话系统服务提供商')}
- 使命：{company.get('mission', '以最低的价格为用户提供最大的电信便利')}

核心服务：
- {services.get('core_service', {}).get('name', '虚拟PBX系统')}
- 主要功能：云端电话系统、商务电话线路、虚拟接待员等

定价模式：{pricing.get('model', '按需付费')}

请用友好、专业的语气回答客户问题，回答要简洁明了，不超过80字。重点介绍我们的虚拟PBX系统和按需付费的优势。"""
        else:
            return """你是一个友好的AI助手。请用自然、简洁的方式回答问题，回答不超过50字。保持对话轻松愉快。"""
    
    def _format_conversation(self, user_input: str, is_business: bool = False) -> str:
        """格式化对话历史"""
        system_prompt = self._create_system_prompt(is_business)
        
        # 构建对话格式（适配不同模型）
        if "qwen" in self.model_name.lower():
            # Qwen格式
            messages = [{"role": "system", "content": system_prompt}]
            
            # 添加历史对话（保留最近5轮）
            for entry in self.conversation_history[-5:]:
                messages.append({"role": "user", "content": entry["user"]})
                messages.append({"role": "assistant", "content": entry["assistant"]})
            
            messages.append({"role": "user", "content": user_input})
            
            # 使用tokenizer的chat template
            if hasattr(self.tokenizer, 'apply_chat_template'):
                return self.tokenizer.apply_chat_template(
                    messages, 
                    tokenize=False, 
                    add_generation_prompt=True
                )
        
        # 通用格式
        conversation = f"System: {system_prompt}\n\n"
        
        for entry in self.conversation_history[-3:]:
            conversation += f"Human: {entry['user']}\nAssistant: {entry['assistant']}\n\n"
        
        conversation += f"Human: {user_input}\nAssistant:"
        
        return conversation
    
    def generate_response(self, user_input: str) -> str:
        """生成回复"""
        start_time = time.time()
        
        try:
            # 判断是否为业务查询
            is_business = self._is_business_query(user_input)
            
            # 格式化输入
            formatted_input = self._format_conversation(user_input, is_business)
            
            # 编码输入
            inputs = self.tokenizer(
                formatted_input,
                return_tensors="pt",
                truncation=True,
                max_length=self.max_length - 150  # 为回复留出空间
            ).to(self.device)
            
            # 生成回复
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=150,
                    temperature=self.temperature,
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    repetition_penalty=1.1
                    # 移除不兼容的参数 length_penalty 和 early_stopping
                )
            
            # 解码回复
            response = self.tokenizer.decode(
                outputs[0][inputs.input_ids.shape[1]:],
                skip_special_tokens=True
            ).strip()
            
            # 清理回复
            response = self._clean_response(response)
            
            # 更新对话历史
            self.conversation_history.append({
                "user": user_input,
                "assistant": response,
                "timestamp": time.time(),
                "is_business": is_business
            })
            
            # 保持历史长度合理
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
            
            generation_time = time.time() - start_time
            logging.info(f"LLM response generated in {generation_time:.2f}s: {len(response)} chars")
            
            return response
            
        except Exception as e:
            logging.error(f"Response generation error: {e}")
            return "抱歉，我遇到了一些技术问题。请稍后再试。"
    
    def _clean_response(self, response: str) -> str:
        """清理生成的回复"""
        # 移除多余的换行和空格
        response = response.strip()
        
        # 移除重复的句子
        sentences = response.split('。')
        unique_sentences = []
        for sentence in sentences:
            if sentence.strip() and sentence.strip() not in unique_sentences:
                unique_sentences.append(sentence.strip())
        
        if unique_sentences:
            response = '。'.join(unique_sentences)
            if not response.endswith('。') and not response.endswith('?') and not response.endswith('!'):
                response += '。'
        
        # 限制长度
        if len(response) > 200:
            response = response[:197] + '...'
        
        return response
    
    def clear_history(self):
        """清除对话历史"""
        self.conversation_history = []
        logging.info("Conversation history cleared")
    
    def get_model_info(self) -> Dict:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "max_length": self.max_length,
            "temperature": self.temperature,
            "use_4bit": self.use_4bit,
            "conversation_turns": len(self.conversation_history)
        }
    
    def test_generation(self, text: str = "你好") -> str:
        """测试生成功能"""
        print(f"Testing LLM with input: {text}")
        response = self.generate_response(text)
        print(f"Generated response: {response}")
        return response