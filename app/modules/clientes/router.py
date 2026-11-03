from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.modules.clientes import schemas, service
from app.modules.ventas import schemas as ventas_schemas, service as ventas_service

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.post(
    "/",
    response_model=schemas.ClienteRead,
    status_code=status.HTTP_201_CREATED,
)
async def crear(
    datos: schemas.ClienteCreate,
    session: AsyncSession = Depends(get_session),
) -> schemas.ClienteRead:
    return await service.crear_cliente(session, datos)


@router.get("/{cliente_id}", response_model=schemas.ClienteRead)
async def obtener(
    cliente_id: int,
    session: AsyncSession = Depends(get_session),
) -> schemas.ClienteRead:
    return await service.obtener_por_id(session, cliente_id)


@router.patch("/{cliente_id}", response_model=schemas.ClienteRead)
async def actualizar(
    cliente_id: int,
    datos: schemas.ClienteUpdate,
    session: AsyncSession = Depends(get_session),
) -> schemas.ClienteRead:
    return await service.actualizar(session, cliente_id, datos)


@router.post(
    "/{cliente_id}/perfil",
    response_model=schemas.PerfilRead,
    status_code=status.HTTP_201_CREATED,
)
async def crear_perfil(
    cliente_id: int,
    datos: schemas.PerfilCreate,
    session: AsyncSession = Depends(get_session),
) -> schemas.PerfilRead:
    return await service.crear_perfil(session, cliente_id, datos)


@router.get("/{cliente_id}/ventas", response_model=list[ventas_schemas.VentaRead])
async def listar_ventas(
    cliente_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[ventas_schemas.VentaRead]:
    return await ventas_service.listar_por_cliente(session, cliente_id, limit, offset)
