# Proposal

## Why

El dominio de la librería (editoriales, géneros, autores, libros, clientes,
ventas, renglones, movimientos de stock, usuarios/seguridad) necesita existir
como tablas en PostgreSQL con todas sus restricciones (UNIQUE, CHECK, FK, índices)
y navegación en ambos extremos de cada relación. El esquema debe versionarse con
Alembic (plantilla asincrónica) y el historial de stock debe ser append-only
mediante un trigger. Este change corresponde al **Ejercicio 2** (modelos) y
parte del **Ejercicio 7** (trigger) del Parcial.

## What Changes

- Modelos de tabla en `app/modules/*/models.py`: `Editorial`, `Genero`, `Autor`,
  `Libro`, `LibroAutor`, `Cliente`, `PerfilCliente`, `Venta`, `RenglonVenta`,
  `MovimientoStock`, `Usuario`, `AsignacionRol`, `IntentoAcceso`, `EventoSeguridad`.
- Relaciones declaradas en ambos extremos (`Relationship(back_populates=...)`),
  con `ON DELETE` correcto por tipo de relación (CASCADE/RESTRICT/SET NULL).
- Dinero como `Decimal`/`NUMERIC`, fechas con zona horaria.
- Migraciones Alembic: `b469c2e9997b` (tablas iniciales), `d29720c70b22`
  (genero + `libro.genero_id`), `8d29d5d17a3a` (seguridad y plantilla C-02),
  `f22d38b1dde0` (trigger append-only sobre `movimiento_stock`).
- Trigger `trg_movimiento_stock_append_only` que rechaza UPDATE/DELETE.

## Capabilities

### New Capabilities
- `modelo-de-datos`: modelos de tabla del dominio con restricciones, relaciones
  navegables en ambos extremos, migraciones Alembic asincrónicas y trigger
  append-only sobre `movimiento_stock`.

### Modified Capabilities
<!-- Ninguna: el esquema se crea por primera vez. -->

## Impact

- Afecta `app/modules/*/models.py` y `migrations/versions/*`.
- Desbloquea `C-03` (repositorios y UoW) y, por transitividad, `C-04`..`C-08`.
- Base debe estar vacía para `alembic upgrade head`.
