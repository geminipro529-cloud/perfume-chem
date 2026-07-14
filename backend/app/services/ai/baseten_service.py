"""
Baseten AI service with automatic rate limiting

Provides rate-limited access to Baseten-hosted models with
OpenAI-compatible interface.
"""

import json
import re
from typing import Any, AsyncGenerator, Dict, List, Optional

from openai import AsyncOpenAI
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


class BasetenService(BaseAIService):
    """
    Baseten AI service with automatic rate limiting

    Features:
    - Automatic rate limit enforcement
    - Exponential backoff on errors
    - Token usage tracking
    - Chemistry validation integration
    """

    def __init__(self, cache: Optional[Any] = None, verbose: bool = False):
        """
        Initialize Baseten service

        Args:
            cache: Optional cache instance
            verbose: Enable verbose logging
        """
        settings = get_settings()

        # Baseten provides OpenAI-compatible API
        self.client = AsyncOpenAI(
            api_key=settings.BASETEN_API_KEY,
            base_url=f"https://api.baseten.co/v1/{settings.BASETEN_MODEL_ID}"
        )

        self.model = settings.BASETEN_MODEL_ID
        self.cache = cache
        self.settings = settings
        self.verbose = verbose

        # Initialize rate limiter
        config_path = settings.RATE_LIMIT_CONFIG_PATH
        if not config_path:
            # Use default location: backend/app/config/rate_limits.yaml
            from pathlib import Path
            # From baseten_service.py: go up 3 levels to reach backend/app/
            config_path = str(
                Path(__file__).parent.parent.parent / "config" / "rate_limits.yaml"
            )

        self.rate_limiter = get_rate_limiter(config_path)

        # Initialize context builder and validator
        self.context_builder = ContextBuilder()
        self.validator = ChemistryValidator()

        logger.info(f"Initialized Baseten service with model: {self.model}")

    def _get_provider_for_model(self, model_name: str) -> str:
        """
        Determine which rate limit provider to use based on model name

        Args:
            model_name: The model name or ID

        Returns:
            Provider string: "kimi_k2" for Kimi K2 models, "baseten" for others
        """
        # Check if model name contains "kimi" or "k2" (case-insensitive)
        model_lower = model_name.lower()
        if re.search(r'kimi|k2', model_lower):
            if self.verbose:
                msg = f"Detected Kimi K2 model: {model_name}, using kimi_k2 rate limits"
                logger.info(msg)
            return "kimi_k2"

        # Default to baseten provider
        return "baseten"

    async def _acquire_rate_limit(self, estimated_tokens: int = 0) -> None:
        """Acquire rate limit permission before making request"""
        try:
            # Determine which provider to use based on model
            provider = self._get_provider_for_model(self.model)

            await self.rate_limiter.acquire(
                provider=provider,
                num_tokens=estimated_tokens,
                max_retries=3
            )
        except Exception as e:
            logger.error(f"Rate limit acquisition failed: {e}")
            raise AIServiceError(f"Rate limit error: {e}", e)

    def _estimate_tokens(self, prompt: str, max_tokens: int = 1000) -> int:
        """Estimate total tokens (prompt + completion)"""
        prompt_tokens = len(prompt) // 4
        return prompt_tokens + max_tokens

    def _record_actual_usage(self, response: Any) -> None:
        """Record actual token usage from response"""
        if hasattr(response, 'usage') and response.usage:
            total_tokens = response.usage.total_tokens
            if self.verbose:
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                logger.info(
                    f"Baseten usage: {prompt_tokens} prompt + "
                    f"{completion_tokens} completion = {total_tokens} total"
                )

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
        **kwargs
    ) -> str:
        """
        Complete a prompt with automatic rate limiting

        Args:
            prompt: The prompt to complete
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            **kwargs: Additional arguments

        Returns:
            Completion text
        """
        try:
            # Check cache first
            cache_key = f"{prompt}:{max_tokens}:{temperature}"
            if self.cache:
                cached = await self.cache.get(cache_key)
                if cached:
                    if self.verbose:
                        logger.info("Cache hit for Baseten completion")
                    return cached

            # Acquire rate limit
            estimated_tokens = self._estimate_tokens(prompt, max_tokens)
            await self._acquire_rate_limit(estimated_tokens)

            # Make API call
            if self.verbose:
                msg = f"Calling Baseten API: {self.model}, max_tokens={max_tokens}"
                logger.info(msg)

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            # Record actual usage
            self._record_actual_usage(response)

            result = response.choices[0].message.content

            # Cache the result
            if self.cache and result:
                await self.cache.set(cache_key, result)

            return result or ""

        except Exception as e:
            logger.error(f"Baseten API error: {str(e)}")
            raise AIServiceError(
                f"Failed to get Baseten completion: {str(e)}", e
            )

    async def stream(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream completion tokens with rate limiting

        Args:
            prompt: The prompt to complete
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            **kwargs: Additional arguments

        Yields:
            Completion text chunks
        """
        try:
            # Acquire rate limit
            estimated_tokens = self._estimate_tokens(prompt, max_tokens)
            await self._acquire_rate_limit(estimated_tokens)

            # Make streaming call
            if self.verbose:
                logger.info(f"Streaming from Baseten API: {self.model}")

            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                **kwargs
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Baseten streaming error: {str(e)}")
            raise AIServiceError(
                f"Failed to stream Baseten completion: {str(e)}", e
            )

    async def analyze_perfume(
        self,
        name: str,
        ingredients: list,
        concentration: float = 15.0
    ) -> Dict[str, Any]:
        """Analyze a perfume composition using Baseten AI"""

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
            validation_context=context.get(
                "validation_context", "No pre-validation"
            )
        )

        response = await self.complete(
            prompt,
            max_tokens=2000,
            temperature=0.7
        )

        try:
            result = json.loads(response)
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

        formula_keys = [
            "suggested_formula", "modified_formula", "new_formula", "formula"
        ]
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

                error_count = sum(
                    1 for i in issues if i.severity.value == "error"
                )
                warning_count = sum(
                    1 for i in issues if i.severity.value == "warning"
                )

                result["validation_summary"] = {
                    "errors": error_count,
                    "warnings": warning_count,
                    "total_issues": len(issues),
                    "status": (
                        "error" if error_count > 0 else
                        ("warning" if warning_count > 0 else "ok")
                    )
                }

                if error_count > 0:
                    corrected, changes = self.validator.auto_correct_formula(
                        suggested_formula
                    )
                    if changes:
                        result["auto_corrected_formula"] = corrected
                        result["corrections_applied"] = changes

        return result

    async def suggest_modifications(
        self,
        formula: Dict[str, Any],
        goal: str
    ) -> Dict[str, Any]:
        """Suggest formula modifications using Baseten"""

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
            result = json.loads(response)
            result = self._post_validate_response(result, ingredients)
            return result
        except json.JSONDecodeError:
            return {"raw_suggestions": response}

    async def suggest_pairings(
        self,
        ingredient: str,
        cas_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """Suggest ingredient pairings using Baseten"""

        context = self.context_builder.build_context(
            query=ingredient,
            ingredients=None,
            include_validation=False
        )

        dosage_info = self.validator.get_dosage_guidelines(ingredient)
        ingredient_dosage = ""
        if dosage_info:
            min_pct = dosage_info.get('min_percent', 0)
            max_pct = dosage_info.get('max_percent', 100)
            typical = dosage_info.get('typical_percent', 'N/A')
            potency = dosage_info.get('potency', 'unknown')
            ingredient_dosage = (
                f"\n**{ingredient}**: {min_pct}-{max_pct}% "
                f"(typical: {typical}%), Potency: {potency}"
            )

        prompt = INGREDIENT_PAIRING_PROMPT.substitute(
            ingredient=ingredient,
            cas_number=cas_number or "N/A",
            dosage_guidelines=ingredient_dosage + "\n\n" + context.get(
                "dosage_guidelines", "N/A"
            ),
            inventory_context=context.get("inventory", "N/A")
        )

        response = await self.complete(
            prompt,
            max_tokens=1500,
            temperature=0.7
        )

        try:
            result = json.loads(response)
            if dosage_info:
                result["validated_dosage"] = dosage_info
            return result
        except json.JSONDecodeError:
            return {"raw_pairings": response}

    def get_usage_stats(self) -> Dict:
        """Get rate limit usage statistics"""
        # Determine which provider to get stats for
        provider = self._get_provider_for_model(self.model)
        return self.rate_limiter.get_usage(provider)
