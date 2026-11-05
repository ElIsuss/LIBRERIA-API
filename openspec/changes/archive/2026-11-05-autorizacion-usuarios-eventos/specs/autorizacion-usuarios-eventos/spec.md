# Spec Delta

## Purpose

Establece el control de acceso basado en roles (RBAC) en tiempo real contra PostgreSQL, el bloqueo global por cambio obligatorio de contraseña, la administración de usuarios y roles con autoprotección de administradores y la auditoría de eventos de seguridad.

## ADDED Requirements

### Requirement: Autenticación de usuario activo y carga con sesión compartida
El sistema MUST resolver la identidad del usuario autenticado a partir de la cookie `access_token`, verificando firma y expiración del JWT y cargando al `Usuario` activo usando la misma sesión de base de datos que el `UnitOfWork`. Si la cookie falta, el token es inválido/expiró o el usuario no existe o está inactivo, el sistema SHALL responder `401 Unauthorized`.

#### Scenario: Petición autenticada con cookie válida
- **WHEN** un cliente realiza una petición a un recurso protegido enviando una cookie `access_token` válida y activa
- **THEN** el sistema resuelve el usuario y permite continuar el flujo de autorización

#### Scenario: Petición sin cookie o con usuario inactivo
- **WHEN** un cliente realiza una petición a un recurso protegido sin la cookie o con un usuario desactivado
- **THEN** el sistema interrumpe la petición y responde `401 Unauthorized`

### Requirement: Bloqueo de acceso por cambio de contraseña pendiente
El sistema MUST evaluar en todas las rutas del grupo protegido si el usuario autenticado tiene `debe_cambiar_password = True`. En caso afirmativo, SHALL rechazar la petición con `403 Forbidden` impidiendo el acceso a los recursos del negocio hasta que se actualice la contraseña en `/auth/cambiar-password`.

#### Scenario: Usuario con clave provisoria intenta acceder a ruta protegida
- **WHEN** un usuario con `debe_cambiar_password = True` intenta acceder a cualquier endpoint del grupo protegido
- **THEN** el sistema responde `403 Forbidden` con mensaje descriptivo del cambio obligatorio

#### Scenario: Usuario con clave definitiva accede a ruta protegida
- **WHEN** un usuario con `debe_cambiar_password = False` accede a una ruta del grupo protegido
- **THEN** el sistema permite el paso hacia la verificación de roles del endpoint

### Requirement: Autorización por roles vigentes en base de datos
Para cada ruta protegida por roles, el sistema MUST consultar en `asignacion_rol` si el usuario posee al menos uno de los roles requeridos con `revocada_en IS NULL` y `(vence_en IS NULL OR vence_en > now())`. Si no posee un rol vigente en la base, SHALL responder `403 Forbidden`, surtiendo efecto la revocación en forma inmediata.

#### Scenario: Acceso permitido con rol vigente en base de datos
- **WHEN** un usuario autenticado con asignación vigente del rol requerido solicita un recurso protegido
- **THEN** el sistema valida el rol en PostgreSQL y responde con el recurso solicitado

#### Scenario: Acceso denegado con rol revocado o vencido
- **WHEN** un usuario intenta acceder a un recurso sin tener el rol vigente en `asignacion_rol`
- **THEN** el sistema rechaza la petición con `403 Forbidden`

### Requirement: Alta de personal con clave provisoria y auditoría
El sistema SHALL permitir a un usuario con rol `ADMIN` vigente registrar personal en `POST /usuarios` creando en una única transacción el usuario con `debe_cambiar_password = True`, su rol inicial en `asignacion_rol` y una fila en `evento_seguridad`. Si el correo ya existe, MUST responder `409 Conflict`.

#### Scenario: Creación exitosa de personal por administrador
- **WHEN** un `ADMIN` envía `POST /usuarios` con datos válidos de un nuevo empleado
- **THEN** el sistema responde `201 Created` y persiste en un solo `UnitOfWork` el `Usuario` con clave provisoria, la asignación de rol y el registro en `evento_seguridad`

