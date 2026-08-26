"""
Llama.cpp AI service for local GGUF models

Uses llama-cpp-python to load GGUF models directly.
Configure via environment variables:
- LLAMA_CPP_MODEL_PATH: Path to GGUF model file (required)
- LLAMA_CPP_N_CTX: Context size (default: 2048)
- LLAMA_CPP_N_GPU_LAYERS: GPU layers for acceleration (default: 0, CPU only)
- LLAMA_CPP_SEED: Random seed (default: -1)
- LLAMA_CPP_VERBOSE: Enable verbose logging (default: False)

Rate limiting: Uses the 'llamacpp' provider configuration in rate_limits.yaml.
"""

import json
from typing import Any, AsyncGenerator, Dict, List, Optional, cast

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.exceptions import AIServiceError
from app.core.logging import get_logger
from app.services.ai.base import BaseAIService
from app.services.ai.prompts.perfume_analysis import (
    ANALYZE_PERFUME_PROMPT,
    INGREDIENT_PAIRING_PROMPT,
    SUGGEST_MODIFICATIONS_PROMPT,
)
from app.services.chemistry_validator import ChemistryValidator
from app.services.context_builder import ContextBuilder
from app.utils.api_rate_limiter import get_rate_limiter

logger = get_logger(__name__)


def normalize_tools_for_llamacpp(tools: Optional[List[Dict]] = None) -> Optional[List[Dict]]:
    """
    Normalize tools for llama.cpp compatibility (not supported, placeholder)

    llama.cpp does not support tool calls; this function returns None.
    """
    # Tools not supported in llama.cpp; return None to ignore
    return None


