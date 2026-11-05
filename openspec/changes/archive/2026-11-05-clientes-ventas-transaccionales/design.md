# Design

## Context

Ver `proposal.md` — Why. El estado actual que condiciona el approach:

- `app/modules/clientes/service.py` y `app/modules/ventas/service.py` operan directamente sobre `AsyncSession`, hacen `commit()`/`rollback()` por su cuenta y no usan repositorios ni Unit of Work.
- `app/modules/clientes/repository.py` ya existe con `get_by_email` y `get_by_usuario_id`, pero no precarga `perfil` ni está integrado a un `UnitOfWork`.
- `app/modules/ventas/` no tiene `repository.py` ni `unit_of_work.py`; `crear()` no descuenta stock ni inserta en `movimiento_stock`.
- El punto único de escritura de stock (`RN-11`) ya está implementado por C-06 en `app/modules/libros/unit_of_work.py`: `LibrosUnitOfWork.registrar_movimiento_stock(libro, usuario_id, cantidad, motivo, venta_id=None)`. Ajusta `libro.stock`, valida que no quede negativo (`409`), inserta `MovimientoStock` y sólo hace `flush()`.
- La infraestructura base de C-03 está disponible: `BaseRepository[T]`, `SoftDeleteRepository[T]`, `UnitOfWork` (`__aexit__` es el único que hace `commit()`/`rollback()`) y `Page[T]` con `Page.create()`.
- La autorización de C-05 está disponible: `get_usuario_actual`, `verificar_password_actualizada` montado en el Grupo Protegido y `requiere_rol(...)` que consulta `asignacion_rol` en cada petición.
- En `app/main.py` los routers de `clientes` y `ventas` ya cuelgan del `protected_router`, pero ninguna de sus rutas exige rol. `logging.basicConfig` usa `INFO` sólo cuando `SQL_ECHO=true`; con el arranque normal queda en `WARNING`.
- No hay cambios de esquema ni migraciones pendientes: `venta`, `renglon_venta`, `cliente`, `perfil_cliente` y `movimiento_stock` ya existen con sus constraints y trigger.

## Goals / Non-Goals

**Goals:**

- Refactorizar `clientes` y `ventas` a la arquitectura de 5 capas con `Repository + UnitOfWork` compartiendo la sesión de la petición.
- Implementar el registro de venta atómico reutilizando el punto único de escritura de stock de C-06.
- Cubrir `Page[T]`, el control de dueño de `RN-14` y el aviso en segundo plano visible en consola.
- Dejar los contratos de entrada estrictos (`extra="forbid"`) y las rutas correctamente clasificadas en el Grupo Protegido.

**Non-Goals:**

- No se modifica el esquema de la base ni se agregan migraciones.
- No se cambia el contrato ni la implementación del punto único de escritura de stock de `app/modules/libros/`.
- No se migra `GET /clientes/{id}/ventas` a `Page[T]`: `IN-01` sólo enumera `GET /ventas` y `GET /mis-ventas`, y la consigna fija `200`/`404` para esa ruta.
- No se implementan `seed.py`, los casos de prueba `.http`, `solo_agregado.sql`, la evidencia de C-14/C-15 ni el `README.md` (corresponden a C-08).
- No se modifican autenticación, JWT, `bcrypt` ni `intento_acceso`.

## Decisions

### Decisión 1: Dos capabilities nuevas y ninguna modificación de `catalogo-stock-baja-logica`

- **Enfoque**: `gestion-clientes` y `ventas-transaccionales` como capabilities nuevas. El punto único de escritura de stock se reutiliza sin alterar el comportamiento del catálogo, por lo que `catalogo-stock-baja-logica` no recibe delta.
- **Alternativa descartada**: Un único capability `clientes-ventas-transaccionales`. Se descartó porque mezcla dos comportamientos durables distintos y dificultaría la evolución futura de cada módulo.

