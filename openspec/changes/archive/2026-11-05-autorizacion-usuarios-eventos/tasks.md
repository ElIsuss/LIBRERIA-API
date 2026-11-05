# Tasks

## 1. Dependencias Centrales de Autorización (`app/core/dependencies.py`)

- [x] 1.1 Implementar en `app/core/dependencies.py` las dependencias `get_usuario_actual` (lectura de cookie `access_token` y carga de usuario con sesión compartida de `Depends(get_session)`), `verificar_password_actualizada` (bloqueo `403` si `debe_cambiar_password = True`) y `requiere_rol(*roles)` (consulta de roles vigentes en BD `RN-04` devolviendo `403`), verificando mediante tests unitarios de dependencias su comportamiento ante usuarios válidos, inactivos y con contraseña provisoria.
- [x] 1.2 Configurar en `app/main.py` el `protected_router` agregando `dependencies=[Depends(verificar_password_actualizada)]` (`DD-01`), verificando que cualquier ruta incluida en él responde automáticamente `403 Forbidden` si `debe_cambiar_password = True`.

## 2. Repositorios de Asignación de Roles y Eventos de Seguridad

- [x] 2.1 Agregar en `AsignacionRolRepository` los métodos `contar_administradores_vigentes() -> int` (para verificar que exista más de 1 admin antes de revocar) y `cerrar_asignacion(usuario_id: int, rol: str)`, verificando que solo ejecutan `flush()` sin `commit()`.
- [x] 2.2 Agregar en `EventoSeguridadRepository` el método `listar_paginado(page: int, size: int) -> tuple[list[EventoSeguridad], int]`, ordenado por fecha descendente con cálculo de offset y limit.

## 3. Contratos Pydantic y Servicio de Administración (`schemas.py` y `service.py`)

- [x] 3.1 Crear en `app/modules/usuarios/schemas.py` los esquemas `UsuarioCreateRequest` (con `extra="forbid"`, validación de 72 bytes en `password_provisoria` y rol inicial permitido), `AsignarRolRequest` (con validador de `vence_en` que exige timezone y fecha futura devolviendo `422`), `AsignacionRolResponse` y `EventoSeguridadRead`, verificando con pruebas de esquemas que fechas pasadas o naive son rechazadas con `ValidationError`.
- [x] 3.2 Implementar en `app/modules/usuarios/service.py` los métodos `crear_personal` (`POST /usuarios` con hash previo, `debe_cambiar_password = True`, rol inicial y auditoría `RN-16`), `listar_roles_usuario` (`GET /usuarios/{id}/roles`), `asignar_rol` (`POST /usuarios/{id}/roles` cerrando asignación previa vencida si existe y registrando en `evento_seguridad`), `revocar_rol` (`DELETE /usuarios/{id}/roles/{rol}` con doble control de autoprotección `RN-05` respondiendo `409 Conflict` si es auto-revocación o el último admin) y `listar_eventos_paginado` (`GET /eventos`).

## 4. Endpoints Protegidos y Verificación Integral

- [x] 4.1 Implementar en `app/modules/usuarios/router.py` las rutas administrativas `POST /usuarios`, `GET /usuarios/{id}/roles`, `POST /usuarios/{id}/roles`, `DELETE /usuarios/{id}/roles/{rol}` y `GET /eventos`, todas protegidas con `Depends(requiere_rol("ADMIN"))`, e incluirlas dentro de `protected_router` en `app/main.py`.
- [x] 4.2 Crear `test/test_c05_e2e.py` y verificar de punta a punta: bloqueo 403 a usuarios con clave provisoria, acceso y rechazo por rol en tiempo real, alta de personal con clave provisoria, asignación de roles con fecha futura y rechazo 422 si es inválida, revocación con autoprotección 409 (tanto al auto-revocarse como al único admin) y consulta paginada de eventos.

## Workflow follow-up

- Archivar el change con `/opsx:archive autorizacion-usuarios-eventos` una vez completadas y verificadas todas las tareas.
- Actualizar el estado de `[C-05]` en `CHANGES.md`.
