"""
Enhanced AI Service Factory with Scientific Model Configuration System

Integrates with the model configuration system to provide:
1. Data provenance tracking for all AI models
2. Scientific integrity guardrails
3. Model selection based on purpose and restrictions
4. Automatic validation of scientific queries

Data provenance: This factory ensures all AI model usage is tracked with
source, version, and training data information to maintain scientific
integrity and reproducibility.
Sources: Model metadata from Hugging Face Hub, Ollama library, and provider
documentation
Last updated: 2026-01-12
"""

import re
from typing import Any, Dict, Optional, cast

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.models_config import (
    ModelPurpose,
    get_model_for_purpose,
    get_model_registry,
    validate_scientific_query,
)
from app.services.ai.base import BaseAIService
from app.services.ai.baseten_service import BasetenService
from app.services.ai.cerebras_service import CerebrasService
from app.services.ai.huggingface_service import HuggingFaceService
from app.services.ai.ollama_service import OllamaService
from app.services.ai.openai_service import OpenAIService

logger = get_logger(__name__)


class ScientificAIModelDetector:
    """
    Enhanced AI model detector with scientific integrity checks.

    Data provenance: This detector validates model usage against scientific
    integrity requirements and data provenance rules.
    """

    # Model patterns for provider detection
    CEREBRAS_PATTERNS = [
        r'^llama3\.1-[0-9]+b$',
        r'^qwen-[0-9]+b',
        r'^cerebras-',
        r'^llama-',
        r'^mistral-',
        r'^mixtral-',
    ]

    BASETEN_PATTERNS = [
        r'kimi',
        r'k2',
        r'baseten-',
        r'^bt-',
    ]

    OPENAI_PATTERNS = [
        r'^gpt-',
        r'^o1-',
        r'^text-',
        r'^davinci-',
        r'^curie-',
        r'^babbage-',
        r'^ada-',
    ]

    HUGGINGFACE_PATTERNS = [
        r'^ehartford/',
        r'^microsoft/',
        r'^google/',
        r'^mistralai/',
        r'^meta-llama/',
        r'^bigscience/',
        r'^tiiuae/',
        r'^Qwen/',
        r'^NousResearch/',
        r'^TheBloke/',
        r'^allenai/',  # SciBERT
        r'^/',
    ]

    OLLAMA_PATTERNS = [
        r'^hf\.co/',
        r':Q[0-9]_[A-Z]_[A-Z]$',
        r':latest$',
        r':[0-9]+b$',
        r'^ollama-',
        r'^llama3\.2:',  # llama3.2:3b
    ]

    @classmethod
    def detect_provider(cls, model_name: str) -> str:
        """
        Detect AI provider based on model name with scientific validation.

        Data provenance: Validates model name against known provider patterns
        to ensure proper data source tracking.
        """
        model_lower = model_name.lower()

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

        # Default to Cerebras (most permissive/free)
        logger.warning(f"Unknown model '{model_name}', defaulting to Cerebras")
        return "cerebras"

    @classmethod
    def validate_scientific_query(cls, model_id: str, query: str) -> Dict[str, Any]:
        """
        Validate a scientific query against model restrictions.

        Data provenance: Ensures queries don't request synthetic data
        generation and comply with scientific integrity requirements.
        """
        return cast(Dict[str, Any], validate_scientific_query(model_id, query))

    @classmethod
    def get_scientific_prompt_template(cls, model_id: str, task_type: str) -> str:
        """
        Get scientific prompt template for a model and task type.

        Data provenance: Includes data source citation requirements and
        scientific integrity guardrails in the prompt template.
        """
        registry = get_model_registry()
        return cast(str, registry.get_scientific_prompt_template(model_id, task_type))


