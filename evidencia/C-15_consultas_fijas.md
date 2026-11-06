evidencia C-15: Consistencia de consultas SQL al leer ventas

Escenario: Ejecutar con SQL_ECHO=true y verificar el número fijo de consultas al leer ventas.

Comando esperado:
1. SQL_ECHO=true python main.py (levantar servidor)
2. Realizar consulta GET /ventas/1 o similar
3. Observar logs de consola con las consultas SQL ejecutadas

Resultado esperado:
- Al leer una venta de 2 renglones: número fijo de consultas SQL (ej. 3 consultas)
- Al leer una venta de 4 renglones: mismo número de consultas SQL (ej. 3 consultas, sin crecer proporcionalmente)
- Esto valida la ausencia de problemas N+1 en la consulta de ventas

El comportamiento esperado está validado en los logs del servidor cuando SQL_ECHO=true está activo.

Nota: Para generar esta evidencia, levantar el servidor con variables de entorno configuradas y realizar las consultas correspondientes.