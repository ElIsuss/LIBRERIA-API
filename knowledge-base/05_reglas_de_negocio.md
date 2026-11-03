# Reglas de Negocio

Las reglas de negocio del parcial (`RN-01` a `RN-16`) reemplazan y amplían las del TP de los capítulos 1 a 4. Siguen vigentes además los `CHECK` de precio (`precio > 0`) y stock (`stock >= 0`) del libro y la búsqueda por título con parámetros ligados.

## Dominio: Identidad, Unicidad y Catálogo

- **RN-01 — Unicidad de correos, nombres e ISBN vigente**:
  - **Enunciado**: El correo de un usuario (`usuario.email`), el de un cliente (`cliente.email`), el nombre de una editorial (`editorial.nombre`) y el de un género (`genero.nombre`) son únicos. El ISBN de un libro (`libro.isbn`) es único **entre los que no están dados de baja** (`WHERE borrado_en IS NULL`).
  - **Garante esperado**: `UNIQUE` e índice único parcial en PostgreSQL; traducción de `IntegrityError` a `409 Conflict` con mensaje propio (nunca consulta previa con `if`).
- **RN-13 — Baja lógica de libros**:
  - **Enunciado**: Un libro dado de baja (`borrado_en IS NOT NULL`) deja de aparecer en el catálogo y no se puede vender ni reponer, pero sus datos se conservan y las ventas anteriores lo siguen mostrando. Su ISBN puede volver a usarse en un libro nuevo.
  - **Garante esperado**: `SoftDeleteRepository` para lecturas de catálogo, verificación en venta/reposición (`404`/`409` según corresponda) e índice único parcial `WHERE borrado_en IS NULL`.

## Dominio: Autenticación, Usuarios y Roles

- **RN-02 — Auto-registro atómico de clientes**:
  - **Enunciado**: El auto-registro (`POST /auth/registro`) crea el `usuario`, su asignación de rol `CLIENTE` y su ficha en `cliente`: o quedan las tres filas, o ninguna. Si ya existe un cliente o usuario con ese correo, el registro responde `409 Conflict` y **no se apropia** de esa ficha.
  - **Garante esperado**: Un único bloque `UnitOfWork` e integridad en la base de datos (`UNIQUE` en `usuario.email` y `cliente.email`).
- **RN-03 — Asignación única abierta por rol**:
  - **Enunciado**: Un usuario tiene a lo sumo una asignación abierta (`revocada_en IS NULL`) por cada rol (`ADMIN`, `VENDEDOR`, `CLIENTE`). Reasignar un rol cuyo vencimiento (`vence_en`) ya pasó cierra primero la fila anterior (escribiendo `revocada_en`) y abre una nueva en la misma transacción.
  - **Garante esperado**: Índice único parcial `(usuario_id, rol) WHERE revocada_en IS NULL`; `409 Conflict` si el rol ya está vigente.
- **RN-04 — Autorización evaluada en la base en cada petición**:
  - **Enunciado**: Los permisos se deciden consultando los roles vigentes en `asignacion_rol` en cada petición. Los roles que trae el token JWT son únicamente informativos.
  - **Garante esperado**: Dependencia `requiere_rol` que consulta `asignacion_rol` usando la misma sesión del request (`403 Forbidden` si no posee el rol vigente).
- **RN-05 — Autoprotección de administradores**:
  - **Enunciado**: Un administrador no puede revocarse su propio rol `ADMIN`, y el sistema nunca puede quedar sin administradores vigentes.
  - **Garante esperado**: Comprobación en el servicio antes de revocar (`409 Conflict`).
- **RN-06 — Bloqueo por cambio de contraseña pendiente**:
  - **Enunciado**: Mientras un usuario tenga `debe_cambiar_password = True`, sólo puede usar las rutas de `/auth` y las que no piden sesión.
  - **Garante esperado**: Dos grupos de rutas en `main.py`; el grupo protegido monta una sola vez la dependencia que devuelve `403 Forbidden` si `debe_cambiar_password` es verdadero.
- **RN-07 — Límite de intentos de login (Rate Limiting)**:
  - **Enunciado**: Después de 5 intentos fallidos con el mismo correo desde la misma dirección IP en los últimos 60 segundos, `POST /auth/login` responde `429 Too Many Requests` con la cabecera `Retry-After` **sin verificar la contraseña** (sin ejecutar `bcrypt`). Un login exitoso reinicia la cuenta (los fallos anteriores siguen en `intento_acceso`, pero dejan de contar porque se cuenta desde el último éxito o dentro de la ventana de 60 s posterior al último éxito).
  - **Garante esperado**: Conteo sobre `intento_acceso` como primer paso del login; cada intento se graba en una sesión y transacción propia que siempre hace `commit`.
