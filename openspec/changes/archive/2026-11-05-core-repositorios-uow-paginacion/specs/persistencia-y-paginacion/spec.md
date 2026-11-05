# Spec Delta

## Purpose

Provee abstracciones de persistencia reutilizables (repositorios genéricos con
CRUD, soft-delete y paginación) y un Unit of Work que centraliza commit/rollback,
de modo que los services no ejecuten `commit()` en los repositorios ni accedan
a la sesión directamente para transacciones.

## ADDED Requirements

### Requirement: BaseRepository provee CRUD genérico
El sistema SHALL proveer `BaseRepository[T]` con `get_by_id`, `get_all`
(filtros, orden, paginación, opciones de carga), `count`, `add`, `update` y
`delete`, donde `add`/`update`/`delete` solo hacen `flush()` (nunca `commit()`).

#### Scenario: add no hace commit
- **WHEN** se llama a `repo.add(instance)`
- **THEN** la instancia queda en la sesión (flush) pero no se commitea

#### Scenario: get_all pagina
- **WHEN** se llama con `page` y `size`
- **THEN** se aplica offset `(page-1)*size` y limit `size`

### Requirement: SoftDeleteRepository filtra borrados por defecto
El sistema SHALL proveer `SoftDeleteRepository[T]` que, para modelos con
`borrado_en`, filtre automáticamente las filas con `borrado_en IS NOT NULL`
en `get_by_id`, `get_all` y `count`, salvo `include_deleted=True`.

#### Scenario: Listado excluye borrados
- **WHEN** existen filas con `borrado_en` no nulo
- **THEN** `get_all()` las excluye por defecto

#### Scenario: include_deleted las incluye
- **WHEN** se llama con `include_deleted=True`
- **THEN** las filas borradas aparecen en el resultado

### Requirement: soft_delete marca borrado_en
El sistema SHALL marcar `borrado_en = now()` en lugar de borrar la fila, y
hacer `flush()`.

#### Scenario: soft_delete marca timestamp
- **WHEN** se llama a `soft_delete(id)`
- **THEN** la fila queda con `borrado_en` no nulo y no se borra físicamente

### Requirement: UnitOfWork centraliza commit/rollback
El sistema SHALL proveer `UnitOfWork` (context manager async) que hace
`commit()` en `__aexit__` si no hubo excepción y `rollback()` en caso
contrario, y expone `commit()`/`rollback()` manuales.

#### Scenario: Commit automático al salir sin error
- **WHEN** el bloque `async with uow:` termina sin excepción
- **THEN** se ejecuta `session.commit()`

#### Scenario: Rollback automático ante excepción
- **WHEN** el bloque `async with uow:` lanza una excepción
- **THEN** se ejecuta `session.rollback()` y la excepción se propaga

### Requirement: Paginación estable con orden total
El sistema SHALL ordenar todo listado antes de limitar; si la columna de orden
no es única, el desempate se hace por `id`.

#### Scenario: Paginación sin repetir filas
- **WHEN** se recorren páginas con `limit=1`
- **THEN** no se repiten ni se saltean filas

### Requirement: ISBN reutilizable tras baja lógica
El sistema SHALL permitir reutilizar un ISBN de un libro dado de baja, mediante
un índice parcial único `uq_libro_isbn_vigente` sobre `isbn` donde
`borrado_en IS NULL`.

#### Scenario: ISBN reutilizable
- **WHEN** un libro con ISBN X se da de baja (soft delete)
- **THEN** se puede crear otro libro con el mismo ISBN X