#### Scenario: Correo ya registrado al crear personal
- **WHEN** un `ADMIN` intenta registrar personal con un correo existente en la base
- **THEN** el sistema no modifica datos y responde `409 Conflict`

### Requirement: Asignación de rol con control de vencimiento y cierre de asignación previa
El endpoint `POST /usuarios/{id}/roles` SHALL permitir a un `ADMIN` asignar un rol a un usuario. Si se provee `vence_en`, MUST validar que contenga zona horaria y sea una fecha futura, respondiendo `422 Unprocessable Entity` en caso contrario. Si existe una asignación abierta ya vencida para ese rol, SHALL marcarla como revocada y abrir la nueva en la misma transacción; si el rol ya está vigente, MUST responder `409 Conflict`. Cada asignación SHALL registrarse en `evento_seguridad`.

#### Scenario: Asignación exitosa de rol con vencimiento futuro
- **WHEN** un `ADMIN` envía `POST /usuarios/{id}/roles` con un rol y un `vence_en` futuro con zona horaria
- **THEN** el sistema responde `201 Created`, persiste la asignación y registra el evento de seguridad

#### Scenario: Fecha de vencimiento inválida o sin zona horaria
- **WHEN** un `ADMIN` envía `POST /usuarios/{id}/roles` con un `vence_en` pasado o naive (sin zona horaria)
- **THEN** el sistema rechaza la solicitud con `422 Unprocessable Entity`

#### Scenario: Intento de asignar rol que ya se encuentra vigente
- **WHEN** un `ADMIN` envía `POST /usuarios/{id}/roles` para un usuario que ya cuenta con ese rol vigente
- **THEN** el sistema no duplica la asignación y responde `409 Conflict`

### Requirement: Revocación de rol con autoprotección de administradores y auditoría
El endpoint `DELETE /usuarios/{id}/roles/{rol}` SHALL permitir a un `ADMIN` revocar una asignación abierta marcando `revocada_en = now()` y auditando en `evento_seguridad`. El sistema MUST impedir que un administrador se revoque su propio rol `ADMIN` o que se revoque al último administrador vigente en todo el sistema, respondiendo `409 Conflict` en ambos casos.

#### Scenario: Revocación exitosa de rol a otro usuario
- **WHEN** un `ADMIN` revoca el rol a otro usuario cuando no se vulneran las reglas de autoprotección
- **THEN** el sistema marca `revocada_en = now()`, registra el evento en `evento_seguridad` y responde `200 OK`

#### Scenario: Administrador intenta revocar su propio rol de administrador
- **WHEN** un usuario con rol `ADMIN` intenta revocar su propio rol `ADMIN` en `DELETE /usuarios/{su_id}/roles/ADMIN`
- **THEN** el sistema rechaza la acción respondiendo `409 Conflict`

#### Scenario: Intento de revocación al único administrador vigente del sistema
- **WHEN** se intenta revocar el rol `ADMIN` a un usuario y este es el único administrador vigente en el sistema
- **THEN** el sistema rechaza la operación respondiendo `409 Conflict` para evitar la acefalía

### Requirement: Consulta paginada de eventos de seguridad
El endpoint `GET /eventos` SHALL estar disponible exclusivamente para usuarios con rol `ADMIN` vigente y responder con una estructura paginada `{items, total, page, size, pages}` conteniendo el historial de `evento_seguridad` ordenado cronológicamente en forma descendente.

#### Scenario: Consulta paginada de eventos por administrador
- **WHEN** un `ADMIN` solicita `GET /eventos?page=1&size=20`
- **THEN** el sistema responde `200 OK` con la lista paginada de eventos y sus totales calculados

#### Scenario: Acceso a eventos por usuario sin rol administrador
- **WHEN** un cliente o usuario sin rol `ADMIN` vigente invoca `GET /eventos`
- **THEN** el sistema responde `403 Forbidden`
