# Design

## Context

El proyecto ya cuenta con:
- `app/core/config.py`: `Settings` con `jwt_secret_key`, `jwt_algorithm` (`HS256`), `jwt_expire_seconds`, `cookie_secure`, `bcrypt_rounds` y `bcrypt_max_concurrency`.
- `app/main.py`: `lifespan` que inicializa `app.state.engine`, `app.state.session_factory` y precalcula `app.state.dummy_hash` al iniciar el servidor, además de montar `open_router` y `protected_router`.
- `app/modules/usuarios/models.py` y `app/modules/clientes/models.py`: Modelos `Usuario`, `AsignacionRol`, `IntentoAcceso`, `EventoSeguridad` y `Cliente` (con `usuario_id` único).
- `app/core/repository.py` y `app/core/unit_of_work.py`: `BaseRepository[T]` (con `flush()`, sin `commit()`) y `UnitOfWork` base (`commit()` / `rollback()` sin cerrar la sesión).

Ver `proposal.md` para la motivación y `specs/autenticacion-seguridad/spec.md` para el contrato de comportamiento.

## Goals / Non-Goals

**Goals:**
- Implementar `app/core/security.py` con operaciones `bcrypt` fuera del event loop (`asyncio.to_thread` + `asyncio.Semaphore`), validación de 72 bytes UTF-8, firma/verificación de JWT (`PyJWT`) y manejo de la cookie `access_token`.
- Implementar los repositorios de `usuarios` y `clientes` y el `UsuarioUnitOfWork` respetando las 5 capas (`Router → Service → UoW → Repository → Model`).
- Aislar el registro de `IntentoAcceso` en una sesión y transacción propia (`request.app.state.session_factory`) con el comentario técnico de 3 puntos exigido en el Ejercicio 7.
- Exponer los 5 endpoints de `/auth/*` en el `open_router` (`POST /auth/registro`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/yo`, `POST /auth/cambiar-password`).

**Non-Goals:**
- No implementa el bloqueo global de rutas del `protected_router` ni `requiere_rol(*roles)` para recursos de negocio ni los endpoints `/usuarios*` y `/eventos` (pertenecen a `C-05 autorizacion-usuarios-eventos`).

## Decisions

### 1. Ejecución de `bcrypt` en `asyncio.to_thread` bajo `asyncio.Semaphore` antes del `UnitOfWork`
- **Decisión**: Encapsular `hash_password` y `verify_password` en `app/core/security.py` usando un `asyncio.Semaphore(settings.bcrypt_max_concurrency)` global al proceso y `await asyncio.to_thread(...)`. En `UsuarioService`, calcular o verificar los hashes **antes** de entrar al bloque `async with uow:`.
- **Alternativas consideradas**:
  - Ejecutar `bcrypt` sincrónicamente en el handler o servicio: bloquea el event loop de Uvicorn (~250-300 ms por petición).
  - Ejecutar `bcrypt` dentro de `async with uow:`: retiene innecesariamente una conexión del pool de PostgreSQL con una transacción abierta mientras la CPU calcula el hash.
- **Justificación**: Cumple `DD-04` y las reglas duras del parcial: evita el bloqueo del bucle de eventos, limita el uso concurrente de CPU y mantiene las transacciones de base de datos lo más cortas posible.

### 2. Validación reutilizable de contraseña (`<= 72 bytes UTF-8`) en esquemas Pydantic
- **Decisión**: Definir un tipo anotado o validador reutilizable (`PasswordStr`) con `@AfterValidator` en `app/core/security.py` (o en `schemas.py` importado desde `security.py`) que verifique `len(v.encode("utf-8")) <= 72` (además de longitud mínima no vacía), aplicable a `password`, `password_actual` y `password_nueva` en todos los esquemas de entrada con `ConfigDict(extra="forbid")`.
- **Alternativas consideradas**: Capturar `ValueError` de `bcrypt` en el servicio.
- **Justificación**: Las versiones modernas de `bcrypt` lanzan `ValueError` cuando la contraseña supera los 72 bytes en UTF-8, lo que produciría un `500 Internal Server Error`. Validar en la capa de contrato Pydantic garantiza devolver `422 Unprocessable Entity` antes de tocar el servicio (`RN-15`).

### 3. Sesión y transacción independientes para `IntentoAcceso` (Ejercicio 7b)
- **Decisión**: Crear una función dedicada `registrar_intento_acceso(session_factory, *, email: str, ip: str, exito: bool)` que abra `async with session_factory() as audit_session:` y confirme con `await audit_session.commit()` de forma independiente de la sesión de `Depends(get_session)` y del `UnitOfWork` de la petición.
- **Alternativas consideradas**: Usar el mismo `UnitOfWork` de la petición y hacer `commit()` manual antes de levantar `HTTPException(401)`.
- **Justificación**: Cumple explícitamente el Ejercicio 7 y `DD-03`. Documentará en un comentario de 3 puntos:
  1. Por qué no usa el `UnitOfWork` de la petición.
  2. Qué ocurriría con el límite de 5 intentos en 60 s si compartiera la transacción que hace `rollback` al fallar el login.
  3. Qué fila queda confirmada en `intento_acceso` aunque el resto de la petición devuelva error (`401`).

### 4. Cálculo de la ventana de Rate Limiting en `POST /auth/login` (`RN-07`)
- **Decisión**: En `IntentoAccesoRepository.contar_fallos_recientes(email, ip, ventana_segundos=60)`, consultar en la tabla `intento_acceso`:
  1. La marca de tiempo `ultimo_exito` del último intento con `exito = True` para ese `(email, ip)` dentro de los últimos 60 segundos (si existe).
  2. La cantidad de filas con `exito = False` para ese `(email, ip)` donde `cuando >= max(ahora - 60s, ultimo_exito)` y el instante `cuando` del primer fallo de esa serie para calcular los segundos restantes de `Retry-After` (entre `1` y `60`).
- **Alternativas consideradas**: Contar todos los fallos de los últimos 60 s ignorando si hubo un login exitoso intermedio.
- **Justificación**: Respeta `RN-07` ("Un login exitoso reinicia la cuenta: los fallos anteriores siguen en `intento_acceso`, pero dejan de contar porque se cuenta desde el último éxito"). Aprovecha el índice compuesto `ix_intento_acceso_email_ip_cuando`.

### 5. Transporte del JWT en cookie `access_token` y dependencia de lectura para `/auth/yo` y `/auth/cambiar-password`
- **Decisión**:
  - El JWT contiene `{"sub": str(usuario.id), "roles": roles_vigentes, "exp": ...}`.
  - `set_auth_cookie(response, token)` configura `key="access_token"`, `value=token`, `httponly=True`, `samesite="lax"`, `max_age=settings.jwt_expire_seconds`, `secure=settings.cookie_secure`, `path="/"`.
  - Para `GET /auth/yo` y `POST /auth/cambiar-password`, extraer y decodificar exclusivamente `request.cookies.get("access_token")`, cargando el `Usuario` activo en la misma sesión de `Depends(get_session)` (función que en `C-05` será promovida/reutilizada en `app/core/dependencies.py`).

## Risks / Trade-offs

- **[Risk] Colisión de `email` en auto-registro cuando ya existe una ficha de `cliente` creada en mostrador (`usuario_id IS NULL`)** → **Mitigación**: `RN-02` prohíbe apropiarse de una ficha previa. Tanto `usuario.email` como `cliente.email` tienen restricción `UNIQUE`; cualquier `IntegrityError` al hacer `flush()`/`commit()` dentro de `async with uow:` dispara `rollback()` automático de las 3 inserciones (`usuario`, `asignacion_rol`, `cliente`) y se traduce en el servicio a `HTTPException(status_code=409, detail=...)`.
- **[Risk] Diferencia de tiempo de respuesta entre correo existente e inexistente en login** → **Mitigación**: Si `usuarios.get_by_email(email)` devuelve `None` (o `not usuario.activo`), se invoca igualmente `verify_password(password, request.app.state.dummy_hash)` antes de registrar el fallo y responder `401` con mensaje idéntico (`"Credenciales inválidas"`).

## Migration Plan

- No requiere nuevas migraciones de Alembic: las tablas `usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad` y la columna `cliente.usuario_id` ya fueron creadas en la 3.ª migración (`8d29d5d17a3a_agregar_seguridad_y_plantilla_c02.py`).
- El rollback consiste simplemente en revertir los archivos de código agregados y la línea de inclusión en `app/main.py`.

## UI Mockups

Decision: no (no UI)
