# Decisiones y Supuestos

## Decisiones documentadas

### DD-01 — Dos grupos de rutas en `main.py` para el cambio obligatorio de contraseña (RN-06)
- **Decisión**: Montar en `app/main.py` dos `APIRouter` de nivel superior (o dos agrupaciones de inclusión): el **Grupo Abierto** (sin dependencia de bloqueo por clave provisoria) y el **Grupo Protegido** (con `dependencies=[Depends(verificar_sin_cambio_password_pendiente)]` declarada una sola vez).
- **Contexto**: En FastAPI las dependencias se suman a medida que se anidan routers y no existe forma de "restar" una dependencia global en una ruta hija como `/auth/cambiar-password`.
- **Alternativas consideradas**: Repetir la dependencia en cada uno de los ~20 endpoints protegidos (propenso a olvidos) o usar un middleware HTTP que parsee rutas por string.
- **Justificación**: Montar el control una sola vez sobre el grupo protegido cumple explícitamente la consigna (Ejercicio 5, sección 5.10) y hace imposible olvidar la validación en un endpoint protegido.
- **Trade-offs aceptados**: Los módulos que tienen tanto rutas abiertas como protegidas (por ejemplo `libros`, `editoriales`, `generos`, `autores`) exponen dos routers internos (`router_abierto` y `router_protegido`) o se registran en el grupo correspondiente.

### DD-02 — Unificación de la sesión entre dependencias de Auth y `UnitOfWork`
- **Decisión**: Tanto `get_usuario_actual` / `requiere_rol` como el proveedor `get_uow` de cada módulo inyectan `session: AsyncSession = Depends(get_session)`.
- **Contexto**: Si `get_usuario_actual` abriera su propia sesión y el `UnitOfWork` abriera otra al entrar al `async with`, cada petición autenticada consumiría **dos conexiones simultáneas** del pool de PostgreSQL.
- **Justificación**: Aprovecha la caché por petición de `Depends(get_session)` en FastAPI. El `UnitOfWork` recibe esa sesión ya creada, hace `commit()` o `rollback()` al salir del `async with`, y **no la cierra** (la cierra el `yield` de `get_session` al finalizar la petición).

### DD-03 — Sesión y transacción independientes para `intento_acceso` (Ejercicio 7)
- **Decisión**: El registro de cada intento de login en `intento_acceso` no usa el `UnitOfWork` de la petición, sino que abre su propia sesión desde `request.app.state.session_factory` y ejecuta `commit()` inmediatamente.
- **Contexto**: Cuando un login falla, el handler termina devolviendo `401 Unauthorized` (o revirtiendo la operación). Si el intento fallido compartiera la transacción de la petición, un rollback borraría el propio fallo que se necesita contar para el límite de 5 intentos en 60 segundos (RN-07).
- **Trade-offs aceptados**: Consume una transacción corta aparte durante el login y deja la fila confirmada aunque el resto de la petición falle; se documenta con el comentario exigido en el Ejercicio 7.

### DD-04 — Cálculo de `bcrypt` fuera del bucle de eventos y antes de abrir el `UnitOfWork`
- **Decisión**: Toda operación de `bcrypt` (`hashpw` y `checkpw`) se ejecuta mediante `await asyncio.to_thread(...)` envuelta en un `asyncio.Semaphore`, y **siempre antes** de entrar al bloque `async with uow:`.
- **Contexto**: `bcrypt` es intensivo en CPU (~250-300 ms). Si corriera en el hilo del event loop bloquearía a todos los demás clientes de FastAPI; si corriera dentro de `async with uow:`, mantendría ociosa y retenida la transacción de PostgreSQL durante esos 300 ms.

### DD-05 — Índices únicos parciales en PostgreSQL (`postgresql_where`) para ISBN y Roles
- **Decisión**: Reemplazar el `UNIQUE` simple de `libro.isbn` por un `Index(..., unique=True, postgresql_where=text("borrado_en IS NULL"))`, y definir en `asignacion_rol` el `Index(..., unique=True, postgresql_where=text("revocada_en IS NULL"))`.
- **Contexto**: El historial de asignaciones de rol revocadas y los libros dados de baja lógica permanecen en sus tablas. Un `UNIQUE` tradicional impediría volver a asignar un rol que alguna vez fue revocado o volver a dar de alta un ISBN descatalogado.

### DD-06 — Punto único de escritura de stock + Trigger Append-Only en 4.ª migración
- **Decisión**: Centralizar toda modificación de `libro.stock` en un único método que simultáneamente actualiza `libro.stock` y agrega la fila correspondiente en `movimiento_stock`, respaldado en la base por un trigger PostgreSQL (`BEFORE UPDATE OR DELETE ON movimiento_stock`) instalado en la 4.ª migración manual.
- **Justificación**: Garantiza en todo momento el invariante `libro.stock == SUM(movimiento_stock.cantidad)` (RN-11 y RN-12).

---

## Supuestos inferidos

### SU-01 — Ejercicios 9 y 10 ya resueltos sobre el estado anterior del TP (Alcance SDD: Ejercicios 1 al 8)
- **Supuesto confirmado**: Los **Ejercicios 9 y 10** (Contenedor Docker con `python:3.12-alpine` y Despliegue en el VPS sobre el TP de los capítulos 1 a 4) **ya fueron realizados antes de iniciar el flujo SDD**. Por lo tanto, este repositorio y todos los `changes` de `CHANGES.md` se enfocan exclusivamente en implementar los **Ejercicios 1 al 8** (correspondientes a la carpeta `parcial/` de la entrega).
- **Origen**: Confirmación explícita del usuario y página 24 de `doc/Parcial_Cap1a6_Consigna.pdf`.
- **Impacto en `CHANGES.md`**: Ningún *change* del roadmap incluirá tareas de Docker ni de despliegue en el VPS.

### SU-02 — `seed.py` en la raíz del proyecto
- **Supuesto**: En `parcial/`, el script de carga inicial se ubica o invoca como `python seed.py` desde la raíz (página 8 y página 21 de la consigna: *"Antes de cada archivo se corre `python seed.py`"*), pudiendo mantener un alias en `app/seed.py` por compatibilidad.
- **Origen**: Tabla de *Estructura obligatoria del proyecto* (página 8) y sección *Casos de prueba mínimos* (página 21).