def create_scientific_ai_service(
    model: Optional[str] = None,
    purpose: Optional[ModelPurpose] = None,
    cache: Optional[Any] = None,
    verbose: bool = False,
    force_provider: Optional[str] = None,
    validate_query: Optional[str] = None
) -> BaseAIService:
    """
    Create AI service with scientific integrity and data provenance.

    Data provenance: This factory ensures all AI services are created with
    proper data source tracking and scientific integrity guardrails.

    Args:
        model: Model name or ID (e.g., "dolphin-mixtral", "llama3.2-3b")
        purpose: Intended use case (e.g., chemical literature analysis)
        cache: Optional cache instance
        verbose: Enable verbose logging
        force_provider: Force specific provider
        validate_query: Optional query to validate before creating service

    Returns:
        AI service instance with scientific integrity guardrails

    Raises:
        ValueError: If query validation fails or model not found
    """
    settings = get_settings()
    registry = get_model_registry()

    # Determine model based on purpose if not specified
    if not model and purpose:
        model_config = get_model_for_purpose(purpose)
        if model_config:
            model = model_config.model_id
            logger.info(f"Selected model for {purpose}: {model}")
        else:
            logger.warning(f"No model found for purpose: {purpose}")

    # Validate query if provided
    if validate_query and model:
        validation = ScientificAIModelDetector.validate_scientific_query(
            model, validate_query
        )
        if not validation["valid"]:
            violations = "\n".join(validation["violations"])
            raise ValueError(
                f"Query validation failed for model {model}:\n{violations}"
            )

    # Determine provider
    if force_provider:
        provider = force_provider.lower()
        logger.info(f"Forcing provider: {provider}")
    else:
        # Use model for detection, fall back to AI_PROVIDER from settings
        if model:
            provider = ScientificAIModelDetector.detect_provider(model)
        else:
            provider = settings.AI_PROVIDER.lower()
            logger.info(f"Using provider from settings: {provider}")

    # Get model configuration for data provenance
    model_config = None
    if model:
        model_config = registry.get_model(model)
        if model_config:
            logger.info(
                f"Using model: {model_config.display_name} "
                f"(provider: {model_config.provider}, "
                f"license: {model_config.license})"
            )
            logger.info(f"Data provenance: {model_config.data_provenance}")

    service: BaseAIService

    # Create appropriate service with scientific guardrails
    if provider == "cerebras":
        service_model = model or settings.CEREBRAS_MODEL
        logger.info(f"Creating Cerebras service with model: {service_model}")

        # Add scientific prompt template if available
        service = CerebrasService(
            cache=cache,
            verbose=verbose,
            model=service_model
        )

        if model is not None and model_config and validate_query:
            template = ScientificAIModelDetector.get_scientific_prompt_template(
                model, "chemical_literature"
            )
            if template:
                service.system_prompt = template.format(task=validate_query)

        return service

    elif provider == "baseten":
        logger.info("Creating Baseten service")
        service = BasetenService(cache=cache, verbose=verbose)

        if model is not None and model_config and validate_query:
            template = ScientificAIModelDetector.get_scientific_prompt_template(
                model, "chemical_literature"
            )
            if template:
                service.system_prompt = template.format(task=validate_query)

        return service

    elif provider == "openai":
        service_model = model or settings.OPENAI_MODEL
        logger.info(f"Creating OpenAI service with model: {service_model}")
        service = OpenAIService(cache=cache)

        if model is not None and model_config and validate_query:
            template = ScientificAIModelDetector.get_scientific_prompt_template(
                model, "chemical_literature"
            )
            if template:
                service.system_prompt = template.format(task=validate_query)

        return service

    elif provider == "huggingface":
        service_model = model or settings.HF_MODEL
        logger.info(f"Creating Hugging Face service with model: {service_model}")
        service = HuggingFaceService(
            cache=cache,
            verbose=verbose,
            model=service_model
        )

        if model is not None and model_config and validate_query:
            template = ScientificAIModelDetector.get_scientific_prompt_template(
                model, "chemical_literature"
            )
            if template:
                service.system_prompt = template.format(task=validate_query)

        return service

    elif provider == "ollama":
        service_model = model or settings.OLLAMA_MODEL
        logger.info(f"Creating Ollama service with model: {service_model}")
        service = OllamaService(
            cache=cache,
            verbose=verbose,
            model=service_model
        )

        if model is not None and model_config and validate_query:
            template = ScientificAIModelDetector.get_scientific_prompt_template(
                model, "chemical_literature"
            )
            if template:
                service.system_prompt = template.format(task=validate_query)

        return service

    else:
        logger.warning(
            f"Unknown provider '{provider}', defaulting to Cerebras"
        )
        return CerebrasService(cache=cache, verbose=verbose)


