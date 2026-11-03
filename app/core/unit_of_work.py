from __future__ import annotations

from typing import Type

from sqlmodel.ext.asyncio.session import AsyncSession


class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self) -> "UnitOfWork":
        return self

    async def __aexit__(self, exc_type: Type[BaseException] | None, exc: BaseException | None, tb: object) -> bool:
        if exc_type is None:
            await self.session.commit()
        else:
            await self.session.rollback()
        return False

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
