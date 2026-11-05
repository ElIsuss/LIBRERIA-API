# Spec Delta

## Purpose

Configura la aplicación FastAPI (validación de variables de entorno sin secretos
en código), gestiona el ciclo de vida de los recursos de base de datos (motor
y fábrica de sesiones) y expone sondas de salud para verificar que el proceso
está vivo y que la base es accesible. Es la fundación sobre la que se construyen
todos los módulos de dominio.

## ADDED Requirements

### Requirement: Settings valida secretos obligatorios al arrancar
El sistema SHALL rechazar el arranque si faltan `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`POSTGRES_DB` o `JWT_SECRET_KEY` (cuando no se provee `DATABASE_URL` legado),
lanzando un error de validación y no iniciando la aplicación.

#### Scenario: Arranque sin secretos
- **WHEN** no se definen `POSTGRES_USER` ni `DATABASE_URL` ni `JWT_SECRET_KEY`
- **THEN** la construcción de `Settings` lanza un error de validación

#### Scenario: Arranque con DATABASE_URL legado
- **WHEN** se define `DATABASE_URL` con el resto de los campos ausentes
- **THEN** `Settings` se construye sin error usando la URL legada

### Requirement: database_url se construye desde POSTGRES_*
El sistema SHALL construir `database_url` como
`postgresql+asyncpg://<user>:<password>@<host>:<port>/<db>` a partir de las
variables `POSTGRES_*`, o usar directamente `DATABASE_URL` cuando se provea.

#### Scenario: Construcción desde POSTGRES_*
- **WHEN** se definen `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- **THEN** `settings.database_url` tiene el esquema `postgresql+asyncpg://` y
  contiene host, puerto y nombre de base

### Requirement: El motor usa el pool dimensionado por Settings
El sistema SHALL crear el motor asincrónico con `pool_size` y `max_overflow`
iguales a `settings.db_pool_size`.

#### Scenario: Pool configurado
- **WHEN** se llama a `create_engine()`
- **THEN** el motor resultante tiene el tamaño de pool configurado

### Requirement: Sesión por petición con expire_on_commit desactivado
El sistema SHALL entregar una `AsyncSession` nueva por petición mediante
`Depends(get_session)`, con `expire_on_commit=False` y `autoflush=False`, y
cerrarla automáticamente al finalizar la petición.

#### Scenario: Sesión cerrada al terminar
- **WHEN** una petición HTTP termina (éxito o error)
- **THEN** la sesión usada se cierra y no queda abierta

### Requirement: /health/live no toca la base
El sistema SHALL responder `200 OK` en `GET /health/live` sin abrir ninguna
conexión a la base de datos.

#### Scenario: Liveness sin base
- **WHEN** se llama a `GET /health/live`
- **THEN** la respuesta es `200` con `{"estado": "vivo"}` y no se emite
  ninguna consulta SQL

### Requirement: /health/ready verifica la base
El sistema SHALL ejecutar `SELECT 1` contra PostgreSQL en `GET /health/ready`,
respondiendo `200 OK` si la base es accesible y `503 Service Unavailable` si no.

#### Scenario: Base accesible
- **WHEN** la base responde a `SELECT 1`
- **THEN** la respuesta es `200` con estado "listo"

#### Scenario: Base inaccesible
- **WHEN** la base no responde
- **THEN** la respuesta es `503`

### Requirement: El lifespan cierra el motor al apagar
El sistema SHALL crear motor y fábrica de sesiones al arrancar, guardarlos en
`app.state`, y cerrar el motor con `await engine.dispose()` al apagar.

#### Scenario: Cierre ordenado
- **WHEN** la aplicación se apaga
- **THEN** se invoca `engine.dispose()` y las conexiones del pool se liberan

### Requirement: Hash ficticio precalculado una sola vez
El sistema SHALL precalcular un único hash `bcrypt` ficticio al arrancar y
guardarlo en `app.state.dummy_hash`, para usarlo en comparaciones en tiempo
constante cuando el usuario no existe.

#### Scenario: dummy_hash disponible
- **WHEN** la aplicación arranca
- **THEN** `app.state.dummy_hash` contiene un hash bcrypt válido y no se
  recalcula por petición
