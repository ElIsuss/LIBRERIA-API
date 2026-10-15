import asyncio
import logging
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.clientes.models import Cliente
from app.modules.libros.models import Libro
from app.modules.ventas.models import RenglonVenta, Venta
from app.modules.ventas.schemas import (
    RenglonVentaRead,
    VentaCreate,
    VentaRead,
)

logger = logging.getLogger(__name__)

MSG_CONFLICTO = (
    "No se pudo crear la venta: el cliente o alguno de los libros "
    "no existe, o hay una restricción de integridad incumplida"
)


async def enviar_comprobante(venta_id: int) -> None:
    await asyncio.sleep(0.5)
    logger.info(f"Aviso: comprobante de la venta #{venta_id} enviado al cliente en segundo plano.")


async def crear(session: AsyncSession, datos: VentaCreate) -> VentaRead:
    try:
        # 1. Comprobar que exista el cliente.
        cliente = await session.get(Cliente, datos.cliente_id)

        if cliente is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se puede crear la venta: el cliente indicado no existe",
            )

        # 2. Buscar todos los libros solicitados en una sola consulta.
        ids_libros = [renglon.libro_id for renglon in datos.renglones]

        statement = select(Libro).where(Libro.id.in_(ids_libros))
        resultado = await session.exec(statement)
        libros = resultado.all()

        libros_por_id = {libro.id: libro for libro in libros}
        ids_inexistentes = set(ids_libros) - set(libros_por_id)

        if ids_inexistentes:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "No se puede crear la venta: no existen los libros "
                    f"con estos IDs: {sorted(ids_inexistentes)}"
                ),
            )

        # 3. Calcular el total usando los precios de la base de datos.
        total = Decimal("0.00")
        renglones_nuevos = []

        for renglon_dato in datos.renglones:
            libro = libros_por_id[renglon_dato.libro_id]
            precio = libro.precio
            subtotal = precio * renglon_dato.cantidad
            total += subtotal

            renglones_nuevos.append(
                RenglonVenta(
                    libro_id=libro.id,
                    cantidad=renglon_dato.cantidad,
                    precio_unitario=precio,
                )
            )

        # 4. Crear la venta y obtener su ID.
        venta = Venta(
            cliente_id=datos.cliente_id,
            total=total,
        )
        session.add(venta)
        await session.flush()

        # 5. Asociar cada renglón con la venta creada.
        for renglon in renglones_nuevos:
            renglon.venta_id = venta.id

        session.add_all(renglones_nuevos)
        await session.flush()

        # 6. Confirmar todas las operaciones juntas.
        await session.commit()

    except HTTPException:
        await session.rollback()
        raise

    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=MSG_CONFLICTO,
        )

    # 7. Devolver el resultado sin depender de una carga perezosa.
    return VentaRead(
        id=venta.id,
        fecha=venta.fecha,
        total=venta.total,
        cliente_id=venta.cliente_id,
        renglones=[
            RenglonVentaRead(
                id=renglon.id,
                libro_id=renglon.libro_id,
                cantidad=renglon.cantidad,
                precio_unitario=renglon.precio_unitario,
            )
            for renglon in renglones_nuevos
        ],
    )
