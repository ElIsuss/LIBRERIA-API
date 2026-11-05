# Tasks

## 1. Contratos estrictos de entrada (TDD)

- [x] 1.1 **RED**: crear `test/test_c07_schemas_unit.py` con `unittest` que verifique que `ClienteCreate`, `ClienteUpdate`, `PerfilCreate`, `VentaCreate` y `RenglonVentaCreate` rechazan campos extra (`extra="forbid"`), que `VentaCreate` rechaza `renglones` vacíos, `cantidad <= 0`, `libro_id` repetido y un `total` enviado por el cliente, y que `RenglonVentaCreate` rechaza `precio_unitario`. Ejecutar `python test/test_c07_schemas_unit.py` y confirmar que las aserciones de campos extra fallan por los schemas actuales.
- [x] 1.2 **GREEN**: agregar `model_config = ConfigDict(extra="forbid")` y los validadores faltantes en `app/modules/clientes/schemas.py` y `app/modules/ventas/schemas.py`. Ejecutar `python test/test_c07_schemas_unit.py` y confirmar que todos los casos pasan.

## 2. Módulo clientes: repositorio y Unit of Work (TDD)

- [x] 2.1 **RED**: crear `test/test_c07_clientes_unit.py` que inserte un cliente con perfil y otro sin perfil, y verifique que `ClienteRepository.get_detalle()` devuelve el `perfil` precargado sin consultas adicionales (contando SQL con un listener del engine) y que `get_by_usuario_id()` encuentra la ficha vinculada. Ejecutar `python test/test_c07_clientes_unit.py` y confirmar que falla porque `get_detalle` no existe.
- [x] 2.2 **GREEN**: implementar en `app/modules/clientes/repository.py` la precarga declarada `joinedload(Cliente.perfil)` y el método `get_detalle`, y crear `app/modules/clientes/unit_of_work.py` con `ClientesUnitOfWork` y `get_clientes_uow`. Ejecutar `python test/test_c07_clientes_unit.py` y confirmar que pasa.
- [x] 2.3 Verificar que `ClienteRepository` y `ClientesUnitOfWork` no ejecutan `commit()` ni `rollback()` propios: agregar al test un espía sobre `AsyncSession.commit` y `AsyncSession.rollback` que confirme que ninguna llamada proviene de las operaciones del repositorio, y ejecutar `python test/test_c07_clientes_unit.py`.

## 3. Módulo clientes: servicio y router con RBAC (TDD)

- [x] 3.1 **RED**: crear `test/test_c07_clientes_e2e.py` con `httpx.ASGITransport` y el `lifespan` de la app cubriendo `POST /clientes` (`201`, `409` por correo duplicado, `422` por campo extra o correo inválido), `GET /clientes/{id}` (`200` con perfil, `200` sin perfil, `404`), `PATCH /clientes/{id}` (`200`, `409`, `404`, `422`) y el rechazo `403` para rol `CLIENTE`. Ejecutar `python test/test_c07_clientes_e2e.py` y confirmar que falla (las rutas aún no exigen rol).
- [x] 3.2 **GREEN**: implementar `crear_cliente`, `obtener_por_id` y `actualizar` en `app/modules/clientes/service.py` sobre `ClientesUnitOfWork`, traduciendo `IntegrityError` a `409` y usando sólo `async with uow:`; crear en `app/modules/clientes/router.py` el router con `dependencies=[Depends(requiere_rol("VENDEDOR", "ADMIN"))]` y registrarlo en el Grupo Protegido de `app/main.py`. Ejecutar `python test/test_c07_clientes_e2e.py` y confirmar que los casos de alta, consulta y actualización pasan.
- [x] 3.3 **RED**: ampliar `test/test_c07_clientes_e2e.py` con `POST /clientes/{id}/perfil` (`201`, `404` con cliente inexistente, `409` con segundo perfil, `422` por campo extra) y con los escenarios de acceso `401` sin cookie y `403` con `debe_cambiar_password = True` sobre las cuatro rutas. Ejecutar el script y confirmar que los casos nuevos fallan.
- [x] 3.4 **GREEN**: implementar `crear_perfil` en el servicio y la ruta `POST /clientes/{id}/perfil` en el router de clientes. Ejecutar `python test/test_c07_clientes_e2e.py` y confirmar que todos los escenarios de `gestion-clientes` (excepto `GET /clientes/{id}/ventas`) pasan.

