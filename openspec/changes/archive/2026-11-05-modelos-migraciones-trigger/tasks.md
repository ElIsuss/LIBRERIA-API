# Tasks

## 1. Modelos simples

- [x] 1.1 Crear `app/modules/autores/models.py`, `editoriales/models.py`,
  `generos/models.py`. Verificación: DDL compilado con dialecto postgresql.
- [x] 1.2 Declarar `__tablename__` explícito y restricciones en `__table_args__`.
  Verificación: `autor` sin UNIQUE; `editorial` y `genero` con UNIQUE(nombre).

## 2. Modelos con relaciones

- [x] 2.1 Crear `app/modules/libros/models.py` (`Libro`, `LibroAutor`).
  Verificación: 8 FK con ON DELETE correcto.
- [x] 2.2 Crear `app/modules/clientes/models.py` (`Cliente`, `PerfilCliente`).
  Verificación: `cliente.perfil` es objeto, no lista; UNIQUE en perfil.
- [x] 2.3 Crear `app/modules/ventas/models.py` (`Venta`, `RenglonVenta`).
  Verificación: CHECK total>=0, cantidad>0, precio_unitario>0.
- [x] 2.4 Crear `app/modules/libros/models.py` (`MovimientoStock`) y modelos de
  seguridad en `app/modules/usuarios/models.py`. Verificación: importan sin error.

## 3. Migraciones

- [x] 3.1 Generar y corregir la 1.ª migración (8 tablas menos genero).
  Verificación: `alembic upgrade head` crea las tablas.
- [x] 3.2 Generar y corregir la 2.ª migración (genero + libro.genero_id).
  Verificación: `downgrade -1` deshace; `upgrade head` restaura.
- [x] 3.3 Generar la 3.ª migración (seguridad y plantilla).
  Verificación: tablas de usuario/seguridad creadas.
- [x] 3.4 Escribir a mano la 4.ª migración (trigger append-only).
  Verificación: `UPDATE movimiento_stock` lanza excepción.

## 4. Verificación

- [x] 4.1 Correr `configure_mappers()` sin error.
  Verificación: import de todos los modelos no falla.
- [x] 4.2 Verificar 21 pruebas de restricción (UNIQUE, CHECK, FK, ON DELETE).
  Verificación: 21/21 correctas.
- [x] 4.3 Verificar trigger append-only (UPDATE y DELETE rechazados).
  Verificación: ambos lanzan excepción.

## Workflow follow-up

- Archivar el change con `/opsx:archive modelos-migraciones-trigger`.
- Actualizar el estado de C-02 en `CHANGES.md` (ya marcado `[x]`).
