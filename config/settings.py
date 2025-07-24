"""
系统配置管理
加载环境变量并提供配置接口
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class VTXConfig:
    """VTX服务器配置"""
    def __init__(self):
        self.server = os.getenv('VTX_SERVER', 'core1-us-lax.myippbx.com')
        self.port = int(os.getenv('VTX_PORT', '5060'))
        self.domain = os.getenv('VTX_DOMAIN', 'aiker.myippbx.com')
        self.did_number = os.getenv('VTX_DID', '14088779998')

class ExtensionConfig:
    """分机配置"""
    def __init__(self, username: str, password: str, description: str = "VTX Extension"):
        self.username = username
        self.password = password
        self.description = description
    
    @classmethod
    def from_env(cls, extension_id: str) -> 'ExtensionConfig':
        prefix = f'EXTENSION_{extension_id}_'
        return cls(
            username=os.getenv(f'{prefix}USERNAME', ''),
            password=os.getenv(f'{prefix}PASSWORD', ''),
            description=os.getenv(f'{prefix}DESCRIPTION', f'Extension {extension_id}')
        )

class NetworkConfig:
    """网络配置"""
    def __init__(self):
        self.sip_port = int(os.getenv('SIP_PORT', '5060'))
        self.rtp_port_start = int(os.getenv('RTP_PORT_START', '10000'))
        self.rtp_port_end = int(os.getenv('RTP_PORT_END', '10500'))
        self.use_stun = os.getenv('USE_STUN', 'true').lower() == 'true'
        
        # 解析STUN服务器
        stun_str = os.getenv('STUN_SERVERS', 'stun.l.google.com:19302')
        self.stun_servers = []
        for server in stun_str.split(','):
            if ':' in server:
                host, port = server.strip().split(':')
                self.stun_servers.append((host, int(port)))
            else:
                self.stun_servers.append((server.strip(), 3478))

class AIConfig:
    """AI配置"""
    def __init__(self):
        self.stt_provider = os.getenv('STT_PROVIDER', 'whisper')
        self.whisper_model = os.getenv('WHISPER_MODEL', 'base')
        self.whisper_language = os.getenv('WHISPER_LANGUAGE', 'en')
        self.tts_provider = os.getenv('TTS_PROVIDER', 'edge-tts')
        self.tts_voice = os.getenv('TTS_VOICE', 'en-US-AriaNeural')
        self.tts_rate = float(os.getenv('TTS_RATE', '1.0'))
        self.llm_provider = os.getenv('LLM_PROVIDER', 'openai')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.llm_model = os.getenv('LLM_MODEL', 'gpt-3.5-turbo')
        self.llm_temperature = float(os.getenv('LLM_TEMPERATURE', '0.7'))

class SystemConfig:
    """系统配置"""
    def __init__(self):
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_file = Path(os.getenv('LOG_FILE', 'logs/vtx_system.log'))
        self.recording_enabled = os.getenv('RECORDING_ENABLED', 'true').lower() == 'true'
        self.recording_path = Path(os.getenv('RECORDING_PATH', 'recordings/'))
        self.max_concurrent_calls = int(os.getenv('MAX_CONCURRENT_CALLS', '10'))
        self.call_timeout_seconds = int(os.getenv('CALL_TIMEOUT_SECONDS', '300'))
        self.vad_threshold = float(os.getenv('VAD_THRESHOLD', '0.5'))
        self.audio_buffer_size = int(os.getenv('AUDIO_BUFFER_SIZE', '8000'))
        self.monitoring_enabled = os.getenv('MONITORING_ENABLED', 'true').lower() == 'true'
        self.prometheus_port = int(os.getenv('PROMETHEUS_PORT', '9090'))
        self.health_check_interval = int(os.getenv('HEALTH_CHECK_INTERVAL', '30'))
        
        # 确保目录存在
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        if self.recording_enabled:
            self.recording_path.mkdir(parents=True, exist_ok=True)

class Settings:
    """统一配置管理器"""
    def __init__(self):
        self.vtx = VTXConfig()
        self.network = NetworkConfig()
        self.ai = AIConfig()
        self.system = SystemConfig()
        self.extensions: Dict[str, ExtensionConfig] = {}
        self._load_extensions()
    
    def _load_extensions(self):
        """加载所有分机配置"""
        for key in os.environ:
            if key.startswith('EXTENSION_') and key.endswith('_USERNAME'):
                ext_id = key.split('_')[1]
                self.extensions[ext_id] = ExtensionConfig.from_env(ext_id)
        
        if not self.extensions:
            raise ValueError("没有找到任何分机配置！请检查环境变量。")
    
    def get_extension(self, ext_id: str) -> Optional[ExtensionConfig]:
        return self.extensions.get(ext_id)
    
    def list_extensions(self) -> List[str]:
        return list(self.extensions.keys())

# 全局配置实例
settings = Settings()