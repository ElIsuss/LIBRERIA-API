# Discovery — Librería API (Parcial: Unidades 1 a 6)

**Fecha**: 2026-11-03  
**Fuente principal**: `doc/Parcial_Cap1a6_Consigna.pdf` + código base del TP (Unidades 1 a 4)  
**Relación con la Knowledge Base**: Documento de origen vinculado a [`knowledge-base/README.md`](../knowledge-base/README.md) (`01` a `10`).

---

## 1. Problema que resuelve
*(Ref: [`knowledge-base/01_vision_y_objetivos.md`](../knowledge-base/01_vision_y_objetivos.md))*

La librería de barrio ya cuenta con su API asincrónica de catálogo, clientes y ventas construida en el TP de las Unidades 1 a 4, pero carece de control de acceso por usuarios y roles, de una capa de repositorios y `Unit of Work` que garantice transacciones atómicas en operaciones de múltiples escrituras, de trazabilidad inmutable de stock y de baja lógica de libros descatalogados.

El objetivo en este repositorio (`parcial/`) es evolucionar el proyecto desde la Unidad 4 hasta la Unidad 6 implementando los **Ejercicios 1 al 8** de la consigna mediante el flujo SDD/OpenSpec.  
*(Nota: Los **Ejercicios 9 y 10** —Contenedor Docker y Despliegue en el VPS sobre el estado del TP de las Unidades 1 a 4— **ya fueron realizados previamente** antes de iniciar este flujo SDD, por lo que no forman parte de los `changes` a implementar acá).*

---

## 2. Usuarios / roles
*(Ref: [`knowledge-base/03_actores_y_roles.md`](../knowledge-base/03_actores_y_roles.md))*

- **Visitante (Anónimo)**: Consulta el catálogo público (`/libros`, `/editoriales`, `/generos` y sub-recursos de libros), verifica salud (`/health/*`) y puede auto-registrarse o iniciar sesión en `/auth/*`.
- **Cliente (`CLIENTE`)**: Se registra por la web (`POST /auth/registro`) creando atómicamente su usuario, su rol `CLIENTE` y su ficha en `cliente`. Consulta sus propias compras en `GET /mis-ventas` y el detalle de sus ventas en `GET /ventas/{id}`.
- **Vendedor (`VENDEDOR`)**: Personal de mostrador que da de alta y edita clientes y perfiles, registra ventas (`POST /ventas`) y consulta ventas globales o por cliente.
- **Administrador (`ADMIN`)**: Mantiene el catálogo (`editoriales`, `generos`, `autores`, `libros`), repone stock (`POST /libros/{id}/reponer`), da de baja lógica libros (`DELETE /libros/{id}`), consulta movimientos de stock, da de alta personal con contraseña provisoria (`POST /usuarios`), asigna/revoca roles con vigencia y audita `/eventos`.
- **Usuario con clave provisoria (`debe_cambiar_password = True`)**: Sólo puede acceder a las rutas del **Grupo Abierto** (`/auth/*` y catálogo público); recibe `403 Forbidden` en cualquier ruta del **Grupo Protegido** hasta cambiar su contraseña.

---

## 3. Casos de uso
*(Ref: [`knowledge-base/06_funcionalidades.md`](../knowledge-base/06_funcionalidades.md) y [`knowledge-base/07_flujos_principales.md`](../knowledge-base/07_flujos_principales.md))*

