from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import requiere_rol
from app.core.paginacion import Page
from app.modules.editoriales import schemas, service
from app.modules.editoriales.unit_of_work import EditorialUnitOfWork, get_editorial_uow

router = APIRouter(prefix="/editoriales", tags=["editoriales"])
editoriales_admin_router = APIRouter(
    prefix="/editoriales",
    tags=["editoriales"],
    dependencies=[Depends(requiere_rol("ADMIN"))],
)


@router.get("", response_model=Page[schemas.EditorialRead])
@router.get("/", response_model=Page[schemas.EditorialRead], include_in_schema=False)
async def listar(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    uow: EditorialUnitOfWork = Depends(get_editorial_uow),
) -> Page[schemas.EditorialRead]:
    return await service.listar_paginado(uow, page, size)


@router.get("/{editorial_id}", response_model=schemas.EditorialRead)
async def obtener(
    editorial_id: int,
    uow: EditorialUnitOfWork = Depends(get_editorial_uow),
) -> schemas.EditorialRead:
    return await service.obtener_por_id(uow, editorial_id)


@router.get("/{editorial_id}/libros", response_model=list[schemas.LibroResumen])
async def listar_libros(
    editorial_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    uow: EditorialUnitOfWork = Depends(get_editorial_uow),
) -> list[schemas.LibroResumen]:
    return await service.listar_libros(uow, editorial_id, limit, offset)


@editoriales_admin_router.post(
    "",
    response_model=schemas.EditorialRead,
    status_code=status.HTTP_201_CREATED,
)
@editoriales_admin_router.post(
    "/",
    response_model=schemas.EditorialRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def crear(
    datos: schemas.EditorialCreate,
    uow: EditorialUnitOfWork = Depends(get_editorial_uow),
) -> schemas.EditorialRead:
    return await service.crear(uow, datos)


@editoriales_admin_router.patch("/{editorial_id}", response_model=schemas.EditorialRead)
async def actualizar(
    editorial_id: int,
    datos: schemas.EditorialUpdate,
    uow: EditorialUnitOfWork = Depends(get_editorial_uow),
) -> schemas.EditorialRead:
    return await service.actualizar(uow, editorial_id, datos)