## 4. Módulo ventas: repositorio y Unit of Work (TDD)

- [x] 4.1 **RED**: crear `test/test_c07_ventas_unit.py` que siembre un cliente, libros (uno con `borrado_en` no nulo), una venta histórica con dos renglones y verifique que `VentaRepository.get_detalle()` devuelve `cliente` y `renglones` con el título del libro dado de baja, y que `listar_paginado()` devuelve `(items, total)` y filtra por cliente. Ejecutar `python test/test_c07_ventas_unit.py` y confirmar que falla porque `VentaRepository` no existe.
- [x] 4.2 **GREEN**: implementar `app/modules/ventas/repository.py` con `VentaRepository(BaseRepository[Venta])`, `_opciones_detalle()` (`joinedload(Venta.cliente)` y `selectinload(Venta.renglones).joinedload(RenglonVenta.libro)`), `get_detalle`, `listar_paginado` y `listar_por_cliente`; y `app/modules/ventas/unit_of_work.py` con `VentasUnitOfWork(LibrosUnitOfWork)` exponiendo `ventas`, `clientes` y `roles`, más `get_ventas_uow`. Ejecutar `python test/test_c07_ventas_unit.py` y confirmar que pasa.
- [x] 4.3 Agregar a `test/test_c07_ventas_unit.py` un caso que invoque `VentasUnitOfWork.registrar_movimiento_stock(...)` y confirme que se reutiliza el método heredado de `LibrosUnitOfWork`: el stock cambia, se inserta un `MovimientoStock` y no hay `commit()` dentro del método. Ejecutar `python test/test_c07_ventas_unit.py` y confirmar que pasa.

## 5. Registro atómico de ventas y aviso en segundo plano (TDD)

- [x] 5.1 **RED**: crear `test/test_c07_ventas_e2e.py` con el escenario exitoso de `POST /ventas`: `201`, `total` calculado con los precios de la base, `precio_unitario` copiado en cada renglón, exactamente un `movimiento_stock` negativo por renglón con `venta_id` y `usuario_id`, y `libro.stock == SUM(movimiento_stock.cantidad)` después de la venta. Ejecutar `python test/test_c07_ventas_e2e.py` y confirmar que falla.
- [x] 5.2 **RED**: ampliar `test/test_c07_ventas_e2e.py` con los rechazos `409` (cliente inexistente, libro inexistente, libro dado de baja lógica y stock insuficiente), el rollback total cuando falla el segundo renglón (stock del primer libro intacto, sin venta ni movimientos), los `422` de contrato y el `403` para rol `CLIENTE`. Ejecutar el script y confirmar que los casos nuevos fallan.
- [x] 5.3 **GREEN**: implementar `ventas.service.crear` con un único `async with uow:` (cliente, libros vigentes con `uow.libros.get_all(filters=[Libro.id.in_(...)], include_deleted=False)`, validación de stock, venta, renglones con precio copiado y llamada a `uow.registrar_movimiento_stock` con `cantidad=-cantidad` y `motivo="Venta"`), la relectura con `uow.ventas.get_detalle` después del commit y el router `ventas_personal_router` con `requiere_rol("VENDEDOR", "ADMIN")` para `POST /ventas`. Ejecutar `python test/test_c07_ventas_e2e.py` y confirmar que los casos de registro pasan.
- [x] 5.4 **RED**: agregar a `test/test_c07_ventas_e2e.py` la verificación del aviso en segundo plano: tras un `201` se ejecuta `enviar_comprobante` (espera de 0.5 s y log en `app.modules.ventas.service`), y tras un `409` o `422` no se agenda. Ejecutar el script y confirmar que falla.
- [x] 5.5 **GREEN**: implementar `enviar_comprobante` con `await asyncio.sleep(0.5)` y log, agendarlo en `background_tasks.add_task(...)` sólo después de que el servicio retorna con éxito, y cambiar `logging.basicConfig` en `app/main.py` a nivel `INFO` incondicional (sin tocar el `echo` del motor). Ejecutar `python test/test_c07_ventas_e2e.py` y confirmar que pasa.

