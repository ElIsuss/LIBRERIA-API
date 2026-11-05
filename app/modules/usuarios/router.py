from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.dependencies import get_usuario_actual, requiere_rol
from app.core.paginacion import Page
from app.core.security import (
    clear_auth_cookie,
    decode_access_token,
    set_auth_cookie,
)
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.schemas import (
    AsignacionRolResponse,
    AsignarRolRequest,
    CambiarPasswordRequest,
    EventoSeguridadRead,
    LoginRequest,
    LoginResponse,
    MensajeResponse,
    RegistroRequest,
    UsuarioAuthResponse,
    UsuarioCreateRequest,
    YoResponse,
)
from app.modules.usuarios.service import UsuarioService
from app.modules.usuarios.unit_of_work import (
    UsuarioUnitOfWork,
    get_usuario_uow,
)

# Router para Grupo Abierto (/auth)
router = APIRouter(prefix="/auth", tags=["auth"])

# Routers para Grupo Protegido (/usuarios y /eventos)
usuarios_admin_router = APIRouter(
    prefix="/usuarios",
    tags=["usuarios"],
    dependencies=[Depends(requiere_rol("ADMIN"))],
)

eventos_router = APIRouter(
    prefix="/eventos",
    tags=["eventos"],
    dependencies=[Depends(requiere_rol("ADMIN"))],
)


# ------------------------------------------------------------------------------
# Endpoints de Autenticación (/auth)
# ------------------------------------------------------------------------------


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
    request: Request,
    usuario: Usuario = Depends(get_usuario_actual),
    uow: UsuarioUnitOfWork = Depends(get_usuario_uow),
) -> YoResponse:
    token = request.cookies.get("access_token", "")
    payload = decode_access_token(token) or {}
    roles_token = payload.get("roles", [])
    return await UsuarioService.obtener_perfil_yo(usuario, roles_token, uow)


@router.post(
    "/cambiar-password",
    response_model=MensajeResponse,
    status_code=status.HTTP_200_OK,
)
async def cambiar_password(
    request: CambiarPasswordRequest,
    usuario: Usuario = Depends(get_usuario_actual),
    uow: UsuarioUnitOfWork = Depends(get_usuario_uow),
) -> MensajeResponse:
    return await UsuarioService.cambiar_password(usuario, request, uow)


# ------------------------------------------------------------------------------
# Endpoints de Administración de Personal y Roles (/usuarios)
# ------------------------------------------------------------------------------


@usuarios_admin_router.post(
    "",
    response_model=UsuarioAuthResponse,
    status_code=status.HTTP_201_CREATED,
)
async def crear_personal(
    request: UsuarioCreateRequest,
    admin: Usuario = Depends(get_usuario_actual),
    uow: UsuarioUnitOfWork = Depends(get_usuario_uow),
) -> UsuarioAuthResponse:
    return await UsuarioService.crear_personal(admin, request, uow)


@usuarios_admin_router.get(
    "/{id}/roles",
    response_model=list[AsignacionRolResponse],
    status_code=status.HTTP_200_OK,
)
async def listar_roles_usuario(
    id: int,
    uow: UsuarioUnitOfWork = Depends(get_usuario_uow),
) -> list[AsignacionRolResponse]:
    return await UsuarioService.listar_roles_usuario(id, uow)


@usuarios_admin_router.post(
    "/{id}/roles",
    response_model=AsignacionRolResponse,
    status_code=status.HTTP_201_CREATED,
)
async def asignar_rol(
    id: int,
    request: AsignarRolRequest,
    admin: Usuario = Depends(get_usuario_actual),
    uow: UsuarioUnitOfWork = Depends(get_usuario_uow),
) -> AsignacionRolResponse:
    return await UsuarioService.asignar_rol(admin, id, request, uow)


@usuarios_admin_router.delete(
    "/{id}/roles/{rol}",
    response_model=MensajeResponse,
    status_code=status.HTTP_200_OK,
)
async def revocar_rol(
    id: int,
    rol: str,
    admin: Usuario = Depends(get_usuario_actual),
    uow: UsuarioUnitOfWork = Depends(get_usuario_uow),
) -> MensajeResponse:
    return await UsuarioService.revocar_rol(admin, id, rol, uow)


# ------------------------------------------------------------------------------
# Endpoints de Auditoría de Seguridad (/eventos)
# ------------------------------------------------------------------------------


@eventos_router.get(
    "",
    response_model=Page[EventoSeguridadRead],
    status_code=status.HTTP_200_OK,
)
async def listar_eventos(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    uow: UsuarioUnitOfWork = Depends(get_usuario_uow),
) -> Page[EventoSeguridadRead]:
    return await UsuarioService.listar_eventos_paginado(page=page, size=size, uow=uow)
