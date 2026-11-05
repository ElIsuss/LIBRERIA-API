# Spec Delta

## Purpose

Provee el registro atómico de ventas con precio congelado, total calculado en el servidor, descuento de stock y movimiento de inventario auditado, además de las consultas de ventas para el personal y para el propio cliente con control de dueño.

## ADDED Requirements

### Requirement: Registro de venta con precio copiado y total del servidor

El endpoint `POST /ventas` SHALL estar disponible para roles `VENDEDOR` y `ADMIN`. En una única transacción SHALL crear la venta y sus renglones, copiar `precio_unitario` desde `libro.precio` en la base y calcular el `total` en el servidor, sin aceptar precios ni totales enviados por el cliente. Responderá `201 Created` con la venta, su cliente y sus renglones.

#### Scenario: Venta exitosa con varios renglones
- **WHEN** un usuario con rol `VENDEDOR` envía `POST /ventas` con un cliente válido y dos libros distintos con stock suficiente
- **THEN** el sistema responde `201 Created` con la venta, su cliente y sus renglones, cada uno con el `precio_unitario` vigente en la base y su `subtotal`

#### Scenario: Total calculado por el servidor
- **WHEN** se registra una venta con cantidades y libros válidos
- **THEN** el `total` de la venta es la suma de `precio_unitario * cantidad` de todos sus renglones, calculado por el servidor

#### Scenario: Rol cliente rechazado en el registro de ventas
- **WHEN** un usuario con rol `CLIENTE` envía `POST /ventas`
- **THEN** el sistema responde `403 Forbidden` y no crea la venta

### Requirement: Contrato estricto del registro de venta

`VentaCreate` MUST exigir al menos un renglón, `libro_id` mayores que cero, `cantidad` mayor que cero y ausencia de libros repetidos, con `extra="forbid"` en el esquema raíz y en cada renglón. Cualquier incumplimiento SHALL responder `422 Unprocessable Entity` sin abrir la transacción de escritura.

#### Scenario: Venta sin renglones
- **WHEN** un usuario con rol `VENDEDOR` envía `POST /ventas` con la lista `renglones` vacía
- **THEN** el sistema responde `422 Unprocessable Entity`

#### Scenario: Libro repetido en la misma venta
- **WHEN** un usuario con rol `VENDEDOR` envía `POST /ventas` con el mismo `libro_id` en dos renglones
- **THEN** el sistema responde `422 Unprocessable Entity` y no registra la venta

#### Scenario: Cantidad inválida
- **WHEN** un usuario con rol `VENDEDOR` envía `POST /ventas` con `cantidad = 0` o negativa en algún renglón
- **THEN** el sistema responde `422 Unprocessable Entity`

#### Scenario: Intento de fijar precio o total desde el cliente
- **WHEN** un usuario con rol `VENDEDOR` envía `POST /ventas` incluyendo un `precio_unitario` en un renglón o un `total` en la venta
- **THEN** el sistema responde `422 Unprocessable Entity` sin usar esos valores

### Requirement: Atomicidad total ante fallos en el registro de venta

Si el cliente no existe, algún libro no existe o está dado de baja lógica (`RN-13`), o el stock de algún libro es insuficiente (`RN-10`), el registro SHALL responder `409 Conflict` y revertir por completo la venta, sus renglones, los descuentos de stock y los movimientos, sin dejar escrituras parciales.

#### Scenario: Cliente inexistente
- **WHEN** un usuario con rol `VENDEDOR` envía `POST /ventas` con un `cliente_id` que no existe
- **THEN** el sistema responde `409 Conflict` y no crea la venta

#### Scenario: Libro inexistente
- **WHEN** un usuario con rol `VENDEDOR` envía `POST /ventas` con un `libro_id` que no existe
- **THEN** el sistema responde `409 Conflict` y no crea la venta ni modifica el stock

#### Scenario: Libro dado de baja lógica
- **WHEN** un usuario con rol `VENDEDOR` envía `POST /ventas` incluyendo un libro con `borrado_en IS NOT NULL`
- **THEN** el sistema responde `409 Conflict` y no crea la venta ni modifica el stock

