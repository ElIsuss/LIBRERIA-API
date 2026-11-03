# Modelo de Datos

## Dominios y organización por módulos

El esquema relacional consta de **14 tablas** distribuidas en **6 módulos con persistencia**:
1. **`usuarios`** (`app/modules/usuarios/models.py`): `Usuario` (`usuario`), `AsignacionRol` (`asignacion_rol`), `IntentoAcceso` (`intento_acceso`), `EventoSeguridad` (`evento_seguridad`).
2. **`editoriales`** (`app/modules/editoriales/models.py`): `Editorial` (`editorial`).
3. **`generos`** (`app/modules/generos/models.py`): `Genero` (`genero`).
4. **`autores`** (`app/modules/autores/models.py`): `Autor` (`autor`).
5. **`libros`** (`app/modules/libros/models.py`): `Libro` (`libro`), `LibroAutor` (`libro_autor`), `MovimientoStock` (`movimiento_stock`).
6. **`clientes`** (`app/modules/clientes/models.py`): `Cliente` (`cliente`), `PerfilCliente` (`perfil_cliente`).
7. **`ventas`** (`app/modules/ventas/models.py`): `Venta` (`venta`), `RenglonVenta` (`renglon_venta`).

## ERD (Diagrama de Relaciones entre Entidades)

```
[Editorial] 1 ──── * [Libro] * ──── 0..1 [Genero]
                       │   │
                       │   └──── * [LibroAutor] * ──── 1 [Autor]
                       │
                       ├──────── * [RenglonVenta] * ──◆ 1 [Venta]
                       │                                    │
                       ▼                                    │
             * [MovimientoStock] * ─── 0..1 ────────────────┤
              («appendOnly»)                                │
                       │                                    ▼
                       │                           1 [Cliente] 1 ── 0..1 [PerfilCliente]
                       │                                    │
                       ▼                                    │ (0..1 acceso opcional)
                 1 [Usuario] 1 ─────────────────────────────┘
                       │
                       ├──────── * [AsignacionRol] (FK usuario_id, FK otorgada_por)
```
*(Tablas independientes sin FK salientes ni entrantes: `IntentoAcceso` y `EventoSeguridad`).*

## Entidades detalladas

### 1. `usuario` (`Usuario`) — *Nuevo en Parcial*
- **Atributos**:
  - `id: int` (PK, autoincremental)
  - `email: str` (`VARCHAR`, `NOT NULL`, `UNIQUE`, indexado)
  - `nombre: str` (`VARCHAR`, `NOT NULL`)
  - `password_hash: str` (`VARCHAR`, `NOT NULL`)
  - `activo: bool` (`BOOLEAN`, `NOT NULL`, default `True`)
  - `debe_cambiar_password: bool` (`BOOLEAN`, `NOT NULL`, default `False`)
- **Relaciones**:
  - `cliente: Cliente | None` (1 a 1 opcional, `back_populates="usuario"`)
  - `asignaciones_rol: list[AsignacionRol]` (1 a muchos sobre `AsignacionRol.usuario_id`)
  - `movimientos_stock: list[MovimientoStock]` (1 a muchos, `back_populates="usuario"`)

### 2. `asignacion_rol` (`AsignacionRol`) — *Nuevo en Parcial*
- **Atributos**:
  - `id: int` (PK)
  - `usuario_id: int` (`FK -> usuario.id`, `NOT NULL`, indexado)
  - `rol: str` (`VARCHAR(20)`, `NOT NULL`)
  - `desde: datetime` (`TIMESTAMPTZ`, `server_default=now()`, `NOT NULL`)
  - `vence_en: datetime | None` (`TIMESTAMPTZ`, `NULL`)
  - `revocada_en: datetime | None` (`TIMESTAMPTZ`, `NULL`)
  - `otorgada_por: int | None` (`FK -> usuario.id`, `NULL`, indexado)
- **Constraints e Índices**:
  - `CheckConstraint("rol IN ('ADMIN', 'VENDEDOR', 'CLIENTE')", name="ck_asignacion_rol_rol")`
  - **Índice único parcial**: `Index("uq_asignacion_rol_abierta", "usuario_id", "rol", unique=True, postgresql_where=text("revocada_en IS NULL"))` (RN-03).

