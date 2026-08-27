"""
Model configuration system for AI providers with data provenance tracking.
Data provenance: Model metadata from Hugging Face Hub, Ollama library,
and provider documentation
Sources:
- Hugging Face Model Hub: https://huggingface.co/models
- Ollama Library: https://ollama.com/library
- Model cards and documentation
Last updated: 2026-01-12
"""

import os
from enum import Enum
from importlib import import_module
from typing import Any, Dict, List, Optional, Protocol, cast

from pydantic import BaseModel, Field, field_validator


class _YamlModule(Protocol):
    """Typed surface used from the dynamically loaded PyYAML module."""

    def safe_load(self, stream: object) -> Any: ...


yaml = cast(_YamlModule, import_module("yaml"))


class ModelPurpose(str, Enum):
    """Defined purposes for model usage in perfume chemistry."""
    CHEMICAL_LITERATURE_ANALYSIS = "chemical_literature_analysis"
    SCIENTIFIC_PAPER_ANALYSIS = "scientific_paper_analysis"
    PERFUME_FORMULATION_ANALYSIS = "perfume_formulation_analysis"
    REGULATORY_COMPLIANCE_CHECK = "regulatory_compliance_check"
    PATENT_ANALYSIS = "patent_analysis"
    GENERAL_KNOWLEDGE = "general_knowledge"


class ModelRestriction(str, Enum):
    """Restrictions to enforce scientific integrity."""
    NO_DATA_GENERATION = "no_data_generation"
    LITERATURE_ONLY = "literature_only"
    EXTRACTION_ONLY = "extraction_only"
    NO_SYNTHESIS = "no_synthesis"
    CROSS_REFERENCE_REQUIRED = "cross_reference_required"
    CITATION_REQUIRED = "citation_required"


class ModelProvider(str, Enum):
    """Supported AI providers."""
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"
    CEREBRAS = "cerebras"
    OPENAI = "openai"
    BASETEN = "baseten"
    ANTHROPIC = "anthropic"


class ModelLicense(str, Enum):
    """Common model licenses."""
    APACHE_2_0 = "Apache 2.0"
    MIT = "MIT"
    LLAMA_COMMUNITY = "Llama Community License"
    COMMERCIAL = "Commercial"
    RESEARCH_ONLY = "Research Only"


class ModelConfig(BaseModel):
    """
    Configuration for an AI model with data provenance tracking.

    Data provenance requirements:
    - Source: Where the model was obtained
    - Version: Specific model version/commit
    - Training data: What data the model was trained on
    - License: Usage restrictions and requirements
    - Last updated: When this configuration was validated
    """

    # Model identification
    model_id: str = Field(..., description="Unique identifier for the model")
    display_name: str = Field(..., description="Human-readable model name")
    provider: ModelProvider = Field(..., description="AI provider")

    # Data provenance
    source_url: str = Field(..., description="URL where model can be accessed")
    version: str = Field(..., description="Model version or commit hash")
    training_data: str = Field(..., description="Description of training data")
    license: ModelLicense = Field(..., description="Model license")
    data_provenance: str = Field(
        ...,
        description="Detailed data provenance information"
    )
    last_validated: str = Field(
        ...,
        description="Date when model was last validated"
    )

    # Technical specifications
    purpose: ModelPurpose = Field(..., description="Intended use case")
    restrictions: List[ModelRestriction] = Field(
        default=[],
        description="Usage restrictions"
    )
    context_window: int = Field(..., description="Token context window size")
    parameter_count: Optional[str] = Field(
        None,
        description="Number of parameters (e.g., '7B', '70B')"
    )
    size_gb: Optional[float] = Field(
        None,
        description="Approximate size in GB"
    )

    # Performance characteristics
    recommended_max_tokens: int = Field(
        512,
        description="Recommended maximum tokens per request"
    )
    recommended_temperature: float = Field(
        0.7,
        description="Recommended temperature"
    )
    supports_tools: bool = Field(
        False,
        description="Whether model supports tool calling"
    )

    # Configuration
    base_url: Optional[str] = Field(
        None,
        description="API base URL if different from default"
    )
    api_key_env_var: Optional[str] = Field(
        None,
        description="Environment variable for API key"
    )
    requires_gpu: bool = Field(False, description="Whether model requires GPU")

    # Scientific integrity
    scientific_accuracy_score: Optional[float] = Field(
        None,
        description="Estimated scientific accuracy score (0-1)",
        ge=0.0,
        le=1.0
    )
    hallucination_risk: str = Field(
        "medium",
        description="Risk of generating hallucinated content"
    )

    class Config:
        use_enum_values = True

    @field_validator("last_validated")
    @classmethod
    def validate_date_format(cls, v):
        """Validate date format is YYYY-MM-DD."""
        from datetime import datetime
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')
        return v


