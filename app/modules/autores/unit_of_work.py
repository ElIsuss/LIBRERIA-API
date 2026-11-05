from __future__ import annotations

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.unit_of_work import UnitOfWork
from app.modules.autores.repository import AutorRepository


class AutorUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.autores = AutorRepository(session)


async def get_autor_uow(
    session: AsyncSession = Depends(get_session),
) -> AutorUnitOfWork:
    return AutorUnitOfWork(session)
