# Funcionalidades

Organizadas por **épica** (alineadas con los Ejercicios 1 a 10 de la consigna del parcial) e **historias de usuario**.

## Épica 1: Configuración, Ciclo de Vida y Salud (Ejercicio 1)

### US-001 — Configuración segura con `pydantic-settings` y ciclo de vida
**Como** operador del sistema
**Quiero** que la aplicación lea toda su configuración crítica desde el entorno sin secretos por defecto y gestione sus recursos en el `lifespan`
**Para** impedir que el servidor arranque mal configurado o filtre credenciales

**Criterios de aceptación**:
- [ ] `Settings` (en `app/core/config.py`) hereda de `BaseSettings` (`pydantic-settings`) y exige sin valor por defecto `POSTGRES_PASSWORD` y la clave de firma JWT.
- [ ] La URL de conexión `postgresql+asyncpg://...` se construye mediante un `@computed_field` a partir de `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST` y `POSTGRES_PORT`.
- [ ] El `lifespan` crea el motor asincrónico (con el tamaño del pool de `Settings`), la fábrica de sesiones (`expire_on_commit=False`), calcula una única vez el hash ficticio de `bcrypt` en `app.state` y cierra el motor con `await engine.dispose()` al apagar.
- [ ] `GET /health/live` responde `200` sin tocar la base; `GET /health/ready` ejecuta `SELECT 1` y responde `200` o `503 Service Unavailable` si la base no contesta.

---

## Épica 2: Autenticación y Gestión de Sesión (Ejercicio 4)

### US-002 — Auto-registro de cliente web
**Como** visitante anónimo
**Quiero** registrarme con mi nombre, correo y contraseña en `POST /auth/registro`
**Para** obtener simultáneamente mi cuenta de usuario, el rol `CLIENTE` y mi ficha de cliente

**Criterios de aceptación**:
- [ ] Valida que la contraseña tenga como máximo 72 bytes en UTF-8 (`422` si los supera) y rechaza campos extra (`extra="forbid"`, impidiendo enviar `rol`).
- [ ] Calcula el hash `bcrypt` con `asyncio.to_thread` y semáforo **antes** de abrir el `UnitOfWork`.
- [ ] Dentro de un único `UnitOfWork`, inserta `Usuario`, `AsignacionRol(rol="CLIENTE")` y `Cliente(usuario_id=usuario.id)`.
- [ ] Si el correo ya existe en `usuario` o en `cliente`, revierte todo y responde `409` con mensaje propio sin apropiarse de la ficha existente.

**Reglas relacionadas**: RN-01, RN-02, RN-15.

### US-003 — Inicio y cierre de sesión con cookie `HttpOnly` y límite de intentos
**Como** usuario registrado
**Quiero** iniciar sesión en `POST /auth/login` y cerrarla en `POST /auth/logout`
**Para** operar en el sistema mediante una cookie segura `access_token`

**Criterios de aceptación**:
- [ ] Antes de verificar el hash, cuenta los intentos fallidos en `intento_acceso` para el par `(email, ip)` en los últimos 60 s (desde el último éxito); si hay 5 o más, responde `429` con cabecera `Retry-After` en pocos milisegundos sin ejecutar `bcrypt`.
- [ ] Si el correo no existe, verifica la contraseña contra el hash ficticio de `app.state` y responde `401` con el mismo mensaje y tiempo que cuando la contraseña es incorrecta.
- [ ] Registra cada intento (exitoso o fallido) en `intento_acceso` usando una **sesión y transacción propias** que se confirman siempre.
- [ ] En login exitoso, emite un JWT con `sub`, `exp` y roles vigentes y lo envía **únicamente** en la cookie `access_token` (`HttpOnly`, `SameSite=Lax`, `Max-Age`, `Secure` configurable); el cuerpo JSON devuelve `{"mensaje": "Sesión iniciada", "debe_cambiar_password": ..., "expira_en_segundos": ...}` sin incluir el token.
- [ ] `POST /auth/logout` borra la cookie `access_token` y responde `200`.
- [ ] `GET /auth/yo` devuelve los datos del usuario autenticado, sus roles vigentes en la base y los roles declarados en el token.

**Reglas relacionadas**: RN-04, RN-07, RN-08.

### US-004 — Cambio de contraseña (voluntario y obligatorio)
**Como** usuario autenticado
**Quiero** cambiar mi contraseña en `POST /auth/cambiar-password`
**Para** desbloquear mi acceso a las rutas protegidas cuando tengo cambio pendiente (`debe_cambiar_password = True`) o actualizar mi clave

**Criterios de aceptación**:
- [ ] Verifica la contraseña actual con `bcrypt` (límite 72 bytes UTF-8 en actual y nueva) y calcula el nuevo hash fuera de la transacción.
- [ ] En un único `UnitOfWork`, actualiza `password_hash`, pone `debe_cambiar_password = False` y registra una fila en `evento_seguridad`.
- [ ] No invalida la cookie actual ni exige volver a iniciar sesión: la misma cookie sirve inmediatamente para acceder a las rutas protegidas.

**Reglas relacionadas**: RN-06, RN-16.

---

## Épica 3: Autorización, Personal y Auditoría (Ejercicio 5)

### US-005 — Alta de personal y administración de roles con vigencia
**Como** administrador (`ADMIN`)
**Quiero** dar de alta personal (`POST /usuarios`), asignar roles (`POST /usuarios/{id}/roles`), revocarlos (`DELETE /usuarios/{id}/roles/{rol}`) y consultar `/eventos`
**Para** controlar en tiempo real quién tiene permisos en el sistema y auditar cada acción