- **RN-08 — Respuesta y tiempo constante en login**:
  - **Enunciado**: El login responde con el mismo cuerpo/código (`401`) y tarda lo mismo exista o no el correo en la base.
  - **Garante esperado**: Cuando el correo no existe, se ejecuta igualmente `bcrypt.checkpw` contra un **hash ficticio** calculado una sola vez en el `lifespan`.
- **RN-14 — Acceso a lo propio (`/mis-ventas` y detalle de venta)**:
  - **Enunciado**: Lo propio sólo pide estar autenticado: un cliente ve sus propias ventas en `GET /mis-ventas` y en `GET /ventas/{id}`, y ninguna otra (`403 Forbidden` si intenta ver la venta de otro cliente sin ser `VENDEDOR` ni `ADMIN`).
  - **Garante esperado**: Ruta `/mis-ventas` filtrada por el cliente del usuario autenticado y comprobación de dueño o personal en el servicio de `GET /ventas/{id}`.
- **RN-16 — Auditoría transaccional en `evento_seguridad`**:
  - **Enunciado**: Cada alta de personal (`POST /usuarios`), cambio de rol (asignación `POST /usuarios/{id}/roles` o revocación `DELETE /usuarios/{id}/roles/{rol}`) y cambio de contraseña (`POST /auth/cambiar-password`) deja una fila en `evento_seguridad` **en la misma transacción** que el cambio.
  - **Garante esperado**: Un único `UnitOfWork` por operación.

## Dominio: Ventas e Inventario (Stock)

- **RN-09 — Inmutabilidad y cálculo servidor de ventas**:
  - **Enunciado**: Una venta nace con sus renglones (al menos uno, sin libros repetidos), con el `precio_unitario` copiado del libro en la base y el `total` calculado por el servidor. Las ventas no se modifican (no hay `PATCH`).
  - **Garante esperado**: Validación en `VentaCreate` (`422`), cálculo en el servicio y ausencia de endpoint de edición.
- **RN-10 — Venta atómica con descuento y movimiento de stock**:
  - **Enunciado**: Registrar una venta descuenta el stock de cada libro y deja un `movimiento_stock` (con cantidad negativa y `venta_id`) por cada renglón. Si el stock de algún libro no alcanza (o el libro/cliente no existe o el libro está dado de baja), **no queda ninguna de esas escrituras** y se responde `409 Conflict`.
  - **Garante esperado**: Un único `UnitOfWork` en el servicio de ventas (`rollback` automático ante error).
- **RN-11 — Punto único de escritura de stock**:
  - **Enunciado**: El stock de un libro sólo cambia a través de movimientos: el alta con `stock_inicial` (crea el libro y su movimiento `"Stock inicial"`), la reposición (`POST /libros/{id}/reponer`) y la venta (`POST /ventas`). No se edita por `PATCH /libros/{id}` (`extra="forbid"` rechaza `stock` con `422`). Siempre se cumple que `libro.stock == SUM(movimiento_stock.cantidad)`.
  - **Garante esperado**: Método único de ajuste de stock en el repositorio/dominio de libros + `extra="forbid"` en `LibroUpdate`.
- **RN-12 — Inmutabilidad de `movimiento_stock` (Sólo agregado)**:
  - **Enunciado**: La tabla `movimiento_stock` es de sólo agregado (*append-only*): nadie puede modificar (`UPDATE`) ni borrar (`DELETE`) sus filas.
  - **Garante esperado**: Disparador (`TRIGGER`) en PostgreSQL instalado por la 4.ª migración de Alembic.

## Dominio: Excepciones globales y Seguridad de Contratos

- **RN-15 — Traducción de errores y ausencia de 500 por entrada inválida**:
  - **Enunciado**: Ningún error devuelve al cliente texto interno de PostgreSQL o trazas de SQLAlchemy. Ninguna entrada inválida termina en un `500 Internal Server Error` (incluyendo contraseñas de más de 72 bytes UTF-8 o páginas fuera de rango).
  - **Garante esperado**: Validadores en contratos Pydantic (`422`) y captura/traducción de `IntegrityError` (`409`).
