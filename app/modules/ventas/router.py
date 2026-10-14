from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.modules.ventas import schemas, service

router = APIRouter(prefix="/ventas", tags=["ventas"])


@router.post(
    "/",
    response_model=schemas.VentaRead,
    status_code=status.HTTP_201_CREATED,
)
async def crear(
    datos: schemas.VentaCreate,
    session: AsyncSession = Depends(get_session),
) -> schemas.VentaRead:
    return await service.crear(session, datos)
