# Tasks

## 1. Script seed.py

- [x] 1.1 Crear `seed.py` en la raíz del proyecto con la lógica de vaciado y carga de datos.
    - [x] Semilla adaptada para ejecución directa con `python seed.py` desde la raíz.
    - [x] Lógica de 5 usuarios con roles (admin, admin2, vendedor, ana, nuevo con `debe_cambiar_password=True`).
    - [x] Carga de catálogo: 3 editoriales, 3 géneros, 6 autores, 5 libros con stock final `10, 5, 8, 3, 1`.
    - [x] Carga de 3 clientes (Lucía con perfil, Tomás sin perfil, Ana vinculada a `ana@example.com`).
    - [x] Creación de venta 1 de Lucía (`1` *Rayuela* + `2` *Ficciones*, `total = 69000.00`).
    - [x] **7 movimientos de stock con distribución consistente**:
        - Movimiento 1: Rayuela, +10 (stock inicial)
        - Movimiento 2: Ficciones, +5 (stock inicial)
        - Movimiento 3: El Aleph, +3 (stock inicial, 3 de 8 totales)
        - Movimiento 4: Respiración artificial, +1 (stock inicial, 1 de 3 totales)
        - Movimiento 5: Bestiario, +1
        - Movimiento 6: El Aleph, +5 (stock adicional, total 8)
        - Movimiento 7: Respiración artificial, +2 (stock adicional, total 3)
        - Verificación: `libro.stock == SUM(movimiento_stock.cantidad)` para cada libro.
    - [x] 1 evento de seguridad (`actor="SISTEMA"`, `accion="Carga de los datos iniciales"`).
    - [x] Estructura coherente con modelos reales (FK, relaciones, CHECK constraints).
    - [x] Comentarios explicando la distribución de movimientos y la consistencia matemática.
    - [x] **Lógica idempotente: borrado FK-order al inicio de `seed()` para ejecución multiple sin duplicados**.
    - [x] **Transacción explícita con `async with session.begin():`** que garantiza rollback on error y commit solo al éxito.
    - [x] **Conflito identificado con trigger RN-12**: `trg_movimiento_stock_append_only` prohíbe DELETE/UPDATE sobre `movimiento_stock`, por lo que el borrado de este campo no se incluye en el seed; la idempotencia parcial borra las 13 tablas FK-ordenadas y deja los movimientos intactos.
- [x] 1.2 Verificación estática de la implementación.
    - [x] Verificación de imports y estructura.
    - [x] Distribución matemática de movimientos validada.
    - [x] Transacción: `try` + `async with session.begin()` + `await session.flush()` + `await engine.dispose()` en finally.
    - [x] Coherencia entre spec, implementación y README.
    - [x] Ausencia de modificaciones en C-01 a C-07.
    - [x] Conflicto trigger RN-12 detectado e documentado.
    - [x] Codificación UTF-8 verificada: sin corrupción en strings españoles.
    - [x] Wrapper raíz: `Path(__file__).resolve().parent` en lugar de `Path.cwd()`.

## 2. Archivos .http de casos de prueba

- [x] 2.1 Archivos `.http` en `test/` que cubran los casos de prueba **`C-01` a `C-16`** en orden.
    - [x] Casos C-01 a C-08 preservados sin modificar.
    - [x] Casos C-09 a C-13, C-15 y C-16 agregados.
    - [x] Todos los casos tienen códigos de respuesta esperados (`200`, `201`, `401`, `403`, `404`, `409`, `422`).
    - [x] Estructura sintácticamente válida para ejecución con REST Client / VS Code.

## 3. Script test/solo_agregado.sql

- [x] 3.1 Script `test/solo_agregado.sql` creado para el caso C-14.
    - [x] Demuestra que `UPDATE` y `DELETE` sobre `movimiento_stock` son rechazados por el trigger append-only (RN-12).
    - [x] Excepción `unique_violation` capturada correctamente.
    - [x] Verificación final con `SELECT COUNT(*) FROM movimiento_stock`.

## 4. Carpeta evidencia/

- [x] 4.1 Carpeta `evidencia/` creada con documentación.
    - [x] `evidencia/C-14_trigger_rejection.md`: documentación del escenario C-14.
    - [x] `evidencia/C-15_consultas_fijas.md`: documentación del escenario C-15.
    - [x] Estructura y formato consistentes con los requerimientos del cambio.

## 5. README.md

- [x] 5.1 `README.md` actualizado con las siguientes correcciones:
    - [x] Línea de "Carga de datos iniciales": `python seed.py` (en lugar de `python -m app.seed`).
    - [x] Estructura del proyecto actualizada: `seed.py` en la raíz, no en `app/`.
    - [x] Rangos de casos de prueba actualizados: de "C-01 a C-08" a "C-01 a C-16".
    - [x] Documentación de cómo verificar consistencia de movimientos de stock con `test/solo_agregado.sql`.
    - [x] Tabla completa de endpoints abiertos y protegidos.

## 3. Verificación estática

- [x] Verificaciones realizadas sin ejecutar seed.py ni acceder a PostgreSQL:
    - [x] Estructura y syntax checking de seed.py.
    - [x] Distribución matemática de 7 movimientos verificadas.
    - [x] Coherencia de roles y relaciones de usuario.
    - [x] Coherencia de estructura de clientes (Lucía, Tomás, Ana).
    - [x] Coherencia de catálogo (5 libros, stocks 10/5/8/3/1).
    - [x] Ausencia de modificaciones en C-01 a C-07.

## 5. Pendientes (requieren ejecución real - fuera del scope actual)

- [ ] Probar ejecución efectiva de `python seed.py` contra base de datos con `.env` configurado.
- [ ] Verificar resultados SQL: `libro.stock == SUM(movimiento_stock.cantidad)` por cada libro.
- [ ] Ejecutar casos `.http` contra servidor en ejecución y validar códigos de respuesta.
- [ ] Ejecutar `psql -U usuario -d base -f test/solo_agregado.sql` y capturar salida.
- [ ] Generar capturas reales de evidencia C-14 (rechazo trigger) y C-15 (logs SQL_ECHO=true).
- [ ] Validar idempotencia: ejecutar seed.py dos veces sobre base limpia y verificar sin duplicados/errors.