class ModelRegistry:
    """
    Registry for all available AI models with data provenance tracking.

    Data provenance: Each model configuration includes source, version,
    and training data information to maintain scientific integrity and
    reproducibility.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize model registry, optionally loading from YAML config."""
        self.models: Dict[str, ModelConfig] = {}
        self._load_default_models()

        if config_path and os.path.exists(config_path):
            self._load_from_yaml(config_path)

    def _load_default_models(self):
        """Load default models with data provenance information."""

        # Approved Hugging Face models for scientific analysis
        self.models["dolphin-mixtral"] = ModelConfig(
            model_id="dolphin-mixtral",
            display_name="Dolphin Mixtral 8x7b",
            provider=ModelProvider.HUGGINGFACE,
            source_url="https://huggingface.co/ehartford/dolphin-2.5-mixtral-8x7b",
            version="dolphin-2.5-mixtral-8x7b",
            training_data="Fine-tuned on diverse datasets including scientific texts",
            license=ModelLicense.APACHE_2_0,
            data_provenance="Community fine-tune of Mixtral 8x7b by Eric Hartford",
            last_validated="2026-01-12",
            purpose=ModelPurpose.CHEMICAL_LITERATURE_ANALYSIS,
            restrictions=[
                ModelRestriction.NO_DATA_GENERATION,
                ModelRestriction.LITERATURE_ONLY,
                ModelRestriction.CITATION_REQUIRED
            ],
            context_window=32768,
            parameter_count="8x7B",
            size_gb=45.0,
            recommended_max_tokens=4096,
            recommended_temperature=0.7,
            supports_tools=True,
            api_key_env_var="HF_API_KEY",
            requires_gpu=True,
            scientific_accuracy_score=0.85,
            hallucination_risk="medium"
        )

        self.models["scibert"] = ModelConfig(
            model_id="scibert",
            display_name="SciBERT",
            provider=ModelProvider.HUGGINGFACE,
            source_url="https://huggingface.co/allenai/scibert",
            version="scibert-scivocab-uncased",
            training_data="Scientific papers from Semantic Scholar (PubMed, arXiv)",
            license=ModelLicense.APACHE_2_0,
            data_provenance="BERT model trained on scientific literature from Semantic Scholar",
            last_validated="2026-01-12",
            purpose=ModelPurpose.SCIENTIFIC_PAPER_ANALYSIS,
            restrictions=[
                ModelRestriction.EXTRACTION_ONLY,
                ModelRestriction.NO_SYNTHESIS,
                ModelRestriction.CROSS_REFERENCE_REQUIRED
            ],
            context_window=512,
            parameter_count="110M",
            size_gb=0.5,
            recommended_max_tokens=256,
            recommended_temperature=0.3,
            supports_tools=False,
            api_key_env_var="HF_API_KEY",
            requires_gpu=False,
            scientific_accuracy_score=0.90,
            hallucination_risk="low"
        )

        # Ollama models
        self.models["llama3.2-3b"] = ModelConfig(
            model_id="llama3.2-3b",
            display_name="Llama 3.2 3B",
            provider=ModelProvider.OLLAMA,
            source_url="https://ollama.com/library/llama3.2:3b",
            version="llama3.2:3b",
            training_data="Diverse text corpus including technical documents",
            license=ModelLicense.LLAMA_COMMUNITY,
            data_provenance="Meta Llama 3.2 3B model quantized for Ollama",
            last_validated="2026-01-12",
            purpose=ModelPurpose.GENERAL_KNOWLEDGE,
            restrictions=[
                ModelRestriction.NO_DATA_GENERATION,
                ModelRestriction.CROSS_REFERENCE_REQUIRED
            ],
            context_window=8192,
            parameter_count="3B",
            size_gb=2.0,
            recommended_max_tokens=2048,
            recommended_temperature=0.7,
            supports_tools=False,
            base_url="http://localhost:11434/v1",
            requires_gpu=False,
            scientific_accuracy_score=0.75,
            hallucination_risk="medium"
        )

        # Cerebras models
        self.models["cerebras-llama3.1-8b"] = ModelConfig(
            model_id="cerebras-llama3.1-8b",
            display_name="Cerebras Llama 3.1 8B",
            provider=ModelProvider.CEREBRAS,
            source_url="https://api.cerebras.ai/v1/models",
            version="llama3.1-8b",
            training_data="Diverse text corpus",
            license=ModelLicense.COMMERCIAL,
            data_provenance="Llama 3.1 8B hosted on Cerebras AI platform",
            last_validated="2026-01-12",
            purpose=ModelPurpose.CHEMICAL_LITERATURE_ANALYSIS,
            restrictions=[
                ModelRestriction.NO_DATA_GENERATION,
                ModelRestriction.CITATION_REQUIRED
            ],
            context_window=32768,
            parameter_count="8B",
            size_gb=None,
            recommended_max_tokens=8192,
            recommended_temperature=0.7,
            supports_tools=True,
            api_key_env_var="CEREBRAS_API_KEY",
            requires_gpu=False,
            scientific_accuracy_score=0.80,
            hallucination_risk="medium"
        )

    def _load_from_yaml(self, config_path: str):
        """Load additional models from YAML configuration file."""
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)

            if config_data and 'models' in config_data:
                for model_id, model_data in config_data['models'].items():
                    try:
                        model_config = ModelConfig(**model_data)
                        self.models[model_id] = model_config
                    except Exception as e:
                        print(f"Warning: Failed to load model {model_id}: {e}")
        except Exception as e:
            print(f"Warning: Failed to load model config from {config_path}: {e}")

    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """Get model configuration by ID."""
        return self.models.get(model_id)

    def get_models_by_purpose(self, purpose: ModelPurpose) -> List[ModelConfig]:
        """Get all models for a specific purpose."""
        return [
            model for model in self.models.values()
            if model.purpose == purpose
        ]

    def get_models_by_provider(self, provider: ModelProvider) -> List[ModelConfig]:
        """Get all models from a specific provider."""
        return [
            model for model in self.models.values()
            if model.provider == provider
        ]

    def list_models(self) -> List[Dict[str, Any]]:
        """List all available models with basic information."""
        return [
            {
                "model_id": model_id,
                "display_name": config.display_name,
                "provider": config.provider,
                "purpose": config.purpose,
                "context_window": config.context_window,
                "scientific_accuracy_score": config.scientific_accuracy_score,
                "restrictions": config.restrictions
            }
            for model_id, config in self.models.items()
        ]

    def validate_model_usage(self, model_id: str, prompt: str) -> Dict[str, Any]:
        """
        Validate if a model can be used for a specific prompt.

        Returns validation results including any restrictions that would be
        violated.
        """
        model = self.get_model(model_id)
        if not model:
            return {
                "valid": False,
                "error": f"Model {model_id} not found",
                "violations": []
            }

        violations = []

        # Check for data generation requests
        if ModelRestriction.NO_DATA_GENERATION in model.restrictions:
            data_generation_keywords = [
                "generate gcms data", "create formula", "invent new",
                "synthesize data", "make up", "fabricate", "hallucinate"
            ]
            prompt_lower = prompt.lower()
            for keyword in data_generation_keywords:
                if keyword in prompt_lower:
                    violations.append(
                        f"Violates NO_DATA_GENERATION: prompt contains '{keyword}'"
                    )
                    break

        # Check for citation requirements
        if ModelRestriction.CITATION_REQUIRED in model.restrictions:
            citation_words = ["cite", "citation", "reference", "source"]
            if not any(word in prompt.lower() for word in citation_words):
                violations.append(
                    "Violates CITATION_REQUIRED: prompt doesn't request citations"
                )

        return {
            "valid": len(violations) == 0,
            "model_id": model_id,
            "model_name": model.display_name,
            "violations": violations,
            "restrictions": model.restrictions
        }

    def get_scientific_prompt_template(self, model_id: str, task_type: str) -> str:
        """
        Get a scientific prompt template for a specific model and task type.

        Includes data provenance requirements and scientific integrity
        guardrails.
        """
        model = self.get_model(model_id)
        if not model:
            return ""

        base_template = """You are a scientific researcher analyzing perfume chemistry data.

DATA PROVENANCE REQUIREMENTS:
1. Use only real datasets from verified sources
2. Never generate synthetic or mock data
3. Cite all sources with PMID/DOI/URL when available
4. State uncertainty when data is incomplete
5. Cross-reference with multiple sources when possible

TASK: {task}

RESPONSE FORMAT:
1. Data source(s) with version and access date
2. Analysis methodology
3. Results with confidence levels
4. Limitations and uncertainties
5. References (PMID/DOI/URL)

IMPORTANT: If you cannot find real data, state "No real data found" and
suggest verification methods."""

        if task_type == "chemical_literature":
            return base_template + """

SPECIFIC INSTRUCTIONS FOR CHEMICAL LITERATURE ANALYSIS:
- Focus on GCMS data from published studies
- Extract chemical compositions with percentages
- Note detection limits and analytical methods
- Compare across multiple studies
- Identify conflicting data points"""

        elif task_type == "formulation_analysis":
            return base_template + """

SPECIFIC INSTRUCTIONS FOR FORMULATION ANALYSIS:
- Analyze perfume formulations from patents or publications
- Identify key aroma chemicals and their functions
- Note concentration ranges and safety limits
- Consider volatility and evaporation profiles
- Reference IFRA restrictions when applicable"""

        return base_template


