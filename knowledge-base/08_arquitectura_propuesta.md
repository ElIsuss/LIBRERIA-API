# Arquitectura Propuesta

## Patrones aplicados

| Patrón | Dónde se usa | Por qué |
|---|---|---|
| **Layered Architecture (`Router → Service → UoW → Repository → Model`)** | Todos los módulos de `app/modules/` | Separa responsabilidades: HTTP en el router, reglas de negocio en el servicio, atomicidad en el UoW y SQL/precargas en el repositorio. |
| **Generic Repository (`BaseRepository[T]`)** | `app/core/repository.py` y `app/modules/*/repository.py` | Centraliza `get_by_id`, `get_all`, `count`, `add`, `update`, `delete` haciendo sólo `flush()` y nunca `commit()`. Recibe `session` y la clase `model` en el constructor porque los genéricos de Python se borran en tiempo de ejecución. |
| **Soft Delete Repository (`SoftDeleteRepository[T]`)** | `app/core/repository.py` → usado por `LibroRepository` | Hereda de `BaseRepository[T]`, filtra automáticamente `borrado_en.is_(None)` en lecturas de catálogo y agrega `get_by_id_including_deleted` y `soft_delete`. |
| **Unit of Work (`UnitOfWork`)** | `app/core/unit_of_work.py` y `app/modules/*/unit_of_work.py` | Gestor de contexto asincrónico (`async with uow:`) que agrupa todas las escrituras de una operación en una sola transacción: hace `commit()` al salir normalmente, `rollback()` si hay excepción y **no cierra la sesión** (la cierra `get_session`). |
| **Session Sharing per Request** | `app/core/database.py` + `app/core/dependencies.py` | Como FastAPI cachea las dependencias dentro de una misma petición, `get_usuario_actual`, `requiere_rol` y el constructor del `UnitOfWork` reciben la **misma instancia de `AsyncSession`**, tomando 1 sola conexión del pool por petición. |
| **Append-Only Ledger (`movimiento_stock` + Trigger)** | `app/modules/libros/` + 4.ª migración Alembic | Protege el historial de inventario con un disparador en PostgreSQL que rechaza cualquier `UPDATE` o `DELETE` (RN-12), garantizando `libro.stock == SUM(movimiento_stock.cantidad)`. |
| **Independent Audit Session (`intento_acceso`)** | `app/modules/usuarios/service.py` | Es la única escritura que abre su propia sesión y confirma siempre, para que el conteo de intentos fallidos sobreviva al `rollback` o error `401` del login. |

## Estructura obligatoria de directorios

### 1. Proyecto `parcial/` (este repositorio evolucionado a Unidades 1 a 6)

```
parcial/
├── app/
│   ├── main.py                      # Aplicación, lifespan, logger y los 2 grupos de rutas (abierto / protegido)
│   ├── core/
│   │   ├── config.py                # Settings con pydantic-settings y @computed_field para database_url
│   │   ├── database.py              # create_engine, create_session_factory y get_session
│   │   ├── security.py              # bcrypt con to_thread + Semaphore (<=72 bytes) y JWT con PyJWT
│   │   ├── dependencies.py          # get_usuario_actual, roles vigentes, cambio obligatorio y requiere_rol
│   │   ├── repository.py            # BaseRepository[T] y SoftDeleteRepository[T]
│   │   ├── paginacion.py            # Envoltorio Page[T] {items, total, page, size, pages}
│   │   └── unit_of_work.py          # UnitOfWork base (__aenter__ / __aexit__)
│   └── modules/
│       ├── health/
│       │   └── router.py            # GET /health/live (200) y GET /health/ready (200 / 503)
│       ├── usuarios/                # Usuario, AsignacionRol, IntentoAcceso, EventoSeguridad + /auth, /usuarios, /eventos
│       │   ├── models.py
│       │   ├── schemas.py
│       │   ├── repository.py
│       │   ├── unit_of_work.py
│       │   ├── service.py
│       │   └── router.py
│       ├── editoriales/             # models.py, schemas.py, repository.py, unit_of_work.py, service.py, router.py
│       ├── generos/                 # models.py, schemas.py, repository.py, unit_of_work.py, service.py, router.py
│       ├── autores/                 # models.py, schemas.py, repository.py, unit_of_work.py, service.py, router.py
│       ├── libros/                  # Libro, LibroAutor, MovimientoStock + alta, baja lógica, reponer, movimientos
│       ├── clientes/                # Cliente (con usuario_id), PerfilCliente
│       └── ventas/                  # Venta, RenglonVenta + /ventas y /mis-ventas
├── migrations/
│   ├── env.py
│   └── versions/                    # 4 migraciones (2 del TP + 3.ª autogenerada + 4.ª manual del trigger)
├── test/
│   ├── *.http                       # Casos de prueba C-01 a C-16 con REST Client
│   └── solo_agregado.sql            # Caso C-14 (prueba de UPDATE y DELETE rechazados en psql)
├── evidencia/                       # Capturas/salidas de C-14 y C-15
├── seed.py                          # Carga del estado inicial conocido (en raíz)
├── alembic.ini                      # sqlalchemy.url vacío
├── env.example                      # Todas las variables sin secretos
├── requirements.txt                 # fastapi[standard], uvicorn, sqlmodel, sqlalchemy[asyncio], asyncpg, alembic, bcrypt, pyjwt, python-dotenv, pydantic-settings
└── README.md
```

