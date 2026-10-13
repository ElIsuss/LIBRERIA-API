from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.modules.libros import schemas, service

router = APIRouter(prefix="/libros", tags=["libros"])


@router.post(
    "/",
    response_model=schemas.LibroDetalle,
    status_code=status.HTTP_201_CREATED,
)
async def crear(
    datos: schemas.LibroCreate,
    session: AsyncSession = Depends(get_session),
) -> schemas.LibroDetalle:
    return await service.crear(session, datos)


@router.get("/", response_model=list[schemas.LibroLista])
async def listar(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    titulo: str | None = Query(default=None),
    genero_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.LibroLista]:
    return await service.listar(session, limit, offset, titulo, genero_id)


@router.get("/{libro_id}", response_model=schemas.LibroDetalle)
async def obtener(
    libro_id: int,
    session: AsyncSession = Depends(get_session),
) -> schemas.LibroDetalle:
    return await service.obtener_por_id(session, libro_id)


@router.patch("/{libro_id}", response_model=schemas.LibroDetalle)
async def actualizar(
    libro_id: int,
    datos: schemas.LibroUpdate,
    session: AsyncSession = Depends(get_session),
) -> schemas.LibroDetalle:
    return await service.actualizar(session, libro_id, datos)
