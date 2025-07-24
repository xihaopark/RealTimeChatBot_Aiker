# Cursor AI Assistant Rules for Aiker Project

## CRITICAL: Protected Modules

The following modules are ABSOLUTELY PROTECTED and must NEVER be modified:

### Core Communication Layer
- `main.py:EnhancedSIPClient` - SIP signaling protocol
- `main.py:RTPHandler` - RTP audio streaming
- `main.py:G711Codec` - G.711 audio codec
- `main.py:SDPParser` - SDP protocol parser

### Protected Constants (from config/protocol_constants.yaml)
- SAMPLE_RATE: 8000 Hz
- FRAME_SIZE: 160 bytes
- SIP_PORT: 5060
- RTP_PORT_RANGE: [10000, 10500]

## Development Guidelines

### 1. Local Engine Development
When implementing local engines in `src/local_engines/`:
- MUST inherit from `BaseLocalEngine`
- MUST maintain the original audio format (μ-law, 8kHz)
- MUST implement all abstract methods
- SHOULD optimize for <500ms latency (STT), <300ms (TTS)

### 2. Adapter Pattern
When creating adapters in `src/adapters/`:
- MUST inherit from `BaseAdapter`
- MUST provide fallback to API mode
- MUST maintain interface compatibility
- SHOULD handle errors gracefully

### 3. Code Generation Templates
Use these templates for consistency:
```python
# Local Engine Template
class Local{Feature}Engine(BaseLocalEngine):
    def __init__(self, model_path: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(model_path, config)
        # Implementation

# Adapter Template  
class {Feature}Adapter(BaseAdapter):
    def __init__(self, use_local: bool = True, config: Optional[Dict[str, Any]] = None):
        super().__init__(use_local, config)
        # Implementation
```

## Pre-modification Checklist
Before ANY modification:
- [ ] Does it touch protected modules?
- [ ] Does it change audio format/parameters?
- [ ] Is there an adapter layer?
- [ ] Are there tests?
- [ ] Has protection_checker.py passed? 