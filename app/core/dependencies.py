from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.security import decode_access_token
from app.modules.usuarios.models import AsignacionRol, Usuario


async def get_usuario_actual(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Usuario:
    """
    Recupera al usuario autenticado leyendo exclusivamente la cookie 'access_token'.
    Usa la misma AsyncSession de la petición (Depends(get_session)) para compartir
    la conexión de BD con el UnitOfWork sin consumir conexiones adicionales (DD-02).
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se encontró la cookie de autenticación",
        )

    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )

    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identificador de usuario inválido en el token",
        )

    usuario = await session.get(Usuario, user_id)
    if usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )

    return usuario


async def verificar_password_actualizada(
    usuario: Usuario = Depends(get_usuario_actual),
) -> Usuario:
    """
    Dependencia montada a nivel global en el Grupo Protegido (DD-01).
    Bloquea el acceso a todas las rutas protegidas si el usuario tiene
    pendiente cambiar su contraseña provisoria (RN-06).
    """
    if usuario.debe_cambiar_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debe cambiar su contraseña provisoria antes de acceder a las rutas protegidas",
        )
    return usuario


def requiere_rol(*roles_permitidos: str) -> Callable:
    """
    Genera una dependencia FastAPI que verifica en tiempo real contra PostgreSQL
    si el usuario autenticado posee al menos uno de los roles solicitados vigente (RN-04).
    """

    async def _verificar_rol(
        usuario: Usuario = Depends(get_usuario_actual),
        session: AsyncSession = Depends(get_session),
    ) -> Usuario:
        now = datetime.now(timezone.utc)
        stmt = (
            select(AsignacionRol.rol)
            .where(
                AsignacionRol.usuario_id == usuario.id,
                AsignacionRol.rol.in_(roles_permitidos),
                AsignacionRol.revocada_en.is_(None),
                or_(AsignacionRol.vence_en.is_(None), AsignacionRol.vence_en > now),
            )
            .limit(1)
        )
        result = await session.execute(stmt)
        rol_vigente = result.scalar_one_or_none()

        if not rol_vigente:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permisos insuficientes. Requiere uno de los siguientes roles: {', '.join(roles_permitidos)}",
            )
        return usuario

    return _verificar_rol
