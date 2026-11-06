evidencia C-14: Rechazo del trigger append-only en movimiento_stock

Escenario: Ejecutar test/solo_agregado.sql con psql y observar el error.
Comando esperado: psql -U usuario -d nombre_base -f test/solo_agregado.sql

Resultado esperado en la salida:
- Intento de UPDATE sobre movimiento_stock: error del trigger, no se modifican filas
- Intento de DELETE sobre movimiento_stock: error del trigger, no se eliminan filas
- COUNT(*) FROM movimiento_stock: mismo número de filas que antes de los intentos

Archivos asociados:
- test/solo_agregado.sql: script SQL que ejecuta los intentos y muestra los errores

Cómo generar:
1. Tener la base de datos con las 4 migraciones aplicadas (C-02)
2. Ejecutar: psql -U usuario -d db -f test/solo_agregado.sql
3. Capturar la salida de consola (errores del trigger)
4. Guardar en este archivo o en evidencias/ con nombre descriptivo