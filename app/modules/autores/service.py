from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.autores.models import Autor
from app.modules.autores.schemas import AutorCreate, AutorUpdate, AutoriaRead
from app.modules.libros.models import Libro, LibroAutor


async def crear(session: AsyncSession, datos: AutorCreate) -> Autor:
    autor = Autor(**datos.model_dump())
    session.add(autor)
    await session.commit()
    return autor


async def obtener_por_id(session: AsyncSession, autor_id: int) -> Autor:
    autor = await session.get(Autor, autor_id)

    if autor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un autor con ese id",
        )

    return autor


async def actualizar(
    session: AsyncSession,
    autor_id: int,
    datos: AutorUpdate,
) -> Autor:
    autor = await obtener_por_id(session, autor_id)
    cambios = datos.model_dump(exclude_unset=True)

    for campo, valor in cambios.items():
        setattr(autor, campo, valor)

    if not cambios:
        return autor

    await session.commit()
    return autor


async def listar_libros(
    session: AsyncSession,
    autor_id: int,
    limit: int,
    offset: int,
) -> list[AutoriaRead]:
    await obtener_por_id(session, autor_id)

    statement = (
        select(Libro, LibroAutor.rol, LibroAutor.orden)
        .join(LibroAutor, Libro.id == LibroAutor.libro_id)
        .where(LibroAutor.autor_id == autor_id)
        .order_by(Libro.titulo, Libro.id)
        .limit(limit)
        .offset(offset)
    )
    result = await session.exec(statement)

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
        for libro, rol, orden in result.all()
    ]