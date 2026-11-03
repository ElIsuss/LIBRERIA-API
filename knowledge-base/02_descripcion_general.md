# Descripción General

## Stack tecnológico (`requirements.txt`)

| Capa | Paquete (`requirements.txt`) / Tecnología | Uso en el proyecto |
|---|---|---|
| **Lenguaje** | Python 3.12+ | Tipado moderno, `asyncio`, `contextlib` |
| **Base de Datos** | PostgreSQL 16+ | Persistencia relacional, restricciones `CHECK`/`UNIQUE`, índices parciales y triggers |
| **Framework Web** | `fastapi[standard]` | API REST asincrónica (`async def`), inyección con `Depends()`, `BackgroundTasks` |
| **Servidor ASGI** | `uvicorn` | Ejecución del servidor HTTP asincrónico |
| **ORM / Modelos** | `sqlmodel` | Definición de modelos de tabla (`table=True`) |
| **Motor y Sesiones** | `sqlalchemy[asyncio]` | `AsyncEngine`, `async_sessionmaker`, `joinedload`, `selectinload`, índices parciales |
| **Driver DB** | `asyncpg` | Controlador asincrónico para PostgreSQL (`postgresql+asyncpg://`) |
| **Migraciones** | `alembic` | Versionado de esquema con plantilla asincrónica (4 migraciones en total) |
| **Seguridad (Hash)** | `bcrypt` | Hashing de contraseñas fuera del event loop (`to_thread` + `Semaphore`, máx. 72 bytes UTF-8) |
| **Seguridad (Tokens)** | `pyjwt` | Firma y verificación de tokens JWT transportados en cookie `HttpOnly` |
| **Entorno (.env)** | `python-dotenv` | Carga de variables desde `.env` (migraciones Alembic y scripts) |
| **Configuración** | `pydantic-settings` | `Settings(BaseSettings)` para validación de variables de entorno y `@computed_field` |

## Arquitectura general

El proyecto `parcial/` se organiza por **módulos funcionales**, donde cada módulo respeta estrictamente una arquitectura en **5 capas**:

```
Petición HTTP
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. Router (app/modules/<modulo>/router.py)                      │
│    - Declara rutas, códigos HTTP, contratos de entrada/salida   │
│    - Ejecuta dependencias de autenticación/autorización         │
│    - Construye el UnitOfWork con Depends() y lo pasa sin abrir  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Service (app/modules/<modulo>/service.py)                    │
│    - Contiene las reglas de negocio                             │
│    - Recibe el UnitOfWork (nunca la sesión directa)             │
│    - Abre el bloque `async with uow:` para agrupar escrituras   │
│    - Calcula hashes bcrypt ANTES de abrir la transacción        │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Unit of Work (app/core/unit_of_work.py + modulo/uow.py)      │
│    - Gestor de contexto asincrónico (`__aenter__` / `__aexit__`)│
│    - Instancia los repositorios compartiendo la misma sesión    │
│    - Confirma (`commit`) al salir sin error; revierte (`rollback`)│
│      ante excepción; NUNCA cierra la sesión (no la creó)        │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Repository (app/core/repository.py + modulo/repository.py)   │
│    - `BaseRepository[T]` y `SoftDeleteRepository[T]`            │
│    - Encapsula consultas SQLModel/SQLAlchemy y precargas eager  │
│    - Ejecuta `flush()`, NUNCA `commit()`                        │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Model (app/modules/<modulo>/models.py)                       │
│    - Clases SQLModel (`table=True`), FKs, CHECKs, índices       │
└─────────────────────────────────────────────────────────────────┘
```

### Dos grupos de rutas en `app/main.py`
Dado que FastAPI suma dependencias y no permite restarlas en sub-rutas, `main.py` monta dos grupos diferenciados:
1. **Grupo Abierto**: No exige el control de cambio obligatorio de contraseña. Incluye `/health/*`, `/auth/*` (para que quien debe cambiar su contraseña pueda autenticarse, consultar `/auth/yo`, cambiar su clave o cerrar sesión) y las consultas públicas del catálogo (`GET /libros`, `GET /libros/{id}`, `GET /editoriales`, `GET /generos` y sus sub-recursos de libros).
2. **Grupo Protegido**: Lleva montada una única vez la dependencia que verifica que el usuario autenticado **no** tenga `debe_cambiar_password = True` (respondiendo `403 Forbidden` si está pendiente, RN-06). Incluye todas las rutas de administración de usuarios/roles/eventos, escrituras de catálogo, clientes y ventas.

