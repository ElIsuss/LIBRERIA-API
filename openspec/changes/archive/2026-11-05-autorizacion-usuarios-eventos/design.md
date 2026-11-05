# Design

## Context

El proyecto cuenta con:
- `app/core/security.py`: JWT y hashing bcrypt no bloqueante.
- `app/modules/usuarios/`: modelos `Usuario`, `AsignacionRol`, `EventoSeguridad` y repositorios base.
- `app/main.py`: `open_router` y `protected_router` separados.

Ver `proposal.md` para la motivación y `specs/autorizacion-usuarios-eventos/spec.md` para los contratos normativos.

## Goals / Non-Goals

**Goals:**
- Implementar `app/core/dependencies.py` con `get_usuario_actual`, `verificar_password_actualizada` y `requiere_rol(*roles)` evaluados contra PostgreSQL.
- Implementar la autoprotección estricta de administradores (`RN-05`) en `UsuarioService`.
- Implementar el alta de personal con clave provisoria (`debe_cambiar_password = True`) y auditoría en `evento_seguridad` (`RN-16`).
- Implementar la asignación y revocación de roles respetando el índice parcial de asignación abierta (`RN-03`) y la auditoría (`RN-16`).
- Exponer y proteger las rutas de `/usuarios*` y `/eventos` bajo `requiere_rol("ADMIN")`.

**Non-Goals:**
- No incluye la refactorización de los repositorios de catálogo ni ventas (corresponden a `C-06` y `C-07`).

## Decisions

### 1. Dependencias centralizadas en `app/core/dependencies.py` compartiendo sesión con el `UnitOfWork` (`DD-02`)
- **Decisión**: Implementar:
  - `get_usuario_actual(request: Request, session: AsyncSession = Depends(get_session))`
  - `verificar_password_actualizada(usuario: Usuario = Depends(get_usuario_actual))`
  - `requiere_rol(*roles_permitidos)`: función de orden superior que devuelve una dependencia FastAPI encargada de consultar `AsignacionRolRepository.get_roles_vigentes(usuario.id)`.
- **Razón**: Al usar `session: AsyncSession = Depends(get_session)`, FastAPI inyecta la misma sesión para autenticar, autorizar y ejecutar el `UnitOfWork` de la petición, consumiendo una sola conexión del pool por request.

### 2. Montaje global de `verificar_password_actualizada` en `protected_router` (`DD-01`)
- **Decisión**: Configurar en `app/main.py`:
  ```python
  protected_router = APIRouter(dependencies=[Depends(verificar_password_actualizada)])
  ```
- **Razón**: Garantiza de manera automática que ninguna ruta del negocio pueda ser accedida por usuarios con contraseña provisoria pendiente (`RN-06`), sin tener que declarar la comprobación endpoint por endpoint.

### 3. Autoprotección de Administradores (`RN-05`) en `UsuarioService.revocar_rol`
- **Decisión**: Al recibir una petición para revocar un rol (`DELETE /usuarios/{id}/roles/{rol}`):
  1. Si `rol == "ADMIN"` y `actor.id == target_user_id`: responder `409 Conflict` (prohibido auto-revocarse).
  2. Si `rol == "ADMIN"`, consultar `AsignacionRolRepository.contar_administradores_vigentes()`. Si el conteo es `<= 1`: responder `409 Conflict` (prohibido dejar al sistema sin administradores vigentes).
- **Razón**: Protege la integridad operativa del sistema frente a errores humanos o ataques administrativos.

### 4. Reasignación de roles abiertos vencidos (`RN-03`)
- **Decisión**: PostgreSQL posee un índice único parcial `uq_asignacion_rol_abierta` sobre `(usuario_id, rol) WHERE revocada_en IS NULL`. Si un usuario tenía una asignación cuyo `vence_en` ya expiró, su `revocada_en` continúa en `NULL`. Al invicar `POST /usuarios/{id}/roles`:
  - Si la asignación abierta está vigente (`vence_en IS NULL OR vence_en > now()`): responde `409 Conflict`.
  - Si la asignación abierta ya expiró (`vence_en <= now()`): el servicio actualiza su `revocada_en = now()` y a continuación inserta la nueva asignación en la misma transacción (`async with uow:`).
- **Razón**: Permite renovar roles vencidos sin violar la restricción de unicidad parcial en base de datos.

### 5. Validación estricta de `vence_en` en esquemas Pydantic
- **Decisión**: Validar en `AsignarRolRequest` que `vence_en` (si no es `None`):
  - Tenga información de zona horaria (`v.tzinfo is not None`).
  - Sea estrictamente posterior al instante presente (`v > datetime.now(timezone.utc)`).
- **Razón**: Devuelve `422 Unprocessable Entity` ante fechas inválidas o ambiguas de inmediato.

## Risks / Trade-offs

- **[Risk] Rendimiento de la consulta de roles en cada petición** → **Mitigación**: La consulta sobre `asignacion_rol` utiliza los índices `usuario_id` y `uq_asignacion_rol_abierta`, resolviéndose en microsegundos y garantizando que la revocación tenga efecto instantáneo en todo el sistema.

## Migration Plan

- No requiere nuevas migraciones de base de datos (las tablas `usuario`, `asignacion_rol`, `evento_seguridad` y sus índices únicos parciales ya existen desde `C-02`).

## UI Mockups

Decision: no (no UI)
