from __future__ import annotations

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.unit_of_work import UnitOfWork
from app.modules.generos.repository import GeneroRepository


class GeneroUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.generos = GeneroRepository(session)


async def get_genero_uow(
    session: AsyncSession = Depends(get_session),
) -> GeneroUnitOfWork:
    return GeneroUnitOfWork(session)