### 2. Proyecto `despliegue/` (carpeta separada para el `.zip` de entrega)

```
despliegue/
├── app/                             # Código del TP Capítulos 1 a 4 tal como se entregó
├── migrations/
├── test/
├── Dockerfile                       # python:3.12-alpine, no-root, HEALTHCHECK wget 127.0.0.1:8000/health/ready
├── .dockerignore                    # Excluye .env, .venv, .git, __pycache__
├── env.example                      # Forma de DATABASE_URL y SQL_ECHO=false
├── DEPLOY.md                        # URL pública en VPS, comandos docker build/run y procedimiento de actualización
└── evidencia/                       # Salidas de los casos D-01 a D-08
```

## Seguridad
- **Autenticación**: Contraseñas hasheadas con `bcrypt` (costo configurable en entorno), ejecutado siempre fuera del event loop (`asyncio.to_thread`) bajo un `asyncio.Semaphore` y antes de abrir la transacción. Límite estricto de 72 bytes UTF-8 validado en los contratos de entrada.
- **Transporte del Token**: JWT firmado con `PyJWT` (`HS256`), enviado y leído **exclusivamente** en la cookie `access_token` (`HttpOnly`, `SameSite=Lax`, `Max-Age`, `Secure` configurable). Nunca viaja en el cuerpo JSON ni se acepta por cabecera `Authorization: Bearer`.
- **Autorización**: Consulta de roles vigentes en `asignacion_rol` en cada petición (`RN-04`); separación de rutas en grupo abierto y grupo protegido para imponer el cambio obligatorio de contraseña (`RN-06`).
- **Validación de Input**: `model_config = ConfigDict(extra="forbid")` en todos los esquemas de entrada; consultas SQL siempre parametrizadas.
- **Gestión de Secretos**: Ninguna contraseña ni clave de firma tiene valor por defecto en `Settings`; si faltan en el entorno/`.env`, la aplicación falla al arrancar.

## Variables de entorno (`env.example` para `parcial/`)

| Variable | Descripción | Ejemplo en `env.example` | Sensible | Tiene default en código |
|---|---|---|:---:|:---:|
| `POSTGRES_USER` | Usuario de PostgreSQL | `postgres` | No | Sí / Opcional |
| `POSTGRES_PASSWORD` | Contraseña de PostgreSQL | `cambiar_por_password` | **Sí** | **No (obligatoria)** |
| `POSTGRES_HOST` | Host del servidor PostgreSQL | `localhost` | No | Sí (`localhost`) |
| `POSTGRES_PORT` | Puerto de PostgreSQL | `5432` | No | Sí (`5432`) |
| `POSTGRES_DB` | Nombre de la base de datos | `libreria_api` | No | Sí (`libreria_api`) |
| `JWT_SECRET_KEY` | Clave secreta para firmar tokens JWT | `generar_con_secrets_token_hex_32` | **Sí** | **No (obligatoria)** |
| `JWT_ALGORITHM` | Algoritmo de firma JWT | `HS256` | No | Sí (`HS256`) |
| `JWT_EXPIRE_SECONDS` | Duración del token y `Max-Age` de cookie | `1800` | No | Sí (`1800`) |
| `COOKIE_SECURE` | Flag `Secure` de la cookie `access_token` | `false` | No | Sí (`false`) |
| `BCRYPT_ROUNDS` | Costo (factor de trabajo) de `bcrypt` | `12` | No | Sí (`12`) |
| `BCRYPT_MAX_CONCURRENCY` | Límite del semáforo para hashes simultáneos | `4` | No | Sí (`4`) |
| `DB_POOL_SIZE` | Tamaño del pool de conexiones del motor | `5` | No | Sí (`5`) |
| `SQL_ECHO` | Imprime las consultas SQL en consola | `false` | No | Sí (`false`) |
