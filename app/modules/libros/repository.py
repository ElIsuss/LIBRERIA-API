from __future__ import annotations

from typing import Sequence
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.repository import BaseRepository, SoftDeleteRepository
from app.modules.libros.models import Libro, LibroAutor, MovimientoStock


class LibroRepository(SoftDeleteRepository[Libro]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Libro)

    @staticmethod
    def _opciones_detalle():
        return (
            joinedload(Libro.editorial),
            joinedload(Libro.genero),
            selectinload(Libro.autorias).selectinload(LibroAutor.autor),
        )

    @staticmethod
    def _opciones_lista():
        return (
            joinedload(Libro.editorial),
            joinedload(Libro.genero),
        )

    async def get_by_isbn(self, isbn: str, *, include_deleted: bool = False) -> Libro | None:
        stmt = select(Libro).where(Libro.isbn == isbn)
        if not include_deleted:
            stmt = stmt.where(Libro.borrado_en.is_(None))
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_detalle(self, libro_id: int, *, include_deleted: bool = False) -> Libro | None:
        return await self.get_by_id(libro_id, include_deleted=include_deleted, options=self._opciones_detalle())

    async def listar_catalogo(
        self,
        *,
        titulo: str | None = None,
        genero_id: int | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Libro], int]:
        filters = []
        if titulo is not None:
            # Parámetro ligado (RN-11 TP): bindparam automático de SQLAlchemy
            filters.append(Libro.titulo.ilike(f"%{titulo}%"))
        if genero_id is not None:
            filters.append(Libro.genero_id == genero_id)

        total = await self.count(filters=filters, include_deleted=False)
        items = await self.get_all(
            filters=filters,
            order_by=(Libro.titulo, Libro.id),
            page=page,
            size=size,
            options=self._opciones_lista(),
            include_deleted=False,
        )
        return items, total

    async def add_autoria(self, autoria: LibroAutor) -> LibroAutor:
        self.session.add(autoria)
        await self.session.flush()
        return autoria


class MovimientoStockRepository(BaseRepository[MovimientoStock]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, MovimientoStock)

    async def get_por_libro(self, libro_id: int) -> list[MovimientoStock]:
        stmt = (
            select(MovimientoStock)
            .where(MovimientoStock.libro_id == libro_id)
            .order_by(MovimientoStock.cuando.asc(), MovimientoStock.id.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
