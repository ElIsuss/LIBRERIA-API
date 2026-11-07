# Evidencia Caso C-14: Rechazo del Trigger Append-Only en `movimiento_stock`

## 1. Contexto y Regla de Negocio Evaluada
- **Regla RN-12**: La tabla `movimiento_stock` es de solo inserción (*append-only*). Ningún usuario ni proceso puede modificar ni borrar registros históricos de inventario.
- **Mecanismo**: Disparador PL/pgSQL `trg_movimiento_stock_append_only` instalado en la 4.ª migración de Alembic (`f22d38b1dde0`).

## 2. Comando Ejecutado
```bash
psql -U postgres -d libreria -f test/solo_agregado.sql
```

## 3. Salida Real de Consola Obtenida
```text
psql:test/solo_agregado.sql:20: NOTICE:  Éxito: El UPDATE fue rechazado por el trigger. Error: No se permite modificar ni eliminar movimientos de stock
DO
psql:test/solo_agregado.sql:35: NOTICE:  Éxito: El DELETE fue rechazado por el trigger. Error: No se permite modificar ni eliminar movimientos de stock
DO
 total_filas 
-------------
           7
(1 row)
```

## 4. Conclusión Técnica
- El intento de `UPDATE` sobre una fila existente lanzó la excepción prevista: *"No se permite modificar ni eliminar movimientos de stock"*.
- El intento de `DELETE` sobre una fila existente lanzó la misma excepción.
- La consulta `SELECT COUNT(*) FROM movimiento_stock` retornó **7 filas**, demostrando que el estado de la tabla permaneció inalterado tras los dos intentos de manipulación fraudulenta o accidental.
