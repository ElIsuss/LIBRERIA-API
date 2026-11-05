# Tasks

## 1. Repositorios y Unit of Work de Catálogo

- [x] 1.1 Implementar `repository.py` y `unit_of_work.py` en los módulos `editoriales`, `generos` y `autores`, extendiendo de `BaseRepository` y `UnitOfWork` base, verificando que ejecutan exclusivamente `flush()` sin `commit()`.
- [x] 1.2 Implementar en `app/modules/libros/repository.py` las clases `LibroRepository(SoftDeleteRepository[Libro])` (con opciones de precarga eager para `editorial`, `genero` y `autorias.autor`, y filtrado automático de `borrado_en`) y `MovimientoStockRepository(BaseRepository[MovimientoStock])`, verificando que `get_all` y `get_by_id` ocultan libros dados de baja a menos que se especifique `include_deleted=True`.

## 2. Unit of Work de Libros y Punto Único de Escritura de Stock

- [x] 2.1 Implementar en `app/modules/libros/unit_of_work.py` la clase `LibrosUnitOfWork` que expone `self.libros`, `self.movimientos` y el método centralizado `registrar_movimiento_stock(libro, usuario_id, cantidad, motivo, venta_id=None)` (`RN-11`), verificando que ajusta `libro.stock` e inserta la fila en `movimiento_stock` garantizando la consistencia de inventario.

## 3. Schemas Estrictos y Servicios de Catálogo

- [x] 3.1 Actualizar en `app/modules/libros/schemas.py` los contratos `LibroCreate` (recibiendo `stock_inicial: int >= 0` y `extra="forbid"`), `LibroUpdate` (sin campo `stock` y con `extra="forbid"`), `ReponerStockRequest` (`cantidad: int > 0`) y `MovimientoStockRead`, y agregar `extra="forbid"` en los schemas de entrada de `editoriales`, `generos` y `autores`, verificando que enviar `stock` en `LibroUpdate` genera `ValidationError` (`422`).
- [x] 3.2 Refactorizar `app/modules/libros/service.py` (`crear_libro` con movimiento inicial, `actualizar_libro`, `reponer_stock`, `eliminar_libro` con baja lógica `soft_delete`, `listar_paginado` devolviendo `Page[LibroLista]` y `listar_movimientos`) y los servicios de `editoriales`, `generos` y `autores` utilizando sus respectivos UoWs y `crear_pagina`.

## 4. Routers, RBAC y Verificación Integral E2E

- [x] 4.1 Reorganizar los routers de `libros`, `editoriales`, `generos` y `autores`, registrando las rutas de lectura en `open_router` y las rutas de mutación (`POST`, `PATCH`, `DELETE`, `/reponer`, `/movimientos`) en `protected_router` con `Depends(requiere_rol("ADMIN"))`, actualizando las inclusiones en `app/main.py`.
- [x] 4.2 Crear `test/test_c06_e2e.py` y verificar integralmente: listado paginado `Page[LibroLista]` excluyendo libros dados de baja y respondiendo `422` ante `page > pages`, obtención de detalle con 404 para libros eliminados, alta de libro con movimiento inicial en `movimiento_stock`, rechazo `422` al enviar `stock` en `PATCH`, reposición exitosa con auditoría, baja lógica con `204 No Content` e inmediata reutilización del ISBN en un libro nuevo (`RN-01`, `RN-13`).

## Workflow follow-up

- Archivar el change con `/opsx:archive catalogo-stock-baja-logica` tras verificar todas las tareas.
- Actualizar el roadmap en `CHANGES.md`.
