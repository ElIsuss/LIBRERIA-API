# Proposal

## Why

El proyecto ya dispone de la configuración base (`C-01`), los modelos y migraciones de seguridad (`C-02`) y las abstracciones de persistencia `BaseRepository` y `UnitOfWork` (`C-03`), pero aún no cuenta con el mecanismo de autenticación ni con los endpoints `/auth/*`. Este cambio (**C-04 — Ejercicios 4 y 7b**) incorpora el hashing no bloqueante con `bcrypt`, la gestión de sesión mediante JWT en cookie `HttpOnly`, la protección contra fuerza bruta con persistencia independiente en `intento_acceso` y los flujos de auto-registro, login, logout, consulta de sesión y cambio de contraseña, desbloqueando el control de acceso para el resto del sistema (`C-05` a `C-08`).

## What Changes

- **Módulo de seguridad criptográfica y cookies (`app/core/security.py`)**:
  - Ejecución de `bcrypt` (`hashpw` y `checkpw`) fuera del bucle de eventos mediante `await asyncio.to_thread(...)` acotado por un `asyncio.Semaphore(settings.bcrypt_max_concurrency)` y siempre **antes** de abrir el `UnitOfWork`.
  - Validador reutilizable de contraseñas que garantiza un máximo de **72 bytes en UTF-8** (`len(v.encode("utf-8")) <= 72`), devolviendo `422 Unprocessable Entity` y nunca `500`.
  - Emisión y decodificación de JWT (`PyJWT`, `HS256`) con claims `sub` (ID del usuario), `exp` y `roles` (lista informativa de roles vigentes al momento de iniciar sesión).
  - Helpers para escribir y eliminar la cookie `access_token` (`HttpOnly=True`, `SameSite="lax"`, `Max-Age=settings.jwt_expire_seconds`, `Secure=settings.cookie_secure`).
- **Repositorios y `UnitOfWork` de autenticación (`app/modules/usuarios/repository.py`, `app/modules/usuarios/unit_of_work.py`, `app/modules/clientes/repository.py`)**:
  - Repositorios para `Usuario`, `AsignacionRol`, `IntentoAcceso`, `EventoSeguridad` y `Cliente` heredando de `BaseRepository` (usando únicamente `flush()`, nunca `commit()`).
  - `UsuarioUnitOfWork` que agrupa `usuarios`, `roles`, `eventos` y `clientes` bajo la misma `AsyncSession` de la petición.
- **Auditoría de `IntentoAcceso` en sesión y transacción independientes (Ejercicio 7b)**:
  - Función dedicada que abre su propia sesión desde `request.app.state.session_factory` y ejecuta `commit()` inmediatamente para registrar cada intento de login (exitoso o fallido), acompañada del comentario explicativo de 3 puntos exigido por la consigna (por qué no usa el `UnitOfWork`, qué pasaría con el límite de intentos si compartiera transacción y qué fila queda confirmada aunque el resto falle).
- **Contratos, servicio y endpoints `/auth/*` (`app/modules/usuarios/schemas.py`, `service.py`, `router.py`)**:
  - `POST /auth/registro` (`201`, `409`, `422`): auto-registro atómico con `extra="forbid"` que crea `Usuario`, `AsignacionRol(rol="CLIENTE")` y `Cliente(usuario_id=usuario.id)` en un único `UnitOfWork` (`RN-02`), traduciendo colisiones de correo en `usuario` o `cliente` a `409 Conflict` sin apropiarse de fichas previas (`RN-01`, `RN-15`).
  - `POST /auth/login` (`200`, `401`, `422`, `429`): verifica primero el límite de 5 intentos fallidos en los últimos 60 segundos para `(email, ip)` posteriores al último éxito (`429 Too Many Requests` + cabecera `Retry-After` sin ejecutar `bcrypt`, `RN-07`); verifica contraseña en tiempo constante usando `app.state.dummy_hash` cuando el correo no existe o está inactivo (`RN-08`); registra el intento en sesión propia; emite el JWT únicamente en la cookie `access_token` y devuelve `{"mensaje": "Sesión iniciada", "debe_cambiar_password": ..., "expira_en_segundos": ...}`.
  - `POST /auth/logout` (`200`): borra la cookie `access_token`.
  - `GET /auth/yo` (`200`, `401`): identifica al usuario activo desde la cookie `access_token` y devuelve su perfil junto con `roles_vigentes` (consultados en BD) y `roles_token` (declarados en el JWT).
  - `POST /auth/cambiar-password` (`200`, `401`, `422`): verifica la contraseña actual, calcula el nuevo hash fuera de la transacción y en un único `UnitOfWork` actualiza `password_hash`, marca `debe_cambiar_password = False` e inserta una fila en `evento_seguridad` (`RN-06`, `RN-16`) sin invalidar la cookie actual.

## Capabilities

### New Capabilities
- `autenticacion-seguridad`: Autenticación de usuarios mediante cookies `HttpOnly` y JWT, hashing `bcrypt` no bloqueante con límite de 72 bytes UTF-8 y semáforo, control de fuerza bruta con auditoría de intentos en sesión independiente, auto-registro atómico de clientes y cambio de contraseña auditado.

### Modified Capabilities
<!-- No hay capacidades existentes que modificar en openspec/specs/ -->

## Impact

- **Nuevos archivos previstos para la fase de aplicación**:
  - `app/core/security.py`
  - `app/modules/clientes/repository.py`
  - `app/modules/usuarios/repository.py`
  - `app/modules/usuarios/unit_of_work.py`
  - `app/modules/usuarios/schemas.py`
  - `app/modules/usuarios/service.py`
  - `app/modules/usuarios/router.py`
- **Archivos existentes afectados en la fase de aplicación**:
  - `app/main.py` (registro del router de `/auth` dentro de `open_router`).
- **Dependencias de paquetes**: Usa exclusivamente paquetes ya presentes en `requirements.txt` (`bcrypt`, `pyjwt`, `fastapi[standard]`, `sqlmodel`, `sqlalchemy[asyncio]`).
