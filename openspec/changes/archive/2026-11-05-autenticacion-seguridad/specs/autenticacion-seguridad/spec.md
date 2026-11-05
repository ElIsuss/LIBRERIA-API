# Spec Delta

## Purpose

Provee la autenticación de usuarios de la librería mediante cookies `HttpOnly` con tokens JWT, validación de contraseñas en UTF-8 hasta 72 bytes, protección contra fuerza bruta con registro independiente de intentos, auto-registro atómico de clientes y cambio de contraseña auditado.

## ADDED Requirements

### Requirement: Validación de longitud de contraseña en UTF-8 y rechazo de campos extra
El sistema MUST validar en todos los contratos de entrada de autenticación que la contraseña codificada en UTF-8 no supere los 72 bytes y que no se envíen atributos no declarados (`extra="forbid"`), respondiendo `422 Unprocessable Entity` ante cualquier incumplimiento y nunca `500 Internal Server Error`.

#### Scenario: Contraseña excede los 72 bytes en UTF-8
- **WHEN** un cliente envía a `POST /auth/registro`, `POST /auth/login` o `POST /auth/cambiar-password` una contraseña cuya representación UTF-8 supera los 72 bytes
- **THEN** el sistema rechaza la petición con `422 Unprocessable Entity` sin llegar a invocar el algoritmo de hashing

#### Scenario: Envío de campo extra no permitido en el auto-registro
- **WHEN** un visitante envía a `POST /auth/registro` un campo adicional como `"rol": "ADMIN"`
- **THEN** el sistema rechaza la petición con `422 Unprocessable Entity`

### Requirement: Auto-registro atómico de cliente web
El sistema SHALL permitir el auto-registro en `POST /auth/registro` creando de forma atómica el usuario (`activo=True`, `debe_cambiar_password=False`), su asignación del rol `CLIENTE` y su ficha en `cliente` vinculada al usuario. Si el correo ya existe en `usuario` o en `cliente`, el sistema MUST revertir todas las escrituras y responder `409 Conflict` sin apropiarse de la ficha existente.

#### Scenario: Auto-registro exitoso de nuevo cliente
- **WHEN** un visitante envía `POST /auth/registro` con nombre, email nuevo y contraseña válida
- **THEN** el sistema responde `201 Created` y quedan persistidas en una sola transacción la fila en `usuario`, la fila en `asignacion_rol` con `rol="CLIENTE"` y la fila en `cliente` con `usuario_id` asociado

#### Scenario: Correo ya registrado como cliente de mostrador o usuario
- **WHEN** un visitante envía `POST /auth/registro` con un `email` que ya figura en `cliente` o en `usuario`
- **THEN** el sistema revierte la transacción completa, no modifica la ficha existente y responde `409 Conflict` con mensaje descriptivo propio

### Requirement: Límite de intentos fallidos de inicio de sesión
El sistema MUST contar en `intento_acceso` los intentos fallidos para el par `(email, ip)` ocurridos en los últimos 60 segundos posteriores al último intento exitoso. Si existen 5 o más intentos fallidos en esa ventana, `POST /auth/login` SHALL responder `429 Too Many Requests` incluyendo la cabecera `Retry-After` sin verificar la contraseña.

#### Scenario: Bloqueo al sexto intento consecutivo en 60 segundos
- **WHEN** un cliente acumula 5 intentos fallidos de login para el mismo `email` e `ip` dentro de los últimos 60 segundos y envía un 6.º intento
- **THEN** el sistema responde `429 Too Many Requests` con la cabecera `Retry-After` en pocos milisegundos sin ejecutar la verificación de contraseña

#### Scenario: Reinicio del contador tras un inicio de sesión exitoso
- **WHEN** un cliente con menos de 5 fallos previos inicia sesión con credenciales válidas
- **THEN** el intento exitoso queda registrado y los fallos anteriores dejan de contabilizarse para futuros intentos dentro de la ventana

