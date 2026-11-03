# Visión y Objetivos

## Propósito del sistema
**Librería API** es el sistema backend asincrónico para la gestión de catálogo editorial, clientes, ventas, inventario y control de acceso de una librería de barrio, desarrollado en el marco de la materia **Programación III** (Unidades 1 a 6: *Del objeto a la transacción*).

El proyecto parte de la base construida en el Trabajo Práctico de las Unidades 1 a 4 (catálogo, clientes y ventas sobre FastAPI + SQLModel + PostgreSQL + Alembic) y evoluciona hacia una arquitectura transaccional en capas (`Router → Service → UoW → Repository → Model`) con autenticación por cookies `HttpOnly`, autorización por roles vigentes en base de datos, auditoría de eventos de seguridad, control de inventario de sólo agregado (`movimiento_stock`) y baja lógica de libros. En paralelo, contempla el empaquetado en contenedor Docker y despliegue en VPS de la versión base (Unidades 1 a 4).

## Objetivos por actor

| Actor | Objetivo principal | Objetivos secundarios |
|---|---|---|
| **Administrador (`ADMIN`)** | Mantener el catálogo completo, reponer stock y administrar al personal y sus roles. | Dar de alta personal con contraseña provisoria, asignar/revocar roles con vigencia, consultar historial de movimientos de stock y eventos de seguridad, dar de baja lógica libros descatalogados. |
| **Vendedor (`VENDEDOR`)** | Registrar ventas en mostrador y gestionar la cartera de clientes. | Dar de alta y actualizar clientes y sus perfiles, consultar ventas globales o por cliente. |
| **Cliente (`CLIENTE`)** | Registrarse en la web y consultar su historial propio de compras. | Explorar el catálogo público, iniciar sesión, cambiar contraseña y consultar `/mis-ventas` y el detalle de sus propias compras. |
| **Visitante (Público)** | Explorar el catálogo de la librería sin necesidad de iniciar sesión. | Consultar libros vigentes (con filtros y paginación), editoriales, géneros y libros por editorial/género/autor. |
| **Auditor / Sistema (`SISTEMA`)** | Garantizar la trazabilidad e inmutabilidad de eventos críticos y movimientos de stock. | Registrar intentos de acceso (exitosos y fallidos), eventos de seguridad transaccionales y movimientos de stock protegidos por disparador en PostgreSQL. |

## Alcance v2.0 (Parcial — Unidades 1 a 6)
- **Reorganización en capas estrictas**: `Router → Service → UnitOfWork → Repository → Model` en todos los módulos (`usuarios`, `editoriales`, `generos`, `autores`, `libros`, `clientes`, `ventas`), más el módulo `health` (`router.py`).
- **Configuración segura con `pydantic-settings`**: Lectura de variables `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT` (con `@computed_field` para `database_url`), clave de firma JWT y costo de `bcrypt` sin secretos por defecto en el código.
- **Evolución del esquema con Alembic**:
  - 3.ª migración (`--autogenerate`, leída y comentada): tablas `usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad`, `movimiento_stock` y cambios en `cliente` (`usuario_id`) y `libro` (`borrado_en` e índice único parcial de ISBN).
  - 4.ª migración (escrita a mano): disparador (`TRIGGER`) en PostgreSQL que impide `UPDATE` y `DELETE` sobre `movimiento_stock` (RN-12).
- **Autenticación robusta (`/auth`)**:
  - Contraseñas hasheadas con `bcrypt` fuera del bucle de eventos (`asyncio.to_thread`) bajo un `asyncio.Semaphore`, con validación de límite de 72 bytes UTF-8.
  - Protección contra fuerza bruta sobre `intento_acceso` (máximo 5 fallos en 60 segundos por correo e IP → `429 Too Many Requests` con `Retry-After`), persistida en sesión/transacción independiente.
  - Tiempo y mensaje de respuesta uniforme ante correos inexistentes usando un hash ficticio precalculado en el `lifespan` (RN-08).
  - Token JWT firmado (`PyJWT`) con `sub`, `exp` y roles informativos, transportado exclusivamente en cookie `access_token` (`HttpOnly`, `SameSite=Lax`, `Max-Age`, `Secure` configurable).
