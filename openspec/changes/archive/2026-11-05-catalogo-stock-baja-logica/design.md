# Design

## Context

El catálogo de la librería comprende cuatro módulos fundamentales: `editoriales`, `generos`, `autores` y `libros`. La base de datos ya cuenta con los modelos actualizados en C-02 (`Libro` con `borrado_en` e índice único parcial `uq_libro_isbn_vigente`, y `MovimientoStock` con trigger append-only de PostgreSQL `RN-12`). La infraestructura de persistencia base (`BaseRepository`, `SoftDeleteRepository`, `UnitOfWork` y `Page[T]`) fue desarrollada en C-03. En este change se completa la refactorización arquitectónica de estos cuatro módulos.

## Goals / Non-Goals

**Goals:**
- Implementar `LibroRepository` como subclase de `SoftDeleteRepository[Libro]` con métodos de precarga eager y filtrado automático de libros dados de baja.
- Implementar `MovimientoStockRepository(BaseRepository[MovimientoStock])`.
- Diseñar en `LibrosUnitOfWork` el punto único de escritura de stock (`RN-11`) reutilizable tanto en reposición como en ventas posteriores.
- Refactorizar `editoriales`, `generos` y `autores` a `Repository + UnitOfWork` con contratos estrictos (`ConfigDict(extra="forbid")`).
- Adoptar la paginación estándar `Page[T]` con `PaginationParams` en `GET /libros`, `GET /editoriales` y `GET /generos` (`IN-01`).
- Blindar las rutas de escritura bajo el Grupo Protegido exigiendo `requiere_rol("ADMIN")`.

**Non-Goals:**
- No incluye el descuento de stock por ventas ni la gestión transaccional de pedidos (exclusivo de C-07).
- No modifica la estructura de tablas de la base de datos (las migraciones y triggers ya están activos desde C-02).

## Decisions

### Decisión 1: Punto Único de Escritura de Stock (`RN-11`)
- **Enfoque**: Se define el método centralizado `registrar_movimiento(libro: Libro, usuario_id: int, cantidad: int, motivo: str, venta_id: int | None = None)` dentro de `LibrosUnitOfWork` (o delegado a su repositorio). Este método:
  1. Verifica que el libro no esté dado de baja si es un alta o reposición.
  2. Ajusta `libro.stock = libro.stock + cantidad` (validando `stock >= 0`).
  3. Inserta la fila en `MovimientoStock` bajo la misma sesión sin hacer commit prematuro (`flush()`).
- **Alternativa descartada**: Permitir que cada endpoint modifique directamente `libro.stock` y opcionalmente inserte un movimiento. Se descartó porque rompería la invariante estricta `libro.stock == SUM(movimiento_stock.cantidad)` y violaría la regla `RN-11`.

### Decisión 2: Herencia de `SoftDeleteRepository` para Libros
- **Enfoque**: `LibroRepository` extiende `SoftDeleteRepository[Libro]`. Las operaciones estándar de lectura (`get_by_id`, `get_all`, `count`) excluyen transparentemente cualquier registro con `borrado_en IS NOT NULL`. Para endpoints de auditoría (`GET /libros/{id}/movimientos`) o ventas históricas se utiliza explícitamente `get_by_id_including_deleted(id)`.
- **Alternativa descartada**: Agregar condiciones manuales `.where(Libro.borrado_en.is_(None))` en cada servicio. Se descartó por propensión a errores y duplicación de código.

### Decisión 3: Estricta Prohibición de Modificación de Stock en `LibroUpdate`
- **Enfoque**: `LibroUpdate` se define sin el atributo `stock` y con `model_config = ConfigDict(extra="forbid")`. Si un cliente envía el atributo `stock` en `PATCH /libros/{id}`, Pydantic responde inmediatamente `422 Unprocessable Entity`.
- **Alternativa descartada**: Ignorar el campo silenciosamente en el endpoint o aceptar `stock: None`. Se descartó porque ocultaría un intento ilegal de modificación de inventario.

### Decisión 4: Organización de Routers entre Grupo Abierto y Grupo Protegido
- **Enfoque**:
  - En `open_router`: `GET /libros`, `GET /libros/{id}`, `GET /editoriales`, `GET /editoriales/{id}`, `GET /editoriales/{id}/libros`, `GET /generos`, `GET /generos/{id}/libros`, `GET /autores`, `GET /autores/{id}`, `GET /autores/{id}/libros`.
  - En `protected_router` (con `Depends(verificar_password_actualizada)` global): sub-routers de administración para `libros`, `editoriales`, `generos` y `autores`, protegidos con `Depends(requiere_rol("ADMIN"))`.
- **Alternativa descartada**: Colocar todas las rutas en un solo router y poner dependencias individuales en cada decorador. Se descartó para mantener consistencia con la arquitectura de 2 grupos de rutas establecida en `app/main.py`.

## Risks / Trade-offs

- **[Riesgo] Traspaso accidental de libros dados de baja a nuevos pedidos o reposiciones**:
  - *Mitigación*: `SoftDeleteRepository` filtra por defecto `borrado_en IS NULL`. En `reponer`, se verifica que el libro esté activo; si está dado de baja, se responde `404 Not Found`.
- **[Riesgo] Error 500 si un usuario intenta borrar un movimiento de stock**:
  - *Mitigación*: El trigger en PostgreSQL bloquea cualquier `UPDATE` o `DELETE` sobre `movimiento_stock`. La aplicación nunca expone endpoints de modificación o eliminación de movimientos (`RN-12`).
