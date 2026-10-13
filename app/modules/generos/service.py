from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.generos.models import Genero
from app.modules.generos.schemas import GeneroCreate
from app.modules.libros.models import Libro

MSG_DUPLICADO = "Ya existe un genero con ese nombre"


async def crear(session: AsyncSession, datos: GeneroCreate) -> Genero:
    genero = Genero(**datos.model_dump())
    session.add(genero)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=MSG_DUPLICADO,
        )

    return genero


async def listar(session: AsyncSession, limit: int, offset: int) -> list[Genero]:
    statement = select(Genero).order_by(Genero.nombre).limit(limit).offset(offset)
    result = await session.exec(statement)
    return list(result.all())


async def obtener_por_id(session: AsyncSession, genero_id: int) -> Genero:
    genero = await session.get(Genero, genero_id)

    if genero is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un genero con ese id",
        )

    return genero


async def listar_libros(
    session: AsyncSession,
    genero_id: int,
    limit: int,
    offset: int,
) -> list[Libro]:
    await obtener_por_id(session, genero_id)

    statement = (
        select(Libro)
        .where(Libro.genero_id == genero_id)
        .order_by(Libro.titulo, Libro.id)
        .limit(limit)
        .offset(offset)
    )
    result = await session.exec(statement)
    return list(result.all())