**Criterios de aceptación**:
- [ ] `POST /usuarios` crea el usuario con `debe_cambiar_password = True`, su rol inicial y un registro en `evento_seguridad` en el mismo `UnitOfWork`.
- [ ] `POST /usuarios/{id}/roles` valida que `vence_en` (si se envía) tenga zona horaria y sea futuro (`422` en caso contrario). Si existía una asignación abierta ya vencida para ese rol, la cierra y abre la nueva; si está vigente, responde `409`. Registra en `evento_seguridad`.
- [ ] `DELETE /usuarios/{id}/roles/{rol}` marca `revocada_en = now()` sin borrar la fila y registra en `evento_seguridad`. Impide que un `ADMIN` se revoque su propio `ADMIN` o deje al sistema sin administradores vigentes (`409`, RN-05).
- [ ] La revocación surte efecto en la petición siguiente aunque la cookie del usuario afectado siga vigente.

**Reglas relacionadas**: RN-03, RN-04, RN-05, RN-16.

---

## Épica 4: Catálogo, Baja Lógica y Movimientos de Stock (Ejercicios 2, 3, 6 y 7)

### US-006 — Gestión de libros con stock inicial, reposición y baja lógica
**Como** administrador (`ADMIN`)
**Quiero** crear libros con `stock_inicial`, editar sus datos básicos sin tocar el stock por `PATCH`, reponer ejemplares y darlos de baja lógica
**Para** mantener trazabilidad total del inventario en `movimiento_stock`

**Criterios de aceptación**:
- [ ] `POST /libros` recibe `stock_inicial` (no `stock`), crea el libro, sus autorías y —si corresponde— el movimiento `"Stock inicial"` en un único `UnitOfWork`.
- [ ] `PATCH /libros/{id}` rechaza el campo `stock` con `422` (`extra="forbid"`).
- [ ] `POST /libros/{id}/reponer` incrementa `libro.stock` y crea la fila en `movimiento_stock` con el usuario autenticado en el mismo `UnitOfWork` (`409` o `404` si el libro está dado de baja).
- [ ] `DELETE /libros/{id}` marca `borrado_en = now()` y responde `204 No Content`. El libro desaparece de `GET /libros`, su ISBN queda libre para un nuevo alta, pero las ventas históricas siguen mostrando su título.
- [ ] `GET /libros/{id}/movimientos` devuelve el historial de movimientos del libro.

**Reglas relacionadas**: RN-01, RN-11, RN-12, RN-13.

---

## Épica 5: Ventas Transaccionales y Consulta Propia (Ejercicios 6 y 8)

### US-007 — Registro atómico de ventas y consulta por dueño o personal
**Como** vendedor/administrador o cliente
**Quiero** registrar ventas que descuenten stock atómicamente y consultar ventas según mi rol
**Para** asegurar que nunca se registren ventas sin respaldo de stock ni se expongan compras ajenas

**Criterios de aceptación**:
- [ ] `POST /ventas` (para `VENDEDOR`/`ADMIN`) ejecuta en un solo `UnitOfWork`: creación de `venta`, creación de `renglon_venta`, descuento en `libro.stock` y creación de `movimiento_stock` (cantidad negativa, con `venta_id` y `usuario_id`). Si algún libro no existe, está dado de baja o no tiene stock suficiente, hace `rollback` total y responde `409`.
- [ ] Agenda con `BackgroundTasks` el aviso simulado (`await asyncio.sleep(0.5)` + log visible en consola de Uvicorn) sólo tras confirmar la transacción.
- [ ] `GET /mis-ventas` devuelve las ventas paginadas del cliente asociado al usuario autenticado.
- [ ] `GET /ventas/{id}` permite el acceso al personal (`VENDEDOR`/`ADMIN`) o al `CLIENTE` dueño de esa venta (`403` si es otro cliente, `404` si no existe) y se resuelve con una cantidad fija de consultas SQL sin N+1 (incluso si el libro de un renglón fue dado de baja lógica).

**Reglas relacionadas**: RN-09, RN-10, RN-11, RN-13, RN-14.

---

## Épica 6: Contenedor y Despliegue en VPS del TP 1-4 (Ejercicios 9 y 10 — YA REALIZADOS)

> **Estado:** Estos dos ejercicios se aplicaban sobre el estado anterior del TP (capítulos 1 a 4) y **ya fueron realizados antes de iniciar el flujo SDD**. Se documentan aquí como referencia de la consigna completa, pero **no generan `changes` pendientes en `CHANGES.md`** (los cambios a implementar son del Ejercicio 1 al 8).

### US-008 — Imagen Docker Alpine y despliegue en VPS (Completado previamente)
**Como** equipo de desarrollo
**Quiero** empaquetar el TP de los capítulos 1 a 4 en una imagen Docker liviana y desplegarla en el VPS de la cátedra
**Para** cumplir con la entrega separada en `despliegue/` y los casos de prueba D-01 a D-08

**Criterios de aceptación**:
- [ ] En la carpeta `despliegue/` (con el código del TP 1-4), el `Dockerfile` parte de `python:3.12-alpine` (< 100 MB), instala `requirements.txt` con `--no-cache-dir` antes de copiar el código, usa un usuario no-root (`USER`), define `HEALTHCHECK` con `wget` contra `http://127.0.0.1:8000/health/ready` y ejecuta `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- [ ] `.dockerignore` excluye `.env`, `.venv`, `.git` y `__pycache__`.
- [ ] `DEPLOY.md` y `despliegue/evidencia/` documentan la URL pública en el VPS, comandos y salidas de los casos D-01 a D-08.
