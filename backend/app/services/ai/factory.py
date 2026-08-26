"""
AI Service Factory with Automatic Provider Detection

Automatically routes to the appropriate AI provider based on model name.
"""

import re
from typing import Any, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.ai.base import BaseAIService
from app.services.ai.baseten_service import BasetenService
from app.services.ai.cerebras_service import CerebrasService
from app.services.ai.deepseek_service import DeepSeekService
from app.services.ai.huggingface_service import HuggingFaceService
from app.services.ai.llama_cpp_service import LlamaCppService
from app.services.ai.ollama_service import OllamaService
from app.services.ai.openai_service import OpenAIService

logger = get_logger(__name__)


class AIModelDetector:
    """Detect AI provider based on model name"""

    # Cerebras model patterns
    CEREBRAS_PATTERNS = [
        r'^llama3\.1-[0-9]+b$',  # llama3.1-8b, llama3.1-70b
        r'^qwen-[0-9]+b',  # qwen-3-235b-a22b-instruct-2507
        r'^cerebras-',  # cerebras-*
        r'^llama-',  # llama-* (other llama models)
        r'^mistral-',  # mistral-*
        r'^mixtral-',  # mixtral-*
    ]

    # Baseten model patterns
    BASETEN_PATTERNS = [
        r'kimi',  # Kimi K2 models
        r'k2',  # K2 models
        r'baseten-',  # baseten-*
        r'^bt-',  # bt-* (Baseten shorthand)
    ]

    # OpenAI model patterns
    OPENAI_PATTERNS = [
        r'^gpt-',  # gpt-4, gpt-3.5-turbo
        r'^o1-',  # o1-*
        r'^text-',  # text-* (older models)
        r'^davinci-',  # davinci-*
        r'^curie-',  # curie-*
        r'^babbage-',  # babbage-*
        r'^ada-',  # ada-*
    ]

    # DeepSeek model patterns
    DEEPSEEK_PATTERNS = [
        r'^deepseek-',  # deepseek-v4-pro, deepseek-chat, etc.
        r'^deepseek/deepseek-',  # deepseek/deepseek-v4-pro format
    ]

    # Hugging Face model patterns (models with /, common prefixes)
    HUGGINGFACE_PATTERNS = [
        r'^ehartford/',  # dolphin models
        r'^microsoft/',  # phi models
        r'^google/',  # gemma, flan
        r'^mistralai/',  # mistral models
        r'^meta-llama/',  # meta llama
        r'^bigscience/',  # bloom
        r'^tiiuae/',  # falcon
        r'^Qwen/',  # qwen
        r'^NousResearch/',  # hermes
        r'^TheBloke/',  # quantized models
        r'^allenai/',  # scibert
        r'^/',  # Any slash indicates Hugging Face model ID
        r'^dolphin-mixtral$',  # Our model registry ID
        r'^scibert$',  # Our model registry ID
        r'^llama3_8b_chat_uncensored$',  # Local Llama 3 8B uncensored
        r'^llama3[-_]8b[-_]',  # Llama 3 8B variants
    ]

    # Ollama model patterns (local/remote Ollama models)
    OLLAMA_PATTERNS = [
        r'^hf\.co/',  # Hugging Face models pulled via Ollama
        r':Q[0-9]_[A-Z]_[A-Z]$',  # Quantization suffix
        r':latest$',  # Common tag
        r':[0-9]+b$',  # e.g., :7b, :13b
        r'^ollama-',  # ollama-* custom naming
        r'^llama3\.2:',  # llama3.2:3b
        r'^llama3\.2-3b$',  # Our model registry ID
    ]

    # Llama.cpp model patterns (local GGUF models)
    LLAMA_CPP_PATTERNS = [
        r'\.gguf$',
        r'^OpenAi-GPT-oss',
        r'^OpenAI-20B',
        r'^llama_cpp_',
        r'^davidau/deepseek-moe-4x8b-r1-distill-llama-3.1-deep-thinker-uncensored-24b-gguf',
        r'^openai-gpt-oss-20b-abliterated-uncensored-neo-imatrix-gguf',
    ]

    @classmethod
    def detect_provider(cls, model_name: str) -> str:
        """
        Detect AI provider based on model name

        Args:
            model_name: The model name or ID

        Returns:
            Provider string: "cerebras", "baseten", "openai",
            "huggingface", "ollama", "llamacpp", or "default"
        """
        model_lower = model_name.lower()

        # Check Llama.cpp patterns first (most specific)
        for pattern in cls.LLAMA_CPP_PATTERNS:
            if re.search(pattern, model_lower):
                logger.debug(f"Detected Llama.cpp model: {model_name}")
                return "llamacpp"

        # Check Cerebras patterns
        for pattern in cls.CEREBRAS_PATTERNS:
            if re.search(pattern, model_lower):
                logger.debug(f"Detected Cerebras model: {model_name}")
                return "cerebras"

        # Check Baseten patterns
        for pattern in cls.BASETEN_PATTERNS:
            if re.search(pattern, model_lower):
                logger.debug(f"Detected Baseten model: {model_name}")
                return "baseten"

        # Check OpenAI patterns
        for pattern in cls.OPENAI_PATTERNS:
            if re.search(pattern, model_lower):
                logger.debug(f"Detected OpenAI model: {model_name}")
                return "openai"

        # Check DeepSeek patterns
        for pattern in cls.DEEPSEEK_PATTERNS:
            if re.search(pattern, model_lower):
                logger.debug(f"Detected DeepSeek model: {model_name}")
                return "deepseek"

        # Check Hugging Face patterns
        for pattern in cls.HUGGINGFACE_PATTERNS:
            if re.search(pattern, model_lower):
                logger.debug(f"Detected Hugging Face model: {model_name}")
                return "huggingface"

        # Check Ollama patterns
        for pattern in cls.OLLAMA_PATTERNS:
            if re.search(pattern, model_lower):
                logger.debug(f"Detected Ollama model: {model_name}")
                return "ollama"

        raise ValueError(f"Unknown AI model provider for '{model_name}'")

    @classmethod
    def get_supported_models(cls) -> dict:
        """Get list of supported models by provider"""
        return {
            "cerebras": [
                "llama3.1-8b (default)",
                "llama3.1-70b",
                "qwen-3-235b-a22b-instruct-2507",
                "cerebras-llama3.1-8b",
                "Any Cerebras-supported model"
            ],
            "baseten": [
                "kimi-k2-thinking",
                "Any Baseten-hosted model"
            ],
            "openai": [
                "gpt-4",
                "gpt-3.5-turbo",
                "o1-preview",
                "o1-mini"
            ],
            "deepseek": [
                "deepseek-v4-pro (default)",
                "deepseek-chat",
                "Any DeepSeek model via OpenAI-compatible API"
            ],
            "huggingface": [
                "ehartford/dolphin-2.5-mixtral-8x7b (default)",
                "dolphin-mixtral",
                "scibert",
                "Any Hugging Face model ID",
                "Local Transformers model (via HF_LOCAL_MODEL_PATH)"
            ],
            "ollama": [
                "hf.co/PsiPi/ehartford_dolphin-2.5-mixtral-8x7b-GGUF:Q3_K_L (default)",
                "llama3.2-3b",
                "llama3.2:3b",
                "Any Ollama model (local/remote)",
                "Quantized GGUF models",
                "ollama-* custom models"
            ],
            "llamacpp": [
                "DavidAU/DeepSeek-MOE-4X8B-R1-Distill-Llama-3.1-Deep-Thinker-Uncensored-24B-GGUF (default)",
                "OpenAi-GPT-oss-20b-abliterated-uncensored-NEO-Imatrix-gguf",
                "Any GGUF model file",
                "Local GGUF model via llama-cpp-python"
            ]
        }


