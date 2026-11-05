# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **Librería API (Parcial: Unidades 1 a 6 — Ejercicios 1 al 8)**.
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**
>
> **Nota de alcance (Ejercicios 1 al 8)**: Aunque la consigna completa del parcial enumera 10 ejercicios, los **Ejercicios 9 (Contenedor Docker) y 10 (Despliegue en el VPS)** se aplicaban sobre el estado anterior del TP (Capítulos 1 a 4) y **ya fueron realizados previamente** antes de iniciar este flujo SDD. Por lo tanto, este documento contiene exclusivamente los changes correspondientes a los **Ejercicios 1 al 8**.

---

## Cómo usar este documento

1. Identificar el change a implementar (verificar que sus dependencias están en `openspec/changes/archive/`).
2. Leer los docs de la knowledge-base indicados en "Leer antes".
3. Ejecutar `/opsx:propose <nombre-del-change>`.
4. Al terminar el change, archivarlo con `/opsx:archive <nombre-del-change>`.
5. Marcar el checkbox `[x]` en este archivo.

---

## Árbol de dependencias

```
C-01 config-lifespan-health (Ejercicio 1)
  └── C-02 modelos-migraciones-trigger (Ejercicio 2 y 7a)
        └── C-03 core-repositorios-uow-paginacion (Ejercicio 3 y 6a)   ← desbloquea Auth y Catálogo
              │
              ├── C-04 autenticacion-seguridad (Ejercicio 4 y 7b)
              │     └── C-05 autorizacion-usuarios-eventos (Ejercicio 5)   ← desbloquea recursos protegidos
              │           │
              │           ├── C-06 catalogo-stock-baja-logica (Ejercicio 3, 6b y 8a)
              │           │     └── C-07 clientes-ventas-transaccionales (Ejercicio 6c y 8b)
              │           │           └── C-08 seed-casos-prueba-documentacion (Ejercicio 8c)
```

### Paralelismo por fase

> Cada "gate" es un punto de sincronización. Los changes dentro de un grupo pueden ejecutarse en paralelo.

```
GATE 0: ninguna
  → C-01 config-lifespan-health (solo)

GATE 1: C-01 ✓
  → C-02 modelos-migraciones-trigger (solo)

GATE 2: C-02 ✓
  → C-03 core-repositorios-uow-paginacion (solo)

GATE 3: C-03 ✓                                         ← PRIMER FORK (Auth + preparación de repositorios de dominio)
  → C-04 autenticacion-seguridad                       [Agente A]

GATE 4: C-04 ✓
  → C-05 autorizacion-usuarios-eventos                 [Agente A]

GATE 5: C-05 ✓                                         ← SEGUNDO FORK (Catálogo/Stock vs Clientes)
  → C-06 catalogo-stock-baja-logica                    [Agente A]
  → C-07 clientes-ventas-transaccionales               [Agente B — tras C-06 ✓ por punto único de stock]

GATE 6: C-06 + C-07 ✓
  → C-08 seed-casos-prueba-documentacion               [Agente C]
```

### Camino crítico (8 changes — mínimo irreducible)

```
C-01 → C-02 → C-03 → C-04 → C-05 → C-06 → C-07 → C-08
```

### Plan óptimo con 3 agentes

```
Paso │ Agente A (Core / Seguridad)        │ Agente B (Dominio / Transacciones)   │ Agente C (QA / Datos / Docs)
─────┼────────────────────────────────────┼──────────────────────────────────────┼─────────────────────────────────────
  1  │ C-01 config-lifespan-health        │                  —                   │                 —
  2  │ C-02 modelos-migraciones-trigger   │                  —                   │                 —
  3  │ C-03 core-repositorios-uow-paginac.│                  —                   │                 —
  4  │ C-04 autenticacion-seguridad       │                  —                   │                 —
  5  │ C-05 autorizacion-usuarios-eventos │                  —                   │                 —
  6  │ C-06 catalogo-stock-baja-logica    │                  —                   │                 —
  7  │                  —                 │ C-07 clientes-ventas-transaccionales │                 —
  8  │                  —                 │                  —                   │ C-08 seed-casos-prueba-documentacion
```

---

## FASE 0 — Configuración, Ciclo de Vida y Esquema de Datos (Ejercicios 1, 2 y 7a)

