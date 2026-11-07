# Spec Delta

## Purpose

Carga el estado inicial del parcial en la base de datos y provee la evidencia y los casos de prueba que validan el cumplimiento de las reglas de negocio implementadas en los changes C-01 a C-07. Este spec cubre el cambio C-08 del camino crítico.

## Added Requirements

### Requirement: script seed.py vacía tablas en orden correcto

El sistema SHALL vaciar las tablas en el orden inverso de dependencias foreign key antes de cargar los datos iniciales, para evitar violaciones de restricciones. El orden SHALL ser: `evento_seguridad`, `movimiento_stock`, `venta`, `cliente`, `libro`, `autoria`, `autor`, `genero`, `editorial`, `asignacion_rol`, `usuario`.

### Requirement: seed.py carga 5 usuarios con roles

El sistema SHALL cargar 5 usuarios con sus respectivas asignaciones de rol:
- `admin@example.com` con rol `ADMIN`
- `admin2@example.com` con rol `ADMIN`
- `vendedor@example.com` con rol `VENDEDOR`
- `ana@example.com` con rol `CLIENTE`
- `nuevo@example.com` con rol `VENDEDOR` y `debe_cambiar_password=True`

#### Scenario: Usuarios cargados con roles vigentes

- **WHEN** se ejecuta `python seed.py`
- **THEN** cada usuario tiene una fila en la tabla `usuario` y una fila en `asignacion_rol` con rol vigente (`revocada_en IS NULL`).

### Requirement: seed.py carga catálogo TP

El sistema SHALL cargar el catálogo del parcial:
- 3 editoriales
- 3 géneros
- 6 autores
- 5 libros con stock final `10, 5, 8, 3, 1` respectivamente

#### Scenario: Catálogo cargado correctamente

- **WHEN** se ejecuta `python seed.py`
- **THEN** las tablas `editorial`, `genero`, `autor` y `libro` contienen las filas esperadas y `libro.stock` toma los valores `10, 5, 8, 3, 1`.

### Requirement: seed.py carga 3 clientes

El sistema SHALL cargar 3 clientes:
- `Lucía`: tiene perfil de cliente (`PerfilCliente`), pero **no** tiene usuario asociado (`usuario_id = NULL`)
- `Tomás`: **no** tiene perfil de cliente y **no** tiene usuario asociado (`usuario_id = NULL`)
- `Ana`: vinculada a `ana@example.com` (`usuario_id` apunta al usuario con email `ana@example.com`, rol `CLIENTE`)

#### Scenario: Clientes cargados con relaciones correctas

- **WHEN** se ejecuta `python seed.py`
- **THEN** la tabla `cliente` tiene 3 filas. Para `Lucía`: existe `PerfilCliente` relacionado y `usuario_id` es `NULL`. Para `Tomás`: no existe `PerfilCliente` y `usuario_id` es `NULL`. Para `Ana`: `usuario_id` apunta al usuario de email `ana@example.com` (rol `CLIENTE`), y puede o no tener `PerfilCliente` asociado.

### Requirement: seed.py crea venta de ejemplo

El sistema SHALL crear una venta de ejemplo registrada por `vendedor@example.com`:
- 1 *Rayuela* (copiando `libro.precio`)
- 2 *Ficciones* (copiando `libro.precio`)
- `total = 69000.00`

#### Scenario: Venta de ejemplo creada con total correcto

- **WHEN** se ejecuta `python seed.py`
- **THEN** la tabla `venta` tiene 1 fila y `venta.total = 69000.00`. Los renglones de la venta tienen `libro.precio` copiado y `venta.precio_total` (o el campo correspondiente) suma correctamente.

### Requirement: 7 movimientos de stock consistentes

El sistema SHALL crear 7 movimientos de stock que cumplan `libro.stock == SUM(movimiento_stock.cantidad)` para los 5 libros cargados. Cada movimiento debe tener `movimiento_stock.cantidad <> 0`.

#### Scenario: Movimientos de stock consistentes

- **WHEN** se ejecuta `python seed.py`
- **THEN** `SELECT libro.stock, SUM(movimiento_stock.cantidad) FROM libro JOIN movimiento_stock ON libro.id = movimiento_stock.libro GROUP BY libro.id` devuelve el mismo valor para cada libro (stock inicial).

### Requirement: 1 evento de seguridad

El sistema SHALL insertar 1 fila en la tabla `evento_seguridad` con `actor="SISTEMA"` y `accion="Carga de los datos iniciales"`.

#### Scenario: Evento de seguridad registrado

- **WHEN** se ejecuta `python seed.py`
- **THEN** la tabla `evento_seguridad` tiene 1 fila con `actor='SISTEMA'` y `accion='Carga de los datos iniciales'`.

### Requirement: archivos .http cubren casos C-01 a C-13, C-15 y C-16

El sistema SHALL tener archivos `.http` en `test/` que cubran los casos de prueba `C-01` a `C-13`, `C-15` y `C-16` en orden, listos para ejecutarse después de `python seed.py`. Cada caso debe probar endpoints abiertos y protegidos, autenticación, autorización y validación de reglas de negocio.

### Requirement: test/solo_agregado.sql demuestra rejection por trigger

El sistema SHALL tener un script `test/solo_agregado.sql` ejecutable con `psql` que intenta un `UPDATE` y un `DELETE` sobre `movimiento_stock` y demuestra que ambos son rechazados por el disparador de la 4.ª migración. El script debe mostrar el error del trigger y no modificar filas.

### Requirement: evidencia C-14 muestra rejection del trigger

La carpeta `evidencia/` SHALL contener capturas de la ejecución de `test/solo_agregado.sql` en `psql` que demuestren que el `UPDATE` y `DELETE` sobre `movimiento_stock` son rechazados por el trigger append-only, mostrando el error correspondiente.

### Requirement: evidencia C-15 muestra consistencia de consultas

La carpeta `evidencia/` SHALL contener logs de `SQL_ECHO=true` mostrando el mismo número fijo de consultas SQL al leer una venta de 2 renglones y una de 4 renglones, validando la ausencia de problemas N+1.

## Impacted Capabilities

- `carga-inicial-datos`: script `seed.py` y estructura de datos iniciales.
- `casos-prueba-documentados`: archivos `.http` y script `solo_agregado.sql`.
- `evidencia-de-comportamiento`: capturas y logs en `evidencia/`.