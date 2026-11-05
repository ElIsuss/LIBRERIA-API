# Design

## Context

Ver `proposal.md` — Why. La persistencia genérica vive en `app/core/` y es
consumida por todos los módulos de dominio. El soft-delete se aplica solo a
`Libro` (que tiene `borrado_en`); el resto usa `BaseRepository`.

## Goals / Non-Goals

**Goals:**
- Repositorios genéricos reutilizables.
- UoW que centraliza commit/rollback.
- Paginación estable.
- Soft-delete con índice parcial para ISBN.

**Non-Goals:**
- Endpoints y DTOs (C-06, C-07).
- Lógica de negocio (services).
- Autenticación (C-04).

## Decisions

- **Genéricos con TypeVar bound a SQLModel:** reutilizables para cualquier
  modelo de tabla.
- **`flush()` en repos, `commit()` solo en UoW:** regla dura del proyecto
  (Regla 13). Los repos nunca commitean.
- **Soft-delete opcional por `hasattr(model, "borrado_en")`:** permite que el
  mismo repositorio sirva para modelos con y sin soft-delete.
- **Paginación con `page`/`size` (1-based) en repos y `limit`/`offset` en
  routers:** los routers exponen `limit`/`offset` (RN-10); los repos usan
  `page`/`size` para uso interno.
- **Índice parcial único:** `postgresql_where=text("borrado_en IS NULL")` permite
  reutilizar ISBN tras baja lógica.

## Risks / Trade-offs

- [Riesgo] El UoW comparte la sesión de la petición con las dependencias de
  auth (`get_usuario_actual`); si una falla, el rollback afecta a todas.
  Mitigación: documentado en Regla 13.
- [Trade-off] Soft-delete solo en `Libro`; otros modelos se borran físicamente.

## Migration Plan

El índice parcial se incluye en la migración de modelos (C-02). No hay
migración nueva en este change.

## Open Questions

Ninguna.
