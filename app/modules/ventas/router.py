from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
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


@router.get("/", response_model=list[schemas.VentaRead])
async def listar(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.VentaRead]:
    return await service.listar(session, limit, offset)


@router.get("/{venta_id}", response_model=schemas.VentaRead)
async def obtener(
    venta_id: int,
    session: AsyncSession = Depends(get_session),
) -> schemas.VentaRead:
    return await service.obtener_por_id(session, venta_id)