### [C-01] `config-lifespan-health`
- **Estado**: `[x]` completado
- **Scope**: Configuración con `pydantic-settings`, ciclo de vida (`lifespan`), sondas de salud y estructura de dos grupos de rutas en `main.py` (**Ejercicio 1**)
  - `app/core/config.py`: clase `Settings(BaseSettings)` leyendo `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT` y construyendo `database_url` (`postgresql+asyncpg://...`) con `@computed_field`; variables de JWT (`JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_EXPIRE_SECONDS`, `COOKIE_SECURE`), costo/concurrencia de `bcrypt` (`BCRYPT_ROUNDS`, `BCRYPT_MAX_CONCURRENCY`), `DB_POOL_SIZE` y `SQL_ECHO`. Ningún secreto (`POSTGRES_PASSWORD`, `JWT_SECRET_KEY`) tiene valor por defecto en código
  - `env.example`: plantilla actualizada con todas las variables de `Settings` sin secretos reales
  - `app/core/database.py`: `create_engine` usando el tamaño de pool de `Settings`, `create_session_factory` (`expire_on_commit=False`) y `get_session`
  - `app/main.py`: `lifespan` que inicializa motor, fábrica de sesiones y precalcula una sola vez el hash ficticio (`dummy_hash`) de `bcrypt` en `app.state`, cerrando el motor con `await engine.dispose()` al apagar; configuración de logging para tareas en segundo plano; estructura de los **dos grupos de rutas** (Grupo Abierto y Grupo Protegido)
  - `app/modules/health/router.py`: `GET /health/live` (`200 OK` sin tocar la base) y `GET /health/ready` (`SELECT 1` contra PostgreSQL devolviendo `200 OK` o `503 Service Unavailable` si la base no responde)
  - `migrations/env.py`: lectura de `settings.database_url` desde `app.core.config`
- **Dependencias**: ninguna
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/01_vision_y_objetivos.md` §Alcance v2.0
  - `knowledge-base/02_descripcion_general.md` §Stack tecnológico y §Dos grupos de rutas en `app/main.py`
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura obligatoria de directorios y §Variables de entorno
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-01

---

### [C-02] `modelos-migraciones-trigger`
- **Estado**: `[x]` completado
- **Scope**: Nuevos modelos de usuarios/seguridad y movimientos de stock, modificaciones en `Cliente` y `Libro`, 3.ª migración autogenerada y 4.ª migración manual del disparador append-only (**Ejercicio 2** y parte del **Ejercicio 7**)
  - `app/modules/usuarios/models.py`: modelos `Usuario` (`usuario`, email único, `activo`, `debe_cambiar_password`), `AsignacionRol` (`asignacion_rol`, FKs `usuario_id` y `otorgada_por`, `CHECK rol IN ('ADMIN', 'VENDEDOR', 'CLIENTE')`, índice único parcial `uq_asignacion_rol_abierta` sobre `(usuario_id, rol) WHERE revocada_en IS NULL`), `IntentoAcceso` (`intento_acceso`, índice compuesto `(email, ip, cuando)`) y `EventoSeguridad` (`evento_seguridad`)
  - `app/modules/libros/models.py`: nuevo modelo `MovimientoStock` (`movimiento_stock`, FKs a `libro`, `venta` opcional y `usuario`, `CHECK cantidad <> 0`); en `Libro` agregar `borrado_en: datetime | None` (`TIMESTAMPTZ NULL`) y reemplazar `UNIQUE` simple de `isbn` por índice único parcial `uq_libro_isbn_vigente` sobre `(isbn) WHERE borrado_en IS NULL` (`postgresql_where`)
  - `app/modules/clientes/models.py`: agregar `usuario_id: int | None` (`FK -> usuario.id`, `UNIQUE`, nullable) y relación 1 a 1 `Cliente.usuario` que devuelva objeto (no lista)
  - **3.ª migración Alembic** (`--autogenerate`, revisada y comentada): crea `usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad`, `movimiento_stock`, altera `cliente` y `libro` e instala los índices únicos parciales
  - **4.ª migración Alembic** (escrita a mano): crea la función PL/pgSQL y el disparador (`TRIGGER`) en PostgreSQL que rechaza con excepción cualquier `UPDATE` o `DELETE` sobre `movimiento_stock` (`RN-12`), con su correspondiente `downgrade()` que elimina el trigger y la función
  - Verificación de ida y vuelta: `alembic upgrade head`, `alembic downgrade base` y `alembic upgrade head` sin errores
- **Dependencias**: C-01
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Entidades detalladas (tablas 1 a 11)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-01, §RN-03, §RN-12, §RN-13
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-05 y §DD-06

---

## FASE 1 — Infraestructura de Persistencia y Contratos Base (Ejercicios 3a y 6a)

### [C-03] `core-repositorios-uow-paginacion`
- **Estado**: `[x]` completado
- **Scope**: Repositorios genéricos (`BaseRepository`, `SoftDeleteRepository`), `UnitOfWork` base y envoltorio de paginación (**Ejercicio 3** parcial y **Ejercicio 6** parcial)
  - `app/core/repository.py`:
    - `BaseRepository[T]`: recibe `session: AsyncSession` y la clase `model: type[T]` en el constructor; implementa `get_by_id`, `get_all` (con paginación y opciones de carga), `count`, `add`, `update`, `delete`; ejecuta únicamente `await self.session.flush()` y `refresh()`, **nunca `commit()`**
    - `SoftDeleteRepository[T](BaseRepository[T])`: filtra automáticamente `borrado_en.is_(None)` en `get_by_id`, `get_all` y `count`, y agrega `get_by_id_including_deleted` y `soft_delete` (marca `borrado_en = now()` + `flush()`)
  - `app/core/unit_of_work.py`: clase base `UnitOfWork` como gestor de contexto asincrónico (`__aenter__` y `__aexit__`): en `__aexit__` ejecuta `await self.session.commit()` si no hubo excepción o `await self.session.rollback()` si la hubo, y **no cierra la sesión** (la cierra `get_session`)
  - `app/core/paginacion.py`: parámetros `PaginationParams` (`page: int >= 1` default 1, `size: int` entre 1 y 100 default 20) y esquema genérico `Page[T]` con `{items, total, page, size, pages}`; validación que devuelve `422 Unprocessable Entity` cuando `page > pages` (con `total == 0` existe 1 página vacía: `page=1, pages=1, items=[]`)
- **Dependencias**: C-02
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/02_descripcion_general.md` §Arquitectura general (5 capas)
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-02
  - `knowledge-base/10_preguntas_abiertas.md` §IN-01 (Paginación)