### Decisión 2: `ClienteRepository` con precarga declarada de `perfil`

- **Enfoque**: En `app/modules/clientes/repository.py`, `ClienteRepository(BaseRepository[Cliente])` expone `_opciones_detalle()` con `joinedload(Cliente.perfil)`, `get_detalle(cliente_id)` (usa `get_by_id(..., options=...)`) y conserva `get_by_email`/`get_by_usuario_id`. `ClientesUnitOfWork` expone `self.clientes` y se obtiene con `Depends(get_clientes_uow)` sobre `get_session`.
- **Por qué**: Evita el acceso perezoso a `cliente.perfil` (prohibido en async) y cumple la precarga declarada del repositorio.
- **Alternativa descartada**: `session.refresh(cliente, ["perfil"])` después del commit, como hace el servicio actual. Se descartó porque la precarga debe vivir en el repositorio.

### Decisión 3: `VentaRepository` con precarga declarada e inclusión de libros dados de baja

- **Enfoque**: En `app/modules/ventas/repository.py`, `VentaRepository(BaseRepository[Venta])` define `_opciones_detalle()` exactamente como:
  - `joinedload(Venta.cliente)`
  - `selectinload(Venta.renglones).joinedload(RenglonVenta.libro)`

  `get_detalle(venta_id)` usa esas opciones; `listar_paginado(page, size, cliente_id=None)` devuelve `(items, total)` con `count(filters=...)` y `get_all(filters=..., order_by=(Venta.fecha.desc(), Venta.id.desc()), page=..., size=..., options=...)`; además `listar_por_cliente(cliente_id)` reutiliza la misma precarga.
- **Por qué**: La relación `RenglonVenta.libro` no aplica ningún filtro de baja lógica, por lo que un `selectinload` normal ya trae los libros con `borrado_en IS NOT NULL`. Eso cumple `RN-13` y evita N+1: `joinedload` resuelve cliente en la misma consulta y `selectinload` resuelve todos los renglones en una única consulta adicional fija, sin importar cuántos sean.
- **Restricción explícita**: no usar `SoftDeleteRepository[Venta]` ni agregar `Libro.borrado_en.is_(None)` en la lectura de ventas históricas. La vigencia del libro sólo se exige al **crear** la venta.
- **Alternativa descartada**: Cargar renglones con lazy loading por venta. Se descartó porque produce N+1 y falla en async.

### Decisión 4: `VentasUnitOfWork` hereda de `LibrosUnitOfWork` para reutilizar el punto único de stock

- **Enfoque**: `app/modules/ventas/unit_of_work.py` define `VentasUnitOfWork(LibrosUnitOfWork)`. El `super().__init__(session)` deja disponibles `self.libros`, `self.movimientos` y `registrar_movimiento_stock(...)`; el constructor agrega `self.ventas = VentaRepository(session)`, `self.clientes = ClienteRepository(session)` y `self.roles = AsignacionRolRepository(session)`. Se obtiene con `Depends(get_ventas_uow)`.
- **Por qué**: Garantiza que la venta use exactamente el mismo método que el alta y la reposición (`RN-11`), sin reimplementar la actualización de `libro.stock` ni la inserción en `movimiento_stock`. No se agrega ningún método nuevo de escritura de stock.
- **Alternativa descartada**: Componer `LibrosUnitOfWork` como atributo y delegar la llamada. Se descartó por indirección innecesaria; la herencia mantiene el mismo contrato y la misma sesión.

### Decisión 5: Registro de venta en un único `UnitOfWork` con lecturas y escrituras dentro de la misma transacción

