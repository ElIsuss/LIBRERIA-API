from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.modules.editoriales import schemas, service

router = APIRouter(prefix="/editoriales", tags=["editoriales"])


@router.post(
    "/",
    response_model=schemas.EditorialRead,
    status_code=status.HTTP_201_CREATED,
)
async def crear(
    datos: schemas.EditorialCreate,
    session: AsyncSession = Depends(get_session),
) -> schemas.EditorialRead:
    return await service.crear(session, datos)


@router.get("/", response_model=list[schemas.EditorialRead])
async def listar(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.EditorialRead]:
    return await service.listar(session, limit, offset)


@router.get("/{editorial_id}", response_model=schemas.EditorialRead)
async def obtener(
    editorial_id: int,
    session: AsyncSession = Depends(get_session),
) -> schemas.EditorialRead:
    return await service.obtener_por_id(session, editorial_id)


@router.patch("/{editorial_id}", response_model=schemas.EditorialRead)
async def actualizar(
    editorial_id: int,
    datos: schemas.EditorialUpdate,
    session: AsyncSession = Depends(get_session),
) -> schemas.EditorialRead:
    return await service.actualizar(session, editorial_id, datos)


@router.get("/{editorial_id}/libros", response_model=list[schemas.LibroResumen])
async def listar_libros(
    editorial_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[schemas.LibroResumen]:
    return await service.listar_libros(session, editorial_id)