#### Scenario: Stock insuficiente en uno de los libros
- **WHEN** un usuario con rol `VENDEDOR` envía `POST /ventas` donde un libro tiene stock menor a la cantidad solicitada
- **THEN** el sistema responde `409 Conflict`, deja el stock de todos los libros sin cambios y no crea la venta ni movimientos de stock

#### Scenario: Falla en un renglón posterior revierte los anteriores
- **WHEN** una venta con dos renglones tiene el primero válido y el segundo con stock insuficiente
- **THEN** el sistema responde `409 Conflict` y el stock del primer libro tampoco se descuenta

### Requirement: Descuento de stock a través del punto único de escritura

Todo descuento de `libro.stock` producido por una venta MUST ejecutarse a través del mismo punto único de escritura de stock usado por el alta y la reposición (`RN-11`). Por cada renglón SHALL registrarse exactamente un `movimiento_stock` con `cantidad` negativa igual a `-cantidad`, `venta_id`, `usuario_id` y motivo `"Venta"`, preservando `libro.stock == SUM(movimiento_stock.cantidad)`.

#### Scenario: Un movimiento de stock por cada renglón
- **WHEN** se registra una venta con dos renglones
- **THEN** existen exactamente dos movimientos de stock negativos asociados a esa venta, uno por cada libro

#### Scenario: Invariante de inventario preservada
- **WHEN** se registran una o más ventas sobre un libro
- **THEN** al finalizar se cumple `libro.stock == SUM(movimiento_stock.cantidad)` para ese libro

#### Scenario: Venta fallida sin movimientos de stock
- **WHEN** un intento de venta termina en `409 Conflict`
- **THEN** no se inserta ninguna fila en `movimiento_stock` para ese intento

### Requirement: Aviso en segundo plano después del commit

Una vez confirmado el `commit` de la venta, el sistema SHALL agendar en `BackgroundTasks` un aviso simulado que espera `asyncio.sleep(0.5)` y escribe un mensaje visible en la consola de Uvicorn con el arranque normal. Si la venta falla MUST NOT agendar la tarea.

#### Scenario: Venta exitosa agenda el aviso
- **WHEN** una venta se registra con `201 Created`
- **THEN** después de responder, el sistema ejecuta el aviso en segundo plano y deja el mensaje visible en la consola de Uvicorn

#### Scenario: Venta fallida no agenda el aviso
- **WHEN** un intento de venta termina en `409 Conflict` o `422 Unprocessable Entity`
- **THEN** no se agencia ninguna tarea en segundo plano

### Requirement: Listado paginado de ventas para el personal

El endpoint `GET /ventas` SHALL estar disponible para roles `VENDEDOR` y `ADMIN`. Devolverá `Page[VentaRead]` con `{items, total, page, size, pages}` usando `page` (mínimo 1, default 1) y `size` (1 a 100, default 20), con cliente y renglones precargados. Si `page` excede las páginas disponibles SHALL responder `422 Unprocessable Entity`.

#### Scenario: Listado paginado exitoso
- **WHEN** un usuario con rol `VENDEDOR` consulta `GET /ventas?page=1&size=10`
- **THEN** el sistema responde `200 OK` con `{items, total, page, size, pages}` y cada venta con su cliente y sus renglones

#### Scenario: Página fuera de rango
- **WHEN** un usuario con rol `ADMIN` consulta `GET /ventas?page=999&size=10` y existen menos páginas
- **THEN** el sistema responde `422 Unprocessable Entity`

#### Scenario: Rol cliente rechazado en el listado global
- **WHEN** un usuario con rol `CLIENTE` consulta `GET /ventas`
- **THEN** el sistema responde `403 Forbidden`

#### Scenario: Cantidad fija de consultas sin N+1
- **WHEN** se leen dos ventas, una con dos renglones y otra con cuatro renglones
- **THEN** el número de consultas SQL emitidas es el mismo en ambos casos y no crece con la cantidad de renglones

