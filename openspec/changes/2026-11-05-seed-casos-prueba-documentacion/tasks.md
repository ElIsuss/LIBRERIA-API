# Tasks

## 1. Script seed.py

- [ ] 1.1 Crear `seed.py` en la raíz del proyecto con la lógica de vaciado y carga de datos.
    - Borrar tablas en orden: `evento_seguridad`, `movimiento_stock`, `renglon_venta`, `venta`, `cliente`, `libro`, `autoria`, `autor`, `genero`, ` editorial`, `asignacion_rol`, `usuario`.
    - Cargar 5 usuarios con sus roles (admin, admin2, vendedor, ana, nuevo con `debe_cambiar_password=True`).
    - Cargar catálogo: 3 editoriales, 3 géneros, 6 autores, 5 libros con stock final `10, 5, 8, 3, 1`.
    - Cargar 3 clientes (Lucía con perfil, Tomás sin perfil, Ana vinculada a `ana@example.com`).
    - Crear venta 1 de Lucía por `vendedor@example.com`: `1` *Rayuela* + `2` *Ficciones*, `total = 69000.00`.
    - Crear 7 movimientos de stock que cumplan `libro.stock == SUM(movimiento_stock.cantidad)`.
    - Crear 1 evento de seguridad (`actor="SISTEMA"`, `accion="Carga de los datos iniciales"`).
    - Verificación: `python seed.py` ejecuta sin errores y los datos persisten correctamente.

- [ ] 1.2 Probar la ejecución de `seed.py` con un `.env` completo y validar que los 5 usuarios, 5 libros, 3 clientes y 1 venta se insertan correctamente.

## 2. Archivos .http de casos de prueba

- [ ] 2.1 Crear/actualizar archivos `.http` en `test/` que cubran los casos de prueba **`C-01` a `C-13`, `C-15` y `C-16`** en orden.
    - Cada archivo debe tener un caso de prueba único y numerado.
    - Cubrir endpoints abiertos y protegidos: autenticación, listado de recursos, creación, lectura, actualización, borrado.
    - Verificar códigos de respuesta esperados (`200`, `201`, `401`, `403`, `404`, `409`, `422`).
    - Verificación: todos los archivos `.http` son sintácticamente válidos y pueden ejecutarse con `httpie` o VS Code.

- [ ] 2.2 Probar la ejecución de los `.http` archivos después de `python seed.py` y verificar que los casos esperados pasan.

## 3. Script test/solo_agregado.sql

- [ ] 3.1 Crear `test/solo_agregado.sql` script SQL ejecutable con `psql` que intenta un `UPDATE` y un `DELETE` sobre `movimiento_stock` y demuestra que ambos son rechazados por el disparador de la 4.ª migración.
    - Incluir comentarios explicando el comportamiento esperado.
    - Verificación: ejecutar `psql -U usuario -d base -f test/solo_agregado.sql` muestra los errores del trigger y no realiza ninguna modificación en la tabla.

## 4. Carpeta evidencia/

- [ ] 4.1 Generar capturas de los casos **C-14** (rechazo del trigger en `psql`) y **C-15** (logs de `SQL_ECHO=true` mostrando igual número fijo de consultas SQL al leer una venta de 2 renglones y una de 4 renglones).
    - Ejecutar `psql` con el script del C-14 y capturar la salida de error.
    - Ejecutar `SQL_ECHO=true python main.py` y realizar una consulta de venta, capturar los logs de SQL.
    - Guardar las capturas en `evidencia/` con nombres descriptivos.

- [ ] 4.2 Documentar en `README.md` cómo generar la evidencia si es necesario.

## 5. README.md

- [ ] 5.1 Actualizar `README.md` con:
    - Documentación de puesta en marcha (variables de entorno de `Settings`).
    - Ejecución de las 4 migraciones (`alembic upgrade head`).
    - Ejecución de `python seed.py`.
    - Tabla completa de endpoints abiertos y protegidos.
    - Instrucciones para correr los casos de prueba `.http` y el script `solo_agregado.sql`.

- [ ] 5.2 Verificar que el README actualizado es coherente con la documentación de los cambios anteriores.

## Workflow follow-up

- Archivar el change con `/opsx:archive seed-casos-prueba-documentacion` una vez verificados todos los artifacts.
- Actualizar el estado de C-08 en `CHANGES.md` (marcar `[x]`).