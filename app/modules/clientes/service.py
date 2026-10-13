from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteRead,
    ClienteUpdate,
    PerfilCreate,
    PerfilRead,
)

MSG_EMAIL_DUPLICADO = "Ya existe un cliente con ese email"
MSG_PERFIL_DUPLICADO = "Ese cliente ya tiene un perfil"


def _a_read(cliente: Cliente) -> ClienteRead:
    return ClienteRead(
        id=cliente.id,
        nombre=cliente.nombre,
        email=cliente.email,
        perfil=PerfilRead.model_validate(cliente.perfil) if cliente.perfil else None,
    )


async def crear_cliente(session: AsyncSession, datos: ClienteCreate) -> ClienteRead:
    cliente = Cliente(**datos.model_dump())
    session.add(cliente)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=MSG_EMAIL_DUPLICADO,
        )

    # El objeto recien creado nunca cargo perfil: sin este refresh,
    # leer cliente.perfil dispararia una carga perezosa (prohibida
    # por la consigna y que en async directamente falla).
    await session.refresh(cliente, ["perfil"])
    return _a_read(cliente)


async def obtener_por_id(session: AsyncSession, cliente_id: int) -> ClienteRead:
    statement = (
        select(Cliente)
        .where(Cliente.id == cliente_id)
        .options(joinedload(Cliente.perfil))
    )
    result = await session.exec(statement)
    cliente = result.one_or_none()

    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un cliente con ese id",
        )

    return _a_read(cliente)


async def actualizar(
    session: AsyncSession,
    cliente_id: int,
    datos: ClienteUpdate,
) -> ClienteRead:
    cliente = await session.get(Cliente, cliente_id)

    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un cliente con ese id",
        )

    cambios = datos.model_dump(exclude_unset=True)

    for campo, valor in cambios.items():
        setattr(cliente, campo, valor)

    if not cambios:
        return await obtener_por_id(session, cliente_id)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=MSG_EMAIL_DUPLICADO,
        )

    return await obtener_por_id(session, cliente_id)


async def crear_perfil(
    session: AsyncSession,
    cliente_id: int,
    datos: PerfilCreate,
) -> PerfilRead:
    # El 404 va primero: sin cliente no hay perfil que crear,
    # y el codigo correcto es 404 aunque la FK tambien rechazaria.
    if await session.get(Cliente, cliente_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un cliente con ese id",
        )

    perfil = PerfilCliente(cliente_id=cliente_id, **datos.model_dump())
    session.add(perfil)

    try:
        await session.commit()
    except IntegrityError:
        # RN-09: el UNIQUE en perfil_cliente.cliente_id rechaza el
        # segundo perfil. Sin if previo: se escribe y la base decide.
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=MSG_PERFIL_DUPLICADO,
        )

    return PerfilRead.model_validate(perfil)