#### Scenario: Venta histórica con libro dado de baja lógica
- **WHEN** el listado incluye una venta cuyo libro fue dado de baja lógica después de la venta
- **THEN** el renglón muestra el título del libro sin error

### Requirement: Consulta paginada de ventas propias

El endpoint `GET /mis-ventas` SHALL estar disponible en la ruta de nivel superior para cualquier usuario autenticado sin cambio de contraseña pendiente. Devolverá `Page[VentaRead]` con las ventas del cliente vinculado al usuario autenticado, sin incluir ventas de otros clientes. Si el usuario no posee ficha de cliente SHALL devolver una página vacía. Si `page` excede las páginas disponibles SHALL responder `422 Unprocessable Entity`.

#### Scenario: Cliente consulta únicamente sus ventas
- **WHEN** un usuario autenticado con rol `CLIENTE` vinculado a una ficha de cliente consulta `GET /mis-ventas`
- **THEN** el sistema responde `200 OK` con las ventas de su ficha y ninguna venta de otro cliente

#### Scenario: Usuario sin ficha de cliente
- **WHEN** un usuario autenticado que no está vinculado a ninguna ficha de cliente consulta `GET /mis-ventas`
- **THEN** el sistema responde `200 OK` con una página vacía

#### Scenario: Página fuera de rango en ventas propias
- **WHEN** un usuario autenticado consulta `GET /mis-ventas?page=999&size=10` y existen menos páginas
- **THEN** el sistema responde `422 Unprocessable Entity`

#### Scenario: Consulta propia sin sesión
- **WHEN** una petición anónima consulta `GET /mis-ventas` sin la cookie `access_token`
- **THEN** el sistema responde `401 Unauthorized`

#### Scenario: Consulta propia con cambio de contraseña pendiente
- **WHEN** un usuario con `debe_cambiar_password = True` consulta `GET /mis-ventas`
- **THEN** el sistema responde `403 Forbidden`

### Requirement: Detalle de venta con control de dueño o personal

El endpoint `GET /ventas/{id}` SHALL estar disponible para cualquier usuario autenticado. El servicio SHALL autorizar al personal con rol `VENDEDOR` o `ADMIN` vigente en `asignacion_rol` en la base (`RN-04`) o al `CLIENTE` cuyo `cliente.usuario_id` coincide con el usuario autenticado. Si la venta no existe SHALL responder `404 Not Found`; si pertenece a otro cliente sin rol de personal SHALL responder `403 Forbidden`.

#### Scenario: Personal consulta cualquier venta
- **WHEN** un usuario con rol `VENDEDOR` o `ADMIN` vigente consulta `GET /ventas/{id}` de cualquier venta existente
- **THEN** el sistema responde `200 OK` con el detalle de la venta

#### Scenario: Cliente dueño consulta su venta
- **WHEN** un usuario con rol `CLIENTE` vinculado a la ficha dueña de la venta consulta `GET /ventas/{id}`
- **THEN** el sistema responde `200 OK` con el detalle de su venta

#### Scenario: Cliente ajeno rechazado
- **WHEN** un usuario con rol `CLIENTE` consulta `GET /ventas/{id}` de una venta que pertenece a otro cliente
- **THEN** el sistema responde `403 Forbidden`

#### Scenario: Venta inexistente
- **WHEN** un usuario autenticado consulta `GET /ventas/{id}` con un identificador que no existe
- **THEN** el sistema responde `404 Not Found`

#### Scenario: Revocación de rol aplicada en la petición siguiente
- **WHEN** a un usuario se le revoca el rol `VENDEDOR` y luego consulta una venta ajena a su ficha de cliente
- **THEN** el sistema responde `403 Forbidden` porque el rol se evalúa en la base en cada petición

#### Scenario: Detalle histórico con libro dado de baja lógica
- **WHEN** se consulta el detalle de una venta cuyo libro fue dado de baja después de la venta
- **THEN** el sistema responde `200 OK` mostrando el título del libro en el renglón

#### Scenario: Detalle sin sesión
- **WHEN** una petición anónima consulta `GET /ventas/{id}` sin la cookie `access_token`
- **THEN** el sistema responde `401 Unauthorized`
