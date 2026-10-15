# Librería API

API asincrónica para el catálogo, los clientes y las ventas de una librería de
barrio. FastAPI + SQLModel + PostgreSQL + Alembic.

Trabajo práctico de Programación III — Unidades 1 a 4: *Del objeto a la
persistencia*.

## Grupo: LOS JAVAS

### Integrantes:
- Isaias Morinigo — 54011
- Giovanna Suarez — 51650
- Juan Ignacio — 53882
- Gaston Puente — 52735

---

## Requisitos

- Python 3.12 o superior
- PostgreSQL 16 o superior

## Puesta en marcha

### 1. Entorno virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Dependencias

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Credenciales

La dirección de la base se lee de la variable `DATABASE_URL`, definida en un
archivo `.env` que **no se versiona**.

```powershell
copy env.example .env
```

Después editá `.env` y poné tus credenciales. La URL tiene esta forma:

```
DATABASE_URL=postgresql+asyncpg://USUARIO:PASSWORD@localhost:5432/NOMBRE_BASE
```

El `+asyncpg` no es opcional: es lo que hace que el motor sea asincrónico.

**No escribas credenciales en ningún archivo del repositorio.** Ni en `.env` de
otros, ni en `alembic.ini`, ni en el código.

### 4. Base de datos

Creá la base vacía (una sola vez):

```sql
CREATE DATABASE libreria_api;
```

### 5. Esquema

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Esto crea las 9 tablas: `editorial`, `genero`, `autor`, `libro`,
`libro_autor`, `cliente`, `perfil_cliente`, `venta` y `renglon_venta`.

Para verificar en qué versión está la base:

```powershell
.\.venv\Scripts\python.exe -m alembic current
```

### 6. Carga de datos iniciales

```powershell
python -m app.seed
```

Esto puebla la base de datos con editoriales, géneros, autores, libros y clientes de prueba.

### 7. Arrancar el servidor

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8001 --reload
```

Documentación interactiva: <http://127.0.0.1:8001/docs>

Si el puerto 8000 está ocupado, usá `--port 8001` como en el ejemplo.

---

## Endpoints

### Salud

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health/live` | El proceso está vivo. No toca la base |
| GET | `/health/ready` | Ejecuta `SELECT 1` contra la base |

### Editoriales

| Método | Ruta | Respuesta | Códigos |
|---|---|---|---|
| POST | `/editoriales/` | `EditorialCreate` → `EditorialRead` | 201, 409, 422 |
| GET | `/editoriales/` | `limit`, `offset` → lista | 200, 422 |
| GET | `/editoriales/{id}` | `EditorialRead` | 200, 404, 422 |
| PATCH | `/editoriales/{id}` | `EditorialUpdate` → `EditorialRead` | 200, 404, 409 |
| GET | `/editoriales/{id}/libros` | Libros de la editorial | 200, 404 |

> **Pendiente.** Faltan los módulos de `generos`, `autores`, `libros`,
> `clientes` y `ventas`.

---

## Estructura del proyecto

```
app/
├── main.py                 lifespan y registro de routers
├── core/
│   ├── config.py           lee DATABASE_URL del entorno
│   └── database.py         motor, fábrica de sesiones, get_session
└── modules/
    └── <módulo>/
        ├── models.py       tabla, restricciones, relaciones
        ├── schemas.py      DTO Create / Update / Read
        ├── service.py      lógica, traducción de errores, precargas
        └── router.py       rutas HTTP
migrations/                 configuración de Alembic y sus versiones
test/                       casos de prueba en archivos .http
```

---

## Migraciones

El esquema se crea **exclusivamente con Alembic**. No se usa `create_all`.

```powershell
# generar una migración comparando los modelos contra la base
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "mensaje"

# aplicarlas
.\.venv\Scripts\python.exe -m alembic upgrade head

# deshacer la última
.\.venv\Scripts\python.exe -m alembic downgrade -1

# ver el historial
.\.venv\Scripts\python.exe -m alembic history
```

El autogenerate compara los modelos contra la base **real**, así que hay que
aplicar la migración N antes de generar la N+1.

Cada migración generada debe **leerse antes de aplicarse**. Si tiene algún
problema, se corrige a mano y se explica con un comentario en el propio archivo.

---

## Configuración

| Variable | Para qué | Default |
|---|---|---|
| `DATABASE_URL` | Conexión a PostgreSQL | — (obligatoria) |
| `ECHO_SQL` | Imprime las consultas en la consola | `false` |

Poner `ECHO_SQL=true` sirve para ver las consultas que emite cada endpoint, que
es como se verifica que no haya problemas de carga por relación (N+1).

---

## Casos de prueba

Los casos de prueba (C-01 a C-08) se encuentran en la carpeta `test/casos_iniciales.http` y pueden ejecutarse con la extensión *REST Client* de VS Code.

---

## Evidencia del caso C-07

Fragmento real de la consola con `ECHO_SQL=true` al consultar el detalle de un libro (`GET /libros/2`):

```text
2026-10-13 23:10:31,096 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2026-10-13 23:10:31,137 INFO sqlalchemy.engine.Engine SELECT libro.id, libro.isbn, libro.titulo, libro.precio, libro.stock, libro.editorial_id, libro.genero_id, editorial_1.id AS id_1, editorial_1.nombre, editorial_1.pais, genero_1.id AS id_2, genero_1.nombre AS nombre_1 
FROM libro LEFT OUTER JOIN editorial AS editorial_1 ON editorial_1.id = libro.editorial_id LEFT OUTER JOIN genero AS genero_1 ON genero_1.id = libro.genero_id 
WHERE libro.id = $1::INTEGER
2026-10-13 23:10:31,192 INFO sqlalchemy.engine.Engine SELECT libro_autor.libro_id, libro_autor.autor_id, libro_autor.rol, libro_autor.orden 
FROM libro_autor 
WHERE libro_autor.libro_id IN ($1::INTEGER)
2026-10-13 23:10:31,230 INFO sqlalchemy.engine.Engine SELECT autor.id, autor.nombre, autor.nacionalidad 
FROM autor 
WHERE autor.id IN ($1::INTEGER)
INFO:     127.0.0.1:50338 - "GET /libros/2 HTTP/1.1" 200 OK
2026-10-13 23:10:31,250 INFO sqlalchemy.engine.Engine ROLLBACK
```