def create_ai_service(
    model: Optional[str] = None,
    cache: Optional[Any] = None,
    verbose: bool = False,
    force_provider: Optional[str] = None
) -> BaseAIService:
    """
    Create AI service with automatic provider detection

    Args:
        model: Model name (e.g., "llama3.1-8b", "gpt-4", "kimi-k2-thinking")
               If None, uses default from settings
        cache: Optional cache instance
        verbose: Enable verbose logging
        force_provider: Force specific provider (overrides auto-detection)

    Returns:
        Appropriate AI service instance
    """
    settings = get_settings()

    # Determine provider
    if force_provider:
        provider = force_provider.lower()
        logger.info(f"Forcing provider: {provider}")
    else:
        # Use model for detection, fall back to AI_PROVIDER from settings
        if model:
            provider = AIModelDetector.detect_provider(model)
        else:
            provider = settings.AI_PROVIDER.lower()
            logger.info(f"Using provider from settings: {provider}")

    # Create appropriate service
    if provider == "cerebras":
        # For Cerebras, pass the model parameter if provided
        service_model = model or settings.CEREBRAS_MODEL
        logger.info(f"Creating Cerebras service with model: {service_model}")
        return CerebrasService(
            cache=cache,
            verbose=verbose,
            model=service_model
        )

    elif provider == "baseten":
        # For Baseten, model is determined by BASETEN_MODEL_ID in settings
        # but we can override if a specific Baseten model is provided
        if model and AIModelDetector.detect_provider(model) == "baseten":
            # If user provided a Baseten model name, we could potentially
            # override BASETEN_MODEL_ID, but for now we'll just log it
            logger.info(f"Baseten model requested: {model}")
            logger.info(
                f"Using configured BASETEN_MODEL_ID: {settings.BASETEN_MODEL_ID}"
            )

        logger.info("Creating Baseten service")
        return BasetenService(cache=cache, verbose=verbose)

    elif provider == "openai":
        # For OpenAI, we could potentially override the model
        # but for now we use the one from settings
        service_model = model or settings.OPENAI_MODEL
        logger.info(f"Creating OpenAI service with model: {service_model}")
        # Note: OpenAIService currently doesn't accept model parameter
        # We'll need to update it if we want to support model override
        return OpenAIService(cache=cache)

    elif provider == "huggingface":
        # For Hugging Face, pass model if provided
        service_model = model or settings.HF_MODEL
        logger.info(f"Creating Hugging Face service with model: {service_model}")
        return HuggingFaceService(
            cache=cache,
            verbose=verbose,
            model=service_model
        )

    elif provider == "ollama":
        # For Ollama, pass model if provided
        service_model = model or settings.OLLAMA_MODEL
        logger.info(f"Creating Ollama service with model: {service_model}")
        return OllamaService(
            cache=cache,
            verbose=verbose,
            model=service_model
        )

    elif provider == "llamacpp":
        # For Llama.cpp, pass model path if provided
        llama_cpp_model = model or settings.LLAMA_CPP_MODEL_PATH
        if not llama_cpp_model:
            raise ValueError(
                "LLAMA_CPP_MODEL_PATH must be set in settings or provided via model parameter"
            )
        logger.info(f"Creating Llama.cpp service with model: {llama_cpp_model}")
        return LlamaCppService(
            cache=cache,
            verbose=verbose,
            model=llama_cpp_model
        )

    elif provider == "deepseek":
        # For DeepSeek, use model from settings or provided parameter
        service_model = model or settings.DEEPSEEK_MODEL
        logger.info(f"Creating DeepSeek service with model: {service_model}")
        return DeepSeekService(cache=cache)

    else:
        raise ValueError(f"Unknown AI provider: '{provider}'")


