import asyncio
import os
import sys
from pathlib import Path

# Resolver la ruta base del proyecto para evitar colisiones con stdlib
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import httpx
from app.core.database import create_engine, create_session_factory
from app.core.security import hash_password
from app.main import app
from app.modules.usuarios.models import AsignacionRol, Usuario


async def setup_admin_and_catalog():
    engine = create_engine()
    session_factory = create_session_factory(engine)
    admin_email = "superadmin@libreria.com"
    admin_pwd = "AdminPassword123!"

    async with session_factory() as session:
        from sqlmodel import select

        stmt = select(Usuario).where(Usuario.email == admin_email)
        res = await session.exec(stmt)
        admin = res.first()

        if not admin:
            pwd_hash = await hash_password(admin_pwd)
            admin = Usuario(
                email=admin_email,
                nombre="Super Admin",
                password_hash=pwd_hash,
                activo=True,
                debe_cambiar_password=False,
            )
            session.add(admin)
            await session.flush()

            rol = AsignacionRol(
                usuario_id=admin.id,
                rol="ADMIN",
                otorgada_por=admin.id,
            )
            session.add(rol)
            await session.commit()
        else:
            admin.activo = True
            admin.debe_cambiar_password = False
            await session.commit()

        # Asegurar al menos una editorial, género y autor para pruebas
        from app.modules.autores.models import Autor
        from app.modules.editoriales.models import Editorial
        from app.modules.generos.models import Genero

        res_ed = await session.exec(select(Editorial).limit(1))
        ed = res_ed.first()
        if not ed:
            ed = Editorial(nombre="Editorial C06", pais="Argentina")
            session.add(ed)
            await session.flush()

        res_gen = await session.exec(select(Genero).limit(1))
        gen = res_gen.first()
        if not gen:
            gen = Genero(nombre="Genero C06")
            session.add(gen)
            await session.flush()

        res_aut = await session.exec(select(Autor).limit(1))
        aut = res_aut.first()
        if not aut:
            aut = Autor(nombre="Autor C06", nacionalidad="Argentina")
            session.add(aut)
            await session.flush()

        await session.commit()
        ed_id = ed.id
        gen_id = gen.id
        aut_id = aut.id

    await engine.dispose()
    return admin_email, admin_pwd, ed_id, gen_id, aut_id


