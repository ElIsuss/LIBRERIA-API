# catalogo-stock-baja-logica Specification

## Purpose
Provee la gestión integral del catálogo de libros con borrado lógico, paginación estándar, reposición de inventario y punto único de escritura de movimientos de stock auditado e inmutable.

## Requirements

### Requirement: Consulta de catálogo y filtrado de libros vigentes con paginación estándar
El endpoint `GET /libros` del Grupo Abierto SHALL devolver una lista paginada `Page[LibroLista]` con estructura `{items, total, page, size, pages}` conteniendo exclusivamente libros cuyo `borrado_en` sea `NULL`. Aceptará parámetros `page` (mínimo 1, default 1), `size` (1 a 100, default 20), `titulo` y `genero_id`. Si se solicita una página mayor al total de páginas calculadas (`page > pages`), el sistema MUST responder `422 Unprocessable Entity`.

#### Scenario: Listado exitoso de catálogo vigente
- **WHEN** un cliente consulta `GET /libros?page=1&size=10`
- **THEN** el sistema responde `200 OK` con `{items, total, page, size, pages}` excluyendo cualquier libro dado de baja lógica

#### Scenario: Filtrado por título y género
- **WHEN** un cliente consulta `GET /libros?titulo=Ficciones&genero_id=1`
- **THEN** el sistema responde `200 OK` con los libros coincidentes que se encuentren vigentes

#### Scenario: Solicitud de página fuera de rango
- **WHEN** un cliente solicita `GET /libros?page=999&size=10` y existen menos páginas
- **THEN** el sistema responde `422 Unprocessable Entity`

### Requirement: Obtención de detalle de libro vigente e invisibilidad de libros dados de baja
El endpoint `GET /libros/{id}` del Grupo Abierto SHALL devolver el detalle completo del libro (`LibroDetalle`) con su editorial, género y autores ordenados. Si el libro no existe o posee `borrado_en IS NOT NULL`, el sistema MUST responder `404 Not Found`.

#### Scenario: Consulta de libro vigente existente
- **WHEN** un cliente consulta `GET /libros/{id}` de un libro activo
- **THEN** el sistema responde `200 OK` con los datos del libro y sus relaciones precargadas sin N+1

#### Scenario: Consulta de libro inexistente o dado de baja lógica
- **WHEN** un cliente consulta `GET /libros/{id}` de un libro con `borrado_en IS NOT NULL` o ID inexistente
- **THEN** el sistema responde `404 Not Found`

### Requirement: Alta de libro con autores y generación obligatoria de movimiento de stock inicial
El endpoint `POST /libros` SHALL permitir a un `ADMIN` registrar un libro con sus autorías y `stock_inicial: int >= 0` usando `extra="forbid"`. En una única transacción de `UnitOfWork`, el sistema SHALL persistir el libro y, si `stock_inicial > 0`, registrar automáticamente una fila en `movimiento_stock` (`RN-11`). Si el ISBN ya pertenece a un libro vigente, MUST responder `409 Conflict`.

#### Scenario: Creación exitosa de libro con stock inicial positivo
- **WHEN** un `ADMIN` envía `POST /libros` con datos válidos y `stock_inicial = 5`
- **THEN** el sistema responde `201 Created`, persiste el libro con `stock = 5` e inserta el movimiento correspondiente en `movimiento_stock`

#### Scenario: Creación exitosa con stock inicial cero
- **WHEN** un `ADMIN` envía `POST /libros` con `stock_inicial = 0`
- **THEN** el sistema responde `201 Created` con `stock = 0` y no inserta filas en `movimiento_stock`

#### Scenario: Conflicto por ISBN duplicado en libro vigente
- **WHEN** un `ADMIN` intenta registrar un libro con un ISBN que ya pertenece a otro libro con `borrado_en IS NULL`
- **THEN** el sistema rechaza la operación respondiendo `409 Conflict`