1. **Auto-registro atómico de cliente**: Como visitante, quiero registrarme en `POST /auth/registro` para que se creen en una sola transacción mi usuario, mi rol `CLIENTE` y mi ficha de cliente (o nada si el correo ya existe).
2. **Inicio de sesión seguro con protección de fuerza bruta**: Como usuario, quiero iniciar sesión en `POST /auth/login` recibiendo un JWT en una cookie `HttpOnly`, con bloqueo `429` tras 5 fallos en 60 s y respuesta uniforme en tiempo constante.
3. **Cambio obligatorio y voluntario de contraseña**: Como usuario autenticado, quiero cambiar mi clave en `POST /auth/cambiar-password` para desbloquear el acceso a las rutas protegidas sin tener que volver a iniciar sesión.
4. **Administración de personal, roles con vigencia y auditoría**: Como `ADMIN`, quiero crear personal con clave provisoria, asignar roles con vencimiento opcional y revocarlos con efecto inmediato en la petición siguiente, dejando rastro transaccional en `evento_seguridad`.
5. **Gestión de catálogo con baja lógica y reposición de stock**: Como `ADMIN`, quiero crear libros con `stock_inicial`, reponer stock y dar de baja lógica libros descatalogados (`204`), permitiendo reutilizar su ISBN sin afectar las ventas históricas.
6. **Registro atómico de ventas con descuento de stock**: Como `VENDEDOR` o `ADMIN`, quiero registrar una venta con sus renglones descontando stock y grabando los movimientos en una única transacción (`UnitOfWork`), revirtiendo todo si algún libro no alcanza.

---

## 4. Soluciones / Referencias comparadas

| Aspecto | Estado TP Base (Unidades 1 a 4) | Evolución Parcial (Unidades 1 a 6 — Ejercicios 1 a 8) |
|---|---|---|
| **Arquitectura de módulos** | `Router → Service → AsyncSession → Model` | `Router → Service → UnitOfWork → Repository → Model` |
| **Configuración** | `os.environ` + `python-dotenv` (`DATABASE_URL` directa) | `Settings(BaseSettings)` con `pydantic-settings` y `@computed_field` |
| **Autenticación y Permisos** | Sin autenticación (todas las rutas públicas) | `bcrypt` (`to_thread` + semáforo) + JWT en cookie `HttpOnly` + roles vigentes en BD |
| **Stock de libros** | Editable libremente por `PATCH /libros/{id}` | Punto único de escritura vía `movimiento_stock` (trigger append-only) |
| **Baja de libros e ISBN** | Sin baja; `isbn` con `UNIQUE` simple | Baja lógica (`borrado_en`) + índice único parcial `WHERE borrado_en IS NULL` |
| **Paginación** | Parámetros `limit` y `offset` devolviendo `list[T]` | Parámetros `page` y `size` devolviendo `{items, total, page, size, pages}` |

---

## 5. Funcionalidades necesarias (Alcance de `CHANGES.md`: Ejercicios 1 al 8)
*(Ref: [`knowledge-base/06_funcionalidades.md`](../knowledge-base/06_funcionalidades.md))*

