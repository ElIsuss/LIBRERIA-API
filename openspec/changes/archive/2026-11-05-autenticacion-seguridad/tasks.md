# Tasks

## 1. Núcleo de Seguridad Criptográfica, JWT y Cookies (`app/core/security.py`)

- [x] 1.1 Implementar en `app/core/security.py` el validador reutilizable de contraseña (`<= 72 bytes UTF-8`) y las funciones `hash_password` y `verify_password` con `asyncio.to_thread` y `asyncio.Semaphore(settings.bcrypt_max_concurrency)`, verificando mediante pruebas unitarias que una clave de 73 bytes UTF-8 es rechazada y que un hash generado se verifica correctamente.
- [x] 1.2 Implementar en `app/core/security.py` las funciones `create_access_token`, `decode_access_token`, `set_auth_cookie` y `clear_auth_cookie` (`HttpOnly=True`, `SameSite="lax"`, `Max-Age=settings.jwt_expire_seconds`, `Secure=settings.cookie_secure`), verificando con pruebas en memoria la codificación/decodificación de claims (`sub`, `roles`, `exp`), el rechazo de tokens expirados/inválidos y las cabeceras `Set-Cookie`.

## 2. Repositorios, `UnitOfWork` y Sesión Independiente de `IntentoAcceso`

- [x] 2.1 Crear `app/modules/clientes/repository.py` (`ClienteRepository(BaseRepository[Cliente])` con `get_by_email` y `get_by_usuario_id`) y `app/modules/usuarios/repository.py` (`UsuarioRepository`, `AsignacionRolRepository` con consulta de roles vigentes en BD, `IntentoAccesoRepository` con conteo de fallos recientes desde el último éxito y `EventoSeguridadRepository`), verificando que heredan de `BaseRepository` y sólo ejecutan `flush()` sin `commit()`.
- [x] 2.2 Crear `app/modules/usuarios/unit_of_work.py` (`UsuarioUnitOfWork(UnitOfWork)`) exponiendo `usuarios`, `roles`, `intentos`, `eventos` y `clientes` sobre la misma `AsyncSession`, junto con el proveedor `get_usuario_uow(session=Depends(get_session))`, verificando su importación e inicialización de repositorios.
- [x] 2.3 Implementar la función de auditoría `registrar_intento_acceso` en sesión y transacción independientes (`session_factory`) incluyendo el comentario obligatorio de 3 puntos del Ejercicio 7 (por qué no usa el `UnitOfWork`, qué pasaría con el límite de intentos si compartiera transacción y qué fila queda confirmada aunque el resto falle), verificando que la fila en `intento_acceso` persiste aunque la operación principal falle.

## 3. Contratos Pydantic y Servicio de Autenticación (`schemas.py` y `service.py`)

- [x] 3.1 Crear `app/modules/usuarios/schemas.py` con `ConfigDict(extra="forbid")` y validación de 72 bytes UTF-8 para `RegistroRequest`, `LoginRequest`, `CambiarPasswordRequest` y los esquemas de salida `UsuarioAuthResponse`, `LoginResponse`, `YoResponse` y `MensajeResponse`, verificando con pruebas de validación que campos extra como `rol` o claves de más de 72 bytes en UTF-8 producen `ValidationError` (`422`).
- [x] 3.2 Implementar en `app/modules/usuarios/service.py` los métodos de negocio `registrar_cliente` (`RN-01`, `RN-02`), `login` (rate-limit de 5 fallos en 60s con `Retry-After` sin `bcrypt` `RN-07`, verificación en tiempo constante con `dummy_hash` `RN-08`, grabación en sesión propia y emisión de token), `obtener_perfil_yo` y `cambiar_password` (`RN-06`, `RN-16`), verificando que todo cálculo `bcrypt` ocurra antes de `async with uow:`.

## 4. Endpoints `/auth/*` e Integración en `app/main.py`

- [x] 4.1 Crear `app/modules/usuarios/router.py` con las rutas `POST /auth/registro` (`201`, `409`, `422`), `POST /auth/login` (`200`, `401`, `422`, `429`), `POST /auth/logout` (`200`), `GET /auth/yo` (`200`, `401`) y `POST /auth/cambiar-password` (`200`, `401`, `422`), e incluir el router en `open_router` dentro de `app/main.py`, verificando que OpenAPI (`/docs`) expone los 5 endpoints bajo el tag `auth`.
- [x] 4.2 Verificar de punta a punta los flujos de `C-04` (auto-registro atómico y colisión `409`, login exitoso con cookie `HttpOnly` sin token en el body, `GET /auth/yo`, bloqueo `429` con `Retry-After` al 6.º intento fallido en 60s, cambio de contraseña auditado en `evento_seguridad` y `POST /auth/logout`).

## Workflow follow-up

- Archivar el change con `/opsx:archive autenticacion-seguridad` una vez completadas y verificadas todas las tareas.
- Actualizar el estado de `[C-04]` en `CHANGES.md`.
