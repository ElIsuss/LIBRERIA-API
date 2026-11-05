# Proposal

## Why

El proyecto necesita una base técnica sobre la que se construyan todos los módulos
de dominio: una configuración validada (sin secretos en código), un ciclo de
vida que cree y cierre los recursos de base de datos, una dependencia de sesión
por petición y sondas de salud. Sin esto, ningún otro change puede implementarse
ni probarse. Este change corresponde al **Ejercicio 1** de la consigna del
Parcial (Unidades 1 a 6) y es el primer change del camino crítico
(`C-01` → `C-02` → ... → `C-08`).

## What Changes

- `app/core/config.py`: clase `Settings(BaseSettings)` con `pydantic-settings`,
  leyendo `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`,
  `POSTGRES_PORT` y construyendo `database_url` (`postgresql+asyncpg://...`) con
  `@computed_field`. Variables de JWT (`JWT_SECRET_KEY`, `JWT_ALGORITHM`,
  `JWT_EXPIRE_SECONDS`, `COOKIE_SECURE`), costo/concurrencia de `bcrypt`
  (`BCRYPT_ROUNDS`, `BCRYPT_MAX_CONCURRENCY`), `DB_POOL_SIZE` y `SQL_ECHO`.
  Ningún secreto tiene valor por defecto en código. Se mantiene compatibilidad
  con `DATABASE_URL` legado.
- `app/core/database.py`: `create_engine` (pool dimensionado por `Settings`),
  `create_session_factory` (`expire_on_commit=False`, `autoflush=False`) y
  `get_session` (una sesión por petición vía `Depends`).
- `app/main.py`: `lifespan` que inicializa motor, fábrica de sesiones y
  precalcula una sola vez el hash ficticio (`dummy_hash`) de `bcrypt` en
  `app.state`, cerrando el motor con `await engine.dispose()` al apagar.
  Configuración de logging para tareas en segundo plano y estructura de los
  **dos grupos de rutas** (Grupo Abierto y Grupo Protegido).
- `app/modules/health/router.py`: `GET /health/live` (`200` sin tocar la base)
  y `GET /health/ready` (`SELECT 1` contra PostgreSQL, `200` o `503`).
- `migrations/env.py`: lectura de `settings.database_url` desde `app.core.config`.
- `env.example`: plantilla con todas las variables de `Settings` sin secretos
  reales.

## Capabilities

### New Capabilities
- `configuracion-ciclo-vida`: configuración validada de la aplicación, gestión
  del ciclo de vida de los recursos de base de datos (motor y fábrica de
  sesiones), dependencia de sesión por petición y sondas de salud (`/health/live`,
  `/health/ready`).

### Modified Capabilities
<!-- Ninguna: es el primer change del proyecto. -->

## Impact

- Afecta `app/core/*`, `app/main.py`, `app/modules/health/*` y `migrations/env.py`.
- Desbloquea todos los changes posteriores (`C-02` ... `C-08`).
- No introduce endpoints de dominio ni tablas; el esquema se crea en `C-02`.
