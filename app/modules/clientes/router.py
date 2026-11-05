from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.dependencies import requiere_rol
from app.modules.clientes import schemas, service
from app.modules.clientes.unit_of_work import (
    ClientesUnitOfWork,
    get_clientes_uow,
)
from app.modules.ventas import service as ventas_service
from app.modules.ventas.unit_of_work import VentasUnitOfWork, get_ventas_uow
from app.modules.ventas import schemas as ventas_schemas

router = APIRouter(
    prefix="/clientes",
    tags=["clientes"],
    dependencies=[Depends(requiere_rol("VENDEDOR", "ADMIN"))],
)


@router.post(
    "/",
    response_model=schemas.ClienteRead,
    status_code=status.HTTP_201_CREATED,
)
async def crear(
    datos: schemas.ClienteCreate,
    uow: ClientesUnitOfWork = Depends(get_clientes_uow),
) -> schemas.ClienteRead:
    return await service.crear_cliente(uow, datos)


@router.get("/{cliente_id}", response_model=schemas.ClienteRead)
async def obtener(
    cliente_id: int,
    uow: ClientesUnitOfWork = Depends(get_clientes_uow),
) -> schemas.ClienteRead:
    return await service.obtener_por_id(uow, cliente_id)


@router.patch("/{cliente_id}", response_model=schemas.ClienteRead)
async def actualizar(
    cliente_id: int,
    datos: schemas.ClienteUpdate,
    uow: ClientesUnitOfWork = Depends(get_clientes_uow),
) -> schemas.ClienteRead:
    return await service.actualizar(uow, cliente_id, datos)


@router.post(
    "/{cliente_id}/perfil",
    response_model=schemas.PerfilRead,
    status_code=status.HTTP_201_CREATED,
)
async def crear_perfil(
    cliente_id: int,
    datos: schemas.PerfilCreate,
    uow: ClientesUnitOfWork = Depends(get_clientes_uow),
) -> schemas.PerfilRead:
    return await service.crear_perfil(uow, cliente_id, datos)


@router.get("/{cliente_id}/ventas", response_model=list[ventas_schemas.VentaRead])
async def listar_ventas_cliente(
    cliente_id: int,
    uow: VentasUnitOfWork = Depends(get_ventas_uow),
) -> list[ventas_schemas.VentaRead]:
    return await ventas_service.listar_por_cliente(uow, cliente_id)
