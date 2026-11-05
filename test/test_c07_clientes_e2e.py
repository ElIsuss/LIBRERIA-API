import asyncio
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import httpx
from sqlalchemy import delete, func, select

from app.core.database import create_engine, create_session_factory
from app.core.security import hash_password
from app.main import app
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro
from app.modules.usuarios.models import AsignacionRol, Usuario
from app.modules.ventas.models import RenglonVenta, Venta

PASSWORD = "ClaveSegura123!"


async def preparar_datos():
    engine = create_engine()
    session_factory = create_session_factory(engine)
    sufijo = uuid4().hex[:10]
    datos = {"sufijo": sufijo, "password": PASSWORD}

    password_hash = await hash_password(PASSWORD)

    async with session_factory() as session:
        definiciones = (
            ("admin", "ADMIN", False),
            ("vendedor", "VENDEDOR", False),
            ("cliente", "CLIENTE", False),
            ("pendiente", "VENDEDOR", True),
        )
        for clave, rol, debe_cambiar in definiciones:
            email = f"c07_{clave}_{sufijo}@test.com"
            usuario = Usuario(
                email=email,
                nombre=f"Usuario {clave}",
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
                    desde=datetime.now(timezone.utc),
                )
            )
            datos[f"{clave}_email"] = email
            datos[f"{clave}_id"] = usuario.id

        cliente_semilla = Cliente(
            nombre="Cliente Semilla",
            email=f"c07_semilla_{sufijo}@test.com",
        )
        session.add(cliente_semilla)
        await session.flush()
        session.add(
            PerfilCliente(
                cliente_id=cliente_semilla.id,
                telefono="1144556677",
                direccion="Av. Semilla 100",
            )
        )
        datos["cliente_semilla_id"] = cliente_semilla.id

        editorial = Editorial(nombre=f"Editorial Clientes {sufijo}", pais="Argentina")
        genero = Genero(nombre=f"Genero Clientes {sufijo}")
        session.add(editorial)
        session.add(genero)
        await session.flush()
        datos["editorial_id"] = editorial.id
        datos["genero_id"] = genero.id

        libro_vigente = Libro(
            isbn=f"9791{sufijo[:10]}",
            titulo=f"Libro Vigente Clientes {sufijo}",
            precio=Decimal("120.00"),
            stock=8,
            editorial_id=editorial.id,
            genero_id=genero.id,
        )
        libro_baja = Libro(
            isbn=f"9792{sufijo[:10]}",
            titulo=f"Libro Baja Clientes {sufijo}",
            precio=Decimal("60.00"),
            stock=3,
            editorial_id=editorial.id,
            genero_id=genero.id,
            borrado_en=datetime.now(timezone.utc),
        )
        session.add(libro_vigente)
        session.add(libro_baja)
        await session.flush()
        datos["libro_vigente_id"] = libro_vigente.id
        datos["libro_baja_id"] = libro_baja.id
        datos["libro_baja_titulo"] = libro_baja.titulo

        ahora = datetime.now(timezone.utc)
        venta_reciente = Venta(
            cliente_id=cliente_semilla.id,
            total=Decimal("120.00"),
            fecha=ahora - timedelta(days=1),
        )
        venta_antigua = Venta(
            cliente_id=cliente_semilla.id,
            total=Decimal("120.00"),
            fecha=ahora - timedelta(days=3),
        )
        session.add(venta_reciente)
        session.add(venta_antigua)
        await session.flush()
        session.add_all(
            [
                RenglonVenta(
                    venta_id=venta_reciente.id,
                    libro_id=libro_vigente.id,
                    cantidad=1,
                    precio_unitario=Decimal("120.00"),
                ),
                RenglonVenta(
                    venta_id=venta_antigua.id,
                    libro_id=libro_baja.id,
                    cantidad=2,
                    precio_unitario=Decimal("60.00"),
                ),
            ]
        )
        datos["venta_reciente_id"] = venta_reciente.id
        datos["venta_antigua_id"] = venta_antigua.id
        await session.commit()

    await engine.dispose()
    return datos


