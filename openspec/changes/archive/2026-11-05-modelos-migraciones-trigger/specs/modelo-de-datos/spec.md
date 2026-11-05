# Spec Delta

## Purpose

Define el esquema relacional del dominio de la librería: tablas con restricciones
de unicidad, comprobación y claves foráneas, navegación en ambos extremos de cada
relación, versionado con Alembic y un trigger append-only que protege el
historial de movimientos de stock.

## ADDED Requirements

### Requirement: El esquema se crea con Alembic sobre base vacía
El sistema SHALL crear todas las tablas mediante `alembic upgrade head` sobre
una base vacía, sin usar `create_all`.

#### Scenario: Upgrade sobre base vacía
- **WHEN** se ejecuta `alembic upgrade head` sobre una base sin tablas
- **THEN** se crean todas las tablas del dominio y `alembic current` indica head

#### Scenario: Downgrade y re-upgrade
- **WHEN** se ejecuta `alembic downgrade -1` seguido de `alembic upgrade head`
- **THEN** ambas operaciones terminan sin error

### Requirement: Unicidad garantizada por la base
El sistema SHALL declarar UNIQUE en `libro.isbn`, `cliente.email`,
`editorial.nombre`, `genero.nombre` y `perfil_cliente.cliente_id`.

#### Scenario: ISBN duplicado
- **WHEN** se inserta un libro con un ISBN ya existente
- **THEN** la base rechaza la inserción con error de unicidad

### Requirement: Comprobaciones (CHECK) en la base
El sistema SHALL declarar CHECK para `libro.precio > 0`, `libro.stock >= 0`,
`renglon_venta.cantidad > 0`, `renglon_venta.precio_unitario > 0`,
`venta.total >= 0`, `libro_autor.orden >= 1` y rol válido, y
`movimiento_stock.cantidad <> 0`.

#### Scenario: Precio no positivo
- **WHEN** se intenta insertar un libro con precio <= 0
- **THEN** la base rechaza la inserción

### Requirement: Claves foráneas con ON DELETE correcto
El sistema SHALL declarar FK con `ON DELETE CASCADE` en composición
(`renglon_venta.venta_id`, `libro_autor.libro_id`/`autor_id` por libro),
`RESTRICT` en asociación/agregación (`libro.editorial_id`, `venta.cliente_id`,
`renglon_venta.libro_id`, `movimiento_stock.*`) y `SET NULL` en agregación
opcional (`libro.genero_id`).

#### Scenario: Composición se borra en cascada
- **WHEN** se borra una venta
- **THEN** sus renglones se borran automáticamente

### Requirement: Índices en todas las FK
El sistema SHALL tener un índice en cada columna que es FK (PostgreSQL no los
crea automáticamente).

#### Scenario: Índice presente
- **WHEN** se inspecciona el esquema
- **THEN** cada FK tiene su índice

### Requirement: Navegación en ambos extremos
El sistema SHALL declarar `Relationship(back_populates=...)` en ambos extremos
de cada relación, de modo que `libro.autorias[i].autor` y
`autor.autorias[i].libro` funcionen.

#### Scenario: Navegación bidireccional
- **WHEN** se carga un libro con sus autorías
- **THEN** cada autoría expone su autor y el libro expone sus autorías

### Requirement: movimientos de stock son append-only
El sistema SHALL rechazar UPDATE y DELETE sobre `movimiento_stock` mediante un
trigger PostgreSQL.

#### Scenario: UPDATE rechazado
- **WHEN** se ejecuta `UPDATE movimiento_stock SET ...`
- **THEN** la base lanza una excepción y no modifica la fila

#### Scenario: DELETE rechazado
- **WHEN** se ejecuta `DELETE FROM movimiento_stock`
- **THEN** la base lanza una excepción y no borra la fila

### Requirement: El dinero se representa con Decimal/NUMERIC
El sistema SHALL usar `NUMERIC` (no float) para `libro.precio`,
`renglon_venta.precio_unitario` y `venta.total`.

#### Scenario: Precisión decimal
- **WHEN** se lee un precio
- **THEN** se serializa como string con 2 decimales, sin pérdida por float