- **Autorización en tiempo real y cambio obligatorio de contraseña**:
  - Verificación de roles vigentes (`ADMIN`, `VENDEDOR`, `CLIENTE`) consultando `asignacion_rol` en la base de datos en cada petición (RN-04).
  - Separación en dos grupos de rutas en `main.py`: grupo abierto y grupo protegido (que exige no tener `debe_cambiar_password=True`, RN-06).
  - Regla de autoprotección de administradores (RN-05) y registro de eventos de seguridad (RN-16).
- **Gestión transaccional de stock y ventas**:
  - Punto único de escritura de stock mediante `movimiento_stock` (alta con `stock_inicial`, reposición y venta, RN-11).
  - Baja lógica de libros (`borrado_en`) con índice único parcial de ISBN entre vigentes (RN-01, RN-13).
  - Registro de venta atómico en un único `UnitOfWork` (venta + renglones + descuento de stock + movimientos, RN-10) y aviso en segundo plano con `BackgroundTasks`.
- **Contratos estrictos y paginación por envoltorio**:
  - `extra="forbid"` en todos los DTOs de entrada.
  - Envoltorio `{items, total, page, size, pages}` en los listados paginados (`page >= 1`, `size` 1..100, `422` si `page > pages`).
- **Despliegue en contenedor (Ejercicios 9 y 10 — YA REALIZADO)**:
  - El empaquetado del TP de los capítulos 1 a 4 en una imagen Docker basada en `python:3.12-alpine` y su despliegue en el VPS se realizaron sobre el estado anterior del TP antes de iniciar el flujo SDD, por lo que **no forman parte de los `changes` a implementar ahora** (el alcance de cambios SDD abarca del **Ejercicio 1 al 8**).

## Fuera de alcance (para los changes de este flujo SDD)
- **Ejercicios 9 y 10 (Contenedor Docker y Despliegue en VPS del TP 1-4)**: Ya completados previamente sobre la versión de las Unidades 1 a 4 antes de iniciar el flujo SDD.
- **Control de concurrencia pesimista/optimista sobre stock (Capítulo 7)**: No se evalúa `SELECT ... FOR UPDATE` ni aislamiento serializable para evitar actualizaciones perdidas entre dos ventas simultáneas del último ejemplar.
- **Colas de tareas distribuidas con Redis / Celery (Capítulo 8)**: El aviso de comprobante de venta se mantiene con `BackgroundTasks` de FastAPI en el mismo proceso.
- **Interfaz gráfica (Frontend UI)**: El proyecto es exclusivamente una API REST documentada con OpenAPI y probada mediante archivos `.http` (REST Client) y scripts SQL.

## Métricas de éxito (Criterios de evaluación)
1. **Esquema y migraciones (10%)**: `alembic upgrade head`, `alembic downgrade base` y `alembic upgrade head` funcionan sin errores sobre una base vacía; el trigger rechaza `UPDATE`/`DELETE` en `movimiento_stock` (Caso C-14).
2. **Proyecto y ciclo de vida (6%)**: `Settings` sin secretos por defecto; `/health/live` (200) y `/health/ready` (200 / 503 si la base no responde).
3. **Contratos y CRUD (8%)**: `extra="forbid"`, envoltorio `{items, total, page, size, pages}`, `204` en baja lógica, nunca `500` ante entradas inválidas (Caso C-16).
4. **Autenticación y Autorización (26%)**: Casos C-01 a C-09 superados (`HttpOnly` cookie, 401 vs 403, rate limit 429 en el 6.º intento, revocación inmediata en sesión abierta, autoprotección ADMIN, cambio obligatorio de contraseña).
5. **Repositorios, UoW e Integridad (26%)**: Casos C-10 a C-14 superados (atomicidad ante falta de stock, invariante `libro.stock == SUM(movimiento_stock.cantidad)`, baja lógica y reutilización de ISBN).
6. **Lecturas sin N+1 y Asincronía (6%)**: Caso C-15 demuestra igual cantidad fija de consultas SQL al leer una venta con 2 y con 4 renglones; log de `BackgroundTasks` visible en consola.
7. **Contenedor y Despliegue en VPS (18%)**: Casos D-01 a D-08 verificados en `despliegue/` sobre el TP 1-4.