### 3. `intento_acceso` (`IntentoAcceso`) — *Nuevo en Parcial*
- **Atributos**:
  - `id: int` (PK)
  - `cuando: datetime` (`TIMESTAMPTZ`, `server_default=now()`, `NOT NULL`)
  - `email: str` (`VARCHAR`, `NOT NULL`)
  - `ip: str` (`VARCHAR`, `NOT NULL`)
  - `exito: bool` (`BOOLEAN`, `NOT NULL`)
- **Índices**:
  - Índice compuesto `Index("ix_intento_acceso_email_ip_cuando", "email", "ip", "cuando")`.
- **Relaciones**: Ninguna (tabla independiente escrita en su propia sesión y transacción).

### 4. `evento_seguridad` (`EventoSeguridad`) — *Nuevo en Parcial*
- **Atributos**:
  - `id: int` (PK)
  - `cuando: datetime` (`TIMESTAMPTZ`, `server_default=now()`, `NOT NULL`)
  - `actor: str` (`VARCHAR`, `NOT NULL` — correo/identificador del usuario o `"SISTEMA"`)
  - `accion: str` (`VARCHAR`, `NOT NULL`)
- **Constraints / Relaciones**: Sin restricciones extra ni claves foráneas.

### 5. `cliente` (`Cliente`) — *Modificado en Parcial*
- **Atributos**:
  - `id: int` (PK)
  - `nombre: str` (`VARCHAR(200)`, `NOT NULL`)
  - `email: str` (`VARCHAR(254)`, `NOT NULL`, `UNIQUE`, indexado)
  - `usuario_id: int | None` (`FK -> usuario.id`, `NULL`, `UNIQUE`, indexado)
- **Relaciones**:
  - `usuario: Usuario | None` (1 a 1 opcional, `back_populates="cliente"`, devuelve objeto y no lista)
  - `perfil: PerfilCliente | None` (1 a 1 opcional, `back_populates="cliente"`)
  - `ventas: list[Venta]` (1 a muchos, `back_populates="cliente"`)

### 6. `perfil_cliente` (`PerfilCliente`) — *Sin cambios respecto del TP*
- **Atributos**: `id` (PK), `cliente_id` (`FK -> cliente.id ON DELETE CASCADE`, `UNIQUE`), `telefono`, `direccion`.

### 7. `editorial` (`Editorial`), `genero` (`Genero`), `autor` (`Autor`) — *Sin cambios respecto del TP*
- `editorial`: `id` (PK), `nombre` (`UNIQUE`), `pais`.
- `genero`: `id` (PK), `nombre` (`UNIQUE`).
- `autor`: `id` (PK), `nombre`, `nacionalidad`.

### 8. `libro` (`Libro`) — *Modificado en Parcial*
- **Atributos**:
  - `id: int` (PK)
  - `isbn: str` (`VARCHAR(20)`, `NOT NULL`, indexado — **deja de tener `unique=True` común**)
  - `titulo: str` (`VARCHAR(200)`, `NOT NULL`, indexado)
  - `precio: Decimal` (`NUMERIC(10, 2)`, `NOT NULL`)
  - `stock: int` (`INTEGER`, `NOT NULL`, default `0`)
  - `editorial_id: int` (`FK -> editorial.id ON DELETE RESTRICT`, `NOT NULL`, indexado)
  - `genero_id: int | None` (`FK -> genero.id ON DELETE SET NULL`, `NULL`, indexado)
  - `borrado_en: datetime | None` (`TIMESTAMPTZ`, `NULL`) — *Borrado lógico*
- **Constraints e Índices**:
  - `CheckConstraint("precio > 0", name="ck_libro_precio")`
  - `CheckConstraint("stock >= 0", name="ck_libro_stock")`
  - **Índice único parcial**: `Index("uq_libro_isbn_vigente", "isbn", unique=True, postgresql_where=text("borrado_en IS NULL"))` (RN-01, RN-13).
- **Relaciones**: `editorial`, `genero`, `autorias`, `renglones_venta`, `movimientos_stock`.

### 9. `libro_autor` (`LibroAutor`) — *Sin cambios respecto del TP*
- **Atributos**: `libro_id` (`PK, FK -> libro.id ON DELETE CASCADE`), `autor_id` (`PK, FK -> autor.id ON DELETE CASCADE`, indexado), `rol` (`CHECK IN ('autor','coautor','traductor','ilustrador')`), `orden` (`CHECK orden >= 1`).

