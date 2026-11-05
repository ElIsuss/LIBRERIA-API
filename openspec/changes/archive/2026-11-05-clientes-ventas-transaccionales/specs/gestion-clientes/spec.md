# Spec Delta

## Purpose

Provee la gestión de fichas de clientes y de su perfil único, junto con la consulta de las ventas de un cliente por parte del personal, bajo contratos estrictos y control de acceso por rol vigente.

## ADDED Requirements

### Requirement: Alta de cliente con correo único

El endpoint `POST /clientes` SHALL estar disponible en el Grupo Protegido para roles `VENDEDOR` y `ADMIN`. Recibirá `nombre` y `email` con `extra="forbid"` y, en una única transacción, SHALL crear la ficha de cliente respondiendo `201 Created`. Si el correo ya existe SHALL responder `409 Conflict` sin dejar escrituras parciales.

#### Scenario: Alta exitosa de un cliente sin perfil
- **WHEN** un usuario con rol `VENDEDOR` envía `POST /clientes` con un `nombre` y un `email` que no existen
- **THEN** el sistema responde `201 Created` con el `id`, el `nombre`, el `email` y `perfil = null`

#### Scenario: Alta rechazada por correo duplicado
- **WHEN** un usuario con rol `VENDEDOR` envía `POST /clientes` con un `email` que ya pertenece a otro cliente
- **THEN** el sistema responde `409 Conflict` con un mensaje propio y no crea ninguna fila

#### Scenario: Alta rechazada por contrato inválido
- **WHEN** un usuario con rol `ADMIN` envía `POST /clientes` con un correo mal formado o con un campo adicional no declarado
- **THEN** el sistema responde `422 Unprocessable Entity` sin llegar a la base de datos

### Requirement: Consulta de cliente con perfil precargado

El endpoint `GET /clientes/{id}` SHALL estar disponible en el Grupo Protegido para roles `VENDEDOR` y `ADMIN`. Devolverá la ficha del cliente junto con su perfil cuando exista, sin consultas adicionales por perfil. Si el cliente no existe SHALL responder `404 Not Found`.

#### Scenario: Consulta de cliente que posee perfil
- **WHEN** un usuario con rol `VENDEDOR` consulta `GET /clientes/{id}` de un cliente con perfil registrado
- **THEN** el sistema responde `200 OK` con la ficha y el objeto `perfil` completo

#### Scenario: Consulta de cliente sin perfil
- **WHEN** un usuario con rol `VENDEDOR` consulta `GET /clientes/{id}` de un cliente que aún no registró su perfil
- **THEN** el sistema responde `200 OK` con la ficha y `perfil = null`

#### Scenario: Consulta de cliente inexistente
- **WHEN** un usuario con rol `ADMIN` consulta `GET /clientes/{id}` con un identificador que no existe
- **THEN** el sistema responde `404 Not Found`

### Requirement: Actualización de cliente con correo único

El endpoint `PATCH /clientes/{id}` SHALL permitir a roles `VENDEDOR` y `ADMIN` modificar `nombre` y/o `email` con `extra="forbid"`. Si el cliente no existe SHALL responder `404 Not Found`; si el nuevo correo ya pertenece a otro cliente SHALL responder `409 Conflict`; ante un contrato inválido SHALL responder `422 Unprocessable Entity`.

#### Scenario: Actualización exitosa de datos del cliente
- **WHEN** un usuario con rol `VENDEDOR` envía `PATCH /clientes/{id}` modificando `nombre` y `email` por valores válidos y libres
- **THEN** el sistema responde `200 OK` con los datos actualizados

#### Scenario: Actualización rechazada por correo duplicado
- **WHEN** un usuario con rol `ADMIN` envía `PATCH /clientes/{id}` con un correo que ya pertenece a otro cliente
- **THEN** el sistema responde `409 Conflict` y conserva los datos anteriores del cliente

#### Scenario: Actualización de cliente inexistente
- **WHEN** un usuario con rol `VENDEDOR` envía `PATCH /clientes/{id}` con un identificador que no existe
- **THEN** el sistema responde `404 Not Found`

#### Scenario: Actualización rechazada por campo no permitido
- **WHEN** un usuario con rol `ADMIN` envía `PATCH /clientes/{id}` incluyendo un campo adicional no declarado
- **THEN** el sistema responde `422 Unprocessable Entity`

### Requirement: Alta del perfil único de un cliente