class LlamaCppService(BaseAIService):
    """
    Llama.cpp AI service for local GGUF models

    Features:
    - Loads GGUF models directly via llama-cpp-python
    - Supports chat completions with system/user/assistant roles
    - Automatic rate limiting (if configured)
    - Exponential backoff on errors
    - No network dependency, purely local inference
    """

    def __init__(self, cache: Optional[Any] = None, verbose: bool = False, model: Optional[str] = None):
        """
        Initialize Llama.cpp service

        Args:
            cache: Optional cache instance
            verbose: Enable verbose logging
            model: Optional model override (defaults to LLAMA_CPP_MODEL_PATH from config)
        """
        settings = get_settings()

        # Use provided model path or fall back to config
        self.model_path = model or settings.LLAMA_CPP_MODEL_PATH
        if not self.model_path:
            raise ValueError("LLAMA_CPP_MODEL_PATH environment variable must be set")

        self.cache = cache
        self.settings = settings
        self.verbose = verbose

        logger.info(f"Initializing Llama.cpp service with model: {self.model_path}")

        # Load llama-cpp-python (optional dependency)
        try:
            from llama_cpp import Llama
        except ImportError as e:
            logger.error("llama-cpp-python not installed. Install with: pip install llama-cpp-python")
            raise AIServiceError("llama-cpp-python not installed. Install with: pip install llama-cpp-python", e)

        # Configuration parameters
        n_ctx = getattr(settings, 'LLAMA_CPP_N_CTX', 2048)
        n_gpu_layers = getattr(settings, 'LLAMA_CPP_N_GPU_LAYERS', 0)
        seed = getattr(settings, 'LLAMA_CPP_SEED', -1)
        verbose_llama = getattr(settings, 'LLAMA_CPP_VERBOSE', False)

        # Load model
        try:
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                seed=seed,
                verbose=verbose_llama,
                chat_format="chatml"  # Supports ChatML format for chat completions
            )
            logger.info(f"Model loaded successfully (n_ctx={n_ctx}, n_gpu_layers={n_gpu_layers})")
        except Exception as e:
            logger.error(f"Failed to load llama.cpp model: {str(e)}")
            raise AIServiceError(f"Failed to load llama.cpp model: {str(e)}", e)

        # Initialize rate limiter (optional, uses 'llamacpp' provider)
        config_path = settings.RATE_LIMIT_CONFIG_PATH
        if not config_path:
            from pathlib import Path
            config_path = str(Path(__file__).parent.parent.parent / "config" / "rate_limits.yaml")

        self.rate_limiter = get_rate_limiter(config_path)

        # Initialize context builder and validator
        self.context_builder = ContextBuilder()
        self.validator = ChemistryValidator()

        logger.info("Llama.cpp service ready")

    async def _acquire_rate_limit(self, estimated_tokens: int = 0) -> None:
        """
        Acquire rate limit permission before making request

        Args:
            estimated_tokens: Estimated token usage for this request
        """
        try:
            await self.rate_limiter.acquire(
                provider="llamacpp",
                num_tokens=estimated_tokens,
                max_retries=3
            )
        except Exception as e:
            logger.error(f"Rate limit acquisition failed: {e}")
            raise AIServiceError(f"Rate limit error: {e}", e)

    def _estimate_tokens(self, prompt: str, max_tokens: int = 1000) -> int:
        """
        Estimate total tokens (prompt + completion)

        Rough estimate: 1 token ≈ 4 characters
        """
        prompt_tokens = len(prompt) // 4
        return prompt_tokens + max_tokens

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def complete(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> str:
        """
        Complete a prompt with Llama.cpp

        Args:
            prompt: The prompt to complete
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            tools: Optional tool definitions (ignored, not supported)
            **kwargs: Additional arguments passed to llama.cpp

        Returns:
            Completion text
        """
        try:
            # Check cache first
            cache_key = f"llamacpp:{prompt}:{max_tokens}:{temperature}"
            if self.cache:
                cached = await self.cache.get(cache_key)
                if cached:
                    if self.verbose:
                        logger.info("Cache hit for Llama.cpp completion")
                    return cast(str, cached)

            # Acquire rate limit
            estimated_tokens = self._estimate_tokens(prompt, max_tokens)
            await self._acquire_rate_limit(estimated_tokens)

            # Normalize tools (ignored)
            _ = normalize_tools_for_llamacpp(tools)

            # Make inference
            if self.verbose:
                logger.info(f"Calling Llama.cpp model: {self.model_path}, max_tokens={max_tokens}")

            # Use chat completion with a single user message
            response = self.llm.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            result = cast(
                str,
                response['choices'][0]['message']['content'] if response['choices'] else ""
            )

            # Record usage if available
            if 'usage' in response:
                logger.debug(f"Llama.cpp usage: {response['usage']['total_tokens']} tokens")

            # Cache the result
            if self.cache and result:
                await self.cache.set(cache_key, result)

            return result

        except Exception as e:
            logger.error(f"Llama.cpp inference error: {str(e)}")
            raise AIServiceError(f"Failed to get Llama.cpp completion: {str(e)}", e)

    async def stream(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream completion tokens with Llama.cpp

        Args:
            prompt: The prompt to complete
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            tools: Optional tool definitions (ignored)
            **kwargs: Additional arguments

        Yields:
            Completion text chunks
        """
        try:
            # Acquire rate limit
            estimated_tokens = self._estimate_tokens(prompt, max_tokens)
            await self._acquire_rate_limit(estimated_tokens)

            # Normalize tools (ignored)
            _ = normalize_tools_for_llamacpp(tools)

            if self.verbose:
                logger.info(f"Streaming from Llama.cpp model: {self.model_path}")

            # Use streaming chat completion
            stream = self.llm.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                **kwargs
            )

            for chunk in stream:
                if 'choices' in chunk and chunk['choices']:
                    delta = chunk['choices'][0].get('delta', {})
                    if 'content' in delta and delta['content']:
                        yield delta['content']

        except Exception as e:
            logger.error(f"Llama.cpp streaming error: {str(e)}")
            raise AIServiceError(f"Failed to stream Llama.cpp completion: {str(e)}", e)

    async def analyze_perfume(
        self,
        name: str,
        ingredients: list,
        concentration: float = 15.0
    ) -> Dict[str, Any]:
        """Analyze a perfume composition using Llama.cpp AI"""

        # Build context
        context = self.context_builder.build_context(
            query=name,
            ingredients=ingredients,
            include_validation=True
        )

        # Format ingredients
        ingredients_str = "\n".join([
            f"- {ing.get('name', 'Unknown')}: {ing.get('percentage', 0)}%"
            for ing in ingredients
        ])

        # Build prompt
        prompt = ANALYZE_PERFUME_PROMPT.substitute(
            name=name,
            concentration=concentration,
            ingredients=ingredients_str,
            dosage_guidelines=context.get("dosage_guidelines", "N/A"),
            inventory_context=context.get("inventory", "N/A"),
            knowledge_context=context.get("relevant_knowledge", "N/A"),
            formulation_context=context.get("similar_formulations", "N/A"),
            validation_context=context.get("validation_context", "No pre-validation")
        )

        response = await self.complete(
            prompt,
            max_tokens=2000,
            temperature=0.7
        )

        try:
            result = cast(Dict[str, Any], json.loads(response))
            result = self._post_validate_response(result, ingredients)
            return result
        except json.JSONDecodeError:
            return {"raw_analysis": response}

    def _post_validate_response(
        self,
        result: Dict[str, Any],
        original_ingredients: List[Dict]
    ) -> Dict[str, Any]:
        """Post-validate AI response"""

        formula_keys = ["suggested_formula", "modified_formula", "new_formula", "formula"]
        suggested_formula = None

        for key in formula_keys:
            if key in result and isinstance(result[key], list):
                suggested_formula = result[key]
                break

        if not suggested_formula:
            suggested_formula = original_ingredients

        if suggested_formula:
            issues = self.validator.validate_formula(suggested_formula)

            if issues:
                result["validation_issues"] = [
                    {
                        "severity": issue.severity.value,
                        "chemical": issue.chemical,
                        "message": issue.message,
                        "fix": issue.suggested_fix,
                        "current": issue.current_value,
                        "recommended": issue.recommended_value
                    }
                    for issue in issues
                ]

                error_count = sum(1 for i in issues if i.severity.value == "error")
                warning_count = sum(1 for i in issues if i.severity.value == "warning")

                result["validation_summary"] = {
                    "errors": error_count,
                    "warnings": warning_count,
                    "total_issues": len(issues),
                    "status": "error" if error_count > 0 else ("warning" if warning_count > 0 else "ok")
                }

                if error_count > 0:
                    corrected, changes = self.validator.auto_correct_formula(suggested_formula)
                    if changes:
                        result["auto_corrected_formula"] = corrected
                        result["corrections_applied"] = changes

        return result

    async def suggest_modifications(
        self,
        formula: Dict[str, Any],
        goal: str
    ) -> Dict[str, Any]:
        """Suggest formula modifications using Llama.cpp"""

        ingredients = formula.get("ingredients", [])

        context = self.context_builder.build_context(
            query=goal,
            ingredients=ingredients,
            include_validation=True
        )

        formula_str = json.dumps(formula, indent=2)

        prompt = SUGGEST_MODIFICATIONS_PROMPT.substitute(
            formula=formula_str,
            goal=goal,
            dosage_guidelines=context.get("dosage_guidelines", "N/A"),
            inventory_context=context.get("inventory", "N/A"),
            knowledge_context=context.get("relevant_knowledge", "N/A")
        )

        response = await self.complete(
            prompt,
            max_tokens=2000,
            temperature=0.7
        )

        try:
            result = cast(Dict[str, Any], json.loads(response))
            result = self._post_validate_response(result, ingredients)
            return result
        except json.JSONDecodeError:
            return {"raw_suggestions": response}

    async def suggest_pairings(
        self,
        ingredient: str,
        cas_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """Suggest ingredient pairings using Llama.cpp"""

        context = self.context_builder.build_context(
            query=ingredient,
            ingredients=None,
            include_validation=False
        )

        dosage_info = self.validator.get_dosage_guidelines(ingredient)
        ingredient_dosage = ""
        if dosage_info:
            ingredient_dosage = (
                f"\n**{ingredient}**: {dosage_info.get('min_percent', 0)}-{dosage_info.get('max_percent', 100)}% "
                f"(typical: {dosage_info.get('typical_percent', 'N/A')}%), "
                f"Potency: {dosage_info.get('potency', 'unknown')}"
            )

        prompt = INGREDIENT_PAIRING_PROMPT.substitute(
            ingredient=ingredient,
            cas_number=cas_number or "N/A",
            dosage_guidelines=ingredient_dosage + "\n\n" + context.get("dosage_guidelines", "N/A"),
            inventory_context=context.get("inventory", "N/A")
        )

        response = await self.complete(
            prompt,
            max_tokens=1500,
            temperature=0.7
        )

        try:
            result = cast(Dict[str, Any], json.loads(response))
            if dosage_info:
                result["validated_dosage"] = dosage_info
            return result
        except json.JSONDecodeError:
            return {"raw_pairings": response}

    def get_usage_stats(self) -> Dict:
        """Get rate limit usage statistics"""
        return cast(Dict[str, Any], self.rate_limiter.get_usage("llamacpp"))
