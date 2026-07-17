"""Base repository pattern for database operations"""

from typing import Any, Dict, Generic, List, Optional, TypeVar, cast

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """Generic repository providing common database operations"""

    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: int) -> Optional[ModelType]:
        """Get a single entity by ID"""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None
    ) -> List[ModelType]:
        """Get all entities with pagination"""
        query = select(self.model).offset(skip).limit(limit)

        if order_by:
            query = query.order_by(order_by)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """Create a new entity"""
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(
        self,
        id: int,
        obj_in: Dict[str, Any]
    ) -> Optional[ModelType]:
        """Update an existing entity"""
        db_obj = await self.get(id)
        if not db_obj:
            return None

        for key, value in obj_in.items():
            if hasattr(db_obj, key):
                setattr(db_obj, key, value)

        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, id: int) -> bool:
        """Delete an entity by ID"""
        result = cast(
            CursorResult[Any],
            await self.session.execute(
                delete(self.model).where(self.model.id == id)
            ),
        )
        await self.session.commit()
        return result.rowcount > 0

    async def count(self) -> int:
        """Count total entities"""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()

    async def exists(self, id: int) -> bool:
        """Check if entity exists"""
        result = await self.session.execute(
            select(self.model.id).where(self.model.id == id)
        )
        return result.scalar_one_or_none() is not None
