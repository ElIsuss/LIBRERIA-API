from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.unit_of_work import UnitOfWork
from app.modules.libros.models import Libro, MovimientoStock
from app.modules.libros.repository import LibroRepository, MovimientoStockRepository


class LibrosUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.libros = LibroRepository(session)
        self.movimientos = MovimientoStockRepository(session)

    async def registrar_movimiento_stock(
        self,
        libro: Libro,
        usuario_id: int,
        cantidad: int,
        motivo: str,
        venta_id: int | None = None,
    ) -> MovimientoStock:
        """
        PUNTO ÚNICO DE ESCRITURA DE STOCK (RN-11)
        
        Garantiza que toda modificación de stock de un libro esté obligatoriamente
        asociada a una fila en `movimiento_stock`, de modo que en todo momento se cumpla:
        libro.stock == SUM(movimiento_stock.cantidad).
        
        No ejecuta commit: sólo actualiza en la sesión y hace flush() para que sea
        el UnitOfWork quien confirme atómicamente la transacción completa.
        """
        if cantidad == 0:
            raise ValueError("La cantidad de un movimiento de stock no puede ser cero")

        nuevo_stock = libro.stock + cantidad
        if nuevo_stock < 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Stock insuficiente para el libro '{libro.titulo}' (disponible: {libro.stock}, requerido: {abs(cantidad)})",
            )

        libro.stock = nuevo_stock
        await self.libros.update(libro)

        movimiento = MovimientoStock(
            libro_id=libro.id,
            venta_id=venta_id,
            usuario_id=usuario_id,
            cantidad=cantidad,
            motivo=motivo,
        )
        movimiento = await self.movimientos.add(movimiento)
        return movimiento


async def get_libros_uow(
    session: AsyncSession = Depends(get_session),
) -> LibrosUnitOfWork:
    return LibrosUnitOfWork(session)