async def limpiar_datos(datos):
    engine = create_engine()
    session_factory = create_session_factory(engine)
    patron = f"%{datos['sufijo']}%"

    async with session_factory() as session:
        ids_ventas = [datos["venta_reciente_id"], datos["venta_antigua_id"]]
        await session.execute(
            delete(RenglonVenta).where(RenglonVenta.venta_id.in_(ids_ventas))
        )
        await session.execute(delete(Venta).where(Venta.id.in_(ids_ventas)))
        await session.execute(
            delete(Libro).where(
                Libro.id.in_([datos["libro_vigente_id"], datos["libro_baja_id"]])
            )
        )
        await session.execute(
            delete(Editorial).where(Editorial.id == datos["editorial_id"])
        )
        await session.execute(delete(Genero).where(Genero.id == datos["genero_id"]))

        ids_clientes = select(Cliente.id).where(Cliente.email.like(patron))
        await session.execute(
            delete(PerfilCliente).where(PerfilCliente.cliente_id.in_(ids_clientes))
        )
        await session.execute(delete(Cliente).where(Cliente.email.like(patron)))

        ids_usuarios = [
            datos["admin_id"],
            datos["vendedor_id"],
            datos["cliente_id"],
            datos["pendiente_id"],
        ]
        await session.execute(
            delete(AsignacionRol).where(AsignacionRol.usuario_id.in_(ids_usuarios))
        )
        await session.execute(delete(Usuario).where(Usuario.id.in_(ids_usuarios)))
        await session.commit()

    await engine.dispose()


async def contar_clientes_por_email(email: str) -> int:
    engine = create_engine()
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        resultado = await session.execute(
            select(func.count()).select_from(Cliente).where(Cliente.email == email)
        )
        total = int(resultado.scalar_one())
    await engine.dispose()
    return total


async def contar_perfiles_por_cliente(cliente_id: int) -> int:
    engine = create_engine()
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        resultado = await session.execute(
            select(func.count())
            .select_from(PerfilCliente)
            .where(PerfilCliente.cliente_id == cliente_id)
        )
        total = int(resultado.scalar_one())
    await engine.dispose()
    return total


