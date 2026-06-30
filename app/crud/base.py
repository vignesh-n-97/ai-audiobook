"""Generic async CRUD base class — mirrors the akomplice CRUDBase pattern."""

from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)


class CRUDBase(Generic[ModelT, CreateSchemaT]):
    """Generic CRUD operations for a SQLAlchemy model."""

    def __init__(self, model: type[ModelT]) -> None:
        self.model = model

    async def get(self, db: AsyncSession, id: uuid.UUID) -> ModelT | None:
        result = await db.execute(select(self.model).where(self.model.id == id))  # type: ignore[attr-defined]
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> list[ModelT]:
        result = await db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaT) -> ModelT:
        obj = self.model(**obj_in.model_dump())
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    async def remove(self, db: AsyncSession, *, id: uuid.UUID) -> ModelT | None:
        obj = await self.get(db, id)
        if obj is not None:
            await db.delete(obj)
            await db.commit()
        return obj
