"""DeepSeek service implementation with OpenAI-compatible API"""

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

logger = get_logger(__name__)


class DeepSeekService(BaseAIService):
    """DeepSeek API service with OpenAI-compatible endpoint, retry logic, and chemistry validation"""

    def __init__(self, cache: Optional[Any] = None):
        settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
        self.model = settings.DEEPSEEK_MODEL
        self.cache = cache
        self.settings = settings
        self.context_builder = ContextBuilder()
        self.validator = ChemistryValidator()

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
        """Complete a prompt with retry logic"""
        try:
            # Check cache first
            if self.cache:
                cached = await self.cache.get(prompt)
                if cached:
                    logger.info("Cache hit for AI completion")
                    return cached

            # Call DeepSeek API (OpenAI-compatible)
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            result = response.choices[0].message.content

            # Cache the result
            if self.cache and result:
                await self.cache.set(prompt, result)

            return result or ""

        except Exception as e:
            logger.error(f"DeepSeek API error: {str(e)}")
            raise AIServiceError(f"Failed to get AI completion: {str(e)}", e)

    async def stream(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream completions from DeepSeek API"""
        try:
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
            logger.error(f"DeepSeek streaming error: {str(e)}")
            raise AIServiceError(f"Streaming failed: {str(e)}", e)

    async def analyze_perfume(self, formula_json: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a perfume formula"""
        context = await self.context_builder.build_formula_context(formula_json)
        prompt = ANALYZE_PERFUME_PROMPT.format(
            formula_json=json.dumps(formula_json, indent=2),
            context=context
        )

        response = await self.complete(prompt, max_tokens=2000)
        return {"analysis": response}

    async def suggest_ingredient_pairings(self, ingredients: List[str], context: str = "") -> Dict[str, Any]:
        """Suggest ingredient pairings"""
        prompt = INGREDIENT_PAIRING_PROMPT.format(
            ingredients=", ".join(ingredients),
            context=context
        )

        response = await self.complete(prompt)
        return {"pairings": response}

    async def suggest_modifications(self, formula_json: Dict[str, Any], goal: str) -> Dict[str, Any]:
        """Suggest formula modifications"""
        prompt = SUGGEST_MODIFICATIONS_PROMPT.format(
            formula_json=json.dumps(formula_json, indent=2),
            goal=goal
        )

        response = await self.complete(prompt, max_tokens=2000)
        return {"suggestions": response}

    async def validate_chemistry(self, formula_json: Dict[str, Any]) -> Dict[str, Any]:
        """Validate chemistry of a formula"""
        validation_report = await self.validator.validate_formula(formula_json)
        return validation_report

    async def health_check(self) -> Dict[str, Any]:
        """Check if DeepSeek API is available"""
        try:
            # Simple test request
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=10,
                temperature=0.7
            )

            if response and response.choices:
                return {
                    "status": "healthy",
                    "provider": "deepseek",
                    "model": self.model
                }
            else:
                return {
                    "status": "unhealthy",
                    "provider": "deepseek",
                    "error": "Empty response"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": "deepseek",
                "error": str(e)
            }