### Requirement: Verificación de credenciales en tiempo constante y registro independiente de intentos
En `POST /auth/login`, cuando el correo no existe o el usuario está inactivo, el sistema MUST ejecutar igualmente la verificación criptográfica contra un hash ficticio precalculado y responder `401 Unauthorized` con idéntico mensaje que ante una contraseña incorrecta. Cada intento evaluado (exitoso o fallido) SHALL persistirse en `intento_acceso` en una transacción independiente que se confirma incluso cuando la petición devuelve `401`.

#### Scenario: Intento de login con correo inexistente o contraseña incorrecta
- **WHEN** un cliente envía `POST /auth/login` con un correo no registrado o con una contraseña errónea
- **THEN** el sistema ejecuta la comparación criptográfica, confirma una fila con `exito=False` en `intento_acceso` y responde `401 Unauthorized` con el mismo mensaje uniforme

### Requirement: Transporte exclusivo de sesión mediante cookie HttpOnly
Al autenticar exitosamente en `POST /auth/login`, el sistema SHALL emitir un token JWT con `sub`, `exp` y la lista informativa de roles vigentes, enviándolo únicamente en la cookie `access_token` (`HttpOnly`, `SameSite=Lax`, `Max-Age`, `Secure` según configuración) y NUNCA en el cuerpo JSON. `POST /auth/logout` SHALL eliminar dicha cookie.

#### Scenario: Login exitoso emite cookie HttpOnly sin exponer el token en el cuerpo
- **WHEN** un usuario activo envía credenciales válidas a `POST /auth/login`
- **THEN** el sistema responde `200 OK` con `Set-Cookie: access_token=...; HttpOnly; SameSite=lax; Max-Age=...` y un cuerpo JSON con `mensaje`, `debe_cambiar_password` y `expira_en_segundos` sin incluir el JWT

#### Scenario: Cierre de sesión en logout
- **WHEN** un cliente invoca `POST /auth/logout`
- **THEN** el sistema responde `200 OK` e instruye al cliente a borrar la cookie `access_token`

### Requirement: Consulta de identidad y roles en sesión actual
El endpoint `GET /auth/yo` SHALL identificar al usuario activo exclusivamente a partir de la cookie `access_token` y devolver sus datos junto con `roles_vigentes` (consultados en tiempo real en `asignacion_rol`) y `roles_token` (declarados en el payload del JWT), o responder `401 Unauthorized` si la cookie falta, el token es inválido/expiró o el usuario está inactivo.

#### Scenario: Consulta de perfil autenticado con cookie válida
- **WHEN** un usuario autenticado realiza `GET /auth/yo` enviando la cookie `access_token`
- **THEN** el sistema responde `200 OK` incluyendo `id`, `email`, `nombre`, `debe_cambiar_password`, `roles_vigentes` y `roles_token`

#### Scenario: Consulta sin cookie o con token inválido
- **WHEN** se invoca `GET /auth/yo` sin la cookie `access_token` o con un token vencido o adulterado
- **THEN** el sistema responde `401 Unauthorized`

### Requirement: Cambio de contraseña transaccional y auditado
El endpoint `POST /auth/cambiar-password` SHALL permitir a cualquier usuario autenticado (incluso con `debe_cambiar_password = True`) verificar su contraseña actual y actualizarla en una única transacción que reemplaza `password_hash`, establece `debe_cambiar_password = False` y registra el evento en `evento_seguridad`, manteniendo válida la sesión actual.

#### Scenario: Cambio de contraseña exitoso desbloquea el estado pendiente
- **WHEN** un usuario autenticado envía `POST /auth/cambiar-password` con su `password_actual` correcta y una `password_nueva` válida
- **THEN** el sistema responde `200 OK`, actualiza `password_hash`, pone `debe_cambiar_password = False` y agrega la fila en `evento_seguridad` dentro de la misma transacción

#### Scenario: Contraseña actual incorrecta al intentar cambiar clave
- **WHEN** un usuario autenticado envía `POST /auth/cambiar-password` con una `password_actual` que no coincide con su hash vigente
- **THEN** el sistema no modifica el usuario ni registra evento de seguridad y responde `401 Unauthorized`
