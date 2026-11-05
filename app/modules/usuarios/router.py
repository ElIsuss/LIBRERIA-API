from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import (
    clear_auth_cookie,
    decode_access_token,
    set_auth_cookie,
)
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.schemas import (
    CambiarPasswordRequest,
    LoginRequest,
    LoginResponse,
    MensajeResponse,
    RegistroRequest,
    UsuarioAuthResponse,
    YoResponse,
)
from app.modules.usuarios.service import UsuarioService
from app.modules.usuarios.unit_of_work import (
    UsuarioUnitOfWork,
    get_usuario_uow,
)

router = APIRouter(prefix="/auth", tags=["auth"])


async def get_current_user_from_cookie(
    request: Request,
    uow: UsuarioUnitOfWork = Depends(get_usuario_uow),
) -> tuple[Usuario, dict[str, Any]]:
    """Extrae el token JWT de la cookie access_token, lo valida y recupera al usuario activo."""
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

    usuario = await uow.usuarios.get_by_id(user_id)
    if usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )

    return usuario, payload


@router.post(
    "/registro",
    response_model=UsuarioAuthResponse,
    status_code=status.HTTP_201_CREATED,
)
async def registrar_cliente(
    request: RegistroRequest,
    uow: UsuarioUnitOfWork = Depends(get_usuario_uow),
) -> UsuarioAuthResponse:
    return await UsuarioService.registrar_cliente(request, uow)


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
async def login(
    request: LoginRequest,
    req: Request,
    res: Response,
    uow: UsuarioUnitOfWork = Depends(get_usuario_uow),
) -> LoginResponse:
    session_factory: async_sessionmaker[AsyncSession] = req.app.state.session_factory
    dummy_hash: str = getattr(req.app.state, "dummy_hash", "")
    client_ip = req.client.host if req.client else "127.0.0.1"

    token, debe_cambiar_password, expira = await UsuarioService.login(
        request=request,
        client_ip=client_ip,
        session_factory=session_factory,
        uow=uow,
        dummy_hash=dummy_hash,
    )

    set_auth_cookie(res, token)
    return LoginResponse(
        mensaje="Sesión iniciada",
        debe_cambiar_password=debe_cambiar_password,
        expira_en_segundos=expira,
    )


@router.post(
    "/logout",
    response_model=MensajeResponse,
    status_code=status.HTTP_200_OK,
)
async def logout(res: Response) -> MensajeResponse:
    clear_auth_cookie(res)
    return MensajeResponse(mensaje="Sesión cerrada exitosamente")


@router.get(
    "/yo",
    response_model=YoResponse,
    status_code=status.HTTP_200_OK,
)
async def obtener_perfil_yo(
    auth_data: tuple[Usuario, dict[str, Any]] = Depends(get_current_user_from_cookie),
    uow: UsuarioUnitOfWork = Depends(get_usuario_uow),
) -> YoResponse:
    usuario, payload = auth_data
    roles_token = payload.get("roles", [])
    return await UsuarioService.obtener_perfil_yo(usuario, roles_token, uow)


@router.post(
    "/cambiar-password",
    response_model=MensajeResponse,
    status_code=status.HTTP_200_OK,
)
async def cambiar_password(
    request: CambiarPasswordRequest,
    auth_data: tuple[Usuario, dict[str, Any]] = Depends(get_current_user_from_cookie),
    uow: UsuarioUnitOfWork = Depends(get_usuario_uow),
) -> MensajeResponse:
    usuario, _ = auth_data
    return await UsuarioService.cambiar_password(usuario, request, uow)
