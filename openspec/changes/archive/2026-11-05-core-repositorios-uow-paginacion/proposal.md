# Proposal

## Why

Los módulos de dominio necesitan una abstracción de persistencia compartida
(`BaseRepository`, `SoftDeleteRepository`) y un `UnitOfWork` que centralice
commit/rollback, para que los services no accedan a la sesión directamente ni
ejecuten `commit()` en los repositorios. La paginación y el soft-delete (baja
lógica) son transversales a todos los listados. Este change corresponde a los
**Ejercicios 3a y 6a** del Parcial.

## What Changes

- `app/core/repository.py`: `BaseRepository[T]` genérico con `get_by_id`,
  `get_all` (filtros, orden, paginación, opciones de carga), `count`, `add`,
  `update`, `delete`. `SoftDeleteRepository[T]` extiende con `include_deleted`,
  `soft_delete` y filtrado automático por `borrado_en IS NULL`.
- `app/core/unit_of_work.py`: `UnitOfWork` async (context manager) que hace
  `commit` en `__aexit__` si no hubo excepción, `rollback` en caso contrario,
  y expone `commit()`/`rollback()` manuales.
- Paginación basada en `page`/`size` (offset = (page-1)*size) además de
  `limit`/`offset` por `Query` en los routers.
- Índice parcial único `uq_libro_isbn_vigente` sobre `libro.isbn` donde
  `borrado_en IS NULL`, para permitir reutilizar ISBN de libros dados de baja.

## Capabilities

### New Capabilities
- `persistencia-y-paginacion`: repositorios genéricos (CRUD + soft-delete),
  Unit of Work con commit/rollback centralizado y paginación reutilizable.

### Modified Capabilities
<!-- Ninguna. -->

## Impact

- Afecta `app/core/repository.py`, `app/core/unit_of_work.py` y todos los
  módulos que los consumen (C-04 ... C-08).
- Desbloquea la implementación de los módulos de dominio con lógica transaccional.
