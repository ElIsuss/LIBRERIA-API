from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import requiere_rol
from app.core.paginacion import Page
from app.modules.editoriales.schemas import LibroResumen
from app.modules.generos import schemas, service
from app.modules.generos.unit_of_work import GeneroUnitOfWork, get_genero_uow

router = APIRouter(prefix="/generos", tags=["generos"])
generos_admin_router = APIRouter(
    prefix="/generos",
    tags=["generos"],
    dependencies=[Depends(requiere_rol("ADMIN"))],
)


@router.get("", response_model=Page[schemas.GeneroRead])
@router.get("/", response_model=Page[schemas.GeneroRead], include_in_schema=False)
async def listar(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    uow: GeneroUnitOfWork = Depends(get_genero_uow),
) -> Page[schemas.GeneroRead]:
    return await service.listar_paginado(uow, page, size)


@router.get("/{genero_id}", response_model=schemas.GeneroRead)
async def obtener(
    genero_id: int,
    uow: GeneroUnitOfWork = Depends(get_genero_uow),
) -> schemas.GeneroRead:
    return await service.obtener_por_id(uow, genero_id)


@router.get("/{genero_id}/libros", response_model=list[LibroResumen])
async def listar_libros(
    genero_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    uow: GeneroUnitOfWork = Depends(get_genero_uow),
) -> list[LibroResumen]:
    return await service.listar_libros(uow, genero_id, limit, offset)


@generos_admin_router.post(
    "",
    response_model=schemas.GeneroRead,
    status_code=status.HTTP_201_CREATED,
)
@generos_admin_router.post(
    "/",
    response_model=schemas.GeneroRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def crear(
    datos: schemas.GeneroCreate,
    uow: GeneroUnitOfWork = Depends(get_genero_uow),
) -> schemas.GeneroRead:
    return await service.crear(uow, datos)
