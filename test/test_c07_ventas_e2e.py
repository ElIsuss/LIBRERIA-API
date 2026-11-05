import asyncio
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import httpx
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import create_engine, create_session_factory
from app.core.security import hash_password
from app.main import app
from app.modules.clientes.models import Cliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, MovimientoStock
from app.modules.usuarios.models import AsignacionRol, Usuario
from app.modules.ventas.models import RenglonVenta, Venta

PASSWORD = "ClaveSegura123!"


def crear_fabrica_de_sesiones(connection):
    return async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        join_transaction_mode="create_savepoint",
    )


async def preparar_datos(session_factory):
    sufijo = uuid4().hex[:10]
    ahora = datetime.now(timezone.utc)
    datos = {"sufijo": sufijo, "password": PASSWORD}

    password_hash = await hash_password(PASSWORD)

    async with session_factory() as session:
        definiciones = (
            ("admin", "ADMIN", False),
            ("vendedor", "VENDEDOR", False),
            ("revocado", "VENDEDOR", False),
            ("cliente_a", "CLIENTE", False),
            ("cliente_b", "CLIENTE", False),
            ("sin_ficha", "CLIENTE", False),
            ("pendiente", "VENDEDOR", True),
        )
        for clave, rol, debe_cambiar in definiciones:
            email = f"c07v_{clave}_{sufijo}@test.com"
            usuario = Usuario(
                email=email,
                nombre=f"Usuario ventas {clave}",
                password_hash=password_hash,
                activo=True,
                debe_cambiar_password=debe_cambiar,
            )
            session.add(usuario)
            await session.flush()
            session.add(
                AsignacionRol(
                    usuario_id=usuario.id,
                    rol=rol,
                    desde=ahora,
                )
            )
            datos[f"{clave}_email"] = email
            datos[f"{clave}_id"] = usuario.id

        editorial = Editorial(nombre=f"Editorial Ventas {sufijo}", pais="Argentina")
        genero = Genero(nombre=f"Genero Ventas {sufijo}")
        session.add(editorial)
        session.add(genero)
        await session.flush()
        datos["editorial_id"] = editorial.id
        datos["genero_id"] = genero.id

        cliente_a = Cliente(
            nombre="Cliente Dueno Ventas",
            email=f"c07v_cliente_a_{sufijo}@test.com",
            usuario_id=datos["cliente_a_id"],
        )
        cliente_b = Cliente(
            nombre="Cliente Ajeno Ventas",
            email=f"c07v_cliente_b_{sufijo}@test.com",
            usuario_id=datos["cliente_b_id"],
        )
        session.add(cliente_a)
        session.add(cliente_b)
        await session.flush()
        datos["cliente_a_id"] = cliente_a.id
        datos["cliente_b_id"] = cliente_b.id

        libros_definicion = (
            ("libro1", "Libro Uno E2E", "100.00", 10, False),
            ("libro2", "Libro Dos E2E", "50.00", 10, False),
            ("libro3", "Libro Tres E2E", "25.00", 5, False),
            ("libro4", "Libro Cuatro E2E", "40.00", 5, False),
            ("libro5", "Libro Cinco E2E", "30.00", 1, False),
            ("libro_baja", "Libro Dado de Baja E2E", "20.00", 3, True),
            ("libro_hist_activo", "Libro Historico Activo E2E", "10.00", 5, False),
            ("libro_hist_baja", "Libro Historico Baja E2E", "15.00", 4, True),
        )
        for indice, (clave, titulo, precio, stock_inicial, borrado) in enumerate(
            libros_definicion, start=1
        ):
            libro = Libro(
                isbn=f"978{indice:02d}{sufijo[:10]}",
                titulo=f"{titulo} {sufijo}",
                precio=Decimal(precio),
                stock=stock_inicial,
                editorial_id=editorial.id,
                genero_id=genero.id,
                borrado_en=ahora if borrado else None,
            )
            session.add(libro)
            await session.flush()
            session.add(
                MovimientoStock(
                    libro_id=libro.id,
                    usuario_id=datos["admin_id"],
                    cantidad=stock_inicial,
                    motivo="Stock inicial",
                )
            )
            datos[f"{clave}_id"] = libro.id
            datos[f"{clave}_titulo"] = libro.titulo
            datos[f"{clave}_precio"] = libro.precio
            datos[f"{clave}_stock_inicial"] = stock_inicial

        venta_historica = Venta(
            cliente_id=cliente_a.id,
            total=Decimal("40.00"),
            fecha=ahora - timedelta(days=2),
        )
        session.add(venta_historica)
        await session.flush()
        session.add_all(
            [
                RenglonVenta(
                    venta_id=venta_historica.id,
                    libro_id=datos["libro_hist_activo_id"],
                    cantidad=1,
                    precio_unitario=Decimal("10.00"),
                ),
                RenglonVenta(
                    venta_id=venta_historica.id,
                    libro_id=datos["libro_hist_baja_id"],
                    cantidad=2,
                    precio_unitario=Decimal("15.00"),
                ),
            ]
        )
        session.add_all(
            [
                MovimientoStock(
                    libro_id=datos["libro_hist_activo_id"],
                    venta_id=venta_historica.id,
                    usuario_id=datos["admin_id"],
                    cantidad=-1,
                    motivo="Venta",
                ),
                MovimientoStock(
                    libro_id=datos["libro_hist_baja_id"],
                    venta_id=venta_historica.id,
                    usuario_id=datos["admin_id"],
                    cantidad=-2,
                    motivo="Venta",
                ),
            ]
        )
        libros_por_id = {
            datos["libro_hist_activo_id"]: 5 - 1,
            datos["libro_hist_baja_id"]: 4 - 2,
        }
        for libro_id, stock_final in libros_por_id.items():
            libro = await session.get(Libro, libro_id)
            libro.stock = stock_final

        datos["venta_historica_id"] = venta_historica.id
        await session.commit()

    return datos