- **Enfoque** (`POST /ventas`):
  1. Validar el contrato con Pydantic (ver Decisión 8).
  2. Abrir `async with uow:` y, dentro del bloque:
     - Verificar el cliente con `uow.clientes.get_by_id(datos.cliente_id)`; si no existe, `409`.
     - Cargar todos los libros con **una sola** consulta: `uow.libros.get_all(filters=[Libro.id.in_(ids)], include_deleted=False)`. `SoftDeleteRepository` excluye `borrado_en IS NOT NULL`, por lo que un libro dado de baja se trata como inexistente y produce `409`.
     - Verificar por renglón que `libro.stock >= cantidad`; si no, `409`.
     - Calcular el `total` con los `Decimal` de la base y crear la `Venta`; `uow.ventas.add(venta)` obtiene el `id` por `flush()`.
     - Crear los `RenglonVenta` con `precio_unitario = libro.precio` y `venta_id = venta.id`.
     - Por cada renglón llamar `uow.registrar_movimiento_stock(libro=libro, usuario_id=actor.id, cantidad=-cantidad, motivo="Venta", venta_id=venta.id)`.
  3. Al salir del bloque, `UnitOfWork.__aexit__` ejecuta un único `commit()`. Cualquier `HTTPException`, `IntegrityError` u otra excepción dispara `rollback()` total (`RN-10`).
- **Por qué**: Las lecturas de stock y las escrituras deben compartir transacción para que la validación y el descuento sean coherentes. El `CHECK (stock >= 0)` de `libro` actúa como última barrera ante concurrencia.
- **Alternativa descartada**: Validar fuera del `UnitOfWork` como hacía el servicio previo. Se descartó porque deja una ventana entre la lectura y el descuento.
- **Alternativa descartada**: `SELECT ... FOR UPDATE`. Se descartó por no ser necesaria para la consigna: el `CHECK` y el `rollback` convierten una carrera en `409`, sin stock negativo.

### Decisión 6: Releer la venta después del commit para armar la respuesta

- **Enfoque**: Después de salir del bloque `async with uow:`, el servicio llama `uow.ventas.get_detalle(venta.id)` y construye `VentaRead` con la precarga ya declarada.
- **Por qué**: `Venta.fecha` tiene `server_default=func.now()` y la fábrica de sesiones usa `expire_on_commit=False`. Un objeto recién creado no tiene `fecha` cargada y accederla dispararía una carga perezosa (falla en async). La relectura con `get_detalle` trae el valor persistido y las relaciones en un número fijo de consultas.
- **Alternativa descartada**: Armar el DTO con los objetos en memoria y `datetime.now()`. Se descartó porque inventaría un valor que no es necesariamente el que guardó la base.

### Decisión 7: Organización de routers de ventas y control de dueño

- **Enfoque**:
  - `ventas_personal_router = APIRouter(prefix="/ventas", dependencies=[Depends(requiere_rol("VENDEDOR", "ADMIN"))])`: `POST /ventas` y `GET /ventas`.
  - `ventas_router = APIRouter(prefix="/ventas")`: `GET /ventas/{venta_id}` con `Depends(get_usuario_actual)`; **no** usa `requiere_rol` porque un `CLIENTE` debe poder ver su propia venta.
  - `mis_ventas_router = APIRouter(prefix="/mis-ventas")`: `GET /mis-ventas`. Ruta de nivel superior, tal como figura en la consigna y en la KB.
  - Los tres se incluyen en `protected_router` (que ya aplica `verificar_password_actualizada`), igual que el router de clientes.
- **Control de dueño en el servicio**: `GET /ventas/{id}` primero busca la venta con `uow.ventas.get_detalle`; si no existe → `404`. Si `venta.cliente.usuario_id == actor.id` → permitido. En caso contrario consulta `uow.roles.get_roles_vigentes(actor.id)` (mismo `AsignacionRolRepository` de C-05) y permite sólo si intersecta `{"VENDEDOR", "ADMIN"}`; si no → `403`.
- **Por qué**: La autorización del detalle no puede expresarse con `requiere_rol` a nivel de router porque bloquearía al `CLIENTE` dueño. La consulta a `asignacion_rol` en el servicio mantiene `RN-04` (nunca se confía en los roles del JWT).
- **Alternativa descartada**: Exponer `/ventas/mis-ventas`. Se descartó porque la consigna y la KB fijan `/mis-ventas` en la raíz y porque, declarada después de `/{venta_id}`, "mis-ventas" se interpretaría como un `int` inválido y devolvería `422`.

