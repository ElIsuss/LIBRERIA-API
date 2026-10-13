from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.libros.models import Libro, LibroAutor
from app.modules.libros.schemas import (
    AutorEnLibro,
    EditorialEnLibro,
    GeneroEnLibro,
    LibroCreate,
    LibroDetalle,
    LibroLista,
    LibroUpdate,
)

MSG_CONFLICTO = "No se pudo guardar el libro: isbn duplicado o id de editorial, genero o autor invalido"


def _a_detalle(libro: Libro) -> LibroDetalle:
    autorias_ordenadas = sorted(libro.autorias, key=lambda a: a.orden)
    return LibroDetalle(
        id=libro.id,
        isbn=libro.isbn,
        titulo=libro.titulo,
        precio=libro.precio,
        stock=libro.stock,
        editorial=EditorialEnLibro.model_validate(libro.editorial),
        genero=GeneroEnLibro.model_validate(libro.genero) if libro.genero else None,
        autores=[
            AutorEnLibro(
                id=a.autor.id,
                nombre=a.autor.nombre,
                nacionalidad=a.autor.nacionalidad,
                rol=a.rol,
                orden=a.orden,
            )
            for a in autorias_ordenadas
        ],
    )


def _a_lista(libro: Libro) -> LibroLista:
    return LibroLista(
        id=libro.id,
        isbn=libro.isbn,
        titulo=libro.titulo,
        precio=libro.precio,
        stock=libro.stock,
        editorial=EditorialEnLibro.model_validate(libro.editorial),
        genero=GeneroEnLibro.model_validate(libro.genero) if libro.genero else None,
    )


def _opciones_detalle():
    return (
        joinedload(Libro.editorial),
        joinedload(Libro.genero),
        selectinload(Libro.autorias).selectinload(LibroAutor.autor),
    )


async def obtener_por_id(session: AsyncSession, libro_id: int) -> LibroDetalle:
    statement = select(Libro).where(Libro.id == libro_id).options(*_opciones_detalle())
    result = await session.exec(statement)
    libro = result.one_or_none()

    if libro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un libro con ese id",
        )

    return _a_detalle(libro)


async def crear(session: AsyncSession, datos: LibroCreate) -> LibroDetalle:
    payload = datos.model_dump()
    autorias_datos = payload.pop("autores", [])
    libro = Libro(**payload)

    try:
        session.add(libro)
        # Con autoflush=False el id recien existe tras el flush.
        # El flush tambien valida isbn y las FK de libro aca mismo.
        await session.flush()
        for a in autorias_datos:
            session.add(
                LibroAutor(
                    libro_id=libro.id,
                    autor_id=a["autor_id"],
                    rol=a["rol"],
                    orden=a["orden"],
                )
            )
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=MSG_CONFLICTO,
        )

    return await obtener_por_id(session, libro.id)


async def listar(
    session: AsyncSession,
    limit: int,
    offset: int,
    titulo: str | None = None,
    genero_id: int | None = None,
) -> list[LibroLista]:
    statement = (
        select(Libro)
        .options(joinedload(Libro.editorial), joinedload(Libro.genero))
        .order_by(Libro.titulo, Libro.id)
    )

    if titulo is not None:
        # Parametro ligado (RN-11): el valor va como bindparam,
        # nunca se concatena SQL con texto del usuario.
        statement = statement.where(Libro.titulo.ilike(f"%{titulo}%"))

    if genero_id is not None:
        statement = statement.where(Libro.genero_id == genero_id)

    statement = statement.limit(limit).offset(offset)
    result = await session.exec(statement)
    return [_a_lista(libro) for libro in result.all()]


async def actualizar(
    session: AsyncSession,
    libro_id: int,
    datos: LibroUpdate,
) -> LibroDetalle:
    libro = await session.get(Libro, libro_id)

    if libro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un libro con ese id",
        )

    cambios = datos.model_dump(exclude_unset=True)

    for campo, valor in cambios.items():
        setattr(libro, campo, valor)

    if not cambios:
        # Nada que guardar: se relee con precargas para el detalle.
        return await obtener_por_id(session, libro_id)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=MSG_CONFLICTO,
        )

    return await obtener_por_id(session, libro_id)