### Requirement: Modificación de libro con prohibición estricta de alteración de stock
El endpoint `PATCH /libros/{id}` SHALL estar restringido a usuarios con rol `ADMIN` en el Grupo Protegido para modificar campos descriptivos (`titulo`, `precio`, `editorial_id`, `genero_id`, `isbn`). El esquema `LibroUpdate` MUST configurar `extra="forbid"` y no contener el atributo `stock`. Si la petición incluye el campo `stock`, el sistema MUST responder `422 Unprocessable Entity`. Si el libro fue dado de baja o no existe, responderá `404 Not Found`.

#### Scenario: Actualización de datos descriptivos
- **WHEN** un `ADMIN` envía `PATCH /libros/{id}` modificando `titulo` y `precio`
- **THEN** el sistema actualiza los campos permitidos y responde `200 OK`

#### Scenario: Rechazo ante intento de modificar stock directamente
- **WHEN** un cliente envía `PATCH /libros/{id}` incluyendo `{"stock": 20}`
- **THEN** el validador rechaza la carga con `422 Unprocessable Entity`

### Requirement: Reposición de stock y trazabilidad append-only de movimientos
El endpoint `POST /libros/{id}/reponer` SHALL estar restringido a usuarios con rol `ADMIN` en el Grupo Protegido. Recibirá `cantidad: int > 0` y `motivo: str` opcional. Utilizará el punto único de escritura de stock para incrementar `libro.stock` y registrar la fila correspondiente en `movimiento_stock` con `cantidad > 0` y el ID del usuario administrador. Si el libro no existe o se encuentra dado de baja lógica, el sistema MUST responder `404 Not Found`.

#### Scenario: Reposición exitosa de stock en libro vigente
- **WHEN** un `ADMIN` envía `POST /libros/{id}/reponer` con `cantidad = 10` y motivo `"Ingreso imprenta"`
- **THEN** el sistema incrementa `libro.stock` en 10, registra la fila en `movimiento_stock` y responde `200 OK`

#### Scenario: Rechazo al intentar reponer un libro dado de baja lógica
- **WHEN** un `ADMIN` intenta enviar `POST /libros/{id}/reponer` sobre un libro con `borrado_en IS NOT NULL`
- **THEN** el sistema rechaza la operación respondiendo `404 Not Found`

### Requirement: Consulta administrativa de historial de movimientos de stock
El endpoint `GET /libros/{id}/movimientos` SHALL estar disponible exclusivamente para usuarios con rol `ADMIN` en el Grupo Protegido. Devolverá la lista cronológica de todos los movimientos de stock registrados para el libro indicado, permitiendo consultar incluso libros que hayan sido dados de baja lógica. Si el ID no existe en la base, responderá `404 Not Found`.

#### Scenario: Consulta de movimientos por administrador
- **WHEN** un `ADMIN` solicita `GET /libros/{id}/movimientos` para un libro con historial
- **THEN** el sistema responde `200 OK` con la lista de movimientos ordenados cronológicamente

#### Scenario: Acceso denegado a usuario sin rol administrador
- **WHEN** un usuario sin rol `ADMIN` invoca `GET /libros/{id}/movimientos`
- **THEN** el sistema responde `403 Forbidden`

### Requirement: Baja lógica de libros y liberación de ISBN vigente
El endpoint `DELETE /libros/{id}` SHALL estar restringido a usuarios con rol `ADMIN` en el Grupo Protegido. Al ejecutarse sobre un libro activo, el sistema marcará `borrado_en = now()` mediante `SoftDeleteRepository` y responderá `204 No Content`. El ISBN del libro dado de baja quedará liberado inmediatamente, permitiendo que un nuevo libro sea registrado con ese mismo ISBN sin violar la restricción de unicidad.

#### Scenario: Baja lógica exitosa de un libro activo
- **WHEN** un `ADMIN` invoca `DELETE /libros/{id}` sobre un libro vigente
- **THEN** el sistema establece `borrado_en = now()`, no elimina físicamente la fila y responde `204 No Content`

#### Scenario: Reutilización exitosa de ISBN tras baja lógica
- **WHEN** un `ADMIN` registra un libro nuevo con un ISBN previamente utilizado por un libro dado de baja
- **THEN** el sistema responde `201 Created` aceptando el alta exitosamente gracias al índice único parcial
