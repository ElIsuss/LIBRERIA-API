import asyncio
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import httpx
from app.main import app


async def test_e2e_c04():
    print("Iniciando pruebas E2E de C-04...")
    # Use httpx.AsyncClient with lifespan handler
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        # Trigger app lifespan
        async with app.router.lifespan_context(app):
            test_email = f"test_e2e_{int(asyncio.get_event_loop().time())}@libreria.com"

            # 1. Validación 422 con contraseña > 72 bytes en UTF-8
            print("1. Probando rechazo 422 con contraseña > 72 bytes UTF-8...")
            res_73 = await client.post(
                "/auth/registro",
                json={
                    "nombre": "Test Long Pwd",
                    "email": "long@test.com",
                    "password": "a" * 73,
                },
            )
            assert res_73.status_code == 422, f"Esperaba 422 pero obtuvo {res_73.status_code}"

            # 2. Validación 422 con campo extra (extra='forbid')
            print("2. Probando rechazo 422 con campo extra...")
            res_extra = await client.post(
                "/auth/registro",
                json={
                    "nombre": "Test Extra",
                    "email": "extra@test.com",
                    "password": "clave_valida_123",
                    "rol": "ADMIN",
                },
            )
            assert res_extra.status_code == 422, f"Esperaba 422 pero obtuvo {res_extra.status_code}"

            # 3. Auto-registro exitoso 201
            print(f"3. Probando auto-registro exitoso con {test_email}...")
            res_reg = await client.post(
                "/auth/registro",
                json={
                    "nombre": "Cliente E2E",
                    "email": test_email,
                    "password": "PasswordSegura123!",
                },
            )
            assert res_reg.status_code == 201, f"Fallo registro: {res_reg.text}"
            data_reg = res_reg.json()
            assert data_reg["email"] == test_email
            assert data_reg["activo"] is True
            assert data_reg["debe_cambiar_password"] is False

            # 4. Colisión de correo 409
            print("4. Probando colisión 409 con el mismo correo...")
            res_dup = await client.post(
                "/auth/registro",
                json={
                    "nombre": "Cliente Duplicado",
                    "email": test_email,
                    "password": "PasswordSegura123!",
                },
            )
            assert res_dup.status_code == 409, f"Esperaba 409 pero obtuvo {res_dup.status_code}"

            # 5. Rate limiting: 5 fallos en 60s seguidos del 6to que da 429
            print("5. Probando 5 fallos y posterior bloqueo 429 Retry-After...")
            brute_email = f"brute_{int(asyncio.get_event_loop().time())}@test.com"
            for i in range(5):
                res_fail = await client.post(
                    "/auth/login",
                    json={"email": brute_email, "password": "clave_incorrecta"},
                )
                assert res_fail.status_code == 401, f"Intento {i+1} no devolvió 401: {res_fail.status_code}"

            # 6.º intento -> debe dar 429
            res_429 = await client.post(
                "/auth/login",
                json={"email": brute_email, "password": "clave_incorrecta"},
            )
            assert res_429.status_code == 429, f"Esperaba 429 pero obtuvo {res_429.status_code}: {res_429.text}"
            assert "Retry-After" in res_429.headers, "Falta cabecera Retry-After"
            print(f"   Rate limit activado: 429, Retry-After={res_429.headers['Retry-After']}")

            # 6. Login exitoso con credenciales válidas
            print("6. Probando login exitoso con cookie HttpOnly...")
            res_login = await client.post(
                "/auth/login",
                json={"email": test_email, "password": "PasswordSegura123!"},
            )
            assert res_login.status_code == 200, f"Login falló: {res_login.text}"
            data_login = res_login.json()
            # Body NO debe contener tokens
            assert "token" not in data_login, "El cuerpo no debe contener token"
            assert "access_token" not in data_login, "El cuerpo no debe contener access_token"
            assert data_login["mensaje"] == "Sesión iniciada"
            # Cookie access_token debe estar presente
            assert "access_token" in client.cookies, "Falta cookie access_token en el cliente"

            # 7. GET /auth/yo con la sesión actual
            print("7. Probando GET /auth/yo...")
            res_yo = await client.get("/auth/yo")
            assert res_yo.status_code == 200, f"GET /auth/yo falló: {res_yo.text}"
            data_yo = res_yo.json()
            assert data_yo["email"] == test_email
            assert "CLIENTE" in data_yo["roles_vigentes"], f"Falta rol CLIENTE en vigentes: {data_yo['roles_vigentes']}"
            assert "CLIENTE" in data_yo["roles_token"], f"Falta rol CLIENTE en token: {data_yo['roles_token']}"

            # 8. POST /auth/cambiar-password
            print("8. Probando POST /auth/cambiar-password...")
            # Clave actual errónea -> 401
            res_bad_pwd = await client.post(
                "/auth/cambiar-password",
                json={
                    "password_actual": "clave_falsa",
                    "password_nueva": "NuevaClaveSuperSegura456!",
                },
            )
            assert res_bad_pwd.status_code == 401, f"Esperaba 401 con clave actual errónea: {res_bad_pwd.text}"

            # Clave actual correcta -> 200
            res_change = await client.post(
                "/auth/cambiar-password",
                json={
                    "password_actual": "PasswordSegura123!",
                    "password_nueva": "NuevaClaveSuperSegura456!",
                },
            )
            assert res_change.status_code == 200, f"Fallo cambio de contraseña: {res_change.text}"

            # 9. POST /auth/logout
            print("9. Probando POST /auth/logout...")
            res_logout = await client.post("/auth/logout")
            assert res_logout.status_code == 200, f"Logout falló: {res_logout.text}"

            # Comprobar que tras logout /auth/yo da 401
            # (Removemos la cookie del cliente para simular el navegador que la borró)
            client.cookies.clear()
            res_yo_after = await client.get("/auth/yo")
            assert res_yo_after.status_code == 401, f"Esperaba 401 tras logout: {res_yo_after.status_code}"

            print("10. Probando login con la nueva contraseña...")
            res_new_login = await client.post(
                "/auth/login",
                json={"email": test_email, "password": "NuevaClaveSuperSegura456!"},
            )
            assert res_new_login.status_code == 200, f"Login con nueva clave falló: {res_new_login.text}"

    print("¡TODOS LOS ESCENARIOS E2E DE C-04 PASARON CON ÉXITO TOTAL!")


if __name__ == "__main__":
    asyncio.run(test_e2e_c04())
