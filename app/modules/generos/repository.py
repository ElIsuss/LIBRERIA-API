from __future__ import annotations

from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.repository import BaseRepository
from app.modules.generos.models import Genero


class GeneroRepository(BaseRepository[Genero]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Genero)

    async def get_by_nombre(self, nombre: str) -> Genero | None:
        stmt = select(Genero).where(Genero.nombre == nombre)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
