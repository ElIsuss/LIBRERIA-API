from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.modules.clientes import schemas, service

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