async def obtener_libro(session_factory, libro_id: int) -> dict:
    async with session_factory() as session:
        libro = await session.get(Libro, libro_id)
        return {
            "stock": libro.stock,
            "precio": libro.precio,
            "titulo": libro.titulo,
        }


async def obtener_movimientos_por_venta(session_factory, venta_id: int) -> list[dict]:
    async with session_factory() as session:
        resultado = await session.execute(
            select(MovimientoStock)
            .where(MovimientoStock.venta_id == venta_id)
            .order_by(MovimientoStock.id)
        )
        return [
            {
                "libro_id": m.libro_id,
                "usuario_id": m.usuario_id,
                "cantidad": m.cantidad,
                "motivo": m.motivo,
                "venta_id": m.venta_id,
            }
            for m in resultado.scalars().all()
        ]


async def sumar_movimientos(session_factory, libro_id: int) -> int:
    async with session_factory() as session:
        resultado = await session.execute(
            select(func.coalesce(func.sum(MovimientoStock.cantidad), 0)).where(
                MovimientoStock.libro_id == libro_id
            )
        )
        return int(resultado.scalar_one())


async def contar_ventas(session_factory) -> int:
    async with session_factory() as session:
        resultado = await session.execute(select(func.count()).select_from(Venta))
        return int(resultado.scalar_one())


