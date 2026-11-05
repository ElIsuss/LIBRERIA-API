from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteRead,
    ClienteUpdate,
    PerfilCreate,
    PerfilRead,
)
from app.modules.clientes.unit_of_work import ClientesUnitOfWork

MSG_EMAIL_DUPLICADO = "Ya existe un cliente con ese email"
MSG_PERFIL_DUPLICADO = "Ese cliente ya tiene un perfil"
MSG_CLIENTE_INEXISTENTE = "No existe un cliente con ese id"


def _a_read(cliente: Cliente) -> ClienteRead:
    return ClienteRead(
        id=cliente.id,
        nombre=cliente.nombre,
        email=cliente.email,
        perfil=PerfilRead.model_validate(cliente.perfil) if cliente.perfil else None,
    )


async def crear_cliente(
    uow: ClientesUnitOfWork,
    datos: ClienteCreate,
) -> ClienteRead:
    try:
        async with uow:
            cliente = await uow.clientes.add(Cliente(**datos.model_dump()))
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=MSG_EMAIL_DUPLICADO,
        ) from exc

    return _a_read(await uow.clientes.get_detalle(cliente.id))


async def obtener_por_id(
    uow: ClientesUnitOfWork,
    cliente_id: int,
) -> ClienteRead:
    cliente = await uow.clientes.get_detalle(cliente_id)
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=MSG_CLIENTE_INEXISTENTE,
        )

    return _a_read(cliente)


async def actualizar(
    uow: ClientesUnitOfWork,
    cliente_id: int,
    datos: ClienteUpdate,
) -> ClienteRead:
    cliente = await uow.clientes.get_detalle(cliente_id)
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=MSG_CLIENTE_INEXISTENTE,
        )

    cambios = datos.model_dump(exclude_unset=True)
    if not cambios:
        return _a_read(cliente)

    for campo, valor in cambios.items():
        setattr(cliente, campo, valor)

    try:
        async with uow:
            await uow.clientes.update(cliente)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=MSG_EMAIL_DUPLICADO,
        ) from exc

    return _a_read(await uow.clientes.get_detalle(cliente_id))


async def crear_perfil(
    uow: ClientesUnitOfWork,
    cliente_id: int,
    datos: PerfilCreate,
) -> PerfilRead:
    cliente = await uow.clientes.get_by_id(cliente_id)
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=MSG_CLIENTE_INEXISTENTE,
        )

    perfil = PerfilCliente(cliente_id=cliente_id, **datos.model_dump())

    try:
        async with uow:
            perfil = await uow.perfiles.add(perfil)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=MSG_PERFIL_DUPLICADO,
        ) from exc

    return PerfilRead.model_validate(perfil)
