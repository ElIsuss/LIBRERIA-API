# Proposal

## Why

El proyecto requiere una carga inicial de datos (seed) que establezca el estado base del parcial, junto con la evidencia y casos de prueba que permitan verificar el correcto funcionamiento de las reglas de negocio implementadas en los changes C-01 a C-07. Este change corresponde al **Ejercicio 8** de la consigna del Parcial (Unidades 1 a 6) y es el último change del camino crítico (`C-01` → `C-02` → ... → `C-08`). Permite validar todo el sistema desde la base de datos hasta los endpoints de la API.

## What Changes

- `seed.py` (en la raíz del proyecto, ejecutable con `python seed.py`): vacía las tablas en el orden correcto y carga: los **5 usuarios** con sus roles (`admin@example.com`, `admin2@example.com`, `vendedor@example.com`, `ana@example.com`, `nuevo@example.com` con `debe_cambiar_password=True`), el catálogo del TP (**3 editoriales, 3 géneros, 6 autores, 5 libros** con stock final `10, 5, 8, 3, 1`), los **3 clientes** (Lucía con perfil, Tomás sin perfil, Ana vinculada a `ana@example.com`), la **venta 1** de Lucía registrada por `vendedor@example.com` (`1` *Rayuela* + `2` *Ficciones*, `total = 69000.00`), los **7 movimientos de stock** (cumpliendo `libro.stock == SUM(movimiento_stock.cantidad)`) y **1 evento de seguridad** (`actor="SISTEMA"`, `accion="Carga de los datos iniciales"`).
- Archivos `.http` en `test/` cubriendo los casos de prueba **`C-01` a `C-13`, `C-15` y `C-16`** en orden, listos para correrse después de `python seed.py`.
- `test/solo_agregado.sql` (**Caso `C-14`**): script SQL ejecutable con `psql` que intenta un `UPDATE` y un `DELETE` sobre `movimiento_stock` y demuestra que ambos son rechazados por el disparador de la 4.ª migración.
- Carpeta `evidencia/`: salidas/capturas de los casos **C-14** (rechazo del trigger en `psql`) y **C-15** (logs de `SQL_ECHO=true` mostrando igual número fijo de consultas SQL al leer una venta de 2 renglones y una de 4 renglones).
- `README.md`: documentación actualizada de puesta en marcha, variables de entorno de `Settings`, ejecución de las 4 migraciones, `python seed.py` y tabla completa de endpoints abiertos y protegidos.

## Capabilities

### New Capabilities

- `carga-inicial-datos`: script `seed.py` que carga el estado inicial del parcial con usuarios, catálogo, clientes, ventas y movimientos de stock consistentes.
- `casos-prueba-documentados`: batería de pruebas `.http` y scripts SQL que cubren los casos C-01 a C-16 y demuestran el comportamiento del sistema (trigger append-only, paginación, autorización, ventas atómicas).
- `evidencia-de-comportamiento`: capturas y logs que evidencian el cumplimiento de las reglas RN-12 (trigger append-only en movimiento_stock) y RN-14 (control de dueño en ventas).

### Modified Capabilities

<!-- Ninguna: es el último change del camino crítico. -->

## Impact

- Afecta `seed.py`, `test/*.http`, `test/solo_agregado.sql`, `evidencia/` y `README.md`.
- Cierra el camino crítico de changes del parcial (C-01 a C-08).
- Habilita la verificación completa del sistema: desde el estado de base de datos hasta el comportamiento de los endpoints protegidos y abiertos.
- No introduce nuevo código de dominio; el cambio es de infraestructura, datos y documentación.

## Open Questions

- Ninguna.