def get_scientific_model_selector() -> Dict[str, Any]:
    """
    Get available models for scientific analysis with data provenance.

    Data provenance: Returns model information including source, version,
    and training data for scientific transparency.
    """
    registry = get_model_registry()
    models = registry.list_models()

    # Group models by purpose for scientific use cases
    purposes: Dict[str, Dict[str, Any]] = {
        "chemical_literature_analysis": {
            "name": "Chemical Literature Analysis",
            "description": "Analysis of GCMS data and chemical compositions",
            "models": []
        },
        "scientific_paper_analysis": {
            "name": "Scientific Paper Analysis",
            "description": "Extraction and analysis of scientific literature",
            "models": []
        },
        "perfume_formulation_analysis": {
            "name": "Perfume Formulation Analysis",
            "description": "Analysis of perfume formulations and patents",
            "models": []
        },
        "general_knowledge": {
            "name": "General Knowledge",
            "description": "General information and analysis",
            "models": []
        }
    }

    # Populate models by purpose
    for model_info in models:
        model_config = registry.get_model(model_info["model_id"])
        if model_config:
            purpose_key = model_config.purpose.value
            if purpose_key in purposes:
                purposes[purpose_key]["models"].append({
                    "id": model_info["model_id"],
                    "name": model_info["display_name"],
                    "provider": model_info["provider"],
                    "context_window": model_info["context_window"],
                    "scientific_accuracy": model_info["scientific_accuracy_score"],
                    "restrictions": model_info["restrictions"],
                    "data_provenance": model_config.data_provenance,
                    "license": model_config.license.value
                })

    return {
        "purposes": purposes,
        "data_provenance_requirements": [
            "All models must track source, version, and training data",
            "No synthetic data generation allowed",
            "Citations required for all data sources",
            "Cross-referencing required for scientific claims"
        ],
        "default_purpose": "chemical_literature_analysis"
    }


def validate_and_create_service(
    query: str,
    purpose: ModelPurpose = ModelPurpose.CHEMICAL_LITERATURE_ANALYSIS,
    cache: Optional[Any] = None,
    verbose: bool = False
) -> BaseAIService:
    """
    Validate query and create appropriate AI service.

    Data provenance: Validates query against scientific integrity requirements
    before creating service to prevent synthetic data generation requests.

    Args:
        query: Scientific query to validate
        purpose: Intended use case
        cache: Optional cache instance
        verbose: Enable verbose logging

    Returns:
        AI service instance with scientific prompt template

    Raises:
        ValueError: If no suitable model found or query validation fails
    """
    # Get appropriate model for purpose
    model_config = get_model_for_purpose(purpose)
    if not model_config:
        raise ValueError(f"No suitable model found for purpose: {purpose}")

    # Validate query against model restrictions
    validation = validate_scientific_query(model_config.model_id, query)
    if not validation["valid"]:
        violations = "\n".join(validation["violations"])
        raise ValueError(
            f"Query validation failed for model {model_config.model_id}:\n"
            f"{violations}\n\nModel restrictions: {model_config.restrictions}"
        )

    # Create service with scientific prompt template
    service = create_scientific_ai_service(
        model=model_config.model_id,
        purpose=purpose,
        cache=cache,
        verbose=verbose,
        validate_query=query
    )

    logger.info(
        f"Created scientific AI service for {purpose.value} "
        f"with model: {model_config.display_name}"
    )

    return service
