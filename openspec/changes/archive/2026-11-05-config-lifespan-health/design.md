# Design

## Context

Ver `proposal.md` — Why. Este change sienta la infraestructura mínima: no hay
modelos de dominio ni tablas todavía (eso es `C-02`). El código vive en
`app/core/` y `app/modules/health/`, con `migrations/env.py` como puente hacia
Alembic.

## Goals / Non-Goals

**Goals:**
- Configuración validada y sin secretos en código (compatibilidad con
  `DATABASE_URL` legado).
- Motor y fábrica de sesiones creados en el `lifespan` y cerrados al apagar.
- Una sesión por petición, compartida entre dependencias.
- Sondas `/health/live` y `/health/ready` con los códigos esperados.
- Hash ficticio precalculado una sola vez.

**Non-Goals:**
- Modelos de tabla y migraciones (C-02).
- Repositorios, Unit of Work y paginación (C-03).
- Autenticación y autorización (C-04, C-05).

## Decisions

- **pydantic-settings sobre python-dotenv directo:** validación tipada y
  `@computed_field` para `database_url`, evitando concatenación manual de
  strings. Alternativa considerada: leer `os.environ` a mano, descartada por
  falta de validación.
- **Pool dimensionado por `db_pool_size` con `max_overflow = db_pool_size`:**
  evita picos de conexiones. Alternativa: `max_overflow` default (10), descartada
  para mantener control explícito.
- **`expire_on_commit=False` + `autoflush=False`:** evita consultas implícitas al
  commit y controla cuándo se flushea. Es la convención del proyecto (Regla 13).
- **`dummy_hash` en `app.state`:** se calcula una sola vez al arrancar, fuera
  del event loop (`asyncio.to_thread`), para comparaciones en tiempo constante.
  Alternativa: calcular por petición, descartada por costo y por filtrado de
  timing.
- **Compatibilidad legada con `DATABASE_URL`:** permite reutilizar `.env` de
  versiones anteriores del TP sin romper el arranque.

## Risks / Trade-offs

- [Riesgo] Si `POSTGRES_PASSWORD` contiene caracteres especiales, la URL
  construida puede romper el parseo. Mitigación: se recomienda `DATABASE_URL`
  legado para passwords complejos.
- [Riesgo] Pool pequeño (`db_pool_size=5`) puede saturarse bajo carga. Mitigación:
  configurable por entorno.
- [Trade-off] `autoflush=False` obliga a `flush()` explícito en los services;
  es intencional (control transaccional).

## Migration Plan

No aplica: este change no crea ni modifica tablas. El esquema se crea en C-02
con Alembic.

## Open Questions

Ninguna.