---

## FASE 2 — Seguridad: Autenticación, Autorización y Auditoría (Ejercicios 4, 5 y 7b)

### [C-04] `autenticacion-seguridad`
- **Estado**: `[x]` completado
- **Scope**: Hashing `bcrypt` no bloqueante, JWT en cookie `HttpOnly`, rate-limiting en sesión propia y endpoints `/auth/*` (**Ejercicio 4** y parte del **Ejercicio 7**)
  - `app/core/security.py`:
    - `bcrypt` con costo configurable (`settings.bcrypt_rounds`), ejecutado siempre en `await asyncio.to_thread(...)` bajo un `asyncio.Semaphore(settings.bcrypt_max_concurrency)` y **antes** de abrir el `UnitOfWork`
    - Validación reutilizable de contraseña con máximo de **72 bytes en UTF-8** (`len(v.encode("utf-8")) <= 72` → `422`, nunca `500`)
    - Emisión y decodificación de JWT (`PyJWT`) con `sub` (ID del usuario), `exp` y lista informativa de roles vigentes; helper para escribir y borrar la cookie `access_token` (`HttpOnly=True`, `SameSite="lax"`, `Max-Age`, `Secure=settings.cookie_secure`)
  - `app/modules/usuarios/repository.py` y `app/modules/usuarios/unit_of_work.py`: repositorios de `Usuario`, `AsignacionRol`, `IntentoAcceso`, `EventoSeguridad` (y acceso a `ClienteRepository` para el auto-registro)
  - Sesión y transacción independientes para `IntentoAcceso` (**Ejercicio 7**): función dedicada con el comentario explicativo de 3 puntos exigido por la consigna (por qué no usa el `UnitOfWork`, qué pasaría con el límite de intentos si compartiera transacción y qué fila queda confirmada aunque el resto falle)
  - `app/modules/usuarios/schemas.py`, `service.py` y `router.py` (rutas de `/auth` en el Grupo Abierto):
    - `POST /auth/registro` (`201`, `409`, `422`): auto-registro con `extra="forbid"`, crea `Usuario`, `AsignacionRol(rol="CLIENTE")` y `Cliente(usuario_id=...)` en un solo `UnitOfWork` (`RN-02`)
    - `POST /auth/login` (`200`, `401`, `422`, `429`): 1.º verifica límite de 5 fallos en 60s por `(email, ip)` desde el último éxito (`429` + `Retry-After` sin ejecutar `bcrypt`, `RN-07`); 2.º verifica contraseña o `dummy_hash` (`RN-08`); 3.º graba `intento_acceso` en sesión propia; 4.º setea cookie `access_token` y devuelve JSON sin el token
    - `POST /auth/logout` (`200`): borra la cookie `access_token`
    - `GET /auth/yo` (`200`, `401`): devuelve perfil del usuario autenticado, `roles_vigentes` (en BD) y `roles_token`
    - `POST /auth/cambiar-password` (`200`, `401`, `422`): verifica clave actual, actualiza `password_hash`, pone `debe_cambiar_password = False` y registra en `evento_seguridad` en el mismo `UnitOfWork` sin invalidar la sesión actual (`RN-06`, `RN-16`)
