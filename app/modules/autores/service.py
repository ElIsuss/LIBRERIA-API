from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select

from app.modules.autores.models import Autor
from app.modules.autores.schemas import AutorCreate, AutorRead, AutorUpdate, AutoriaRead
from app.modules.autores.unit_of_work import AutorUnitOfWork
from app.modules.libros.models import Libro, LibroAutor


async def crear(uow: AutorUnitOfWork, datos: AutorCreate) -> AutorRead:
    autor = Autor(**datos.model_dump())
    async with uow:
        autor = await uow.autores.add(autor)
    return AutorRead.model_validate(autor)


async def listar(uow: AutorUnitOfWork, limit: int = 20, offset: int = 0) -> list[AutorRead]:
    items = await uow.autores.get_all(
        order_by=Autor.nombre,
        page=(offset // limit) + 1 if limit > 0 else 1,
        size=limit,
    )
    return [AutorRead.model_validate(a) for a in items]


async def obtener_por_id(uow: AutorUnitOfWork, autor_id: int) -> AutorRead:
    autor = await uow.autores.get_by_id(autor_id)
    if autor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un autor con ese id",
        )
    return AutorRead.model_validate(autor)


async def actualizar(
    uow: AutorUnitOfWork,
    autor_id: int,
    datos: AutorUpdate,
) -> AutorRead:
    autor = await uow.autores.get_by_id(autor_id)
    if autor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un autor con ese id",
        )

    cambios = datos.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(autor, campo, valor)

    if not cambios:
        return AutorRead.model_validate(autor)

    async with uow:
        autor = await uow.autores.update(autor)

    return AutorRead.model_validate(autor)


async def listar_libros(
    uow: AutorUnitOfWork,
    autor_id: int,
    limit: int = 20,
    offset: int = 0,
) -> list[AutoriaRead]:
    await obtener_por_id(uow, autor_id)

    stmt = (
        select(Libro, LibroAutor.rol, LibroAutor.orden)
        .join(LibroAutor, Libro.id == LibroAutor.libro_id)
        .where(LibroAutor.autor_id == autor_id)
        .where(Libro.borrado_en.is_(None))
        .order_by(Libro.titulo, Libro.id)
        .limit(limit)
        .offset(offset)
    )
    res = await uow.session.execute(stmt)

    return [
        AutoriaRead(
            id=libro.id,
            isbn=libro.isbn,
            titulo=libro.titulo,
            precio=libro.precio,
            stock=libro.stock,
            rol=rol,
            orden=orden,
        )
        for libro, rol, orden in res.all()
    ]
