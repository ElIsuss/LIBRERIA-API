from fastapi import APIRouter, BackgroundTasks, Depends, status
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
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> schemas.VentaRead:
    venta = await service.crear(session, datos)
    background_tasks.add_task(service.enviar_comprobante, venta.id)
    return venta
