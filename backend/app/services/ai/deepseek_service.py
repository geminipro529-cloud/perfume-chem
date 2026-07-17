"""DeepSeek service implementation with OpenAI-compatible API"""

import json
from typing import Any, AsyncGenerator, Dict, List, Optional, cast

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
                    return cast(str, cached)

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

    async def analyze_perfume(
        self,
        name: str,
        ingredients: list[dict[str, Any]],
        concentration: float = 15.0,
    ) -> Dict[str, Any]:
        """Analyze a perfume formula with the shared chemistry context."""
        context = self.context_builder.build_context(
            query=name,
            ingredients=ingredients,
            include_validation=True,
        )
        ingredients_text = "\n".join(
            f"- {item.get('name', 'Unknown')}: {item.get('percentage', 0)}%"
            for item in ingredients
        )
        prompt = ANALYZE_PERFUME_PROMPT.substitute(
            name=name,
            concentration=concentration,
            ingredients=ingredients_text,
            dosage_guidelines=context.get("dosage_guidelines", "N/A"),
            inventory_context=context.get("inventory", "N/A"),
            knowledge_context=context.get("relevant_knowledge", "N/A"),
            formulation_context=context.get("similar_formulations", "N/A"),
            validation_context=context.get("validation_context", "No pre-validation"),
        )

        response = await self.complete(prompt, max_tokens=2000)
        try:
            return cast(Dict[str, Any], json.loads(response))
        except json.JSONDecodeError:
            return {"raw_analysis": response}

    async def suggest_ingredient_pairings(self, ingredients: List[str], context: str = "") -> Dict[str, Any]:
        """Backward-compatible plural pairing entry point."""
        return await self.suggest_pairings(", ".join(ingredients))

    async def suggest_pairings(
        self,
        ingredient: str,
        cas_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Suggest ingredient pairings using the shared prompt contract."""
        context = self.context_builder.build_context(
            query=ingredient,
            ingredients=None,
            include_validation=False,
        )
        dosage = self.validator.get_dosage_guidelines(ingredient)
        dosage_text = json.dumps(dosage, sort_keys=True) if dosage else "N/A"
        prompt = INGREDIENT_PAIRING_PROMPT.substitute(
            ingredient=ingredient,
            cas_number=cas_number or "N/A",
            dosage_guidelines=f"{dosage_text}\n\n{context.get('dosage_guidelines', 'N/A')}",
            inventory_context=context.get("inventory", "N/A"),
        )

        response = await self.complete(prompt)
        try:
            return cast(Dict[str, Any], json.loads(response))
        except json.JSONDecodeError:
            return {"raw_pairings": response}

    async def suggest_modifications(self, formula: Dict[str, Any], goal: str) -> Dict[str, Any]:
        """Suggest formula modifications"""
        ingredients = cast(list[dict[str, Any]], formula.get("ingredients", []))
        context = self.context_builder.build_context(
            query=goal,
            ingredients=ingredients,
            include_validation=True,
        )
        prompt = SUGGEST_MODIFICATIONS_PROMPT.substitute(
            formula=json.dumps(formula, indent=2),
            goal=goal,
            dosage_guidelines=context.get("dosage_guidelines", "N/A"),
            inventory_context=context.get("inventory", "N/A"),
            knowledge_context=context.get("relevant_knowledge", "N/A"),
        )

        response = await self.complete(prompt, max_tokens=2000)
        try:
            return cast(Dict[str, Any], json.loads(response))
        except json.JSONDecodeError:
            return {"raw_suggestions": response}

    async def validate_chemistry(self, formula_json: Dict[str, Any]) -> Dict[str, Any]:
        """Validate chemistry of a formula"""
        ingredients = cast(list[dict[str, Any]], formula_json.get("ingredients", []))
        issues = self.validator.validate_formula(ingredients)
        return {
            "issues": [issue.to_dict() for issue in issues],
            "total_issues": len(issues),
        }

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