async def iniciar_sesion(client: httpx.AsyncClient, email: str) -> None:
    respuesta = await client.post(
        "/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert respuesta.status_code == 200, f"Login falló para {email}: {respuesta.text}"


async def test_e2e_c07_clientes():
    print("Iniciando pruebas E2E de C-07 (módulo clientes)...")
    datos = await preparar_datos()
    sufijo = datos["sufijo"]

    transport = httpx.ASGITransport(app=app)
    try:
        async with (
            httpx.AsyncClient(
                transport=transport, base_url="http://test", follow_redirects=True
            ) as admin_client,
            httpx.AsyncClient(
                transport=transport, base_url="http://test", follow_redirects=True
            ) as vendedor_client,
            httpx.AsyncClient(
                transport=transport, base_url="http://test", follow_redirects=True
            ) as cliente_client,
            httpx.AsyncClient(
                transport=transport, base_url="http://test", follow_redirects=True
            ) as pendiente_client,
            httpx.AsyncClient(
                transport=transport, base_url="http://test", follow_redirects=True
            ) as anon_client,
        ):
            async with app.router.lifespan_context(app):
                await iniciar_sesion(admin_client, datos["admin_email"])
                await iniciar_sesion(vendedor_client, datos["vendedor_email"])
                await iniciar_sesion(cliente_client, datos["cliente_email"])

                print("1. Probando POST /clientes ...")
                email_nuevo = f"c07_nuevo_{sufijo}@test.com"
                res_alta = await vendedor_client.post(
                    "/clientes/",
                    json={"nombre": "Cliente Nuevo", "email": email_nuevo},
                )
                assert res_alta.status_code == 201, f"Esperaba 201: {res_alta.text}"
                cliente_nuevo = res_alta.json()
                assert cliente_nuevo["nombre"] == "Cliente Nuevo"
                assert cliente_nuevo["email"] == email_nuevo
                assert cliente_nuevo["perfil"] is None

                res_duplicado = await admin_client.post(
                    "/clientes/",
                    json={"nombre": "Cliente Duplicado", "email": email_nuevo},
                )
                assert res_duplicado.status_code == 409, (
                    f"Esperaba 409 por correo duplicado: {res_duplicado.text}"
                )
                assert await contar_clientes_por_email(email_nuevo) == 1

                res_extra = await admin_client.post(
                    "/clientes/",
                    json={
                        "nombre": "Cliente Extra",
                        "email": f"c07_extra_{sufijo}@test.com",
                        "extra": "no permitido",
                    },
                )
                assert res_extra.status_code == 422, (
                    f"Esperaba 422 por campo extra: {res_extra.text}"
                )

                res_email_invalido = await admin_client.post(
                    "/clientes/",
                    json={"nombre": "Cliente Inválido", "email": "no-es-un-email"},
                )
                assert res_email_invalido.status_code == 422, (
                    f"Esperaba 422 por correo inválido: {res_email_invalido.text}"
                )

                print("2. Probando GET /clientes/{id} ...")
                res_con_perfil = await vendedor_client.get(
                    f"/clientes/{datos['cliente_semilla_id']}"
                )
                assert res_con_perfil.status_code == 200, res_con_perfil.text
                datos_con_perfil = res_con_perfil.json()
                assert datos_con_perfil["perfil"] is not None
                assert datos_con_perfil["perfil"]["telefono"] == "1144556677"
                assert datos_con_perfil["perfil"]["direccion"] == "Av. Semilla 100"

                res_sin_perfil = await vendedor_client.get(
                    f"/clientes/{cliente_nuevo['id']}"
                )
                assert res_sin_perfil.status_code == 200, res_sin_perfil.text
                assert res_sin_perfil.json()["perfil"] is None

                res_inexistente = await admin_client.get("/clientes/999999999")
                assert res_inexistente.status_code == 404, res_inexistente.text

                print("3. Probando PATCH /clientes/{id} ...")
                email_actualizado = f"c07_patch_{sufijo}@test.com"
                res_patch = await vendedor_client.patch(
                    f"/clientes/{cliente_nuevo['id']}",
                    json={
                        "nombre": "Cliente Actualizado",
                        "email": email_actualizado,
                    },
                )
                assert res_patch.status_code == 200, res_patch.text
                cliente_actualizado = res_patch.json()
                assert cliente_actualizado["nombre"] == "Cliente Actualizado"
                assert cliente_actualizado["email"] == email_actualizado

                res_patch_duplicado = await admin_client.patch(
                    f"/clientes/{cliente_nuevo['id']}",
                    json={"email": f"c07_semilla_{sufijo}@test.com"},
                )
                assert res_patch_duplicado.status_code == 409, (
                    f"Esperaba 409 por correo duplicado: {res_patch_duplicado.text}"
                )

                res_releer = await vendedor_client.get(
                    f"/clientes/{cliente_nuevo['id']}"
                )
                assert res_releer.status_code == 200
                assert res_releer.json()["nombre"] == "Cliente Actualizado"
                assert res_releer.json()["email"] == email_actualizado

                res_patch_inexistente = await vendedor_client.patch(
                    "/clientes/999999999",
                    json={"nombre": "Fantasma"},
                )
                assert res_patch_inexistente.status_code == 404, (
                    res_patch_inexistente.text
                )

                res_patch_extra = await admin_client.patch(
                    f"/clientes/{cliente_nuevo['id']}",
                    json={"nombre": "Otro", "extra": "no permitido"},
                )
                assert res_patch_extra.status_code == 422, res_patch_extra.text

                print("4. Probando control de acceso por rol ...")
                res_cliente_post = await cliente_client.post(
                    "/clientes/",
                    json={
                        "nombre": "Cliente No Autorizado",
                        "email": f"c07_noautorizado_{sufijo}@test.com",
                    },
                )
                assert res_cliente_post.status_code == 403, (
                    f"Esperaba 403 para rol CLIENTE: {res_cliente_post.text}"
                )

                res_cliente_get = await cliente_client.get(
                    f"/clientes/{cliente_nuevo['id']}"
                )
                assert res_cliente_get.status_code == 403, (
                    f"Esperaba 403 para rol CLIENTE: {res_cliente_get.text}"
                )

                res_admin_get = await admin_client.get(
                    f"/clientes/{cliente_nuevo['id']}"
                )
                assert res_admin_get.status_code == 200, (
                    f"Esperaba 200 para rol ADMIN: {res_admin_get.text}"
                )

                print("5. Probando POST /clientes/{id}/perfil ...")
                res_perfil = await vendedor_client.post(
                    f"/clientes/{cliente_nuevo['id']}/perfil",
                    json={
                        "telefono": "1122334455",
                        "direccion": "Calle Perfil 123",
                    },
                )
                assert res_perfil.status_code == 201, res_perfil.text
                perfil = res_perfil.json()
                assert perfil["cliente_id"] == cliente_nuevo["id"]
                assert perfil["telefono"] == "1122334455"
                assert perfil["direccion"] == "Calle Perfil 123"

                res_con_perfil_nuevo = await vendedor_client.get(
                    f"/clientes/{cliente_nuevo['id']}"
                )
                assert res_con_perfil_nuevo.status_code == 200
                assert res_con_perfil_nuevo.json()["perfil"]["id"] == perfil["id"]

                res_perfil_duplicado = await admin_client.post(
                    f"/clientes/{cliente_nuevo['id']}/perfil",
                    json={
                        "telefono": "9999999999",
                        "direccion": "Otra Direccion 456",
                    },
                )
                assert res_perfil_duplicado.status_code == 409, (
                    f"Esperaba 409 por segundo perfil: {res_perfil_duplicado.text}"
                )
                assert await contar_perfiles_por_cliente(cliente_nuevo["id"]) == 1

                res_perfil_inexistente = await vendedor_client.post(
                    "/clientes/999999999/perfil",
                    json={
                        "telefono": "1122334455",
                        "direccion": "Calle Perfil 123",
                    },
                )
                assert res_perfil_inexistente.status_code == 404, (
                    res_perfil_inexistente.text
                )

                res_perfil_extra = await admin_client.post(
                    f"/clientes/{cliente_nuevo['id']}/perfil",
                    json={
                        "telefono": "1122334455",
                        "direccion": "Calle Perfil 123",
                        "extra": "no permitido",
                    },
                )
                assert res_perfil_extra.status_code == 422, res_perfil_extra.text

                print(
                    "6. Probando 401 sin cookie y 403 con cambio de password pendiente ..."
                )
                await iniciar_sesion(pendiente_client, datos["pendiente_email"])

                rutas_protegidas = (
                    (
                        "POST",
                        "/clientes/",
                        {
                            "nombre": "Cliente Anónimo",
                            "email": f"c07_anonimo_{sufijo}@test.com",
                        },
                    ),
                    ("GET", f"/clientes/{cliente_nuevo['id']}", None),
                    (
                        "PATCH",
                        f"/clientes/{cliente_nuevo['id']}",
                        {"nombre": "Cliente Anónimo"},
                    ),
                    (
                        "POST",
                        f"/clientes/{cliente_nuevo['id']}/perfil",
                        {"telefono": "1122334455", "direccion": "Calle 1"},
                    ),
                )

                for metodo, ruta, cuerpo in rutas_protegidas:
                    kwargs = {"json": cuerpo} if cuerpo is not None else {}
                    res_anonimo = await anon_client.request(metodo, ruta, **kwargs)
                    assert res_anonimo.status_code == 401, (
                        f"Esperaba 401 sin cookie en {metodo} {ruta}: "
                        f"{res_anonimo.status_code} {res_anonimo.text}"
                    )

                for metodo, ruta, cuerpo in rutas_protegidas:
                    kwargs = {"json": cuerpo} if cuerpo is not None else {}
                    res_pendiente = await pendiente_client.request(
                        metodo, ruta, **kwargs
                    )
                    assert res_pendiente.status_code == 403, (
                        f"Esperaba 403 con cambio pendiente en {metodo} {ruta}: "
                        f"{res_pendiente.status_code} {res_pendiente.text}"
                    )
    finally:
        await limpiar_datos(datos)

    print("¡TODOS LOS ESCENARIOS E2E DE C-07 CLIENTES (GRUPO 3) PASARON!")


if __name__ == "__main__":
    asyncio.run(test_e2e_c07_clientes())
