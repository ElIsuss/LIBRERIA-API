from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import Depends
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.repository import ClienteRepository
from app.modules.usuarios.models import IntentoAcceso
from app.modules.usuarios.repository import (
    AsignacionRolRepository,
    EventoSeguridadRepository,
    IntentoAccesoRepository,
    UsuarioRepository,
)


class UsuarioUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.usuarios = UsuarioRepository(session)
        self.roles = AsignacionRolRepository(session)
        self.intentos = IntentoAccesoRepository(session)
        self.eventos = EventoSeguridadRepository(session)
        self.clientes = ClienteRepository(session)


async def get_usuario_uow(session: AsyncSession = Depends(get_session)) -> UsuarioUnitOfWork:
    return UsuarioUnitOfWork(session)


# ==============================================================================
# AUDITORÍA DE INTENTO_ACCESO EN SESIÓN Y TRANSACCIÓN INDEPENDIENTES (Ejercicio 7)
#
# 1. Por qué no usa el UnitOfWork de la petición:
#    El UnitOfWork de la petición está atado a la sesión y transacción del ciclo de vida
#    de la solicitud HTTP. Si el intento de login resulta fallido, el flujo termina
#    levantando una excepción HTTPException(401) que dispara un rollback de la transacción.
#
# 2. Qué pasaría con el límite de intentos si compartiera transacción:
#    Si el registro en `intento_acceso` compartiera la transacción del UnitOfWork de la petición,
#    el rollback provocado por el error 401 desharía también la inserción del intento fallido.
#    Como consecuencia, la base de datos nunca acumularía el historial de fallos y el rate
#    limiting de 5 intentos en 60 segundos (RN-07) jamás podría detectar un ataque de fuerza bruta.
#
# 3. Qué fila queda confirmada aunque el resto falle:
#    Esta función abre su propia sesión asincrónica aislada desde `session_factory` y ejecuta
#    un `commit()` exclusivo e inmediato. De esta forma, la fila `IntentoAcceso(email, ip, exito, cuando)`
#    queda definitivamente guardada y persistida en PostgreSQL, incluso si la petición responde 401.
# ==============================================================================
async def registrar_intento_acceso(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    email: str,
    ip: str,
    exito: bool,
) -> IntentoAcceso:
    async with session_factory() as audit_session:
        intento = IntentoAcceso(
            email=email,
            ip=ip,
            exito=exito,
            cuando=datetime.now(timezone.utc),
        )
        audit_session.add(intento)
        await audit_session.commit()
        await audit_session.refresh(intento)
        return intento
