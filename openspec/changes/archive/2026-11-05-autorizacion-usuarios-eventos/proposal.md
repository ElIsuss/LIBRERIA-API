# Proposal

## Why

Con la autenticación y la gestión de sesiones mediante JWT en cookies `HttpOnly` completadas en `C-04`, el sistema necesita ahora controlar el acceso a los recursos protegidos según los roles vigentes del usuario evaluados en tiempo real en la base de datos (`RN-04`), bloquear el acceso al negocio a aquellos usuarios que tienen un cambio de contraseña pendiente (`RN-06`), permitir a los administradores dar de alta personal y gestionar sus roles con salvaguardas para no desproteger el sistema (`RN-03`, `RN-05`), y auditar de forma transaccional cada operación sensible en la tabla `evento_seguridad` (`RN-16`). Este cambio (**C-05 — Ejercicio 5**) implementa la capa de autorización RBAC, los endpoints administrativos `/usuarios*` y la consulta paginada de `/eventos`.

## What Changes

- **Capa central de dependencias de autorización (`app/core/dependencies.py`)**:
  - `get_usuario_actual`: extrae `access_token` de la cookie de la petición, decodifica el JWT y carga al `Usuario` activo usando la misma `AsyncSession` de `Depends(get_session)` que compartirá con el `UnitOfWork` (`401 Unauthorized` si falta la cookie, venció, es inválido o el usuario está inactivo).
  - `verificar_password_actualizada`: dependencia montada a nivel global en el `protected_router` de `app/main.py`, respondiendo `403 Forbidden` si `usuario.debe_cambiar_password == True` (`RN-06`).
  - `requiere_rol(*roles)`: dependencia parametrizada que consulta en `asignacion_rol` los roles vigentes (`revocada_en IS NULL AND (vence_en IS NULL OR vence_en > now())`) en cada petición (`RN-04`), respondiendo `403 Forbidden` si el usuario no posee al menos uno de los roles requeridos.
- **Servicio y repositorios de administración (`app/modules/usuarios/`)**:
  - `AsignacionRolRepository`: métodos para verificar existencia de asignación abierta/vigente y conteo de administradores vigentes en el sistema para la regla de autoprotección (`RN-05`).
  - `EventoSeguridadRepository`: consulta paginada de eventos con conteo y orden cronológico descendente.
  - `UsuarioService`: lógica de alta de personal con contraseña provisoria, asignación de rol cerrando asignaciones vencidas previas, revocación lógica con doble chequeo de autoprotección de `ADMIN` (`RN-05`), y registro transaccional en `evento_seguridad` dentro del mismo `UnitOfWork` (`RN-16`).
- **Contratos Pydantic estrictos (`app/modules/usuarios/schemas.py`)**:
  - `UsuarioCreateRequest`: creación de personal con `nombre`, `email`, `password_provisoria` y `rol_inicial` (`ADMIN`, `VENDEDOR`, `CLIENTE`).
  - `AsignarRolRequest`: asignación con `rol` y `vence_en` opcional con validación estricta de timezone y tiempo futuro (`422`).
  - `AsignacionRolResponse`: detalle de la asignación con fechas formateadas.
  - `EventoSeguridadRead`: detalle de la fila de auditoría para su consulta paginada `Page[EventoSeguridadRead]`.
- **Endpoints de administración en `app/modules/usuarios/router.py`**:
  - `POST /usuarios` (`201`, `409`, `422`): alta de personal (`requiere_rol("ADMIN")`).
  - `GET /usuarios/{id}/roles` (`200`, `404`): listado de roles del usuario (`requiere_rol("ADMIN")`).
  - `POST /usuarios/{id}/roles` (`201`, `404`, `409`, `422`): asignación de rol (`requiere_rol("ADMIN")`).
  - `DELETE /usuarios/{id}/roles/{rol}` (`200`, `404`, `409`): revocación de rol con autoprotección (`requiere_rol("ADMIN")`).
  - `GET /eventos` (`200`, `422`): listado paginado `{items, total, page, size, pages}` de `evento_seguridad` (`requiere_rol("ADMIN")`).
- **Configuración de rutas protegidas en `app/main.py`**:
  - Configuración de `protected_router` con `dependencies=[Depends(verificar_password_actualizada)]` (`DD-01`).
  - Montaje de las rutas de administración de usuarios y eventos dentro de `protected_router`.

## Capabilities

### New Capabilities
- `autorizacion-usuarios-eventos`: Autorización basada en roles (RBAC) en tiempo real, bloqueo de acceso a recursos de negocio por contraseña provisoria pendiente, administración de usuarios y roles con autoprotección de administradores, y auditoría transaccional de eventos de seguridad.

### Modified Capabilities
<!-- No se modifican capabilities existentes -->

## Impact

- **Nuevos archivos previstos**:
  - `app/core/dependencies.py`
  - `test/test_c05_e2e.py`
- **Archivos existentes modificados**:
  - `app/modules/usuarios/schemas.py` (nuevos esquemas para personal, asignaciones y eventos)
  - `app/modules/usuarios/repository.py` (conteo de administradores vigentes y paginación de eventos)
  - `app/modules/usuarios/service.py` (alta de personal, administración de roles y autoprotección)
  - `app/modules/usuarios/router.py` (rutas protegidas `/usuarios*` y `/eventos`)
  - `app/main.py` (aplicación de la dependencia de protección en `protected_router`)
- **Dependencias**: Usa los paquetes ya instalados en `requirements.txt`.
