from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import func, select
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: type[T]):
        self.session = session
        self.model = model

    async def get_by_id(self, item_id: Any, *, options: Sequence[Any] = ()) -> T | None:
        stmt = select(self.model).where(self.model.id == item_id)
        for option in options:
            stmt = stmt.options(option)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        filters: Sequence[Any] = (),
        order_by: Any | None = None,
        page: int | None = None,
        size: int | None = None,
        options: Sequence[Any] = (),
    ) -> list[T]:
        stmt = select(self.model)
        for filter_ in filters:
            stmt = stmt.where(filter_)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        if page is not None and size is not None:
            stmt = stmt.offset((page - 1) * size).limit(size)
        for option in options:
            stmt = stmt.options(option)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, *, filters: Sequence[Any] = ()) -> int:
        stmt = select(func.count()).select_from(self.model)
        for filter_ in filters:
            stmt = stmt.where(filter_)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def add(self, instance: T) -> T:
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(self, instance: T) -> T:
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def delete(self, item_id: Any) -> T | None:
        instance = await self.get_by_id(item_id)
        if instance is None:
            return None
        self.session.delete(instance)
        await self.session.flush()
        return instance


class SoftDeleteRepository(BaseRepository[T]):
    async def get_by_id(self, item_id: Any, *, include_deleted: bool = False, options: Sequence[Any] = ()) -> T | None:
        stmt = select(self.model).where(self.model.id == item_id)
        if not include_deleted and hasattr(self.model, "borrado_en"):
            stmt = stmt.where(getattr(self.model, "borrado_en").is_(None))
        for option in options:
            stmt = stmt.options(option)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        filters: Sequence[Any] = (),
        order_by: Any | None = None,
        page: int | None = None,
        size: int | None = None,
        options: Sequence[Any] = (),
        include_deleted: bool = False,
    ) -> list[T]:
        stmt = select(self.model)
        if not include_deleted and hasattr(self.model, "borrado_en"):
            stmt = stmt.where(getattr(self.model, "borrado_en").is_(None))
        for filter_ in filters:
            stmt = stmt.where(filter_)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        if page is not None and size is not None:
            stmt = stmt.offset((page - 1) * size).limit(size)
        for option in options:
            stmt = stmt.options(option)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, *, filters: Sequence[Any] = (), include_deleted: bool = False) -> int:
        stmt = select(func.count()).select_from(self.model)
        if not include_deleted and hasattr(self.model, "borrado_en"):
            stmt = stmt.where(getattr(self.model, "borrado_en").is_(None))
        for filter_ in filters:
            stmt = stmt.where(filter_)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def get_by_id_including_deleted(self, item_id: Any, *, options: Sequence[Any] = ()) -> T | None:
        return await self.get_by_id(item_id, include_deleted=True, options=options)

    async def soft_delete(self, item_id: Any, *, borrado_en: datetime | None = None) -> T | None:
        if not hasattr(self.model, "borrado_en"):
            raise AttributeError(f"{self.model.__name__} does not implement soft delete.")

        instance = await self.get_by_id_including_deleted(item_id)
        if instance is None:
            return None

        setattr(instance, "borrado_en", borrado_en or datetime.now(timezone.utc))
        await self.session.flush()
        return instance