### Decisión 8: Contratos estrictos y traducción de errores

- **Enfoque**: `ClienteCreate`, `ClienteUpdate`, `PerfilCreate`, `VentaCreate` y `RenglonVentaCreate` llevan `model_config = ConfigDict(extra="forbid")`. `VentaCreate` valida al menos un renglón (`min_length=1`), sin `libro_id` repetidos y con `cantidad > 0`; el esquema raíz también prohíbe `total` y los renglones prohíben `precio_unitario`. Las unicidades (`cliente.email`, `perfil_cliente.cliente_id`) se resuelven escribiendo y traduciendo `IntegrityError` a `409` con mensaje propio, sin consulta previa. `Page.create` se envuelve para traducir `page > pages` a `422`.
- **Por qué**: Cumple la regla de contratos estrictos y `RN-15` (nunca un `500` por entrada inválida ni texto interno de PostgreSQL).
- **Alternativa descartada**: Aceptar y descartar silenciosamente campos extra. Se descartó porque ocultaría intentos de fijar precios o totales desde el cliente.

### Decisión 9: `GET /clientes/{id}/ventas` sin paginación

- **Enfoque**: La ruta permanece en `clientes/router.py`, protegida con `requiere_rol("VENDEDOR", "ADMIN")`, y delega en `ventas.service.listar_por_cliente(uow, cliente_id)` usando `VentasUnitOfWork` (que ya integra el repositorio de clientes y el de ventas). Devuelve `list[VentaRead]` ordenada por fecha descendente; verifica la existencia del cliente antes de listar (`404`).
- **Por qué**: La consigna no incluye esta ruta en la migración a `Page[T]` (`IN-01`) y fija `200`/`404`. Reutilizar el servicio de ventas evita duplicar la precarga.
- **Alternativa descartada**: Agregar un `VentaRepository` dentro de `ClientesUnitOfWork`. Se descartó porque duplicaría el repositorio de ventas y rompería la separación de módulos.

### Decisión 10: Aviso en segundo plano visible con el arranque normal

- **Enfoque**: El router de `POST /ventas` agenda `background_tasks.add_task(service.enviar_comprobante, venta.id)` **después** de que el servicio retorna (es decir, después del `commit`). `enviar_comprobante` hace `await asyncio.sleep(0.5)` y registra el mensaje. Para que el mensaje sea visible con `SQL_ECHO=false`, `app/main.py` pasa a configurar `logging.basicConfig(level=logging.INFO, ...)` de forma incondicional; `SQL_ECHO` sigue controlando únicamente el `echo` del motor.
- **Por qué**: El requisito pide un log visible en el arranque normal de Uvicorn. Con la configuración actual (`WARNING` cuando `SQL_ECHO=false`) un `logger.info` no se vería.
- **Alternativa descartada**: Emitir el aviso con `logger.warning`. Se descartó porque clasifica como advertencia un evento normal y confunde el diagnóstico.
- **Alternativa descartada**: `print()`. Se descartó para mantener el logging estructurado del proyecto.

### Decisión 11: Router de clientes con una sola dependencia de rol

- **Enfoque**: `clientes_router = APIRouter(prefix="/clientes", dependencies=[Depends(requiere_rol("VENDEDOR", "ADMIN"))])` agrupa las cinco rutas: `POST /clientes`, `GET /clientes/{id}`, `PATCH /clientes/{id}`, `POST /clientes/{id}/perfil` y `GET /clientes/{id}/ventas`. Se incluye en `protected_router` (que ya aplica `verificar_password_actualizada`).
- **Por qué**: Declarar el rol una sola vez a nivel de router evita repetir la dependencia en cada endpoint y garantiza que ninguna ruta de clientes quede desprotegida.
- **Alternativa descartada**: `Depends(requiere_rol(...))` en cada decorador. Se descartó por duplicación y riesgo de olvidar una ruta.

