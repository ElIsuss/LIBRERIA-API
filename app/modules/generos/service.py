from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.paginacion import Page
from app.modules.editoriales.schemas import LibroResumen
from app.modules.generos.models import Genero
from app.modules.generos.schemas import GeneroCreate, GeneroRead
from app.modules.generos.unit_of_work import GeneroUnitOfWork
from app.modules.libros.models import Libro

MSG_DUPLICADO = "Ya existe un genero con ese nombre"


async def crear(uow: GeneroUnitOfWork, datos: GeneroCreate) -> GeneroRead:
    genero = Genero(**datos.model_dump())
    try:
        async with uow:
            genero = await uow.generos.add(genero)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=MSG_DUPLICADO,
        )
    return GeneroRead.model_validate(genero)


async def listar_paginado(
    uow: GeneroUnitOfWork,
    page: int = 1,
    size: int = 20,
) -> Page[GeneroRead]:
    total = await uow.generos.count()
    items = await uow.generos.get_all(
        order_by=Genero.nombre,
        page=page,
        size=size,
    )
    items_read = [GeneroRead.model_validate(g) for g in items]
    try:
        return Page.create(items=items_read, total=total, page=page, size=size)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La página {page} solicitada excede el total de páginas disponibles",
        )


async def obtener_por_id(uow: GeneroUnitOfWork, genero_id: int) -> GeneroRead:
    genero = await uow.generos.get_by_id(genero_id)
    if genero is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un genero con ese id",
        )
    return GeneroRead.model_validate(genero)


async def listar_libros(
    uow: GeneroUnitOfWork,
    genero_id: int,
    limit: int = 20,
    offset: int = 0,
) -> list[LibroResumen]:
    await obtener_por_id(uow, genero_id)

    stmt = (
        select(Libro)
        .where(Libro.genero_id == genero_id)
        .where(Libro.borrado_en.is_(None))
        .order_by(Libro.titulo, Libro.id)
        .limit(limit)
        .offset(offset)
    )
    res = await uow.session.execute(stmt)
    libros = list(res.scalars().all())
    return [LibroResumen.model_validate(l) for l in libros]
