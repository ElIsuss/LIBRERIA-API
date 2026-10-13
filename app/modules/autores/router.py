from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.modules.autores import schemas, service

router = APIRouter(prefix="/autores", tags=["autores"])


@router.post(
    "/",
    response_model=schemas.AutorRead,
    status_code=status.HTTP_201_CREATED,
)
async def crear(
    datos: schemas.AutorCreate,
    session: AsyncSession = Depends(get_session),
) -> schemas.AutorRead:
    return await service.crear(session, datos)


@router.get("/{autor_id}", response_model=schemas.AutorRead)
async def obtener(
    autor_id: int,
    session: AsyncSession = Depends(get_session),
) -> schemas.AutorRead:
    return await service.obtener_por_id(session, autor_id)


@router.patch("/{autor_id}", response_model=schemas.AutorRead)
async def actualizar(
    autor_id: int,
    datos: schemas.AutorUpdate,
    session: AsyncSession = Depends(get_session),
) -> schemas.AutorRead:
    return await service.actualizar(session, autor_id, datos)


@router.get("/{autor_id}/libros", response_model=list[schemas.AutoriaRead])
async def listar_libros(
    autor_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.AutoriaRead]:
    return await service.listar_libros(session, autor_id, limit, offset)