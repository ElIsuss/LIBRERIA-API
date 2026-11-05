from __future__ import annotations

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.modules.clientes.repository import ClienteRepository
from app.modules.libros.unit_of_work import LibrosUnitOfWork
from app.modules.usuarios.repository import AsignacionRolRepository
from app.modules.ventas.repository import VentaRepository


class VentasUnitOfWork(LibrosUnitOfWork):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.ventas = VentaRepository(session)
        self.clientes = ClienteRepository(session)
        self.roles = AsignacionRolRepository(session)


async def get_ventas_uow(
    session: AsyncSession = Depends(get_session),
) -> VentasUnitOfWork:
    return VentasUnitOfWork(session)
