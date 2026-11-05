# Tasks

## 1. Configuración

- [x] 1.1 Crear `app/core/config.py` con `Settings(BaseSettings)` leyendo
  `POSTGRES_*`, `JWT_SECRET_KEY`, `BCRYPT_*`, `DB_POOL_SIZE`, `SQL_ECHO` y
  compatibilidad legada con `DATABASE_URL`. Verificación: `from app.core.config
  import settings` no lanza error con `.env` válido; lanza error sin secretos.
- [x] 1.2 Crear `env.example` con todas las variables sin secretos reales.
  Verificación: `git check-ignore .env` confirma que `.env` no se versiona.

## 2. Base de datos y ciclo de vida

- [x] 2.1 Crear `app/core/database.py` con `create_engine`, `create_session_factory`
  (`expire_on_commit=False`, `autoflush=False`) y `get_session`.
  Verificación: `SELECT 1` via `/health/ready` responde 200.
- [x] 2.2 Crear `app/main.py` con `lifespan` que inicializa motor y fábrica,
  precalcula `dummy_hash` en `app.state` y cierra el motor al apagar.
  Verificación: al apagar el servidor el pool se libera (`engine.dispose`).
- [x] 2.3 Registrar la estructura de dos grupos de rutas (Abierto/Protegido).
  Verificación: `/docs` lista los routers registrados.

## 3. Sondas de salud

- [x] 3.1 Crear `app/modules/health/router.py` con `GET /health/live` (200, sin
  tocar la base) y `GET /health/ready` (`SELECT 1`, 200 o 503).
  Verificación: `/health/live` no abre conexión; `/health/ready` abre 1.

## 4. Migraciones

- [x] 4.1 Ajustar `migrations/env.py` para leer `settings.database_url`.
  Verificación: `alembic upgrade head` crea el esquema sin error.

## 5. Verificación integrada

- [x] 5.1 Levantar el servidor y comprobar `/health/live` y `/health/ready`.
  Verificación: ambos responden 200.
- [x] 5.2 Comprobar que 3 llamadas seguidas a `/health/ready` reutilizan el pool.
  Verificación: logs de asyncpg muestran reutilización.

## Workflow follow-up

- Archivar el change con `/opsx:archive config-lifespan-health` una vez verificado.
- Actualizar el estado de C-01 en `CHANGES.md` (ya marcado `[x]`).