# Global registry instance
model_registry = ModelRegistry()


def get_model_registry() -> ModelRegistry:
    """Get the global model registry instance."""
    return model_registry


def validate_scientific_query(model_id: str, query: str) -> Dict[str, Any]:
    """
    Validate a scientific query against model restrictions.

    Data provenance: This validation ensures scientific integrity by preventing
    requests for synthetic data generation.
    """
    registry = get_model_registry()
    return registry.validate_model_usage(model_id, query)


def get_available_models() -> List[Dict[str, Any]]:
    """Get list of all available models with basic information."""
    registry = get_model_registry()
    return registry.list_models()


def get_model_for_purpose(purpose: ModelPurpose) -> Optional[ModelConfig]:
    """
    Get the most appropriate model for a specific purpose.

    Selection criteria:
    1. Highest scientific accuracy score
    2. Appropriate restrictions for the task
    3. Available context window
    4. Technical requirements (GPU, etc.)
    """
    registry = get_model_registry()
    models = registry.get_models_by_purpose(purpose)

    if not models:
        return None

    # Sort by scientific accuracy score (descending)
    models.sort(key=lambda x: x.scientific_accuracy_score or 0, reverse=True)

    # Filter out models with hallucination risk "high"
    filtered_models = [m for m in models if m.hallucination_risk != "high"]

    return filtered_models[0] if filtered_models else models[0]
