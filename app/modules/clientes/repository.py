from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.repository import BaseRepository
from app.modules.clientes.models import Cliente, PerfilCliente


class ClienteRepository(BaseRepository[Cliente]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Cliente)

    def _opciones_detalle(self) -> Sequence[Any]:
        return (joinedload(Cliente.perfil),)

    async def get_detalle(self, cliente_id: int) -> Cliente | None:
        return await self.get_by_id(cliente_id, options=self._opciones_detalle())

    async def get_by_email(self, email: str) -> Cliente | None:
        stmt = select(Cliente).where(Cliente.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_usuario_id(self, usuario_id: int) -> Cliente | None:
        stmt = select(Cliente).where(Cliente.usuario_id == usuario_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class PerfilClienteRepository(BaseRepository[PerfilCliente]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, PerfilCliente)
