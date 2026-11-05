# Proposal

## Why

El catálogo (`editoriales`, `generos`, `autores` y `libros`) opera actualmente sobre consultas directas en los servicios acopladas a la sesión y carece de abstracciones de repositorio y Unit of Work. Además, el stock de libros se modifica de forma descontrolada sin trazabilidad histórica, no existe el borrado lógico que permita conservar libros vendidos y liberar ISBNs vigentes (`RN-01`, `RN-13`), los listados utilizan `limit`/`offset` en lugar del envoltorio estándar `{items, total, page, size, pages}` (`IN-01`), y las operaciones de escritura están desprotegidas contra accesos no autorizados. Es mandatorio refactorizar estos cuatro módulos para cumplir con los Ejercicios 3b, 6b y 8a del Parcial.

## What Changes

- **Punto único de escritura de stock (`RN-11`)**: Centralización de toda mutación de `libro.stock` ligada obligatoriamente a una inserción en `movimiento_stock`, garantizando `libro.stock == SUM(movimiento_stock.cantidad)`.
- **Inmutabilidad de stock en actualización**: `LibroUpdate` no contiene el campo `stock` y posee `extra="forbid"`, retornando `422 Unprocessable Entity` si se envía `stock` en `PATCH /libros/{id}` (**BREAKING** respecto al TP 1-4).
- **Alta de libro con stock inicial**: `LibroCreate` recibe `stock_inicial: int >= 0` (en lugar de `stock`) y genera automáticamente el movimiento `"Stock inicial"` en la misma transacción (**BREAKING** respecto al TP 1-4).
- **Reposición de stock (`POST /libros/{id}/reponer`)**: Endpoint administrativo (`requiere_rol("ADMIN")`) para incrementar stock registrando el movimiento correspondiente.
- **Historial de movimientos (`GET /libros/{id}/movimientos`)**: Endpoint administrativo (`requiere_rol("ADMIN")`) para consultar todos los movimientos de stock de un libro (incluso si está dado de baja).
- **Baja lógica de libros (`DELETE /libros/{id}`)**: Endpoint administrativo (`requiere_rol("ADMIN")`) que marca `borrado_en = now()` (`RN-13`), devolviendo `204 No Content` y liberando el ISBN para futuros libros activos (`RN-01`).
- **Repositorio `LibroRepository` con `SoftDeleteRepository`**: Exclusión automática de libros con `borrado_en IS NOT NULL` en búsquedas públicas (`GET /libros`, `GET /libros/{id}`), con precargas eager declaradas (`joinedload`, `selectinload`).
- **Migración a paginación estándar `Page[T]` (`IN-01`)**: `GET /libros`, `GET /editoriales` y `GET /generos` adoptan `page` y `size`, devolviendo `{items, total, page, size, pages}` y respondiendo `422 Unprocessable Entity` si `page > pages`.
- **Protección RBAC en escritura**: Todas las rutas de modificación (`POST /libros`, `PATCH /libros/{id}`, `DELETE /libros/{id}`, `POST /editoriales`, `PATCH /editoriales/{id}`, `POST /generos`, `POST /autores`, `PATCH /autores/{id}`) exigen rol `ADMIN` en el Grupo Protegido (`RN-04`, `RN-06`).

## Capabilities

### New Capabilities
- `catalogo-stock-baja-logica`: Gestión de catálogo con soft delete, paginación estándar, reposición y punto único de escritura de movimientos de stock con trigger append-only.

### Modified Capabilities
<!-- None -->

## Impact

- Módulos afectados: `app/modules/libros/`, `app/modules/editoriales/`, `app/modules/generos/`, `app/modules/autores/`, y `app/main.py`.
- Contratos: `LibroCreate` cambia `stock` por `stock_inicial`. `LibroUpdate` prohíbe `stock`.
- API Pública: `GET /editoriales`, `GET /generos` y `GET /libros` devuelven la estructura `{items, total, page, size, pages}`.
- Pruebas: Se desarrollarán pruebas E2E integrales en `test/test_c06_e2e.py` cubriendo todos los escenarios.