async def medir_selects_de_peticion(client: httpx.AsyncClient, ruta: str):
    consultas = []

    def registrar(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            consultas.append(statement)

    event.listen(app.state.engine.sync_engine, "before_cursor_execute", registrar)
    try:
        respuesta = await client.get(ruta)
    finally:
        event.remove(app.state.engine.sync_engine, "before_cursor_execute", registrar)

    return respuesta, consultas


async def iniciar_sesion(client: httpx.AsyncClient, email: str) -> None:
    respuesta = await client.post(
        "/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert respuesta.status_code == 200, f"Login falló para {email}: {respuesta.text}"


async def test_e2e_c07_ventas():
    print("Iniciando pruebas E2E de C-07 (módulo ventas)...")

    async with app.router.lifespan_context(app):
        engine = create_engine()
        connection = await engine.connect()
        transaction = await connection.begin()
        session_factory = crear_fabrica_de_sesiones(connection)
        app.state.engine = engine
        app.state.session_factory = session_factory

        transport = httpx.ASGITransport(app=app)
        try:
            datos = await preparar_datos(session_factory)

            async with (
                httpx.AsyncClient(
                    transport=transport, base_url="http://test", follow_redirects=True
                ) as admin_client,
                httpx.AsyncClient(
                    transport=transport, base_url="http://test", follow_redirects=True
                ) as vendedor_client,
                httpx.AsyncClient(
                    transport=transport, base_url="http://test", follow_redirects=True
                ) as cliente_a_client,
                httpx.AsyncClient(
                    transport=transport, base_url="http://test", follow_redirects=True
                ) as cliente_b_client,
                httpx.AsyncClient(
                    transport=transport, base_url="http://test", follow_redirects=True
                ) as pendiente_client,
                httpx.AsyncClient(
                    transport=transport, base_url="http://test", follow_redirects=True
                ) as sin_ficha_client,
                httpx.AsyncClient(
                    transport=transport, base_url="http://test", follow_redirects=True
                ) as revocado_client,
                httpx.AsyncClient(
                    transport=transport, base_url="http://test", follow_redirects=True
                ) as anon_client,
            ):
                await iniciar_sesion(admin_client, datos["admin_email"])
                await iniciar_sesion(vendedor_client, datos["vendedor_email"])
                await iniciar_sesion(cliente_a_client, datos["cliente_a_email"])
                await iniciar_sesion(cliente_b_client, datos["cliente_b_email"])
                await iniciar_sesion(sin_ficha_client, datos["sin_ficha_email"])
                await iniciar_sesion(revocado_client, datos["revocado_email"])
                await iniciar_sesion(pendiente_client, datos["pendiente_email"])

                print("1. Probando POST /ventas exitoso ...")
                stock_libro1_antes = (
                    await obtener_libro(session_factory, datos["libro1_id"])
                )["stock"]
                stock_libro2_antes = (
                    await obtener_libro(session_factory, datos["libro2_id"])
                )["stock"]

                res_venta = await vendedor_client.post(
                    "/ventas/",
                    json={
                        "cliente_id": datos["cliente_a_id"],
                        "renglones": [
                            {"libro_id": datos["libro1_id"], "cantidad": 2},
                            {"libro_id": datos["libro2_id"], "cantidad": 3},
                        ],
                    },
                )
                assert res_venta.status_code == 201, res_venta.text
                venta = res_venta.json()
                venta_id = venta["id"]
                datos["venta_creada_id"] = venta_id

                assert venta["cliente"]["id"] == datos["cliente_a_id"]
                assert Decimal(str(venta["total"])) == Decimal("350.00")

                renglones_por_libro = {
                    renglon["libro_id"]: renglon for renglon in venta["renglones"]
                }
                renglon1 = renglones_por_libro[datos["libro1_id"]]
                renglon2 = renglones_por_libro[datos["libro2_id"]]
                assert Decimal(str(renglon1["precio_unitario"])) == Decimal(
                    str(datos["libro1_precio"])
                )
                assert Decimal(str(renglon2["precio_unitario"])) == Decimal(
                    str(datos["libro2_precio"])
                )
                assert Decimal(str(renglon1["subtotal"])) == Decimal("200.00")
                assert Decimal(str(renglon2["subtotal"])) == Decimal("150.00")
                assert renglon1["titulo"] == datos["libro1_titulo"]
                assert renglon2["titulo"] == datos["libro2_titulo"]

                movimientos = await obtener_movimientos_por_venta(
                    session_factory, venta_id
                )
                assert len(movimientos) == 2, movimientos
                movimientos_por_libro = {
                    movimiento["libro_id"]: movimiento for movimiento in movimientos
                }
                assert movimientos_por_libro[datos["libro1_id"]]["cantidad"] == -2
                assert movimientos_por_libro[datos["libro2_id"]]["cantidad"] == -3
                for movimiento in movimientos:
                    assert movimiento["venta_id"] == venta_id
                    assert movimiento["usuario_id"] == datos["vendedor_id"]
                    assert movimiento["motivo"] == "Venta"

                stock_libro1 = await obtener_libro(session_factory, datos["libro1_id"])
                stock_libro2 = await obtener_libro(session_factory, datos["libro2_id"])
                assert stock_libro1["stock"] == stock_libro1_antes - 2
                assert stock_libro2["stock"] == stock_libro2_antes - 3
                assert stock_libro1["stock"] == await sumar_movimientos(
                    session_factory, datos["libro1_id"]
                )
                assert stock_libro2["stock"] == await sumar_movimientos(
                    session_factory, datos["libro2_id"]
                )

                print("2. Probando rechazos 409 y rollback total ...")
                ventas_antes = await contar_ventas(session_factory)
                stock_libro1_antes = (
                    await obtener_libro(session_factory, datos["libro1_id"])
                )["stock"]
                movimientos_libro1_antes = await sumar_movimientos(
                    session_factory, datos["libro1_id"]
                )

                res_cliente_inexistente = await vendedor_client.post(
                    "/ventas/",
                    json={
                        "cliente_id": 999999999,
                        "renglones": [
                            {"libro_id": datos["libro1_id"], "cantidad": 1}
                        ],
                    },
                )
                assert res_cliente_inexistente.status_code == 409, (
                    res_cliente_inexistente.text
                )
                assert await contar_ventas(session_factory) == ventas_antes
                assert (
                    await obtener_libro(session_factory, datos["libro1_id"])
                )["stock"] == stock_libro1_antes

                res_libro_inexistente = await vendedor_client.post(
                    "/ventas/",
                    json={
                        "cliente_id": datos["cliente_a_id"],
                        "renglones": [{"libro_id": 999999999, "cantidad": 1}],
                    },
                )
                assert res_libro_inexistente.status_code == 409, (
                    res_libro_inexistente.text
                )
                assert await contar_ventas(session_factory) == ventas_antes

                stock_baja_antes = (
                    await obtener_libro(session_factory, datos["libro_baja_id"])
                )["stock"]
                res_libro_baja = await vendedor_client.post(
                    "/ventas/",
                    json={
                        "cliente_id": datos["cliente_a_id"],
                        "renglones": [
                            {"libro_id": datos["libro_baja_id"], "cantidad": 1}
                        ],
                    },
                )
                assert res_libro_baja.status_code == 409, res_libro_baja.text
                assert await contar_ventas(session_factory) == ventas_antes
                assert (
                    await obtener_libro(session_factory, datos["libro_baja_id"])
                )["stock"] == stock_baja_antes

                stock_libro3_antes = (
                    await obtener_libro(session_factory, datos["libro3_id"])
                )["stock"]
                res_stock_insuficiente = await vendedor_client.post(
                    "/ventas/",
                    json={
                        "cliente_id": datos["cliente_a_id"],
                        "renglones": [{"libro_id": datos["libro3_id"], "cantidad": 6}],
                    },
                )
                assert res_stock_insuficiente.status_code == 409, (
                    res_stock_insuficiente.text
                )
                assert await contar_ventas(session_factory) == ventas_antes
                assert (
                    await obtener_libro(session_factory, datos["libro3_id"])
                )["stock"] == stock_libro3_antes

                res_rollback = await vendedor_client.post(
                    "/ventas/",
                    json={
                        "cliente_id": datos["cliente_a_id"],
                        "renglones": [
                            {"libro_id": datos["libro1_id"], "cantidad": 1},
                            {"libro_id": datos["libro3_id"], "cantidad": 999},
                        ],
                    },
                )
                assert res_rollback.status_code == 409, res_rollback.text
                assert await contar_ventas(session_factory) == ventas_antes
                assert (
                    await obtener_libro(session_factory, datos["libro1_id"])
                )["stock"] == stock_libro1_antes
                assert (
                    await sumar_movimientos(session_factory, datos["libro1_id"])
                    == movimientos_libro1_antes
                )

                print("3. Probando rechazos 422 de contrato ...")
                ventas_antes = await contar_ventas(session_factory)
                payloads_invalidos = (
                    {
                        "cliente_id": datos["cliente_a_id"],
                        "renglones": [],
                    },
                    {
                        "cliente_id": datos["cliente_a_id"],
                        "renglones": [
                            {"libro_id": datos["libro1_id"], "cantidad": 1},
                            {"libro_id": datos["libro1_id"], "cantidad": 2},
                        ],
                    },
                    {
                        "cliente_id": datos["cliente_a_id"],
                        "renglones": [{"libro_id": datos["libro1_id"], "cantidad": 0}],
                    },
                    {
                        "cliente_id": datos["cliente_a_id"],
                        "renglones": [{"libro_id": datos["libro1_id"], "cantidad": 1}],
                        "total": 10,
                    },
                    {
                        "cliente_id": datos["cliente_a_id"],
                        "renglones": [
                            {
                                "libro_id": datos["libro1_id"],
                                "cantidad": 1,
                                "precio_unitario": 1,
                            }
                        ],
                    },
                )
                for payload in payloads_invalidos:
                    res_invalido = await vendedor_client.post(
                        "/ventas/", json=payload
                    )
                    assert res_invalido.status_code == 422, res_invalido.text
                assert await contar_ventas(session_factory) == ventas_antes

                print("4. Probando 403 para rol CLIENTE ...")
                res_cliente = await cliente_a_client.post(
                    "/ventas/",
                    json={
                        "cliente_id": datos["cliente_a_id"],
                        "renglones": [
                            {"libro_id": datos["libro1_id"], "cantidad": 1}
                        ],
                    },
                )
                assert res_cliente.status_code == 403, res_cliente.text
                assert await contar_ventas(session_factory) == ventas_antes

                print("5. Probando aviso en segundo plano ...")
                from app.modules.ventas import service as ventas_service

                llamadas = []
                original_enviar_comprobante = ventas_service.enviar_comprobante

                async def enviar_comprobante_falso(venta_id: int) -> None:
                    llamadas.append(venta_id)

                ventas_service.enviar_comprobante = enviar_comprobante_falso
                try:
                    res_con_aviso = await vendedor_client.post(
                        "/ventas/",
                        json={
                            "cliente_id": datos["cliente_a_id"],
                            "renglones": [
                                {"libro_id": datos["libro2_id"], "cantidad": 1}
                            ],
                        },
                    )
                finally:
                    ventas_service.enviar_comprobante = original_enviar_comprobante

                assert res_con_aviso.status_code == 201, res_con_aviso.text
                assert llamadas == [res_con_aviso.json()["id"]], llamadas

                llamadas.clear()
                ventas_service.enviar_comprobante = enviar_comprobante_falso
                try:
                    res_conflicto = await vendedor_client.post(
                        "/ventas/",
                        json={
                            "cliente_id": 999999999,
                            "renglones": [
                                {"libro_id": datos["libro2_id"], "cantidad": 1}
                            ],
                        },
                    )
                    res_invalido = await vendedor_client.post(
                        "/ventas/",
                        json={
                            "cliente_id": datos["cliente_a_id"],
                            "renglones": [],
                        },
                    )
                finally:
                    ventas_service.enviar_comprobante = original_enviar_comprobante

                assert res_conflicto.status_code == 409, res_conflicto.text
                assert res_invalido.status_code == 422, res_invalido.text
                assert llamadas == [], llamadas

                registros = []

                class CapturadorDeLogs(logging.Handler):
                    def emit(self, record):
                        registros.append(record.getMessage())

                capturador = CapturadorDeLogs()
                logger_ventas = logging.getLogger("app.modules.ventas.service")
                logger_ventas.addHandler(capturador)
                try:
                    inicio = time.monotonic()
                    await original_enviar_comprobante(res_con_aviso.json()["id"])
                    duracion = time.monotonic() - inicio
                finally:
                    logger_ventas.removeHandler(capturador)

                assert duracion >= 0.5, duracion
                assert any(
                    "comprobante" in mensaje.lower()
                    and str(res_con_aviso.json()["id"]) in mensaje
                    for mensaje in registros
                ), registros

                print("6. Probando GET /ventas ...")
                res_listado = await vendedor_client.get("/ventas?page=1&size=100")
                assert res_listado.status_code == 200, res_listado.text
                listado = res_listado.json()
                assert {"items", "total", "page", "size", "pages"} <= set(listado)
                assert listado["page"] == 1
                assert listado["size"] == 100
                assert listado["pages"] >= 1
                assert listado["total"] == len(listado["items"])

                ventas_por_id = {venta["id"]: venta for venta in listado["items"]}
                assert datos["venta_historica_id"] in ventas_por_id
                for venta_listada in listado["items"]:
                    if venta_listada["cliente"]["id"] in {
                        datos["cliente_a_id"],
                        datos["cliente_b_id"],
                    }:
                        assert isinstance(venta_listada["renglones"], list)

                historica = ventas_por_id[datos["venta_historica_id"]]
                titulos_historicos = {
                    renglon["titulo"] for renglon in historica["renglones"]
                }
                assert datos["libro_hist_baja_titulo"] in titulos_historicos

                res_fuera_de_rango = await admin_client.get(
                    "/ventas?page=999&size=10"
                )
                assert res_fuera_de_rango.status_code == 422, (
                    res_fuera_de_rango.text
                )

                res_listado_cliente = await cliente_a_client.get("/ventas")
                assert res_listado_cliente.status_code == 403, (
                    res_listado_cliente.text
                )

                res_antes, consultas_antes = await medir_selects_de_peticion(
                    vendedor_client, "/ventas?page=1&size=100"
                )
                assert res_antes.status_code == 200, res_antes.text

                res_cuatro_renglones = await vendedor_client.post(
                    "/ventas/",
                    json={
                        "cliente_id": datos["cliente_a_id"],
                        "renglones": [
                            {"libro_id": datos["libro1_id"], "cantidad": 1},
                            {"libro_id": datos["libro2_id"], "cantidad": 1},
                            {"libro_id": datos["libro3_id"], "cantidad": 1},
                            {"libro_id": datos["libro4_id"], "cantidad": 1},
                        ],
                    },
                )
                assert res_cuatro_renglones.status_code == 201, (
                    res_cuatro_renglones.text
                )
                datos["venta_cuatro_renglones_id"] = res_cuatro_renglones.json()["id"]

                res_despues, consultas_despues = await medir_selects_de_peticion(
                    vendedor_client, "/ventas?page=1&size=100"
                )
                assert res_despues.status_code == 200, res_despues.text
                ids_despues = {
                    venta["id"] for venta in res_despues.json()["items"]
                }
                assert datos["venta_cuatro_renglones_id"] in ids_despues
                assert len(consultas_antes) == len(consultas_despues), (
                    consultas_antes,
                    consultas_despues,
                )

                print("7. Probando GET /mis-ventas ...")
                res_venta_b = await vendedor_client.post(
                    "/ventas/",
                    json={
                        "cliente_id": datos["cliente_b_id"],
                        "renglones": [
                            {"libro_id": datos["libro4_id"], "cantidad": 1}
                        ],
                    },
                )
                assert res_venta_b.status_code == 201, res_venta_b.text
                datos["venta_cliente_b_id"] = res_venta_b.json()["id"]

                res_mis_ventas = await cliente_a_client.get(
                    "/mis-ventas?page=1&size=100"
                )
                assert res_mis_ventas.status_code == 200, res_mis_ventas.text
                mis_ventas = res_mis_ventas.json()
                assert {"items", "total", "page", "size", "pages"} <= set(mis_ventas)
                assert mis_ventas["page"] == 1
                assert mis_ventas["size"] == 100
                mis_ventas_ids = {venta["id"] for venta in mis_ventas["items"]}
                assert datos["venta_creada_id"] in mis_ventas_ids
                assert datos["venta_cuatro_renglones_id"] in mis_ventas_ids
                assert datos["venta_cliente_b_id"] not in mis_ventas_ids
                assert all(
                    venta["cliente"]["id"] == datos["cliente_a_id"]
                    for venta in mis_ventas["items"]
                )

                res_sin_ficha = await sin_ficha_client.get("/mis-ventas")
                assert res_sin_ficha.status_code == 200, res_sin_ficha.text
                pagina_vacia = res_sin_ficha.json()
                assert pagina_vacia["items"] == []
                assert pagina_vacia["total"] == 0
                assert pagina_vacia["page"] == 1
                assert pagina_vacia["pages"] == 1

                res_mis_ventas_oob = await cliente_a_client.get(
                    "/mis-ventas?page=999&size=10"
                )
                assert res_mis_ventas_oob.status_code == 422, (
                    res_mis_ventas_oob.text
                )

                res_mis_ventas_anon = await anon_client.get("/mis-ventas")
                assert res_mis_ventas_anon.status_code == 401, (
                    res_mis_ventas_anon.text
                )

                res_mis_ventas_pendiente = await pendiente_client.get(
                    "/mis-ventas"
                )
                assert res_mis_ventas_pendiente.status_code == 403, (
                    res_mis_ventas_pendiente.text
                )

                print("9. Probando GET /ventas/{id} ...")
                res_detalle_vendedor = await vendedor_client.get(
                    f"/ventas/{datos['venta_cliente_b_id']}"
                )
                assert res_detalle_vendedor.status_code == 200, (
                    res_detalle_vendedor.text
                )
                assert (
                    res_detalle_vendedor.json()["cliente"]["id"]
                    == datos["cliente_b_id"]
                )

                res_detalle_admin = await admin_client.get(
                    f"/ventas/{datos['venta_creada_id']}"
                )
                assert res_detalle_admin.status_code == 200, res_detalle_admin.text

                res_detalle_dueno = await cliente_a_client.get(
                    f"/ventas/{datos['venta_creada_id']}"
                )
                assert res_detalle_dueno.status_code == 200, res_detalle_dueno.text

                res_detalle_ajeno = await cliente_b_client.get(
                    f"/ventas/{datos['venta_creada_id']}"
                )
                assert res_detalle_ajeno.status_code == 403, (
                    res_detalle_ajeno.text
                )

                res_detalle_inexistente = await vendedor_client.get(
                    "/ventas/999999999"
                )
                assert res_detalle_inexistente.status_code == 404, (
                    res_detalle_inexistente.text
                )

                res_detalle_historica = await vendedor_client.get(
                    f"/ventas/{datos['venta_historica_id']}"
                )
                assert res_detalle_historica.status_code == 200, (
                    res_detalle_historica.text
                )
                titulos_detalle = {
                    renglon["titulo"]
                    for renglon in res_detalle_historica.json()["renglones"]
                }
                assert datos["libro_hist_baja_titulo"] in titulos_detalle

                res_revocado_antes = await revocado_client.get(
                    f"/ventas/{datos['venta_cliente_b_id']}"
                )
                assert res_revocado_antes.status_code == 200, (
                    res_revocado_antes.text
                )

                async with session_factory() as session:
                    resultado_asignacion = await session.execute(
                        select(AsignacionRol).where(
                            AsignacionRol.usuario_id == datos["revocado_id"],
                            AsignacionRol.rol == "VENDEDOR",
                        )
                    )
                    asignacion = resultado_asignacion.scalar_one()
                    asignacion.revocada_en = datetime.now(timezone.utc)
                    await session.commit()

                res_revocado_despues = await revocado_client.get(
                    f"/ventas/{datos['venta_cliente_b_id']}"
                )
                assert res_revocado_despues.status_code == 403, (
                    res_revocado_despues.text
                )

                res_detalle_anon = await anon_client.get(
                    f"/ventas/{datos['venta_creada_id']}"
                )
                assert res_detalle_anon.status_code == 401, res_detalle_anon.text
        finally:
            await transaction.rollback()
            await connection.close()
            await engine.dispose()

    print("¡TODOS LOS ESCENARIOS E2E DE C-07 VENTAS (GRUPO 5) PASARON!")


if __name__ == "__main__":
    asyncio.run(test_e2e_c07_ventas())
