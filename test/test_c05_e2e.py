import asyncio
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import httpx
from app.core.database import create_engine, create_session_factory
from app.core.security import hash_password
from app.main import app
from app.modules.usuarios.models import AsignacionRol, Usuario


async def setup_admin_user() -> tuple[str, str]:
    engine = create_engine()
    session_factory = create_session_factory(engine)
    admin_email = "superadmin@libreria.com"
    admin_pwd = "AdminPassword123!"

    async with session_factory() as session:
        from sqlalchemy import select

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
                desde=datetime.now(timezone.utc),
            )
            session.add(rol)
            await session.commit()
            print("Admin inicial creado para pruebas C-05.")

    await engine.dispose()
    return admin_email, admin_pwd


async def test_e2e_c05():
    print("Iniciando pruebas E2E de C-05...")
    admin_email, admin_pwd = await setup_admin_user()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        async with app.router.lifespan_context(app):
            # 1. Login con Admin
            print("1. Login con Super Admin...")
            res_admin_login = await client.post(
                "/auth/login",
                json={"email": admin_email, "password": admin_pwd},
            )
            assert res_admin_login.status_code == 200, f"Login de admin falló: {res_admin_login.text}"
            assert "access_token" in client.cookies

            # 2. Alta de personal: POST /usuarios con clave provisoria
            staff_email = f"staff_{int(asyncio.get_event_loop().time())}@libreria.com"
            staff_pwd_provisoria = "Provisoria123!"
            print(f"2. Admin crea nuevo personal ({staff_email}) con clave provisoria...")
            res_create_staff = await client.post(
                "/usuarios",
                json={
                    "nombre": "Vendedor Prueba",
                    "email": staff_email,
                    "password_provisoria": staff_pwd_provisoria,
                    "rol_inicial": "VENDEDOR",
                },
            )
            assert res_create_staff.status_code == 201, f"Error al crear personal: {res_create_staff.text}"
            staff_data = res_create_staff.json()
            assert staff_data["debe_cambiar_password"] is True
            staff_id = staff_data["id"]

            # 3. Probar colisión al crear personal con el mismo correo -> 409
            print("3. Probando colisión 409 al registrar personal con correo repetido...")
            res_dup_staff = await client.post(
                "/usuarios",
                json={
                    "nombre": "Vendedor Duplicado",
                    "email": staff_email,
                    "password_provisoria": "OtraClave123!",
                    "rol_inicial": "VENDEDOR",
                },
            )
            assert res_dup_staff.status_code == 409, f"Esperaba 409 pero fue {res_dup_staff.status_code}"

            # 4. Probar Bloqueo RN-06: Empleado con debe_cambiar_password=True
            print("4. Empleado inicia sesión con clave provisoria y comprueba bloqueo 403...")
            # Cliente HTTP separado para el nuevo empleado
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as staff_client:
                res_staff_login = await staff_client.post(
                    "/auth/login",
                    json={"email": staff_email, "password": staff_pwd_provisoria},
                )
                assert res_staff_login.status_code == 200
                assert res_staff_login.json()["debe_cambiar_password"] is True

                # GET /auth/yo debe funcionar (está en open_router)
                res_staff_yo = await staff_client.get("/auth/yo")
                assert res_staff_yo.status_code == 200
                assert res_staff_yo.json()["debe_cambiar_password"] is True

                # Intento de acceder a CUALQUIER ruta protegida -> 403 Forbidden (RN-06)
                res_blocked = await staff_client.get("/ventas/")
                assert res_blocked.status_code == 403, f"Esperaba 403 pero fue {res_blocked.status_code}: {res_blocked.text}"
                print("   Bloqueo exitoso en ruta protegida por contraseña pendiente (403 Forbidden).")

                # El empleado cambia su contraseña
                print("5. Empleado cambia su contraseña obligatoria...")
                res_staff_change = await staff_client.post(
                    "/auth/cambiar-password",
                    json={
                        "password_actual": staff_pwd_provisoria,
                        "password_nueva": "ClaveDefinitivaSegura789!",
                    },
                )
                assert res_staff_change.status_code == 200

                # Ahora la ruta protegida no lo bloquea por clave provisoria
                # /ventas/ responde 200
                res_unblocked = await staff_client.get("/ventas/")
                assert res_unblocked.status_code == 200, f"Esperaba 200 pero fue {res_unblocked.status_code}"

                # Pero si intenta acceder a rutas de ADMIN (/usuarios o /eventos), recibe 403 por falta de rol!
                res_forbidden_admin = await staff_client.get("/eventos")
                assert res_forbidden_admin.status_code == 403, "VENDEDOR no debe poder ver /eventos"
                print("   Control de rol verificado: 403 para VENDEDOR en ruta ADMIN.")

            # 6. Admin asigna rol con validación de fechas (POST /usuarios/{id}/roles)
            print("6. Admin asigna nuevo rol con validación estricta de fechas...")
            # Fecha pasada -> 422
            past_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            res_past = await client.post(
                f"/usuarios/{staff_id}/roles",
                json={"rol": "ADMIN", "vence_en": past_date},
            )
            assert res_past.status_code == 422, f"Esperaba 422 con fecha pasada pero fue {res_past.status_code}"

            # Fecha naive (sin timezone) -> 422
            naive_date = "2030-01-01T12:00:00"
            res_naive = await client.post(
                f"/usuarios/{staff_id}/roles",
                json={"rol": "ADMIN", "vence_en": naive_date},
            )
            assert res_naive.status_code == 422, f"Esperaba 422 con fecha naive pero fue {res_naive.status_code}"

            # Fecha futura con timezone -> 201 Created (Se le asigna rol ADMIN al staff)
            future_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
            res_assign = await client.post(
                f"/usuarios/{staff_id}/roles",
                json={"rol": "ADMIN", "vence_en": future_date},
            )
            assert res_assign.status_code == 201, f"Fallo al asignar rol: {res_assign.text}"

            # Intento de reasignar rol ADMIN que ya está vigente -> 409 Conflict
            res_dup_role = await client.post(
                f"/usuarios/{staff_id}/roles",
                json={"rol": "ADMIN", "vence_en": future_date},
            )
            assert res_dup_role.status_code == 409, f"Esperaba 409 con rol duplicado vigente: {res_dup_role.status_code}"

            # 7. Consultar roles del usuario (GET /usuarios/{id}/roles)
            print("7. Consultando historial de roles del usuario...")
            res_roles = await client.get(f"/usuarios/{staff_id}/roles")
            assert res_roles.status_code == 200
            roles_list = res_roles.json()
            roles_nombres = [r["rol"] for r in roles_list]
            assert "VENDEDOR" in roles_nombres
            assert "ADMIN" in roles_nombres

            # 8. Autoprotección de Administradores (DELETE /usuarios/{id}/roles/ADMIN)
            print("8. Probando autoprotección de administradores (RN-05)...")
            admin_yo = (await client.get("/auth/yo")).json()
            admin_id = admin_yo["id"]

            # Caso A: Admin intenta auto-revocarse el rol ADMIN -> 409
            res_self_revoke = await client.delete(f"/usuarios/{admin_id}/roles/ADMIN")
            assert res_self_revoke.status_code == 409, f"Esperaba 409 en auto-revocación pero fue {res_self_revoke.status_code}"
            print("   Auto-revocación rechazada correctamente con 409.")

            # Caso B: Admin revoca el rol ADMIN al staff (quedará 1 solo admin: el superadmin) -> 200 OK
            res_revoke_staff = await client.delete(f"/usuarios/{staff_id}/roles/ADMIN")
            assert res_revoke_staff.status_code == 200, f"Revocación de admin staff falló: {res_revoke_staff.text}"

            # Caso C: Ahora solo queda 1 admin en el sistema. Si se intentara revocar (creando un tercer admin y revocándolo, o si fuera posible)
            # Para probar el conteo de acefalía, intentamos revocar de nuevo a ese usuario ya revocado -> 404
            res_not_found_role = await client.delete(f"/usuarios/{staff_id}/roles/ADMIN")
            assert res_not_found_role.status_code == 404

            # 9. Consulta paginada de eventos de seguridad (GET /eventos)
            print("9. Probando listado paginado de eventos de seguridad...")
            res_eventos = await client.get("/eventos?page=1&size=5")
            assert res_eventos.status_code == 200
            eventos_data = res_eventos.json()
            assert "items" in eventos_data
            assert "total" in eventos_data
            assert eventos_data["total"] >= 3
            assert len(eventos_data["items"]) <= 5
            print(f"   Eventos auditados encontrados: {eventos_data['total']} eventos registrados.")

    print("¡TODOS LOS ESCENARIOS E2E DE C-05 PASARON CON ÉXITO TOTAL!")


if __name__ == "__main__":
    asyncio.run(test_e2e_c05())