El endpoint `POST /clientes/{id}/perfil` SHALL permitir a roles `VENDEDOR` y `ADMIN` registrar `telefono` y `direccion` con `extra="forbid"`. Creará el perfil en una única transacción y responderá `201 Created`. Si el cliente no existe SHALL responder `404 Not Found`; si ya posee un perfil SHALL responder `409 Conflict`.

#### Scenario: Alta exitosa del perfil
- **WHEN** un usuario con rol `VENDEDOR` envía `POST /clientes/{id}/perfil` con `telefono` y `direccion` válidos para un cliente sin perfil
- **THEN** el sistema responde `201 Created` con el perfil creado y asociado al cliente

#### Scenario: Alta de perfil para cliente inexistente
- **WHEN** un usuario con rol `VENDEDOR` envía `POST /clientes/{id}/perfil` con un identificador de cliente que no existe
- **THEN** el sistema responde `404 Not Found`

#### Scenario: Segundo perfil rechazado por unicidad
- **WHEN** un usuario con rol `ADMIN` envía `POST /clientes/{id}/perfil` para un cliente que ya tiene un perfil
- **THEN** el sistema responde `409 Conflict` y no crea una segunda fila

#### Scenario: Alta de perfil rechazada por contrato inválido
- **WHEN** un usuario con rol `ADMIN` envía `POST /clientes/{id}/perfil` con un campo adicional no declarado
- **THEN** el sistema responde `422 Unprocessable Entity`

### Requirement: Consulta de ventas de un cliente

El endpoint `GET /clientes/{id}/ventas` SHALL estar disponible en el Grupo Protegido para roles `VENDEDOR` y `ADMIN`. Devolverá las ventas del cliente ordenadas de la más reciente a la más antigua, incluyendo cliente y renglones con el título del libro aunque el libro haya sido dado de baja lógica. Si el cliente no existe SHALL responder `404 Not Found`.

#### Scenario: Consulta de ventas de un cliente con historial
- **WHEN** un usuario con rol `VENDEDOR` consulta `GET /clientes/{id}/ventas` de un cliente con ventas registradas
- **THEN** el sistema responde `200 OK` con la lista de ventas ordenada de la más reciente a la más antigua, con sus renglones

#### Scenario: Venta histórica con libro dado de baja lógica
- **WHEN** el cliente consultado tiene una venta que incluye un libro con `borrado_en IS NOT NULL`
- **THEN** el sistema responde `200 OK` mostrando el título del libro en el renglón correspondiente

#### Scenario: Consulta de ventas de un cliente sin ventas
- **WHEN** un usuario con rol `ADMIN` consulta `GET /clientes/{id}/ventas` de un cliente que no tiene ventas
- **THEN** el sistema responde `200 OK` con una lista vacía

#### Scenario: Consulta de ventas de un cliente inexistente
- **WHEN** un usuario con rol `VENDEDOR` consulta `GET /clientes/{id}/ventas` con un identificador que no existe
- **THEN** el sistema responde `404 Not Found`

### Requirement: Control de acceso por rol en las rutas de clientes

Las cinco rutas de clientes (`POST /clientes`, `GET /clientes/{id}`, `PATCH /clientes/{id}`, `POST /clientes/{id}/perfil` y `GET /clientes/{id}/ventas`) MUST residir en el Grupo Protegido y exigir un rol `VENDEDOR` o `ADMIN` vigente consultado en `asignacion_rol` en cada petición (`RN-04`). Sin sesión válida SHALL responder `401 Unauthorized`; con cambio de contraseña pendiente o sin los roles requeridos SHALL responder `403 Forbidden`.

#### Scenario: Acceso permitido a un vendedor
- **WHEN** un usuario con rol `VENDEDOR` vigente invoca cualquiera de las rutas de clientes
- **THEN** el sistema continúa con el flujo del endpoint en lugar de rechazar la petición

#### Scenario: Acceso denegado a un cliente
- **WHEN** un usuario con rol `CLIENTE` invoca `POST /clientes` o `GET /clientes/{id}`
- **THEN** el sistema responde `403 Forbidden`

#### Scenario: Acceso denegado sin sesión
- **WHEN** una petición anónima invoca cualquiera de las rutas de clientes sin la cookie `access_token`
- **THEN** el sistema responde `401 Unauthorized`

#### Scenario: Acceso denegado con cambio de contraseña pendiente
- **WHEN** un usuario con `debe_cambiar_password = True` invoca cualquiera de las rutas de clientes
- **THEN** el sistema responde `403 Forbidden`
