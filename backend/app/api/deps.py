"""API dependency injection"""

from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db_session import get_session
from app.services.ai.base import BaseAIService
from app.services.ai.factory import create_ai_service, get_model_selector


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency"""
    async with get_session() as session:
        yield session


async def get_ai_service(
    model: Optional[str] = None,
    force_provider: Optional[str] = None
) -> BaseAIService:
    """
    Get AI service dependency with automatic provider detection

    Automatically routes to appropriate provider based on model name:
    - Cerebras models: llama3.1-8b, llama3.1-70b, etc.
    - Baseten models: kimi-k2-thinking, other Baseten-hosted models
    - OpenAI models: gpt-4, gpt-3.5-turbo, etc.

    Args:
        model: Model name (e.g., "llama3.1-8b", "gpt-4", "kimi-k2-thinking")
               If None, uses default from settings
        force_provider: Force specific provider (overrides auto-detection)

    Returns:
        Appropriate AI service instance
    """
    return create_ai_service(
        model=model,
        cache=None,
        verbose=True,
        force_provider=force_provider
    )


def get_model_selector_dep() -> dict:
    """Get model selector configuration for UI"""
    return get_model_selector()


def get_settings_dep() -> Settings:
    """Get settings dependency"""
    return get_settings()
