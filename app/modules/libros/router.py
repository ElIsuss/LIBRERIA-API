from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_usuario_actual, requiere_rol
from app.core.paginacion import Page
from app.modules.libros import schemas, service
from app.modules.libros.unit_of_work import LibrosUnitOfWork, get_libros_uow
from app.modules.usuarios.models import Usuario

router = APIRouter(prefix="/libros", tags=["libros"])
libros_admin_router = APIRouter(
    prefix="/libros",
    tags=["libros"],
    dependencies=[Depends(requiere_rol("ADMIN"))],
)


@router.get("", response_model=Page[schemas.LibroLista])
@router.get("/", response_model=Page[schemas.LibroLista], include_in_schema=False)
async def listar(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    titulo: str | None = None,
    genero_id: int | None = None,
    uow: LibrosUnitOfWork = Depends(get_libros_uow),
) -> Page[schemas.LibroLista]:
    return await service.listar_paginado(uow, page=page, size=size, titulo=titulo, genero_id=genero_id)


@router.get("/{libro_id}", response_model=schemas.LibroDetalle)
async def obtener(
    libro_id: int,
    uow: LibrosUnitOfWork = Depends(get_libros_uow),
) -> schemas.LibroDetalle:
    return await service.obtener_por_id(uow, libro_id)


@libros_admin_router.post(
    "",
    response_model=schemas.LibroDetalle,
    status_code=status.HTTP_201_CREATED,
)
@libros_admin_router.post(
    "/",
    response_model=schemas.LibroDetalle,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def crear(
    datos: schemas.LibroCreate,
    uow: LibrosUnitOfWork = Depends(get_libros_uow),
    admin: Usuario = Depends(get_usuario_actual),
) -> schemas.LibroDetalle:
    return await service.crear(uow, datos, admin_id=admin.id)


@libros_admin_router.patch("/{libro_id}", response_model=schemas.LibroDetalle)
async def actualizar(
    libro_id: int,
    datos: schemas.LibroUpdate,
    uow: LibrosUnitOfWork = Depends(get_libros_uow),
) -> schemas.LibroDetalle:
    return await service.actualizar(uow, libro_id, datos)


@libros_admin_router.delete("/{libro_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar(
    libro_id: int,
    uow: LibrosUnitOfWork = Depends(get_libros_uow),
) -> None:
    await service.eliminar_libro(uow, libro_id)


@libros_admin_router.post(
    "/{libro_id}/reponer",
    response_model=schemas.MovimientoStockRead,
    status_code=status.HTTP_200_OK,
)
async def reponer(
    libro_id: int,
    datos: schemas.ReponerStockRequest,
    uow: LibrosUnitOfWork = Depends(get_libros_uow),
    admin: Usuario = Depends(get_usuario_actual),
) -> schemas.MovimientoStockRead:
    return await service.reponer_stock(uow, libro_id, datos, admin_id=admin.id)


@libros_admin_router.get(
    "/{libro_id}/movimientos",
    response_model=list[schemas.MovimientoStockRead],
    status_code=status.HTTP_200_OK,
)
async def movimientos(
    libro_id: int,
    uow: LibrosUnitOfWork = Depends(get_libros_uow),
) -> list[schemas.MovimientoStockRead]:
    return await service.listar_movimientos(uow, libro_id)
