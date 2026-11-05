from __future__ import annotations

from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.repository import BaseRepository
from app.modules.editoriales.models import Editorial


class EditorialRepository(BaseRepository[Editorial]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Editorial)

    async def get_by_nombre(self, nombre: str) -> Editorial | None:
        stmt = select(Editorial).where(Editorial.nombre == nombre)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
