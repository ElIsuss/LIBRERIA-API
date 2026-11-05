from __future__ import annotations

from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.repository import BaseRepository
from app.modules.autores.models import Autor


class AutorRepository(BaseRepository[Autor]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Autor)

    async def get_by_nombre(self, nombre: str) -> Autor | None:
        stmt = select(Autor).where(Autor.nombre == nombre)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
