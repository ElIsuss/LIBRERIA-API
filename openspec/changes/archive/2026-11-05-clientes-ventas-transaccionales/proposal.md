# Proposal

## Why

Los módulos `clientes` y `ventas` siguen operando con servicios acoplados directamente a la sesión, sin repositorios ni Unit of Work, y el registro de ventas actual no descuenta stock ni genera `movimiento_stock`. Eso incumple `RN-09`, `RN-10` y `RN-11`: una venta podría confirmarse sin respaldo de inventario y un fallo a mitad de camino podría dejar escrituras parciales. Tampoco existen `GET /mis-ventas` ni el control de dueño en `GET /ventas/{id}` (`RN-14`), y los listados no usan el envoltorio estándar `Page[T]` (`IN-01`). Este change corresponde a `C-07` del roadmap y depende de `C-06`.

## What Changes

- **Refactorización del módulo `clientes` a `Repository + UnitOfWork`**:
  - `ClienteRepository` con precarga declarada de `perfil` y `ClientesUnitOfWork`.
  - Schemas de entrada con `model_config = ConfigDict(extra="forbid")`.
  - Rutas en el Grupo Protegido con `requiere_rol("VENDEDOR", "ADMIN")`: `POST /clientes`, `GET /clientes/{id}`, `PATCH /clientes/{id}`, `POST /clientes/{id}/perfil` y `GET /clientes/{id}/ventas`.
- **Refactorización del módulo `ventas` a `Repository + UnitOfWork`**:
  - `VentaRepository` con precarga declarada `joinedload(Venta.cliente)` y `selectinload(Venta.renglones).joinedload(RenglonVenta.libro)`, incluyendo libros con baja lógica en ventas históricas (`RN-13`) y sin N+1.
  - `VentasUnitOfWork` que integra los repositorios de ventas, clientes y roles, y **reutiliza** el punto único de escritura de stock de `LibrosUnitOfWork` (`RN-11`).
- **`POST /ventas` (`VENDEDOR`, `ADMIN` → `201`, `409`, `422`)**: un solo `UnitOfWork` que valida cliente y libros vigentes con stock suficiente, copia `libro.precio` en cada renglón (`RN-09`), calcula el `total` en el servidor, descuenta stock y registra un `movimiento_stock` negativo por renglón con `venta_id` y `usuario_id` (`RN-11`). Ante cualquier fallo hace `rollback` total y responde `409` (`RN-10`).
- **Aviso en segundo plano**: después del `commit`, el router agenda en `BackgroundTasks` el aviso con `await asyncio.sleep(0.5)` y un log visible en el arranque normal de Uvicorn.
- **`GET /ventas` (`VENDEDOR`, `ADMIN` → `200`, `422`)**: listado paginado con envoltorio `Page[VentaRead]`.
- **`GET /mis-ventas` (cualquier autenticado sin cambio de clave pendiente → `200`, `422`)**: listado paginado de las ventas del cliente vinculado al usuario autenticado (`RN-14`).
- **`GET /ventas/{id}` (autenticado → `200`, `403`, `404`)**: el servicio autoriza al personal (`VENDEDOR`/`ADMIN`, consultando `asignacion_rol` en la base, `RN-04`) o al `CLIENTE` dueño de la venta; si pertenece a otro cliente responde `403` (`RN-14`).

## Capabilities

### New Capabilities

- `gestion-clientes`: alta, consulta, modificación de clientes y alta de su perfil único, más la consulta de ventas de un cliente por parte del personal, con contratos estrictos y RBAC `VENDEDOR`/`ADMIN`.
- `ventas-transaccionales`: registro atómico de ventas con copia de precio, cálculo de total en servidor, descuento de stock y movimiento de stock; listados paginados para personal, consulta propia del cliente y control de dueño en el detalle.

### Modified Capabilities

<!-- Ninguna: el punto único de escritura de stock de catalogo-stock-baja-logica se reutiliza sin cambiar sus requisitos. -->

## Impact

- Módulos afectados: `app/modules/clientes/` (models, schemas, repository, unit_of_work, service, router), `app/modules/ventas/` (schemas, repository, unit_of_work, service, router) y `app/main.py` (registro de routers y nivel de logging de las tareas en segundo plano).
- Contratos: se agrega `extra="forbid"` a los schemas de entrada de clientes y ventas; `GET /ventas` pasa de `list[VentaRead]` con `limit`/`offset` a `Page[VentaRead]` con `page`/`size` (**BREAKING** respecto del TP 1-4); se agrega la ruta de nivel superior `GET /mis-ventas`.
- Base de datos: sin cambios de esquema ni migraciones; se reutilizan las tablas y el trigger append-only existentes.
- Pruebas: unitarias con `unittest.IsolatedAsyncioTestCase` y E2E con script asincrónico en `test/`, siguiendo la convención de C-04, C-05 y C-06.
