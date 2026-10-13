from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.modules.generos import schemas, service
from app.modules.libros.schemas import LibroResumen

router = APIRouter(prefix="/generos", tags=["generos"])


@router.post(
    "/",
    response_model=schemas.GeneroRead,
    status_code=status.HTTP_201_CREATED,
)
async def crear(
    datos: schemas.GeneroCreate,
    session: AsyncSession = Depends(get_session),
) -> schemas.GeneroRead:
    return await service.crear(session, datos)


@router.get("/", response_model=list[schemas.GeneroRead])
async def listar(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.GeneroRead]:
    return await service.listar(session, limit, offset)


@router.get("/{genero_id}/libros", response_model=list[LibroResumen])
async def listar_libros(
    genero_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[LibroResumen]:
    return await service.listar_libros(session, genero_id, limit, offset)