## 6. Consultas de ventas y acceso por dueño (TDD)

- [x] 6.1 **RED**: ampliar `test/test_c07_ventas_e2e.py` con `GET /ventas`: `200` con `{items, total, page, size, pages}`, `422` cuando `page` excede las páginas, `403` para rol `CLIENTE`, título visible de un libro dado de baja y cantidad fija de consultas SQL al comparar una venta de 2 renglones con otra de 4 (listener `before_cursor_execute`). Ejecutar el script y confirmar que falla.
- [x] 6.2 **RED**: agregar a `test/test_c07_ventas_e2e.py` los escenarios de `GET /mis-ventas`: `200` con sólo las ventas del cliente vinculado, `200` con página vacía para un usuario sin ficha de cliente, `422` fuera de rango, `401` sin cookie y `403` con cambio de contraseña pendiente. Ejecutar el script y confirmar que falla.
- [x] 6.3 **RED**: agregar a `test/test_c07_ventas_e2e.py` los escenarios de `GET /ventas/{id}`: `200` para `VENDEDOR`/`ADMIN` sobre cualquier venta, `200` para el `CLIENTE` dueño, `403` para un `CLIENTE` ajeno, `404` para una venta inexistente, `403` en la petición siguiente a la revocación del rol `VENDEDOR`, título visible de un libro dado de baja y `401` sin cookie. Ejecutar el script y confirmar que falla.
- [x] 6.4 **RED**: agregar a `test/test_c07_clientes_e2e.py` los escenarios de `GET /clientes/{id}/ventas`: `200` ordenado de la más reciente a la más antigua, título visible de un libro dado de baja, `200` con lista vacía, `404` con cliente inexistente y `403` para rol `CLIENTE`. Ejecutar el script y confirmar que falla.
- [x] 6.5 **GREEN**: implementar en `ventas.service` el listado paginado para personal, la consulta propia y el detalle con control de dueño o personal (roles vigentes vía `uow.roles.get_roles_vigentes`), y `listar_por_cliente` para `GET /clientes/{id}/ventas`; crear `ventas_router` (`GET /ventas/{id}` con `get_usuario_actual`), `mis_ventas_router` (`GET /mis-ventas` en la raíz) y montar los tres routers de ventas en el Grupo Protegido de `app/main.py`. Ejecutar `python test/test_c07_ventas_e2e.py` y `python test/test_c07_clientes_e2e.py` y confirmar que todos los escenarios pasan.

## 7. Verificación de integración

- [x] 7.1 Ejecutar en orden `python test/test_c04_e2e.py`, `python test/test_c05_e2e.py`, `python test/test_c06_e2e.py`, `python test/test_c07_clientes_e2e.py` y `python test/test_c07_ventas_e2e.py`, y confirmar que no hay regresiones en los changes anteriores.
- [x] 7.2 Verificar manualmente con Uvicorn en arranque normal (sin `SQL_ECHO`): registrar una venta y confirmar que el mensaje del aviso en segundo plano aparece en consola, y que `/docs` lista las rutas nuevas (`/clientes`, `/clientes/{id}/perfil`, `/clientes/{id}/ventas`, `/ventas`, `/ventas/{id}`, `/mis-ventas`).
- [x] 7.3 Verificar estáticamente que ningún archivo nuevo de `app/modules/clientes/` o `app/modules/ventas/` contiene rutas absolutas ni credenciales, y que los repositorios no llaman `commit()` ni `rollback()`; ejecutar `openspec validate "clientes-ventas-transaccionales" --strict` y confirmar que no hay errores.

## Workflow follow-up

- Archivar el change con `/opsx-archive clientes-ventas-transaccionales` después de revisar la implementación.
- Actualizar `CHANGES.md` marcando `C-07` como completado.
