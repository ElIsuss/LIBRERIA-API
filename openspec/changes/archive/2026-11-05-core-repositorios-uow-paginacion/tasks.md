# Tasks

## 1. Repositorios

- [x] 1.1 Crear `app/core/repository.py` con `BaseRepository[T]` (CRUD genérico).
  Verificación: `get_by_id`, `get_all`, `count`, `add`, `update`, `delete`
  usan `flush()` y no `commit()`.
- [x] 1.2 Crear `SoftDeleteRepository[T]` con `include_deleted`, `soft_delete`.
  Verificación: listado excluye borrados por defecto; `soft_delete` marca
  `borrado_en`.

## 2. Unit of Work

- [x] 2.1 Crear `app/core/unit_of_work.py` con `UnitOfWork` (context manager).
  Verificación: commit automático sin error; rollback ante excepción.

## 3. Paginación y soft-delete

- [x] 3.1 Implementar paginación estable (orden por columna + desempate por id).
  Verificación: `limit=1` recorre sin repetir ni saltear.
- [x] 3.2 Agregar índice parcial único `uq_libro_isbn_vigente` en `libro.isbn`.
  Verificación: reutilizar ISBN tras soft-delete funciona.

## 4. Verificación

- [x] 4.1 Verificar que ningún repositorio ejecuta `commit()`.
  Verificación: grep `commit()` en `app/core/repository.py` = 0 resultados.
- [x] 4.2 Verificar UoW con test de commit/rollback.
  Verificación: test pasa.

## Workflow follow-up

- Archivar el change con `/opsx:archive core-repositorios-uow-paginacion`.
- Actualizar el estado de C-03 en `CHANGES.md` (ya marcado `[x]`).
