"""
Ollama AI service for local/remote Ollama instances

Uses the OpenAI-compatible API endpoint exposed by Ollama (http://localhost:11434/v1).
Configure via environment variables:
- OLLAMA_BASE_URL: Base URL for Ollama API (default: http://localhost:11434/v1)
- OLLAMA_MODEL: Model name to use (default: hf.co/PsiPi/ehartford_dolphin-2.5-mixtral-8x7b-GGUF:Q3_K_L)

Rate limiting: Uses the 'ollama' provider configuration in rate_limits.yaml.
"""

import json
from typing import AsyncGenerator, Optional, Dict, Any, List
from openai import AsyncOpenAI
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.services.ai.base import BaseAIService
from app.services.ai.prompts.perfume_analysis import (
    ANALYZE_PERFUME_PROMPT,
    SUGGEST_MODIFICATIONS_PROMPT,
    INGREDIENT_PAIRING_PROMPT
)
from app.services.context_builder import ContextBuilder
from app.services.chemistry_validator import ChemistryValidator
from app.core.config import get_settings
from app.core.exceptions import AIServiceError
from app.core.logging import get_logger
from app.utils.api_rate_limiter import get_rate_limiter

logger = get_logger(__name__)


def normalize_tools_for_ollama(tools: Optional[List[Dict]] = None) -> Optional[List[Dict]]:
    """
    Normalize tools for Ollama API compatibility
    
    Ollama's OpenAI-compatible endpoint may have limitations with tools.
    This function ensures tools are properly formatted.
    
    Args:
        tools: List of tool definitions
    
    Returns:
        Normalized tools, or None
    """
    if not tools:
        return None
    
    import copy
    normalized = []
    
    for tool in tools:
        # Deep copy to avoid modifying original
        tool_copy = copy.deepcopy(tool)
        
        # Ensure function has 'strict' parameter set to False
        if 'function' in tool_copy:
            tool_copy['function']['strict'] = False
        
        normalized.append(tool_copy)
    
    return normalized


class OllamaService(BaseAIService):
    """
    Ollama AI service for local/remote Ollama instances
    
    Features:
    - Uses Ollama's OpenAI-compatible API
    - Automatic rate limiting
    - Tool normalization
    - Exponential backoff on errors
    """
    
    def __init__(self, cache: Optional[Any] = None, verbose: bool = False, model: Optional[str] = None):
        """
        Initialize Ollama service
        
        Args:
            cache: Optional cache instance
            verbose: Enable verbose logging
            model: Optional model override (defaults to OLLAMA_MODEL from config)
        """
        settings = get_settings()
        
        # Use provided model or fall back to config
        self.model = model or settings.OLLAMA_MODEL
        self.cache = cache
        self.settings = settings
        self.verbose = verbose
        
        logger.info(f"Initializing Ollama service with model: {self.model}")
        
        # Create custom HTTP client
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout=60.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
        self.client = AsyncOpenAI(
            api_key="ollama",  # Ollama doesn't require API key, but client expects something
            base_url=settings.OLLAMA_BASE_URL,
            http_client=http_client
        )
        
        # Initialize rate limiter
        config_path = settings.RATE_LIMIT_CONFIG_PATH
        if not config_path:
            from pathlib import Path
            config_path = str(Path(__file__).parent.parent.parent / "config" / "rate_limits.yaml")
        
        self.rate_limiter = get_rate_limiter(config_path)
        
        # Initialize context builder and validator
        self.context_builder = ContextBuilder()
        self.validator = ChemistryValidator()
        
        logger.info(f"Ollama service ready (base_url: {settings.OLLAMA_BASE_URL})")
    
    async def _acquire_rate_limit(self, estimated_tokens: int = 0) -> None:
        """
        Acquire rate limit permission before making request
        
        Args:
            estimated_tokens: Estimated token usage for this request
        """
        try:
            await self.rate_limiter.acquire(
                provider="ollama",
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
        Complete a prompt with Ollama
        
        Args:
            prompt: The prompt to complete
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            tools: Optional tool definitions
            **kwargs: Additional arguments
        
        Returns:
            Completion text
        """
        try:
            # Check cache first
            cache_key = f"ollama:{prompt}:{max_tokens}:{temperature}"
            if self.cache:
                cached = await self.cache.get(cache_key)
                if cached:
                    if self.verbose:
                        logger.info("Cache hit for Ollama completion")
                    return cached
            
            # Acquire rate limit
            estimated_tokens = self._estimate_tokens(prompt, max_tokens)
            await self._acquire_rate_limit(estimated_tokens)
            
            # Normalize tools
            normalized_tools = normalize_tools_for_ollama(tools)
            
            # Make API call
            if self.verbose:
                logger.info(f"Calling Ollama API: {self.model}, max_tokens={max_tokens}")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                tools=normalized_tools,
                **kwargs
            )
            
            result = response.choices[0].message.content or ""
            
            # Record usage if available
            if hasattr(response, 'usage') and response.usage:
                logger.debug(f"Ollama usage: {response.usage.total_tokens} tokens")
            
            # Cache the result
            if self.cache and result:
                await self.cache.set(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Ollama API error: {str(e)}")
            raise AIServiceError(f"Failed to get Ollama completion: {str(e)}", e)
    
    async def stream(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream completion tokens with Ollama
        
        Args:
            prompt: The prompt to complete
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            tools: Optional tool definitions
            **kwargs: Additional arguments
        
        Yields:
            Completion text chunks
        """
        try:
            # Acquire rate limit
            estimated_tokens = self._estimate_tokens(prompt, max_tokens)
            await self._acquire_rate_limit(estimated_tokens)
            
            # Normalize tools
            normalized_tools = normalize_tools_for_ollama(tools)
            
            if self.verbose:
                logger.info(f"Streaming from Ollama API: {self.model}")
            
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                tools=normalized_tools,
                **kwargs
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Ollama streaming error: {str(e)}")
            raise AIServiceError(f"Failed to stream Ollama completion: {str(e)}", e)
    
    async def analyze_perfume(
        self,
        name: str,
        ingredients: list,
        concentration: float = 15.0
    ) -> Dict[str, Any]:
        """Analyze a perfume composition using Ollama AI"""
        
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
        """Suggest formula modifications using Ollama"""
        
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
        """Suggest ingredient pairings using Ollama"""
        
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
        return self.rate_limiter.get_usage("ollama")