# Design

## Context

Ver `proposal.md` — Why. Este change crea el esquema completo del dominio y lo
versiona con Alembic. No incluye lógica de negocio ni repositorios (eso es C-03).

## Goals / Non-Goals

**Goals:**
- Todos los modelos con restricciones y relaciones navegables.
- Migraciones asincrónicas aplicables y reversibles.
- Trigger append-only sobre `movimiento_stock`.

**Non-Goals:**
- Repositorios, UoW, paginación (C-03).
- Endpoints y DTOs (C-06, C-07).
- Autenticación (C-04).

## Decisions

- **Objeto de asociación `LibroAutor`:** se modela como entidad (no `link_model`)
  porque tiene `rol` y `orden` propios. Navegación: `libro.autorias[i].autor`.
- **Composición vs asociación por ON DELETE:** CASCADE para composición
  (renglón→venta), RESTRICT para asociación/agregación.
- **`NUMERIC` + `Decimal`:** nunca float para dinero.
- **Trigger manual (4.ª migración):** la 3.ª es autogenerada; la 4.ª (trigger)
  se escribe a mano porque Alembic no la detecta.
- **Autogenerate con correcciones manuales:** `AutoString()` sin import se cambia
  a `sa.String()`; FK sin nombre se nombra (`fk_libro_genero_id`).

## Risks / Trade-offs

- [Riesgo] El autogenerate puede generar SQL incorrecto. Mitigación: leer cada
  migración antes de aplicarla y corregir a mano.
- [Riesgo] El trigger impide correcciones accidentales pero también legítimas.
  Mitigación: las correcciones de stock pasan por el punto único de escritura.
- [Trade-off] 4 migraciones en lugar de 1: permite `downgrade -1` granular.

## Migration Plan

`alembic upgrade head` sobre base vacía crea todas las tablas. `downgrade -1`
deshace la última migración. Verificado: upgrade → downgrade -1 → upgrade head.

## Open Questions

Ninguna.
