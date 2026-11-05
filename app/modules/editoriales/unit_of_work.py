from __future__ import annotations

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.unit_of_work import UnitOfWork
from app.modules.editoriales.repository import EditorialRepository


class EditorialUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.editoriales = EditorialRepository(session)


async def get_editorial_uow(
    session: AsyncSession = Depends(get_session),
) -> EditorialUnitOfWork:
    return EditorialUnitOfWork(session)
