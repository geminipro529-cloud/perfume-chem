"""
Cerebras AI service with automatic rate limiting and tool normalization

Solves two key issues:
1. Rate limit enforcement (30 req/min, 64k tokens/min)
2. Tool strict parameter conflict (auto-normalizes to strict: false)
"""

import json
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


def validate_tools_for_cerebras(tools: Optional[List[Dict]]) -> bool:
    """
    Validate that all tools have consistent strict values

    Returns True if valid, False if issues found
    """
    if not tools:
        return True

    strict_values = set()
    for i, tool in enumerate(tools):
        if 'function' in tool:
            if 'strict' in tool['function']:
                strict_values.add(tool['function']['strict'])
                logger.debug(f"Tool {i+1} has strict={tool['function']['strict']}")

    if len(strict_values) > 1:
        logger.error(f"MIXED STRICT VALUES DETECTED: {strict_values}")
        return False

    logger.debug(f"Tools validation OK: {len(tools)} tools, strict values: {strict_values}")
    return True


def normalize_tools_for_cerebras(tools: Optional[List[Dict]] = None) -> Optional[List[Dict]]:
    """
    Normalize tools for Cerebras compatibility

    Cerebras requires ALL tools to have the same 'strict' value.
    This function ensures all tools have 'strict: false' to avoid mixed values error.

    Error from Cerebras:
    "Tools with mixed values for 'strict' are not allowed.
     Please set all tools to 'strict: true' or 'strict: false'"

    Args:
        tools: List of tool definitions

    Returns:
        Normalized tools with strict=false, or None
    """
    if not tools:
        return None

    import copy
    import json

    normalized = []
    for i, tool in enumerate(tools):
        # Deep copy to avoid modifying original
        tool_copy = copy.deepcopy(tool)

        # Recursively remove ALL strict parameters first
        def remove_strict_recursive(obj):
            if isinstance(obj, dict):
                # Remove strict at this level
                if 'strict' in obj:
                    del obj['strict']
                # Recurse into nested dicts
                for key, value in list(obj.items()):
                    remove_strict_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    remove_strict_recursive(item)

        remove_strict_recursive(tool_copy)

        # Now explicitly set strict=false ONLY at function level
        if 'function' in tool_copy:
            tool_copy['function']['strict'] = False

        normalized.append(tool_copy)

        logger.debug(f"Tool {i+1} normalized: {json.dumps(tool_copy, indent=2)}")

    return normalized