async def test_e2e_c06():
    print("Iniciando pruebas E2E de C-06 (Catálogo, Stock y Baja Lógica)...")
    admin_email, admin_pwd, ed_id, gen_id, aut_id = await setup_admin_and_catalog()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=True,
    ) as client:
        async with app.router.lifespan_context(app):
            # 1. Login como ADMIN
            print("1. Autenticación de Administrador...")
            res_login = await client.post(
                "/auth/login",
                json={"email": admin_email, "password": admin_pwd},
            )
            assert res_login.status_code == 200, f"Error en login: {res_login.text}"
            assert "access_token" in client.cookies
            print("   Login admin exitoso.")

            # 2. Catálogo inicial y paginación estándar
            print("2. Probando GET /libros con paginación envoltorio...")
            res_cat = await client.get("/libros?page=1&size=5")
            assert res_cat.status_code == 200, f"Error en catálogo: {res_cat.text}"
            cat_data = res_cat.json()
            assert "items" in cat_data
            assert "total" in cat_data
            assert "page" in cat_data
            assert "size" in cat_data
            assert "pages" in cat_data
            assert cat_data["page"] == 1
            assert cat_data["size"] == 5

            # Paginación fuera de rango -> 422
            res_out_of_bounds = await client.get("/libros?page=9999&size=5")
            assert res_out_of_bounds.status_code == 422, f"Esperaba 422 pero fue {res_out_of_bounds.status_code}"
            print("   Validación de paginación fuera de rango (422) exitosa.")

            # 3. Alta de libro con autores y stock inicial (POST /libros)
            print("3. Alta de libro con movimiento inicial (POST /libros)...")
            isbn_test = "978-987-9999-01-1"
            res_create = await client.post(
                "/libros",
                json={
                    "isbn": isbn_test,
                    "titulo": "Libro de Prueba C06",
                    "precio": 12500.50,
                    "stock_inicial": 7,
                    "editorial_id": ed_id,
                    "genero_id": gen_id,
                    "autores": [
                        {"autor_id": aut_id, "rol": "autor", "orden": 1}
                    ],
                },
            )
            assert res_create.status_code == 201, f"Fallo al crear libro: {res_create.text}"
            libro_creado = res_create.json()
            libro_id = libro_creado["id"]
            assert libro_creado["isbn"] == isbn_test
            assert libro_creado["stock"] == 7
            assert libro_creado["borrado_en"] is None
            print(f"   Libro creado (id={libro_id}, stock=7).")

            # Comprobar que se creó automáticamente el movimiento de stock inicial (RN-11)
            res_movs = await client.get(f"/libros/{libro_id}/movimientos")
            assert res_movs.status_code == 200
            movs = res_movs.json()
            assert len(movs) == 1
            assert movs[0]["cantidad"] == 7
            assert movs[0]["motivo"] == "Stock inicial"
            print("   Movimiento de stock inicial verificado en movimiento_stock.")

            # 4. Prohibición estricta de modificación de stock en PATCH /libros/{id}
            print("4. Probando inmutabilidad de stock en PATCH /libros/{id}...")
            res_patch_stock = await client.patch(
                f"/libros/{libro_id}",
                json={"stock": 50},
            )
            assert res_patch_stock.status_code == 422, f"Esperaba 422 pero fue {res_patch_stock.status_code}"
            print("   Intento de modificar stock por PATCH rechazado correctamente con 422 Unprocessable Entity.")

            # Modificación descriptiva válida
            res_patch_valido = await client.patch(
                f"/libros/{libro_id}",
                json={"titulo": "Libro de Prueba C06 (Edición Revisada)", "precio": 14200.00},
            )
            assert res_patch_valido.status_code == 200
            libro_actualizado = res_patch_valido.json()
            assert libro_actualizado["titulo"] == "Libro de Prueba C06 (Edición Revisada)"
            assert libro_actualizado["stock"] == 7, "El stock no debe haber cambiado"
            print("   Actualización descriptiva permitida conservando stock intacto.")

            # 5. Reposición de stock (POST /libros/{id}/reponer)
            print("5. Probando reposición de stock (POST /libros/{id}/reponer)...")
            res_reponer = await client.post(
                f"/libros/{libro_id}/reponer",
                json={"cantidad": 13, "motivo": "Ingreso de imprenta"},
            )
            assert res_reponer.status_code == 200, f"Error al reponer stock: {res_reponer.text}"
            mov_reponer = res_reponer.json()
            assert mov_reponer["cantidad"] == 13
            assert mov_reponer["motivo"] == "Ingreso de imprenta"

            # Comprobar stock consolidado: 7 + 13 = 20
            res_detalle = await client.get(f"/libros/{libro_id}")
            assert res_detalle.status_code == 200
            assert res_detalle.json()["stock"] == 20
            print("   Stock actualizado a 20 mediante punto único de escritura.")

            # Comprobar historial de movimientos: ahora son 2
            res_movs_2 = await client.get(f"/libros/{libro_id}/movimientos")
            assert res_movs_2.status_code == 200
            assert len(res_movs_2.json()) == 2

            # 6. Baja lógica (DELETE /libros/{id})
            print("6. Probando baja lógica de libros (DELETE /libros/{id})...")
            res_delete = await client.delete(f"/libros/{libro_id}")
            assert res_delete.status_code == 204
            print("   Baja lógica respondió 204 No Content.")

            # Comprobar que ya no aparece en GET /libros/{id}
            res_get_deleted = await client.get(f"/libros/{libro_id}")
            assert res_get_deleted.status_code == 404, f"Esperaba 404 pero fue {res_get_deleted.status_code}"
            print("   Libro dado de baja responde 404 en consulta individual.")

            # Comprobar que no se puede reponer stock a un libro dado de baja
            res_reponer_deleted = await client.post(
                f"/libros/{libro_id}/reponer",
                json={"cantidad": 5},
            )
            assert res_reponer_deleted.status_code == 404
            print("   Intento de reponer libro dado de baja rechazado con 404.")

            # Comprobar que el historial de movimientos sigue disponible para ADMIN
            res_movs_deleted = await client.get(f"/libros/{libro_id}/movimientos")
            assert res_movs_deleted.status_code == 200
            assert len(res_movs_deleted.json()) == 2
            print("   Historial de movimientos conservado y accesible para ADMIN.")

            # 7. Liberación y reutilización de ISBN vigente (RN-01, RN-13)
            print("7. Probando liberación y reutilización de ISBN tras baja lógica...")
            # Crear un NUEVO libro activo usando el MISMO ISBN que el libro dado de baja
            res_reuse_isbn = await client.post(
                "/libros",
                json={
                    "isbn": isbn_test,
                    "titulo": "Nuevo Libro con ISBN Reutilizado",
                    "precio": 9990.00,
                    "stock_inicial": 3,
                    "editorial_id": ed_id,
                    "genero_id": gen_id,
                    "autores": [
                        {"autor_id": aut_id, "rol": "autor", "orden": 1}
                    ],
                },
            )
            assert res_reuse_isbn.status_code == 201, f"Fallo al reutilizar ISBN liberado: {res_reuse_isbn.text}"
            nuevo_libro = res_reuse_isbn.json()
            assert nuevo_libro["isbn"] == isbn_test
            assert nuevo_libro["id"] != libro_id
            print("   ISBN reutilizado exitosamente en libro nuevo gracias al índice parcial.")

            # Pero un tercer libro con ese mismo ISBN mientras este está activo debe dar 409 Conflict
            res_dup_isbn = await client.post(
                "/libros",
                json={
                    "isbn": isbn_test,
                    "titulo": "Tercer Libro Duplicado",
                    "precio": 5000.00,
                    "stock_inicial": 1,
                    "editorial_id": ed_id,
                    "genero_id": gen_id,
                },
            )
            assert res_dup_isbn.status_code == 409, f"Esperaba 409 pero fue {res_dup_isbn.status_code}"
            print("   ISBN duplicado en libro activo rechazado con 409 Conflict.")

            # 8. Paginación en Editoriales y Géneros
            print("8. Probando paginación estándar en Editoriales y Géneros...")
            res_eds = await client.get("/editoriales?page=1&size=5")
            assert res_eds.status_code == 200
            assert "items" in res_eds.json()
            assert "total" in res_eds.json()

            res_gens = await client.get("/generos?page=1&size=5")
            assert res_gens.status_code == 200
            assert "items" in res_gens.json()
            assert "total" in res_gens.json()

            res_eds_oob = await client.get("/editoriales?page=9999&size=5")
            assert res_eds_oob.status_code == 422
            print("   Paginación estándar Page[T] en Editoriales y Géneros verificada.")

    print("¡TODOS LOS ESCENARIOS E2E DE C-06 PASARON CON ÉXITO TOTAL!")


if __name__ == "__main__":
    asyncio.run(test_e2e_c06())