- **Ejercicio 1**: `Settings` con `pydantic-settings` y `@computed_field`, `lifespan` con cálculo único de hash ficticio y pool configurable, módulo `health` (`/health/live` 200 y `/health/ready` 200/503) y estructura de dos grupos de rutas en `main.py`.
- **Ejercicio 2**: Nuevos modelos (`Usuario`, `AsignacionRol`, `IntentoAcceso`, `EventoSeguridad`, `MovimientoStock`), cambios en `Cliente` (`usuario_id`) y `Libro` (`borrado_en` + índice parcial de ISBN), 3.ª migración autogenerada y 4.ª migración manual con el trigger append-only sobre `movimiento_stock`.
- **Ejercicio 3**: Contratos de entrada con `extra="forbid"`, envoltorio de paginación `{items, total, page, size, pages}` (`app/core/paginacion.py`) y actualización de CRUDs existentes.
- **Ejercicio 4**: Seguridad en `app/core/security.py` (`bcrypt` con `to_thread`, semáforo y tope de 72 bytes UTF-8; JWT en cookie `access_token` `HttpOnly`), endpoints `/auth/registro`, `/auth/login`, `/auth/logout`, `/auth/yo` y `/auth/cambiar-password`.
- **Ejercicio 5**: Dependencias `get_usuario_actual` (`401`), control de cambio obligatorio de contraseña (`403` en grupo protegido) y `requiere_rol` (`403` consultando `asignacion_rol` en cada request); endpoints `/usuarios`, `/usuarios/{id}/roles`, `DELETE /usuarios/{id}/roles/{rol}`, `/eventos`, `/mis-ventas` y control de dueño en `GET /ventas/{id}`.
- **Ejercicio 6**: `BaseRepository[T]`, `SoftDeleteRepository[T]`, `UnitOfWork` base y por módulo compartiendo sesión con auth; refactorización de todos los módulos a repositorios + UoW; punto único de escritura de stock en alta de libro, reposición (`POST /libros/{id}/reponer`) y venta (`POST /ventas`).
- **Ejercicio 7**: Garantía de sólo agregado en `movimiento_stock` por disparador en PostgreSQL y registro de `intento_acceso` en sesión/transacción independiente documentada.
- **Ejercicio 8**: Carga anticipada declarada en los repositorios sin N+1 (incluso con libros dados de baja lógica en ventas históricas), handlers 100 % asincrónicos, aviso de venta con `BackgroundTasks` visible en la consola normal de Uvicorn, `seed.py` actualizado y casos de prueba `C-01` a `C-16` + `test/solo_agregado.sql`.

---

## 6. Funcionalidades ya realizadas fuera de este flujo o fuera de alcance

- **Ya realizadas previamente (sobre el TP de las Unidades 1 a 4)**:
  - **Ejercicio 9 (Contenedor: la imagen)** y **Ejercicio 10 (Despliegue en el VPS)**: Se resolvieron antes de iniciar el flujo SDD sobre el estado anterior del TP (capítulos 1 a 4), por lo que quedan fuera de los `changes` a implementar en este proyecto.
- **Fuera de alcance por consigna**:
  - Control de concurrencia por bloqueo de filas en ventas simultáneas (Capítulo 7).
  - Colas de tareas con Redis (Capítulo 8).

---

## 7. Reglas de negocio
*(Ref: [`knowledge-base/05_reglas_de_negocio.md`](../knowledge-base/05_reglas_de_negocio.md))*

- **RN-01**: Correos de usuario/cliente y nombres de editorial/género únicos; ISBN único entre libros vigentes (`WHERE borrado_en IS NULL`); `409` con mensaje propio.
- **RN-02**: Auto-registro crea `usuario`, rol `CLIENTE` y `cliente` en un solo `UnitOfWork` (`409` si el correo ya existe, sin apropiarse de la ficha).
- **RN-03**: A lo sumo una asignación abierta por rol (`WHERE revocada_en IS NULL`; `409`).
- **RN-04**: Los permisos se deciden consultando `asignacion_rol` en la base en cada petición (los roles del token son informativos).
- **RN-05**: Un `ADMIN` no puede revocarse su propio `ADMIN` ni dejar al sistema sin administradores vigentes (`409`).
- **RN-06**: Con `debe_cambiar_password = True`, sólo se permiten las rutas de `/auth` y las públicas (`403` en el grupo protegido).
- **RN-07**: Tras 5 intentos fallidos con el mismo correo e IP en 60 s, el login responde `429` con `Retry-After` sin ejecutar `bcrypt`. Un login exitoso reinicia la cuenta.
- **RN-08**: El login responde igual y tarda lo mismo exista o no el correo (verificación contra hash ficticio).
- **RN-09**: La venta nace con sus renglones, copia el precio del libro y calcula el total en el servidor; no tiene `PATCH`.
- **RN-10**: Registrar una venta descuenta stock y crea un movimiento por renglón en un solo `UnitOfWork` (`409` y rollback total si no alcanza).
- **RN-11**: El stock sólo cambia por movimientos (alta con `stock_inicial`, reposición y venta; no se edita por `PATCH`). Siempre `libro.stock == SUM(movimiento_stock.cantidad)`.
- **RN-12**: `movimiento_stock` es de sólo agregado, protegido por disparador en PostgreSQL.
- **RN-13**: Un libro dado de baja lógica (`borrado_en`) no aparece en catálogo ni se vende/repone (`409`), su ISBN queda libre, pero las ventas viejas siguen mostrándolo.
- **RN-14**: Un cliente autenticado sólo ve sus propias ventas (`/mis-ventas` y comprobación de dueño en `/ventas/{id}` → `403`).
- **RN-15**: Ningún error filtra texto interno de PostgreSQL y ninguna entrada inválida termina en `500`.
- **RN-16**: Cada alta de personal, cambio de rol y cambio de contraseña deja una fila en `evento_seguridad` en el mismo `UnitOfWork`.

