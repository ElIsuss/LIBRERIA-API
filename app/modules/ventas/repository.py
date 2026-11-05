from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy.orm import joinedload, selectinload
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.repository import BaseRepository
from app.modules.ventas.models import RenglonVenta, Venta


class VentaRepository(BaseRepository[Venta]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Venta)

    @staticmethod
    def _opciones_detalle() -> Sequence[Any]:
        return (
            joinedload(Venta.cliente),
            selectinload(Venta.renglones).joinedload(RenglonVenta.libro),
        )

    async def get_detalle(self, venta_id: int) -> Venta | None:
        return await self.get_by_id(venta_id, options=self._opciones_detalle())

    async def listar_paginado(
        self,
        *,
        page: int,
        size: int,
        cliente_id: int | None = None,
    ) -> tuple[list[Venta], int]:
        filters = []
        if cliente_id is not None:
            filters.append(Venta.cliente_id == cliente_id)

        total = await self.count(filters=filters)
        items = await self.get_all(
            filters=filters,
            order_by=(Venta.fecha.desc(), Venta.id.desc()),
            page=page,
            size=size,
            options=self._opciones_detalle(),
        )
        return items, total

    async def listar_por_cliente(self, cliente_id: int) -> list[Venta]:
        return await self.get_all(
            filters=[Venta.cliente_id == cliente_id],
            order_by=(Venta.fecha.desc(), Venta.id.desc()),
            options=self._opciones_detalle(),
        )