def get_model_selector() -> dict:
    """
    Get available models for UI model selector

    Returns:
        Dictionary of providers and their available models
    """
    return {
        "providers": {
            "cerebras": {
                "name": "Cerebras AI",
                "description": "Free tier with rate limiting",
                "models": [
                    {
                        "id": "llama3.1-8b",
                        "name": "LLaMA 3.1 8B",
                        "description": "Fast, efficient"
                    },
                    {
                        "id": "llama3.1-70b",
                        "name": "LLaMA 3.1 70B",
                        "description": "High quality"
                    },
                    {
                        "id": "qwen-3-235b-a22b-instruct-2507",
                        "name": "Qwen 3 235B",
                        "description": "Latest Qwen model"
                    },
                    {
                        "id": "cerebras-llama3.1-8b",
                        "name": "Cerebras LLaMA 3.1 8B",
                        "description": "Scientific analysis model"
                    },
                    {
                        "id": "custom",
                        "name": "Custom Cerebras Model",
                        "description": "Any Cerebras-supported model"
                    }
                ],
                "default": "llama3.1-8b"
            },
            "baseten": {
                "name": "Baseten",
                "description": "Hosted models with automatic rate limiting",
                "models": [
                    {
                        "id": "kimi-k2-thinking",
                        "name": "Kimi K2 Thinking",
                        "description": "Specialized thinking model"
                    },
                    {
                        "id": "custom",
                        "name": "Custom Baseten Model",
                        "description": "Any Baseten-hosted model"
                    }
                ],
                "default": "kimi-k2-thinking"
            },
            "openai": {
                "name": "OpenAI",
                "description": "GPT models with commercial API",
                "models": [
                    {
                        "id": "gpt-4",
                        "name": "GPT-4",
                        "description": "Most capable model"
                    },
                    {
                        "id": "gpt-3.5-turbo",
                        "name": "GPT-3.5 Turbo",
                        "description": "Fast and cost-effective"
                    },
                    {
                        "id": "o1-preview",
                        "name": "o1 Preview",
                        "description": "Reasoning model"
                    },
                    {
                        "id": "o1-mini",
                        "name": "o1 Mini",
                        "description": "Smaller reasoning model"
                    }
                ],
                "default": "gpt-4"
            },
            "huggingface": {
                "name": "Hugging Face",
                "description": "Open-source models via Inference API or local Transformers",
                "models": [
                    {
                        "id": "ehartford/dolphin-2.5-mixtral-8x7b",
                        "name": "Dolphin 2.5 Mixtral 8x7B",
                        "description": "Uncensored Mixtral fine-tune"
                    },
                    {
                        "id": "dolphin-mixtral",
                        "name": "Dolphin Mixtral (Scientific)",
                        "description": "Scientific analysis with data provenance"
                    },
                    {
                        "id": "scibert",
                        "name": "SciBERT",
                        "description": "Scientific paper analysis"
                    },
                    {
                        "id": "microsoft/phi-2",
                        "name": "Microsoft Phi-2",
                        "description": "Small but capable model"
                    },
                    {
                        "id": "google/gemma-2b",
                        "name": "Google Gemma 2B",
                        "description": "Lightweight Gemma model"
                    },
                    {
                        "id": "llama3_8b_chat_uncensored",
                        "name": "Llama 3 8B Uncensored",
                        "description": "Local Llama 3 8B uncensored model"
                    },
                    {
                        "id": "custom",
                        "name": "Custom Hugging Face Model",
                        "description": "Any Hugging Face model ID"
                    },
                    {
                        "id": "local",
                        "name": "Local Transformers Model",
                        "description": "Model loaded from local path"
                    }
                ],
                "default": "ehartford/dolphin-2.5-mixtral-8x7b"
            },
            "ollama": {
                "name": "Ollama",
                "description": "Local/remote Ollama models via OpenAI-compatible API",
                "models": [
                    {
                        "id": "hf.co/PsiPi/ehartford_dolphin-2.5-mixtral-8x7b-GGUF:Q3_K_L",
                        "name": "Dolphin 2.5 Mixtral 8x7B GGUF",
                        "description": "Quantized Mixtral fine-tune via Ollama"
                    },
                    {
                        "id": "llama3.2-3b",
                        "name": "LLaMA 3.2 3B",
                        "description": "Lightweight local model"
                    },
                    {
                        "id": "llama3.1:latest",
                        "name": "LLaMA 3.1 Latest",
                        "description": "Latest LLaMA 3.1 via Ollama"
                    },
                    {
                        "id": "custom",
                        "name": "Custom Ollama Model",
                        "description": "Any Ollama model (local/remote)"
                    }
                ],
                "default": "hf.co/PsiPi/ehartford_dolphin-2.5-mixtral-8x7b-GGUF:Q3_K_L"
            },
            "llamacpp": {
                "name": "Llama.cpp",
                "description": "Local GGUF models via llama-cpp-python",
                "models": [
                    {
                        "id": "DavidAU/DeepSeek-MOE-4X8B-R1-Distill-Llama-3.1-Deep-Thinker-Uncensored-24B-GGUF",
                        "name": "DeepSeek MOE 4×8B Deep Thinker (24B GGUF)",
                        "description": "Uncensored deep-thinking model for perfume chemistry"
                    },
                    {
                        "id": "OpenAi-GPT-oss-20b-abliterated-uncensored-NEO-Imatrix-gguf",
                        "name": "OpenAI 20B NEO Uncensored",
                        "description": "Large uncensored model"
                    },
                    {
                        "id": "custom",
                        "name": "Custom GGUF Model",
                        "description": "Any local GGUF model file"
                    }
                ],
                "default": "DavidAU/DeepSeek-MOE-4X8B-R1-Distill-Llama-3.1-Deep-Thinker-Uncensored-24B-GGUF"
            }
        },
        "auto_detection": True,
        "default_provider": "cerebras"
    }
