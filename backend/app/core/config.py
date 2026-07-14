"""Application configuration using Pydantic Settings"""

from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Application
    APP_NAME: str = "Perfume Chemistry API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./perfume_chem.db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False

    # Redis Cache
    REDIS_URL: Optional[str] = None
    CACHE_TTL: int = 3600  # 1 hour default

    # AI Services
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_MAX_TOKENS: int = 2000
    OPENAI_TEMPERATURE: float = 0.7
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = None

    # Cerebras AI (model-agnostic - works with any Cerebras model)
    CEREBRAS_API_KEY: str = ""
    CEREBRAS_BASE_URL: str = "https://api.cerebras.ai/v1"
    CEREBRAS_MODEL: str = "llama3.1-8b"  # Can be any: llama3.1-8b, llama3.1-70b, qwen-3-235b-a22b-instruct-2507, etc.

    # Baseten AI
    BASETEN_API_KEY: str = ""
    BASETEN_MODEL_ID: str = ""  # Your deployed model ID

    # DeepSeek AI (OpenAI-compatible API)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-v4-pro"

    # Hugging Face AI
    HF_API_KEY: str = ""  # Hugging Face token for Inference API
    HF_MODEL: str = "NousResearch/Hermes-3-Llama-3.1-8B"  # Model ID for Inference API
    HF_BASE_URL: str = "https://api-inference.huggingface.co/v1/"  # OpenAI-compatible endpoint
    HF_LOCAL_MODEL_PATH: Optional[str] = None  # Optional local model path for Transformers

    # Ollama AI (local or remote)
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_MODEL: str = "hf.co/DavidAU/DeepSeek-MOE-4X8B-R1-Distill-Llama-3.1-Deep-Thinker-Uncensored-24B-GGUF"  # Newly installed model

    # Llama.cpp AI (local GGUF models)
    LLAMA_CPP_MODEL_PATH: Optional[str] = None
    LLAMA_CPP_N_CTX: int = 2048
    LLAMA_CPP_N_GPU_LAYERS: int = 0
    LLAMA_CPP_SEED: int = -1
    LLAMA_CPP_VERBOSE: bool = False

    # Rate Limiting
    RATE_LIMIT_CONFIG_PATH: Optional[str] = None  # Path to rate_limits.yaml

    # AI Provider Selection
    AI_PROVIDER: str = "deepseek"  # Options: "openai", "cerebras", "baseten", "huggingface", "ollama", "deepseek", "llamacpp"

    # Security
    SECRET_KEY: str = "CHANGE_THIS_TO_A_SECURE_RANDOM_STRING"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # Perfumery Settings
    DEFAULT_DILUTION_SOLVENT: str = "ethanol"
    DEFAULT_DROP_SIZE_ML: float = 0.05
    IFRA_COMPLIANCE_CHECK: bool = True
    ENABLE_AI_SUGGESTIONS: bool = True

    # OpenTelemetry Tracing
    OTEL_ENABLED: bool = True
    OTEL_SERVICE_NAME: str = "perfume-chem-api"
    OTEL_OTLP_ENDPOINT: str = "http://localhost:4318"  # HTTP OTLP endpoint
    OTEL_TRACES_SAMPLER: str = "parentbased_traceidratio"
    OTEL_TRACES_SAMPLER_ARG: float = 1.0  # 1.0 = 100% sampling

    # File Storage
    DATA_DIR: str = "./data"
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_flag(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production", "false", "0", "no", "off"}:
                return False
            if normalized in {"dev", "development", "debug", "true", "1", "yes", "on"}:
                return True
        return value

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