## Integraciones externas

| Servicio | Propósito | Tipo |
|---|---|---|
| **PostgreSQL 16+** | Motor relacional transaccional y garante de integridad (FK, CHECK, UNIQUE parciales, Trigger append-only). | Conexión TCP asincrónica vía `asyncpg` |
| **VPS de la Cátedra** | Servidor Linux remoto con PostgreSQL preinstalado donde se despliega el contenedor Docker del TP (capítulos 1 a 4). | Docker Engine + HTTP público |

## API REST — Resumen de Endpoints de Referencia

### Grupo Abierto

| Método | Ruta | Quién | Códigos |
|---|---|---|---|
| `GET` | `/health/live` | Cualquiera | `200` |
| `GET` | `/health/ready` | Cualquiera | `200`, `503` |
| `POST` | `/auth/registro` | Cualquiera | `201`, `409`, `422` |
| `POST` | `/auth/login` | Cualquiera | `200`, `401`, `422`, `429` |
| `POST` | `/auth/logout` | Cualquiera | `200` |
| `GET` | `/auth/yo` | Autenticado | `200`, `401` |
| `POST` | `/auth/cambiar-password` | Autenticado | `200`, `401`, `422` |
| `GET` | `/libros` (`page`, `size`, `titulo`, `genero_id`) | Cualquiera | `200`, `422` |
| `GET` | `/libros/{id}` | Cualquiera | `200`, `404`, `422` |
| `GET` | `/editoriales`, `/generos` (`page`, `size`) | Cualquiera | `200`, `422` |
| `GET` | `/editoriales/{id}/libros`, `/generos/{id}/libros`, `/autores/{id}/libros` | Cualquiera | `200`, `404` |

*(Nota: También se mantiene `GET /editoriales/{id}` y `GET /autores/{id}` del TP base).*

### Grupo Protegido (responde además `401` sin sesión y `403` con cambio de contraseña pendiente)

| Método | Ruta | Quién | Códigos |
|---|---|---|---|
| `POST` | `/usuarios` (alta de personal con clave provisoria) | `ADMIN` | `201`, `409`, `422` |
| `GET` | `/usuarios/{id}/roles` | `ADMIN` | `200`, `404` |
| `POST` | `/usuarios/{id}/roles` | `ADMIN` | `201`, `404`, `409`, `422` |
| `DELETE` | `/usuarios/{id}/roles/{rol}` | `ADMIN` | `200`, `404`, `409` |
| `GET` | `/eventos` (`page`, `size`) | `ADMIN` | `200`, `422` |
| `POST` | `/editoriales`, `/generos`, `/autores` | `ADMIN` | `201`, `409`, `422` |
| `PATCH` | `/editoriales/{id}`, `/autores/{id}` | `ADMIN` | `200`, `404`, `409`, `422` |
| `POST` | `/libros` (con `autores` y `stock_inicial`) | `ADMIN` | `201`, `409`, `422` |
| `PATCH` | `/libros/{id}` (`titulo`, `precio`, `editorial_id`, `genero_id`; **sin `stock`**) | `ADMIN` | `200`, `404`, `409`, `422` |
| `DELETE` | `/libros/{id}` (baja lógica) | `ADMIN` | `204`, `404` |
| `POST` | `/libros/{id}/reponer` | `ADMIN` | `200`, `404`, `409`, `422` |
| `GET` | `/libros/{id}/movimientos` | `ADMIN` | `200`, `404` |
| `POST` | `/clientes` | `VENDEDOR`, `ADMIN` | `201`, `409`, `422` |
| `GET`, `PATCH` | `/clientes/{id}` (con su perfil) | `VENDEDOR`, `ADMIN` | `200`, `404`, `409`, `422` |
| `POST` | `/clientes/{id}/perfil` | `VENDEDOR`, `ADMIN` | `201`, `404`, `409` |
| `GET` | `/clientes/{id}/ventas` | `VENDEDOR`, `ADMIN` | `200`, `404` |
| `POST` | `/ventas` (con `renglones`) | `VENDEDOR`, `ADMIN` | `201`, `409`, `422` |
| `GET` | `/ventas` (`page`, `size`) | `VENDEDOR`, `ADMIN` | `200`, `422` |
| `GET` | `/ventas/{id}` | Personal (`VENDEDOR`/`ADMIN`) o `CLIENTE` dueño | `200`, `403`, `404` |
| `GET` | `/mis-ventas` (`page`, `size`) | Autenticado | `200`, `422` |