### 10. `movimiento_stock` (`MovimientoStock`) — *Nuevo en Parcial («appendOnly»)*
- **Atributos**:
  - `id: int` (PK)
  - `libro_id: int` (`FK -> libro.id ON DELETE RESTRICT`, `NOT NULL`, indexado)
  - `venta_id: int | None` (`FK -> venta.id ON DELETE RESTRICT`, `NULL`, indexado)
  - `usuario_id: int` (`FK -> usuario.id ON DELETE RESTRICT`, `NOT NULL`, indexado)
  - `cantidad: int` (`INTEGER`, `NOT NULL`)
  - `motivo: str` (`VARCHAR`, `NOT NULL`)
  - `cuando: datetime` (`TIMESTAMPTZ`, `server_default=now()`, `NOT NULL`)
- **Constraints**:
  - `CheckConstraint("cantidad <> 0", name="ck_movimiento_stock_cantidad")`
  - **Disparador de sólo agregado (4.ª migración)**: `BEFORE UPDATE OR DELETE ON movimiento_stock FOR EACH ROW EXECUTE FUNCTION ...` que lanza excepción en PostgreSQL (RN-12).

### 11. `venta` (`Venta`) y `renglon_venta` (`RenglonVenta`) — *Sin cambios de columnas respecto del TP*
- `venta`: `id` (PK), `fecha` (`TIMESTAMPTZ`, `server_default=now()`), `total` (`NUMERIC(12, 2)`, `CHECK total >= 0`), `cliente_id` (`FK -> cliente.id ON DELETE RESTRICT`, indexado). Relación adicional con `movimientos_stock`.
- `renglon_venta`: `id` (PK), `venta_id` (`FK -> venta.id ON DELETE CASCADE`, indexado), `libro_id` (`FK -> libro.id ON DELETE RESTRICT`, indexado), `cantidad` (`CHECK > 0`), `precio_unitario` (`NUMERIC(10, 2)`, `CHECK > 0`).

## Seed data inicial (`seed.py`)

El script `seed.py` vacía las tablas (respetando o reiniciando el estado conocido, incluyendo poder vaciar o truncar limpiamente) y carga obligatoriamente:
1. **Usuarios (5)**:
   - `admin@example.com` y `admin2@example.com` (rol `ADMIN`)
   - `vendedor@example.com` (rol `VENDEDOR`)
   - `ana@example.com` (rol `CLIENTE`)
   - `nuevo@example.com` (rol `VENDEDOR`, con `debe_cambiar_password = True`)
2. **Catálogo del TP**:
   - **3 editoriales**, **3 géneros** y **6 autores**.
   - **5 libros** con su stock final actual:
     - *Rayuela* (stock final `10`: nace con stock inicial `11` y tiene `-1` por la venta 1)
     - *Antología de la literatura fantástica* (stock `5`, movimiento inicial `5`)
     - *Ficciones* (stock final `8`: nace con stock inicial `10` y tiene `-2` por la venta 1)
     - *Respiración artificial* (stock `3`, movimiento inicial `3`)
     - *Bestiario* (stock `1`, movimiento inicial `1`)
3. **Clientes (3)**:
   - *Lucía Fernández* (con perfil, sin usuario)
   - *Tomás Ríos* (sin perfil, sin usuario)
   - *Ana Paz* (vinculada al usuario `ana@example.com`)
4. **Venta inicial (1)**:
   - Venta `1`, de *Lucía Fernández*, registrada por `vendedor@example.com`: `1` ejemplar de *Rayuela* y `2` ejemplares de *Ficciones*, `total = 69000.00`.
5. **Movimientos de stock (7)**:
   - 5 movimientos `"Stock inicial"` (`11`, `5`, `10`, `3`, `1`) + 2 movimientos de salida por la venta 1 (`-1` en *Rayuela* y `-2` en *Ficciones*), cumpliendo `libro.stock == SUM(movimiento_stock.cantidad)` en los 5 libros.
6. **Historial de seguridad (1)**:
   - 1 fila en `evento_seguridad` con `actor = "SISTEMA"` y `accion = "Carga de los datos iniciales"`.
