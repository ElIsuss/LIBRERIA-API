from __future__ import annotations

import asyncio
import logging
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.modules.libros.models import Libro
from app.modules.ventas.models import RenglonVenta, Venta
from app.modules.ventas.schemas import (
    ClienteEnVenta,
    RenglonVentaRead,
    VentaCreate,
    VentaRead,
)
from app.modules.ventas.unit_of_work import VentasUnitOfWork

logger = logging.getLogger(__name__)

MSG_CONFLICTO = (
    "No se pudo registrar la venta por una restricción de integridad"
)
MSG_CLIENTE_INEXISTENTE = "No se puede crear la venta: el cliente indicado no existe"
MSG_LIBRO_INEXISTENTE = (
    "No se puede crear la venta: alguno de los libros indicados no existe o fue dado de baja"
)
MSG_STOCK_INSUFICIENTE = "No se puede crear la venta: stock insuficiente para el libro '{titulo}'"


def _a_read(venta: Venta) -> VentaRead:
    renglones_ordenados = sorted(venta.renglones, key=lambda r: r.id or 0)
    return VentaRead(
        id=venta.id,
        fecha=venta.fecha,
        total=venta.total,
        cliente=ClienteEnVenta.model_validate(venta.cliente),
        renglones=[
            RenglonVentaRead(
                libro_id=renglon.libro_id,
                titulo=renglon.libro.titulo,
                cantidad=renglon.cantidad,
                precio_unitario=renglon.precio_unitario,
                subtotal=renglon.precio_unitario * renglon.cantidad,
            )
            for renglon in renglones_ordenados
        ],
    )


async def enviar_comprobante(venta_id: int) -> None:
    await asyncio.sleep(0.5)
    logger.info(
        "Aviso: comprobante de la venta #%s enviado al cliente en segundo plano.",
        venta_id,
    )


async def crear(
    uow: VentasUnitOfWork,
    datos: VentaCreate,
    usuario_id: int,
) -> VentaRead:
    ids_libros = [renglon.libro_id for renglon in datos.renglones]

    try:
        async with uow:
            cliente = await uow.clientes.get_by_id(datos.cliente_id)
            if cliente is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=MSG_CLIENTE_INEXISTENTE,
                )

            libros = await uow.libros.get_all(
                filters=[Libro.id.in_(ids_libros)],
                include_deleted=False,
            )
            libros_por_id = {libro.id: libro for libro in libros}
            ids_faltantes = sorted(set(ids_libros) - set(libros_por_id))
            if ids_faltantes:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=MSG_LIBRO_INEXISTENTE,
                )

            for renglon_dato in datos.renglones:
                libro = libros_por_id[renglon_dato.libro_id]
                if libro.stock < renglon_dato.cantidad:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=MSG_STOCK_INSUFICIENTE.format(titulo=libro.titulo),
                    )

            total = sum(
                (
                    libros_por_id[renglon_dato.libro_id].precio
                    * renglon_dato.cantidad
                    for renglon_dato in datos.renglones
                ),
                Decimal("0.00"),
            )

            venta = Venta(cliente_id=datos.cliente_id, total=total)
            venta.renglones = [
                RenglonVenta(
                    libro_id=renglon_dato.libro_id,
                    cantidad=renglon_dato.cantidad,
                    precio_unitario=libros_por_id[renglon_dato.libro_id].precio,
                )
                for renglon_dato in datos.renglones
            ]
            venta = await uow.ventas.add(venta)

            for renglon_dato in datos.renglones:
                await uow.registrar_movimiento_stock(
                    libro=libros_por_id[renglon_dato.libro_id],
                    usuario_id=usuario_id,
                    cantidad=-renglon_dato.cantidad,
                    motivo="Venta",
                    venta_id=venta.id,
                )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=MSG_CONFLICTO,
        ) from exc

    venta_con_detalle = await uow.ventas.get_detalle(venta.id)
    return _a_read(venta_con_detalle)


async def listar_paginado(
    uow: VentasUnitOfWork,
    page: int = 1,
    size: int = 20,
) -> Page[VentaRead]:
    from app.core.paginacion import Page
    items, total = await uow.ventas.listar_paginado(page=page, size=size)
    items_read = [_a_read(v) for v in items]
    try:
        return Page.create(items=items_read, total=total, page=page, size=size)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La página {page} solicitada excede el total de páginas disponibles",
        )


async def listar_por_cliente(
    uow: VentasUnitOfWork,
    cliente_id: int,
) -> list[VentaRead]:
    cliente = await uow.clientes.get_by_id(cliente_id)
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un cliente con ese id",
        )
    ventas = await uow.ventas.listar_por_cliente(cliente_id)
    return [_a_read(v) for v in ventas]


async def listar_por_usuario(
    uow: VentasUnitOfWork,
    usuario: Usuario,
    page: int = 1,
    size: int = 20,
) -> Page[VentaRead]:
    from app.core.paginacion import Page
    cliente = await uow.clientes.get_by_usuario_id(usuario.id)
    if cliente is None:
        return Page.create(items=[], total=0, page=page, size=size)
    items, total = await uow.ventas.listar_paginado(page=page, size=size, cliente_id=cliente.id)
    items_read = [_a_read(v) for v in items]
    try:
        return Page.create(items=items_read, total=total, page=page, size=size)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La página {page} solicitada excede el total de páginas disponibles",
        )


async def obtener_por_id_con_acceso(
    uow: VentasUnitOfWork,
    venta_id: int,
    usuario: Usuario,
) -> VentaRead:
    venta = await uow.ventas.get_detalle(venta_id)
    if venta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una venta con ese id",
        )
    is_owner = False
    if venta.cliente and venta.cliente.usuario_id == usuario.id:
        is_owner = True

    if not is_owner:
        roles_vigentes = await uow.roles.get_roles_vigentes(usuario.id)
        if not set(roles_vigentes).intersection({"VENDEDOR", "ADMIN"}):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para ver esta venta",
            )
    return _a_read(venta)