### Decisión 12: Sesión compartida y límites de transacción

- **Enfoque**: Todos los routers reciben su UoW con `Depends(get_*_uow)`, que internamente usa `Depends(get_session)`. Los repositorios sólo hacen `flush()`/`refresh()`; nunca `commit()` ni `rollback()`. El UoW nunca cierra la sesión. `GET /ventas/{id}` y `GET /mis-ventas` usan la misma sesión para resolver el usuario, consultar la venta y verificar roles.
- **Por qué**: Cumple las reglas duras del proyecto y evita consumir más de una conexión del pool por petición.
- **Alternativa descartada**: Abrir una sesión nueva por consulta. Se descartó por costo y por romper la coherencia de la petición.

## Risks / Trade-offs

- **[Riesgo] Dos ventas concurrentes podrían leer el mismo stock y sobrevender.** → *Mitigación*: el `CHECK (stock >= 0)` de `libro` rechaza el segundo `commit`; el servicio traduce `IntegrityError` a `409 Conflict` y el UoW revierte todo. No se agrega bloqueo pesimista porque la consigna no lo exige.
- **[Riesgo] Un `selectinload` mal escrito podría filtrar libros dados de baja y romper `RN-13`.** → *Mitigación*: la precarga se declara una sola vez en `VentaRepository._opciones_detalle()` y se prueba explícitamente con una venta histórica de un libro dado de baja.
- **[Riesgo] Los repositorios podrían terminar llamando `commit()` por costumbre del código previo.** → *Mitigación*: los servicios usan exclusivamente `async with uow:` y el UoW es el único que confirma; las pruebas verifican el rollback ante `409`.
- **[Riesgo] Armar el DTO de respuesta con la venta recién creada fallaría por `fecha` no cargada.** → *Mitigación*: relectura post-commit con `get_detalle` (Decisión 6).
- **[Riesgo] El log del aviso en segundo plano no se vería con la configuración normal de logging.** → *Mitigación*: `logging.basicConfig` en `INFO` (Decisión 10) y verificación manual en la consola de Uvicorn.
- **[Riesgo] Duplicar `/mis-ventas` bajo el prefijo `/ventas` generaría colisión con `/{venta_id}`.** → *Mitigación*: router separado sin prefijo `/ventas` (Decisión 7).
- **[Trade-off] `GET /clientes/{id}/ventas` no se pagina.** → Se acepta porque `IN-01` no lo incluye; si la cátedra lo pidiera, el cambio queda acotado al router y al servicio de clientes.

## Migration Plan

- No hay migraciones de base de datos: se reutilizan las tablas, constraints e índices existentes.
- Despliegue: reemplazar los archivos de `app/modules/clientes/` y `app/modules/ventas/`, actualizar los routers en `app/main.py` y reiniciar Uvicorn. Las rutas nuevas conviven con las existentes en el mismo prefijo.
- Rollback: restaurar los archivos de los módulos y `app/main.py`; no hay datos que revertir ni esquema que deshacer.
- No se requiere `alembic upgrade head` para este change.

## Open Questions

Ninguna pendiente. Las ambigüedades detectadas se resolvieron así:

- `GET /mis-ventas` se implementa en la raíz (`/mis-ventas`), no bajo `/ventas`, según la consigna y la KB.
- Un usuario autenticado sin ficha de cliente recibe `200 OK` con una `Page` vacía en `/mis-ventas`, porque la consigna sólo admite `200`/`422` para esa ruta.
- `GET /clientes/{id}/ventas` conserva la respuesta de lista (sin `Page[T]`) porque `IN-01` no la incluye.
