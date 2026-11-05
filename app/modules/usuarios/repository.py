from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Sequence

from sqlalchemy import func, select, and_, or_
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.repository import BaseRepository
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    IntentoAcceso,
    Usuario,
)


class UsuarioRepository(BaseRepository[Usuario]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Usuario)

    async def get_by_email(self, email: str) -> Usuario | None:
        stmt = select(Usuario).where(Usuario.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class AsignacionRolRepository(BaseRepository[AsignacionRol]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, AsignacionRol)

    async def get_roles_vigentes(self, usuario_id: int) -> list[str]:
        """Consulta en la BD los roles que no están revocados y cuya fecha de vencimiento es futura o nula."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(AsignacionRol.rol)
            .where(
                AsignacionRol.usuario_id == usuario_id,
                AsignacionRol.revocada_en.is_(None),
                or_(AsignacionRol.vence_en.is_(None), AsignacionRol.vence_en > now),
            )
            .distinct()
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_asignaciones_por_usuario(self, usuario_id: int) -> list[AsignacionRol]:
        stmt = select(AsignacionRol).where(AsignacionRol.usuario_id == usuario_id).order_by(AsignacionRol.desde.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_asignacion_abierta(self, usuario_id: int, rol: str) -> AsignacionRol | None:
        stmt = select(AsignacionRol).where(
            AsignacionRol.usuario_id == usuario_id,
            AsignacionRol.rol == rol,
            AsignacionRol.revocada_en.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class IntentoAccesoRepository(BaseRepository[IntentoAcceso]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, IntentoAcceso)

    async def contar_fallos_recientes(
        self,
        email: str,
        ip: str,
        ventana_segundos: int = 60,
    ) -> tuple[int, datetime | None]:
        """
        Cuenta los intentos fallidos en los últimos `ventana_segundos` posteriores al último éxito (RN-07).
        Devuelve (cantidad_fallos, primer_fallo_de_la_serie).
        """
        now = datetime.now(timezone.utc)
        limite_tiempo = now - timedelta(seconds=ventana_segundos)

        # 1. Buscar si hubo un login exitoso reciente en la ventana
        stmt_exito = (
            select(func.max(IntentoAcceso.cuando))
            .where(
                IntentoAcceso.email == email,
                IntentoAcceso.ip == ip,
                IntentoAcceso.exito.is_(True),
                IntentoAcceso.cuando >= limite_tiempo,
            )
        )
        res_exito = await self.session.execute(stmt_exito)
        ultimo_exito = res_exito.scalar_one_or_none()

        inicio_ventana = limite_tiempo
        if ultimo_exito is not None and ultimo_exito > inicio_ventana:
            inicio_ventana = ultimo_exito

        # 2. Contar fallos y obtener el primer fallo posterior al inicio de ventana
        condiciones = [
            IntentoAcceso.email == email,
            IntentoAcceso.ip == ip,
            IntentoAcceso.exito.is_(False),
            IntentoAcceso.cuando >= inicio_ventana,
        ]

        stmt_count = select(func.count(), func.min(IntentoAcceso.cuando)).where(and_(*condiciones))
        result = await self.session.execute(stmt_count)
        row = result.one()
        cantidad_fallos = int(row[0]) if row[0] is not None else 0
        primer_fallo = row[1]

        return cantidad_fallos, primer_fallo


class EventoSeguridadRepository(BaseRepository[EventoSeguridad]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, EventoSeguridad)

    async def registrar(self, actor: str, accion: str) -> EventoSeguridad:
        evento = EventoSeguridad(
            actor=actor,
            accion=accion,
            cuando=datetime.now(timezone.utc),
        )
        return await self.add(evento)