- **Dependencias**: C-03
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §Modelo de Vigencia de Roles
  - `knowledge-base/05_reglas_de_negocio.md` §RN-02, §RN-06, §RN-07, §RN-08, §RN-15, §RN-16
  - `knowledge-base/06_funcionalidades.md` §Épica 2 (US-002, US-003, US-004)
  - `knowledge-base/07_flujos_principales.md` §Flujo 1 y §Flujo 2
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-03 y §DD-04

---

### [C-05] `autorizacion-usuarios-eventos`
- **Estado**: `[ ]` pendiente
- **Scope**: Dependencias de autenticación/autorización en tiempo real, bloqueo por cambio obligatorio de contraseña y gestión de usuarios, roles y eventos de seguridad (**Ejercicio 5**)
  - `app/core/dependencies.py`:
    - `get_usuario_actual`: lee exclusivamente `request.cookies.get("access_token")`, valida JWT y carga el `Usuario` activo usando la **misma sesión `Depends(get_session)`** que el `UnitOfWork` (`401 Unauthorized` si falta, venció, es inválido o está inactivo)
    - `verificar_password_actualizada`: dependencia montada **una sola vez** en el Grupo Protegido de `app/main.py`; responde `403 Forbidden` si `usuario.debe_cambiar_password == True` (`RN-06`)
    - `requiere_rol(*roles)`: consulta en `asignacion_rol` los roles vigentes (`revocada_en IS NULL AND (vence_en IS NULL OR vence_en > now())`) en cada petición (`RN-04`); responde `403 Forbidden` si no posee el rol requerido
  - Endpoints de administración en `app/modules/usuarios/router.py` (en el Grupo Protegido, `requiere_rol("ADMIN")`):
    - `POST /usuarios` (`201`, `409`, `422`): alta de personal con contraseña provisoria (`debe_cambiar_password = True`), rol inicial y fila en `evento_seguridad` en un solo `UnitOfWork` (`RN-16`)
    - `GET /usuarios/{id}/roles` (`200`, `404`): listado de asignaciones de rol del usuario
    - `POST /usuarios/{id}/roles` (`201`, `404`, `409`, `422`): asigna rol validando que `vence_en` (si se envía) tenga zona horaria y sea futuro (`422`); si había una asignación abierta ya vencida, la cierra y abre la nueva; si ya está vigente, devuelve `409` (`RN-03`); registra en `evento_seguridad` (`RN-16`)
    - `DELETE /usuarios/{id}/roles/{rol}` (`200`, `404`, `409`): marca `revocada_en = now()` sin borrar la fila; aplica **autoprotección de administradores** (`RN-05`: un `ADMIN` no puede revocarse su propio `ADMIN` ni dejar al sistema sin administradores vigentes → `409`); registra en `evento_seguridad` (`RN-16`)
    - `GET /eventos` (`200`, `422`): listado paginado `{items, total, page, size, pages}` de `evento_seguridad`
- **Dependencias**: C-04
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Matriz de permisos por recurso
  - `knowledge-base/05_reglas_de_negocio.md` §RN-03, §RN-04, §RN-05, §RN-06, §RN-16
  - `knowledge-base/06_funcionalidades.md` §Épica 3 (US-005)
  - `knowledge-base/07_flujos_principales.md` §Flujo 3
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-01 y §DD-02

---

