from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import requiere_rol
from app.modules.autores import schemas, service
from app.modules.autores.unit_of_work import AutorUnitOfWork, get_autor_uow

router = APIRouter(prefix="/autores", tags=["autores"])
autores_admin_router = APIRouter(
    prefix="/autores",
    tags=["autores"],
    dependencies=[Depends(requiere_rol("ADMIN"))],
)


@router.get("", response_model=list[schemas.AutorRead])
@router.get("/", response_model=list[schemas.AutorRead], include_in_schema=False)
async def listar(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    uow: AutorUnitOfWork = Depends(get_autor_uow),
) -> list[schemas.AutorRead]:
    return await service.listar(uow, limit, offset)


@router.get("/{autor_id}", response_model=schemas.AutorRead)
async def obtener(
    autor_id: int,
    uow: AutorUnitOfWork = Depends(get_autor_uow),
) -> schemas.AutorRead:
    return await service.obtener_por_id(uow, autor_id)


@router.get("/{autor_id}/libros", response_model=list[schemas.AutoriaRead])
async def listar_libros(
    autor_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    uow: AutorUnitOfWork = Depends(get_autor_uow),
) -> list[schemas.AutoriaRead]:
    return await service.listar_libros(uow, autor_id, limit, offset)


@autores_admin_router.post(
    "",
    response_model=schemas.AutorRead,
    status_code=status.HTTP_201_CREATED,
)
@autores_admin_router.post(
    "/",
    response_model=schemas.AutorRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def crear(
    datos: schemas.AutorCreate,
    uow: AutorUnitOfWork = Depends(get_autor_uow),
) -> schemas.AutorRead:
    return await service.crear(uow, datos)


@autores_admin_router.patch("/{autor_id}", response_model=schemas.AutorRead)
async def actualizar(
    autor_id: int,
    datos: schemas.AutorUpdate,
    uow: AutorUnitOfWork = Depends(get_autor_uow),
) -> schemas.AutorRead:
    return await service.actualizar(uow, autor_id, datos)
