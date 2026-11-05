from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.paginacion import Page
from app.modules.editoriales.models import Editorial
from app.modules.editoriales.schemas import EditorialCreate, EditorialRead, EditorialUpdate, LibroResumen
from app.modules.editoriales.unit_of_work import EditorialUnitOfWork
from app.modules.libros.models import Libro

MSG_DUPLICADA = "Ya existe una editorial con ese nombre"


async def crear(uow: EditorialUnitOfWork, datos: EditorialCreate) -> EditorialRead:
    editorial = Editorial(**datos.model_dump())
    try:
        async with uow:
            editorial = await uow.editoriales.add(editorial)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=MSG_DUPLICADA,
        )
    return EditorialRead.model_validate(editorial)


async def listar_paginado(
    uow: EditorialUnitOfWork,
    page: int = 1,
    size: int = 20,
) -> Page[EditorialRead]:
    total = await uow.editoriales.count()
    items = await uow.editoriales.get_all(
        order_by=Editorial.nombre,
        page=page,
        size=size,
    )
    items_read = [EditorialRead.model_validate(e) for e in items]
    try:
        return Page.create(items=items_read, total=total, page=page, size=size)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La página {page} solicitada excede el total de páginas disponibles",
        )


async def obtener_por_id(uow: EditorialUnitOfWork, editorial_id: int) -> EditorialRead:
    editorial = await uow.editoriales.get_by_id(editorial_id)
    if editorial is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una editorial con ese id",
        )
    return EditorialRead.model_validate(editorial)


async def actualizar(
    uow: EditorialUnitOfWork,
    editorial_id: int,
    datos: EditorialUpdate,
) -> EditorialRead:
    editorial = await uow.editoriales.get_by_id(editorial_id)
    if editorial is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una editorial con ese id",
        )

    cambios = datos.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(editorial, campo, valor)

    if not cambios:
        return EditorialRead.model_validate(editorial)

    try:
        async with uow:
            editorial = await uow.editoriales.update(editorial)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=MSG_DUPLICADA,
        )

    return EditorialRead.model_validate(editorial)


async def listar_libros(
    uow: EditorialUnitOfWork,
    editorial_id: int,
    limit: int = 20,
    offset: int = 0,
) -> list[LibroResumen]:
    await obtener_por_id(uow, editorial_id)

    stmt = (
        select(Libro)
        .where(Libro.editorial_id == editorial_id)
        .where(Libro.borrado_en.is_(None))
        .order_by(Libro.titulo, Libro.id)
        .limit(limit)
        .offset(offset)
    )
    res = await uow.session.execute(stmt)
    libros = list(res.scalars().all())
    return [LibroResumen.model_validate(l) for l in libros]