## FASE 3 — Refactorización de Dominio a Repositorios y Unit of Work (Ejercicios 3b, 6b, 6c, 8a y 8b)

> `C-06` implementa el punto único de escritura de stock en `libros`, que luego es reutilizado por `C-07` al registrar ventas.

### [C-06] `catalogo-stock-baja-logica`
- **Estado**: `[ ]` pendiente
- **Scope**: Refactorización de `editoriales`, `generos`, `autores` y `libros` a `Repository + UnitOfWork`, contratos estrictos (`extra="forbid"`), paginación por envoltorio, baja lógica de libros y punto único de escritura de stock (**Ejercicios 3, 6 y 8**)
  - Módulos `editoriales`, `generos` y `autores`:
    - Creación de `repository.py` y `unit_of_work.py` en cada módulo con precargas declaradas en el repositorio
    - Schemas de entrada con `model_config = ConfigDict(extra="forbid")`
    - Separación de rutas públicas de lectura (Grupo Abierto, paginadas con `{items, total, page, size, pages}` en `GET /editoriales` y `GET /generos`) y rutas de escritura `POST`/`PATCH` (Grupo Protegido, `requiere_rol("ADMIN")`)
  - Módulo `libros` (`app/modules/libros/`):
    - `LibroRepository(SoftDeleteRepository[Libro])` y `MovimientoStockRepository(BaseRepository[MovimientoStock])` con precarga eager de `editorial`, `genero` y `autorias.autor`
    - **Punto único de escritura de stock (`RN-11`)**: método centralizado que modifica `libro.stock` y crea simultáneamente la fila en `movimiento_stock`, garantizando `libro.stock == SUM(movimiento_stock.cantidad)`
    - `LibroCreate`: recibe `stock_inicial: int >= 0` (en lugar de `stock`), `extra="forbid"`; en un único `UnitOfWork` crea el libro, sus autorías y el movimiento `"Stock inicial"`
    - `LibroUpdate`: **no** incluye `stock` y tiene `extra="forbid"` (enviar `stock` en `PATCH /libros/{id}` devuelve `422`)
    - `DELETE /libros/{id}` (`ADMIN`, `204 No Content`, `404`): baja lógica marcando `borrado_en = now()` (`RN-13`); libera el ISBN para futuros libros (`RN-01`)
    - `POST /libros/{id}/reponer` (`ADMIN`, `200`, `404`, `409`, `422`): incrementa stock y registra movimiento usando el punto único de escritura (`409`/`404` si el libro fue dado de baja)
    - `GET /libros/{id}/movimientos` (`ADMIN`, `200`, `404`): historial de movimientos del libro (incluyendo libros dados de baja)
    - `GET /libros` (`page`, `size`, `titulo`, `genero_id`) en el Grupo Abierto devolviendo `Page[LibroLista]` sólo con libros vigentes (`borrado_en IS NULL`)
- **Dependencias**: C-05
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §8 (`libro`) y §10 (`movimiento_stock`)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-01, §RN-11, §RN-12, §RN-13
  - `knowledge-base/06_funcionalidades.md` §Épica 4 (US-006)
  - `knowledge-base/10_preguntas_abiertas.md` §IN-01 y §IN-03

---