class CerebrasService(BaseAIService):
    """
    Cerebras AI service with automatic rate limiting

    Features:
    - Automatic rate limit enforcement (30 req/min, 64k tokens/min)
    - Tool strict parameter normalization
    - Exponential backoff on rate limit errors
    - Token usage tracking
    - Chemistry validation integration
    """

    def __init__(self, cache: Optional[Any] = None, verbose: bool = False, model: Optional[str] = None):
        """
        Initialize Cerebras service (model-agnostic)

        Works with ANY Cerebras model:
        - llama3.1-8b (default, fast)
        - llama3.1-70b (larger, better quality)
        - qwen-3-235b-a22b-instruct-2507 (Qwen model)
        - Any other Cerebras-supported model

        Args:
            cache: Optional cache instance
            verbose: Enable verbose logging
            model: Optional model override (defaults to CEREBRAS_MODEL from config)
        """
        settings = get_settings()

        # Initialize OpenAI-compatible client pointing to Cerebras
        self.client = AsyncOpenAI(
            api_key=settings.CEREBRAS_API_KEY,
            base_url=settings.CEREBRAS_BASE_URL
        )

        # Use provided model or fall back to config
        self.model = model or settings.CEREBRAS_MODEL
        self.cache = cache
        self.settings = settings
        self.verbose = verbose

        # Initialize rate limiter
        config_path = settings.RATE_LIMIT_CONFIG_PATH
        if not config_path:
            # Use default location: backend/app/config/rate_limits.yaml
            from pathlib import Path
            # From cerebras_service.py: go up 3 levels (.parent.parent.parent) to reach backend/app/
            config_path = str(Path(__file__).parent.parent.parent / "config" / "rate_limits.yaml")

        self.rate_limiter = get_rate_limiter(config_path)

        # Initialize context builder and validator
        self.context_builder = ContextBuilder()
        self.validator = ChemistryValidator()

        logger.info(f"Initialized Cerebras service with model: {self.model}")

    async def _acquire_rate_limit(self, estimated_tokens: int = 0) -> None:
        """
        Acquire rate limit permission before making request

        Args:
            estimated_tokens: Estimated token usage for this request
        """
        try:
            await self.rate_limiter.acquire(
                provider="cerebras",
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

    def _record_actual_usage(self, response: Any) -> None:
        """Record actual token usage from response"""
        if hasattr(response, 'usage') and response.usage:
            total_tokens = response.usage.total_tokens
            if self.verbose:
                logger.info(
                    f"Cerebras usage: {response.usage.prompt_tokens} prompt + "
                    f"{response.usage.completion_tokens} completion = {total_tokens} total"
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
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> str:
        """
        Complete a prompt with automatic rate limiting

        Args:
            prompt: The prompt to complete
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            tools: Optional tool definitions (will be normalized)
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
                        logger.info("Cache hit for Cerebras completion")
                    return cached

            # Acquire rate limit
            estimated_tokens = self._estimate_tokens(prompt, max_tokens)
            await self._acquire_rate_limit(estimated_tokens)

            # NORMALIZE tools for Cerebras compatibility
            normalized_tools = normalize_tools_for_cerebras(tools)

            # Make API call
            if self.verbose:
                logger.info(f"Calling Cerebras API: {self.model}, max_tokens={max_tokens}")
                if normalized_tools:
                    logger.info(f"Using {len(normalized_tools)} normalized tools")
                    logger.debug(f"Normalized tools: {normalized_tools}")

            # Remove any tool-related or strict parameters from kwargs
            kwargs_clean = {k: v for k, v in kwargs.items() if k not in ['strict']}

            # Pass normalized tools to API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                tools=normalized_tools,  # Pass normalized tools
                **kwargs_clean
            )

            # Record actual usage
            self._record_actual_usage(response)

            result = response.choices[0].message.content

            # Cache the result
            if self.cache and result:
                await self.cache.set(cache_key, result)

            return result or ""

        except Exception as e:
            logger.error(f"Cerebras API error: {str(e)}")
            raise AIServiceError(f"Failed to get Cerebras completion: {str(e)}", e)

    async def stream(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream completion tokens with rate limiting

        Args:
            prompt: The prompt to complete
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            tools: Optional tool definitions (will be normalized)
            **kwargs: Additional arguments

        Yields:
            Completion text chunks
        """
        try:
            # Acquire rate limit
            estimated_tokens = self._estimate_tokens(prompt, max_tokens)
            await self._acquire_rate_limit(estimated_tokens)

            # NORMALIZE tools for Cerebras compatibility
            normalized_tools = normalize_tools_for_cerebras(tools)

            # Make streaming call
            if self.verbose:
                logger.info(f"Streaming from Cerebras API: {self.model}")
                if normalized_tools:
                    logger.info(f"Using {len(normalized_tools)} normalized tools")

            # Remove any tool-related or strict parameters from kwargs
            kwargs_clean = {k: v for k, v in kwargs.items() if k not in ['strict']}

            # Pass normalized tools to API
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                tools=normalized_tools,  # Pass normalized tools
                **kwargs_clean
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Cerebras streaming error: {str(e)}")
            raise AIServiceError(f"Failed to stream Cerebras completion: {str(e)}", e)

    async def analyze_perfume(
        self,
        name: str,
        ingredients: list,
        concentration: float = 15.0
    ) -> Dict[str, Any]:
        """Analyze a perfume composition using Cerebras AI"""

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
        """Post-validate AI response (same as OpenAI service)"""

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
        """Suggest formula modifications using Cerebras"""

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
        """Suggest ingredient pairings using Cerebras"""

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
            result = json.loads(response)
            if dosage_info:
                result["validated_dosage"] = dosage_info
            return result
        except json.JSONDecodeError:
            return {"raw_pairings": response}

    def get_usage_stats(self) -> Dict:
        """Get rate limit usage statistics"""
        return self.rate_limiter.get_usage("cerebras")
