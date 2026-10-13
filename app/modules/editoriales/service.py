from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.editoriales.models import Editorial
from app.modules.editoriales.schemas import EditorialCreate, EditorialUpdate
from app.modules.libros.models import Libro

MSG_DUPLICADA = "Ya existe una editorial con ese nombre"


async def crear(session: AsyncSession, datos: EditorialCreate) -> Editorial:
    editorial = Editorial(**datos.model_dump())
    session.add(editorial)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=MSG_DUPLICADA,
        )

    return editorial


async def listar(session: AsyncSession, limit: int, offset: int) -> list[Editorial]:
    statement = select(Editorial).order_by(Editorial.nombre).limit(limit).offset(offset)
    result = await session.exec(statement)
    return list(result.all())


async def obtener_por_id(session: AsyncSession, editorial_id: int) -> Editorial:
    editorial = await session.get(Editorial, editorial_id)

    if editorial is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una editorial con ese id",
        )

    return editorial


async def actualizar(
    session: AsyncSession,
    editorial_id: int,
    datos: EditorialUpdate,
) -> Editorial:
    editorial = await obtener_por_id(session, editorial_id)
    cambios = datos.model_dump(exclude_unset=True)

    for campo, valor in cambios.items():
        setattr(editorial, campo, valor)

    if not cambios:
        return editorial

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=MSG_DUPLICADA,
        )

    return editorial


async def listar_libros(session: AsyncSession, editorial_id: int) -> list[Libro]:
    await obtener_por_id(session, editorial_id)

    statement = (
        select(Libro)
        .where(Libro.editorial_id == editorial_id)
        .order_by(Libro.titulo, Libro.id)
    )
    result = await session.exec(statement)
    return list(result.all())