---

## 8. Integraciones
*(Ref: [`knowledge-base/02_descripcion_general.md`](../knowledge-base/02_descripcion_general.md))*

- **PostgreSQL 16+** mediante `SQLAlchemy 2.0 (asyncio)` y driver `asyncpg`.

---

## 9. Restricciones
*(Ref: [`knowledge-base/08_arquitectura_propuesta.md`](../knowledge-base/08_arquitectura_propuesta.md))*

- **Esquema**: Exclusivamente con Alembic (prohibido `create_all`). `alembic upgrade head`, `alembic downgrade base` y `alembic upgrade head` deben funcionar de punta a punta.
- **Secretos y Portabilidad**: Cero contraseñas, claves JWT o rutas absolutas en el código o en `alembic.ini`; sin valores por defecto para secretos en `Settings`.
- **Transacciones y Sesiones**: Ningún repositorio ejecuta `commit()`; ningún servicio construye su `UnitOfWork`; el `UnitOfWork` no cierra la sesión; las dependencias de autenticación y el `UnitOfWork` comparten la misma sesión de la petición.
- **Asincronía y N+1**: Prohibida la carga perezosa (toda relación se precarga en el repositorio); `bcrypt` corre siempre en `asyncio.to_thread` con semáforo y antes de abrir la transacción.

---

## 10. Riesgos
*(Ref: [`knowledge-base/09_decisiones_y_supuestos.md`](../knowledge-base/09_decisiones_y_supuestos.md))*

- **Riesgo de doble conexión por petición**: Si `get_usuario_actual` y el `UnitOfWork` no comparten la misma dependencia `Depends(get_session)`, cada request autenticado tomaría dos conexiones del pool.
- **Riesgo de pérdida de conteo de intentos fallidos**: Si `intento_acceso` se escribiera en el `UnitOfWork` de la petición, el fallo del login revertiría la fila y nunca se alcanzaría el límite de `RN-07` (`429`).
- **Riesgo de error `500` con contraseñas largas en `bcrypt >= 5`**: `bcrypt` lanza `ValueError` si recibe más de 72 bytes UTF-8; debe validarse en `len(v.encode("utf-8")) <= 72` en todos los schemas de entrada (`422`).
- **Riesgo de invisibilidad del log de `BackgroundTasks`**: El logger de un módulo propio en nivel `INFO` no se imprime por defecto en la consola estándar de Uvicorn a menos que se configure o se emita por el logger de `uvicorn.info` / configuración de logging en `main.py` (Ejercicio 8).

---

## 11. Preguntas abiertas / Notas de cierre
*(Ref: [`knowledge-base/10_preguntas_abiertas.md`](../knowledge-base/10_preguntas_abiertas.md))*

- **Alcance de `CHANGES.md` confirmado por el equipo**: Los *changes* del flujo SDD abarcan únicamente los **Ejercicios 1 al 8** (evolución del proyecto `parcial/`). Los **Ejercicios 9 y 10** (Docker y despliegue en VPS sobre el TP 1-4) ya fueron completados antes de iniciar este flujo.