### [C-07] `clientes-ventas-transaccionales`
- **Estado**: `[ ]` pendiente
- **Scope**: Refactorización de `clientes` y `ventas` a `Repository + UnitOfWork`, venta atómica con descuento y movimiento de stock, `/mis-ventas`, control de dueño en `/ventas/{id}` y `BackgroundTasks` visible en consola (**Ejercicios 5, 6 y 8**)
  - Módulo `clientes` (`app/modules/clientes/`):
    - `ClienteRepository` (con precarga de `perfil`) y `ClientesUnitOfWork`
    - Schemas con `extra="forbid"`; rutas en el Grupo Protegido protegidas con `requiere_rol("VENDEDOR", "ADMIN")` (`POST /clientes`, `GET /clientes/{id}`, `PATCH /clientes/{id}`, `POST /clientes/{id}/perfil`, `GET /clientes/{id}/ventas`)
  - Módulo `ventas` (`app/modules/ventas/`):
    - `VentaRepository` con precarga declarada (`joinedload(Venta.cliente)` y `selectinload(Venta.renglones).joinedload(RenglonVenta.libro)`) que incluye libros dados de baja lógica en ventas históricas (`RN-13`, sin N+1)
    - `VentasUnitOfWork` integrando repositorios de ventas, clientes y el punto único de escritura de stock de libros
    - `POST /ventas` (`VENDEDOR`, `ADMIN` → `201`, `409`, `422`): en un único `UnitOfWork` verifica cliente y libros vigentes con stock suficiente (`409` y rollback total si alguno falla, `RN-10`), crea la venta y sus renglones copiando `libro.precio` (`RN-09`), descuenta stock y registra un `movimiento_stock` negativo por renglón (`RN-11`); tras el `commit`, agenda en `BackgroundTasks` el aviso con `await asyncio.sleep(0.5)` y log visible en el arranque normal de Uvicorn
    - `GET /ventas` (`VENDEDOR`, `ADMIN` → `200`, `422`): listado paginado con envoltorio `Page[VentaRead]`
    - `GET /mis-ventas` (Cualquier autenticado sin cambio de clave pendiente → `200`, `422`): listado paginado de las ventas del cliente vinculado al usuario autenticado (`RN-14`)
    - `GET /ventas/{id}` (Autenticado → `200`, `403`, `404`): comprueba en el servicio que quien consulta sea personal (`VENDEDOR`/`ADMIN`) o el `CLIENTE` dueño de esa venta (`403 Forbidden` si es de otro cliente, `RN-14`)
- **Dependencias**: C-06
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §RN-09, §RN-10, §RN-11, §RN-13, §RN-14
  - `knowledge-base/06_funcionalidades.md` §Épica 5 (US-007)
  - `knowledge-base/07_flujos_principales.md` §Flujo 4 (Registro de Venta)
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados

---

## FASE 4 — Carga Inicial, Casos de Prueba y Evidencia (Ejercicio 8c)

### [C-08] `seed-casos-prueba-documentacion`
- **Estado**: `[ ]` pendiente
- **Scope**: Script `seed.py` en raíz con el estado inicial del parcial, batería de pruebas `C-01` a `C-16`, script `test/solo_agregado.sql`, evidencia `C-14`/`C-15` y actualización de `README.md` (**Ejercicio 8**)
  - `seed.py` (en la raíz del proyecto, ejecutable con `python seed.py`):
    - Vacía las tablas en el orden correcto y carga: los **5 usuarios** con sus roles (`admin@example.com`, `admin2@example.com`, `vendedor@example.com`, `ana@example.com`, `nuevo@example.com` con `debe_cambiar_password=True`), el catálogo del TP (**3 editoriales, 3 géneros, 6 autores, 5 libros** con stock final `10, 5, 8, 3, 1`), los **3 clientes** (Lucía con perfil, Tomás sin perfil, Ana vinculada a `ana@example.com`), la **venta 1** de Lucía registrada por `vendedor@example.com` (`1` *Rayuela* + `2` *Ficciones*, `total = 69000.00`), los **7 movimientos de stock** (cumpliendo `libro.stock == SUM(movimiento_stock.cantidad)`) y **1 evento de seguridad** (`actor="SISTEMA"`, `accion="Carga de los datos iniciales"`)
  - Archivos `.http` en `test/` cubriendo los casos de prueba **`C-01` a `C-13`, `C-15` y `C-16`** en orden, listos para correrse después de `python seed.py`
  - `test/solo_agregado.sql` (**Caso `C-14`**): script SQL ejecutable con `psql` que intenta un `UPDATE` y un `DELETE` sobre `movimiento_stock` y demuestra que ambos son rechazados por el disparador de la 4.ª migración
  - Carpeta `evidencia/`: salidas/capturas de los casos `C-14` (rechazo del trigger en `psql`) y `C-15` (logs de `SQL_ECHO=true` mostrando igual número fijo de consultas SQL al leer una venta de 2 renglones y una de 4 renglones)
  - `README.md`: documentación actualizada de puesta en marcha, variables de entorno de `Settings`, ejecución de las 4 migraciones, `python seed.py` y tabla completa de endpoints abiertos y protegidos
- **Dependencias**: C-07
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Seed data inicial (`seed.py`)
  - `knowledge-base/02_descripcion_general.md` §API REST — Resumen de Endpoints de Referencia
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura obligatoria de directorios y §Variables de entorno
  - `knowledge-base/09_decisiones_y_supuestos.md` §SU-01 y §SU-02
