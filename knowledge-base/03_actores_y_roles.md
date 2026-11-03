# Actores y Roles

## Actores del sistema

| Actor | Descripción | Cómo interactúa |
|---|---|---|
| **Visitante (Anónimo)** | Persona no autenticada que navega el catálogo o desea registrarse/iniciar sesión. | Consume rutas del **Grupo Abierto** (`/health/*`, `GET /libros*`, `GET /editoriales*`, `GET /generos*`, `GET /autores/{id}/libros`, `POST /auth/registro`, `POST /auth/login`). |
| **Cliente (`CLIENTE`)** | Comprador registrado vía web (`POST /auth/registro`), vinculado 1 a 1 con su ficha en la tabla `cliente`. | Autenticado mediante cookie `access_token`. Puede ver sus compras en `GET /mis-ventas` y el detalle de una venta propia en `GET /ventas/{id}`. |
| **Vendedor (`VENDEDOR`)** | Personal de mostrador dado de alta por un administrador. | Autenticado mediante cookie `access_token`. Gestiona clientes (`POST/GET/PATCH /clientes*`, perfil, ventas del cliente) y registra/consulta ventas (`POST/GET /ventas*`). |
| **Administrador (`ADMIN`)** | Personal con control total del catálogo, inventario y seguridad. | Autenticado mediante cookie `access_token`. Mantiene catálogo (`editoriales`, `generos`, `autores`, `libros`), repone stock, da de baja libros, crea personal (`POST /usuarios`), asigna/revoca roles y audita `/eventos`. |
| **Usuario con clave provisoria** | Personal recién dado de alta (`debe_cambiar_password = True`). | Tiene sesión válida (`GET /auth/yo`, `POST /auth/cambiar-password`, `POST /auth/logout`), pero recibe `403 Forbidden` en cualquier ruta del **Grupo Protegido** hasta que actualice su contraseña (RN-06). |
| **Actor `SISTEMA`** | Identificador textual de procesos internos (ej. carga inicial `seed.py`). | No es una fila de `usuario`: se registra como cadena `"SISTEMA"` en `evento_seguridad.actor`. |

## Modelo de Vigencia de Roles

Los roles **no viven como una columna en `usuario`**, sino como filas en la tabla `asignacion_rol`.
Una asignación de rol está **vigente** en el instante de la petición si y sólo si cumple ambas condiciones en la base de datos:
1. `revocada_en IS NULL` (no fue revocada).
2. `vence_en IS NULL OR vence_en > now()` (no tiene vencimiento o su fecha de vencimiento está en el futuro).

> **Regla crítica (RN-04):** El token JWT incluye la lista de roles vigentes al momento del login únicamente con fines informativos (`GET /auth/yo` muestra tanto `roles_vigentes` en la base como `roles_token`). La dependencia `requiere_rol` **siempre consulta la tabla `asignacion_rol` en cada petición**, de modo que revocar un rol quita el permiso de inmediato sin esperar a que venza la cookie.

## RBAC — Matriz de permisos por recurso

| Recurso / Operación | Anónimo | `CLIENTE` | `VENDEDOR` | `ADMIN` | Con `debe_cambiar_password=True` |
|---|:---:|:---:|:---:|:---:|:---:|
| `GET /health/live`, `/health/ready` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `POST /auth/registro`, `/auth/login`, `/auth/logout` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `GET /auth/yo`, `POST /auth/cambiar-password` | ❌ (401) | ✅ | ✅ | ✅ | ✅ |
| `GET` catálogo (`/libros`, `/editoriales`, `/generos`, sub-recursos `/libros`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| `GET /mis-ventas` | ❌ (401) | ✅ | ✅ | ✅ | ❌ (403) |
| `GET /ventas/{id}` | ❌ (401) | ✅ (sólo si es dueño, si no 403) | ✅ (todas) | ✅ (todas) | ❌ (403) |
| `POST /clientes`, `GET/PATCH /clientes/{id}`, `POST /clientes/{id}/perfil`, `GET /clientes/{id}/ventas` | ❌ (401) | ❌ (403) | ✅ | ✅ | ❌ (403) |
| `POST /ventas`, `GET /ventas` | ❌ (401) | ❌ (403) | ✅ | ✅ | ❌ (403) |
| `POST/PATCH` en `/editoriales`, `/generos`, `/autores` | ❌ (401) | ❌ (403) | ❌ (403) | ✅ | ❌ (403) |
| `POST/PATCH/DELETE /libros*`, `/reponer`, `/movimientos` | ❌ (401) | ❌ (403) | ❌ (403) | ✅ | ❌ (403) |
| `POST /usuarios`, `GET/POST/DELETE /usuarios/{id}/roles*`, `GET /eventos` | ❌ (401) | ❌ (403) | ❌ (403) | ✅ | ❌ (403) |

## Rutas públicas (Sin sesión)
- `GET /health/live`
- `GET /health/ready`
- `POST /auth/registro`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /libros` y `GET /libros/{id}`
- `GET /editoriales`, `GET /editoriales/{id}` y `GET /editoriales/{id}/libros`
- `GET /generos` y `GET /generos/{id}/libros`
- `GET /autores/{id}` y `GET /autores/{id}/libros`
