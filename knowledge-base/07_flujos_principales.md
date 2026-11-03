# Flujos Principales

Cada flujo documenta extremo a extremo las interacciones entre capas (`Router → Service → UoW → Repository → DB`) y el manejo de transacciones.

## Flujo 1: Login con Rate Limiting, Hash Ficticio y Sesión Propia de Intentos
**Disparador**: `POST /auth/login` con `{ "email": "...", "password": "..." }`
**Actor**: Cualquier persona (Visitante / Usuario)

**Pasos**:
1. **Validación de Contrato (`Router / Pydantic`)**: Verifica formato de correo, `extra="forbid"` y que `password` no supere los **72 bytes en UTF-8** (`422` si falla).
2. **Conteo de Intentos Recientes (`Service → Repository`)**: Consulta en `intento_acceso` cuántos intentos fallidos (`exito = False`) hubo para ese `(email, ip)` en los últimos 60 segundos posteriores al último intento exitoso.
   - Si hay **5 o más**, responde inmediatamente `429 Too Many Requests` con cabecera `Retry-After` **sin ejecutar `bcrypt`** (en pocos milisegundos).
3. **Búsqueda de Usuario y Verificación en Tiempo Constante (`Service → Security`)**:
   - Busca el usuario por `email`.
   - Si no existe (o está inactivo), selecciona el **hash ficticio** guardado en `app.state.dummy_hash` al iniciar el `lifespan`.
   - Ejecuta `bcrypt.checkpw` fuera del bucle de eventos (`await asyncio.to_thread(...)`) protegido por un `asyncio.Semaphore`.
4. **Registro del Intento en Sesión Independiente (`Service → Session Factory`)**:
   - Abre una **sesión y transacción propias** (separadas de la sesión de la petición), inserta la fila en `intento_acceso(email, ip, exito=...)` y hace `commit()` siempre.
   - Si la verificación fue falsa o el usuario está inactivo, levanta `401 Unauthorized` con mensaje uniforme (`"Credenciales inválidas"`).
5. **Emisión de JWT y Cookie `HttpOnly`**:
   - Consulta los roles vigentes en `asignacion_rol`, firma el JWT (`sub`, `exp`, `roles`) y escribe la cabecera `Set-Cookie: access_token=...; HttpOnly; SameSite=Lax; Max-Age=...`.
   - Devuelve `200 OK` con `{"mensaje": "Sesión iniciada", "debe_cambiar_password": ..., "expira_en_segundos": ...}`.

```
Cliente ──POST /auth/login──► Router ──► Service
                                            ├── 1. SELECT COUNT(*) FROM intento_acceso (¿>=5 en 60s? ──► 429 Retry-After)
                                            ├── 2. SELECT usuario (si no existe, usa dummy_hash)
                                            ├── 3. to_thread(bcrypt.checkpw) bajo Semaphore
                                            ├── 4. [Sesión propia] INSERT INTO intento_acceso + COMMIT
                                            └── 5. Si OK: emite JWT en Set-Cookie HttpOnly ──► 200 OK
```

---

## Flujo 2: Auto-registro Atómico de Cliente (`RN-02`)
**Disparador**: `POST /auth/registro`
**Actor**: Visitante

**Pasos**:
1. **Validación**: `extra="forbid"` (impide inyectar `rol`) y límite de 72 bytes UTF-8 en `password`.
2. **Hash previo a la transacción**: `Service` calcula `password_hash` con `bcrypt` en `to_thread` **antes** de abrir el `UnitOfWork`, para no retener una conexión del pool durante ~300 ms.
3. **Transacción única (`async with uow:`)**:
   - `uow.usuarios.add(Usuario(..., activo=True, debe_cambiar_password=False))` → `flush()` obtiene `usuario.id`.
   - `uow.roles.add(AsignacionRol(usuario_id=usuario.id, rol="CLIENTE"))` → `flush()`.
   - `uow.clientes.add(Cliente(nombre=..., email=..., usuario_id=usuario.id))` → `flush()`.
   - Al salir del bloque `async with uow:`, se ejecuta un único `commit()`.
4. **Casos de error**:
   - Si el correo ya existía en `usuario` o en `cliente` (p. ej. un cliente de mostrador sin usuario web), PostgreSQL lanza `IntegrityError`, el `UnitOfWork` hace `rollback()` de las 3 tablas y se responde `409 Conflict` con mensaje propio.

---

## Flujo 3: Autorización por Rol Vigente en cada Petición (`RN-04`, `RN-06`)
**Disparador**: Petición a cualquier ruta del Grupo Protegido con `Depends(requiere_rol(...))`
**Actor**: Usuario con cookie `access_token`

**Pasos**:
1. **`get_usuario_actual`**: Lee `request.cookies.get("access_token")`, verifica firma y expiración del JWT y busca el `Usuario` en la base usando **la misma sesión** que recibirá el `UnitOfWork`. Si falta la cookie, el token venció/es inválido o el usuario no está activo → `401 Unauthorized`.
2. **Control del Grupo Protegido (`verificar_password_actualizada`)**: Montado una sola vez en el router de grupo protegido en `main.py`. Si `usuario.debe_cambiar_password == True` → `403 Forbidden` (RN-06).
3. **`requiere_rol(*roles_permitidos)`**: Consulta en `asignacion_rol` los roles del usuario con `revocada_en IS NULL AND (vence_en IS NULL OR vence_en > now())`. Si no intersecta con `roles_permitidos` → `403 Forbidden`.

---

## Flujo 4: Registro de Venta con Descuento y Movimiento de Stock (`RN-10`, `RN-11`)
**Disparador**: `POST /ventas`
**Actor**: `VENDEDOR` o `ADMIN`

**Pasos**:
1. **Validación de Contrato (`VentaCreate`)**: Al menos un renglón, cantidades `> 0`, sin `libro_id` repetidos (`422`) y `extra="forbid"`.
2. **Transacción única (`async with uow:`)**:
   - Verifica que el `cliente_id` exista (`409` si no existe).
   - Trae los libros solicitados vigentes (`borrado_en IS NULL`). Si alguno no existe o está dado de baja → `409`.
   - Verifica que para cada renglón `libro.stock >= renglon.cantidad`. Si alguno no alcanza → levanta `409` (el `uow` revierte todo).
   - Crea la `Venta` (`flush()` para obtener `venta.id`) y sus `RenglonVenta` copiando `libro.precio`.
   - Por cada renglón, invoca el **punto único de escritura de stock**, que descuenta `libro.stock -= cantidad` e inserta una fila en `movimiento_stock(libro_id, venta_id=venta.id, usuario_id=actor.id, cantidad=-cantidad, motivo="Venta")`.
   - Al salir del bloque `async with uow:`, confirma las 4 escrituras en un solo `commit()`.
3. **Tarea en Segundo Plano**:
   - Una vez confirmado el `commit`, el router agenda en `BackgroundTasks` el envío del comprobante (`await asyncio.sleep(0.5)` + mensaje en consola visible con el arranque normal de Uvicorn).
