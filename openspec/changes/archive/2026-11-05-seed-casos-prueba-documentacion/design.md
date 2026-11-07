# Design

## Context

Los changes C-01 a C-07 han implementado la infraestructura de la API (configuración, base de datos, migraciones, repositorios, Unit of Work, seguridad, autenticación y autorización). El change C-08 es el último paso del camino crítico y se enfoca en: (1) cargar el estado inicial del parcial en la base de datos, (2) proporcionar casos de prueba documentados y (3) generar evidencia del cumplimiento de las reglas de negocio. No se introduce nuevo código de dominio; el cambio es de infraestructura, datos y documentación.

## Goals

- **Carga inicial consistente** (`seed.py`): el script vacía tablas en orden inverso de dependencias y carga usuarios con roles, catálogo de editoriales/géneros/autores/libros con stock, clientes y una venta de ejemplo con movimientos de stock consistentes. Debe cumplir `libro.stock == SUM(movimiento_stock.cantidad)` para los 7 movimientos.
- **Casos de prueba completos** (`.http` en `test/`): cobertura de C-01 a C-13, C-15 y C-16, listos para ejecutarse después de `python seed.py`. Deben cubrir endpoints abiertos y protegidos, autenticación, autorización, creación/lectura/actualización/borrado de recursos, y validación de reglas de negocio.
- **Evidencia del trigger append-only** ( `evidencia/C-14`): script `test/solo_agregado.sql` que demuestra que `UPDATE` y `DELETE` sobre `movimiento_stock` son rechazados por el trigger de la 4.ª migración. Capturas en `evidencia/` del rechazo en `psql`.
- **Evidencia de consistencia de consultas** (`evidencia/C-15`): logs de `SQL_ECHO=true` mostrando el mismo número fijo de consultas SQL al leer una venta de 2 renglones y una de 4 renglones, validando la ausencia de problemas N+1.

## Non-Goals

- No implementar nuevos endpoints de API más allá de los ya definidos en C-07.
- No añadir nuevos modelos de tabla o restricciones al esquema de base de datos.
- No modificar la lógica de negocio implementada en changes anteriores.

## Risks / Trade-offs

- [Riesgo] Si el orden de vaciado de tablas en `seed.py` no es el correcto, pueden producirse errores de clave foránea. Mitigación: utilizar `DELETE FROM` en el orden correcto que respete las Foreign Keys (ver Tasks) en lugar de `model.metadata.drop_all()`, que eliminaría el esquema.
- [Riesgo] Los scripts `.http` pueden fallar si las variables de entorno no están configuradas. Mitigación: documentar en `README.md` las variables necesarias y probar con el `.env` completo.
- [Trade-off] La carpeta `evidencia/` requiere captura manual o automatizada; se documenta cómo generarla pero no se incluye en el código fuente versionado.

## Migration Plan

No aplica: este change no modifica el esquema de base de datos. Las 4 migraciones de Alembic ya fueron aplicadas en C-02. El script `seed.py` opera sobre el esquema existente.

## Open Questions

- ¿Se deben generar las capturas de `evidencia/` automáticamente o se incluyen manualmente después de correr `seed.py`?