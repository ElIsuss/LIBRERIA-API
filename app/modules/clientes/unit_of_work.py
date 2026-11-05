from __future__ import annotations

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.repository import (
    ClienteRepository,
    PerfilClienteRepository,
)


class ClientesUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.clientes = ClienteRepository(session)
        self.perfiles = PerfilClienteRepository(session)


async def get_clientes_uow(
    session: AsyncSession = Depends(get_session),
) -> ClientesUnitOfWork:
    return ClientesUnitOfWork(session)
