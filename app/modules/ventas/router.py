from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.core.dependencies import get_usuario_actual, requiere_rol
from app.core.paginacion import Page
from app.modules.usuarios.models import Usuario
from app.modules.ventas import schemas, service
from app.modules.ventas.unit_of_work import VentasUnitOfWork, get_ventas_uow

ventas_personal_router = APIRouter(
    prefix="/ventas",
    tags=["ventas"],
    dependencies=[Depends(requiere_rol("VENDEDOR", "ADMIN"))],
)


@ventas_personal_router.post(
    "",
    response_model=schemas.VentaRead,
    status_code=status.HTTP_201_CREATED,
)
@ventas_personal_router.post(
    "/",
    response_model=schemas.VentaRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def crear(
    datos: schemas.VentaCreate,
    background_tasks: BackgroundTasks,
    uow: VentasUnitOfWork = Depends(get_ventas_uow),
    usuario: Usuario = Depends(get_usuario_actual),
) -> schemas.VentaRead:
    venta = await service.crear(uow, datos, usuario_id=usuario.id)
    background_tasks.add_task(service.enviar_comprobante, venta.id)
    return venta


@ventas_personal_router.get(
    "",
    response_model=Page[schemas.VentaRead],
)
@ventas_personal_router.get(
    "/",
    response_model=Page[schemas.VentaRead],
    include_in_schema=False,
)
async def listar_paginado(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    uow: VentasUnitOfWork = Depends(get_ventas_uow),
) -> Page[schemas.VentaRead]:
    return await service.listar_paginado(uow, page=page, size=size)


mis_ventas_router = APIRouter(tags=["ventas"])


@mis_ventas_router.get(
    "/mis-ventas",
    response_model=Page[schemas.VentaRead],
)
async def listar_mis_ventas(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    uow: VentasUnitOfWork = Depends(get_ventas_uow),
    usuario: Usuario = Depends(get_usuario_actual),
) -> Page[schemas.VentaRead]:
    return await service.listar_por_usuario(uow, usuario, page=page, size=size)


ventas_router = APIRouter(
    prefix="/ventas",
    tags=["ventas"],
)


@ventas_router.get(
    "/{venta_id}",
    response_model=schemas.VentaRead,
)
async def obtener_por_id(
    venta_id: int,
    uow: VentasUnitOfWork = Depends(get_ventas_uow),
    usuario: Usuario = Depends(get_usuario_actual),
) -> schemas.VentaRead:
    return await service.obtener_por_id_con_acceso(uow, venta_id, usuario)
