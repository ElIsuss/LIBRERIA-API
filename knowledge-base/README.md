# Librería API — Base de Conocimiento (Unidades 1 a 6)

Base de conocimiento generada a partir de la consigna oficial del Parcial (`doc/Parcial_Cap1a6_Consigna.pdf`) y del código base entregado en el TP de las Unidades 1 a 4.

## Índice de Archivos

| Archivo | Contenido |
|---|---|
| [01_vision_y_objetivos.md](01_vision_y_objetivos.md) | Propósito del sistema, objetivos por actor (`ADMIN`, `VENDEDOR`, `CLIENTE`, Visitante), alcance v2.0 y criterios de evaluación. |
| [02_descripcion_general.md](02_descripcion_general.md) | Stack tecnológico, arquitectura en 5 capas (`Router → Service → UoW → Repository → Model`), los 2 grupos de rutas y tabla completa de endpoints. |
| [03_actores_y_roles.md](03_actores_y_roles.md) | Actores, modelo de vigencia de roles en `asignacion_rol`, matriz RBAC y listado de rutas públicas vs protegidas. |
| [04_modelo_de_datos.md](04_modelo_de_datos.md) | Las 14 tablas del esquema relacional, diagrama ERD, índices únicos parciales (`postgresql_where`), trigger append-only y datos de `seed.py`. |
| [05_reglas_de_negocio.md](05_reglas_de_negocio.md) | Reglas `RN-01` a `RN-16` codificadas con sus garantes en base de datos, contratos y servicios. |
| [06_funcionalidades.md](06_funcionalidades.md) | Épicas e historias de usuario (`US-001` a `US-008`) mapeadas a los Ejercicios 1 a 10 del parcial. |
| [07_flujos_principales.md](07_flujos_principales.md) | Flujos extremo a extremo: Login con rate limit y sesión independiente, Auto-registro atómico, Autorización por rol vigente y Venta con descuento de stock. |
| [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md) | Patrones aplicados, estructura obligatoria de `parcial/` y `despliegue/`, seguridad y variables de entorno. |
| [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md) | Decisiones arquitectónicas (`DD-01` a `DD-06`) y supuestos de entrega (`SU-01`, `SU-02`). |
| [10_preguntas_abiertas.md](10_preguntas_abiertas.md) | Evoluciones entre el TP (Caps 1-4) y el Parcial (Caps 1-6) (`IN-01` a `IN-03`) y preguntas abiertas. |

## Quick Start para Desarrolladores

1. **Entender el dominio y los permisos** → [01_vision_y_objetivos.md](01_vision_y_objetivos.md), [03_actores_y_roles.md](03_actores_y_roles.md)
2. **Entender las 14 tablas y las migraciones** → [04_modelo_de_datos.md](04_modelo_de_datos.md)
3. **Entender las reglas `RN-01` a `RN-16`** → [05_reglas_de_negocio.md](05_reglas_de_negocio.md)
4. **Entender las capas (`Repository` + `UnitOfWork`) y la configuración** → [02_descripcion_general.md](02_descripcion_general.md), [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md), [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md)
5. **Implementar flujos y casos de prueba (`C-01` a `C-16` y `D-01` a `D-08`)** → [06_funcionalidades.md](06_funcionalidades.md), [07_flujos_principales.md](07_flujos_principales.md)
6. **Revisar cambios respecto del TP 1-4 antes de codificar** → [10_preguntas_abiertas.md](10_preguntas_abiertas.md)

## Resumen Ejecutivo

El parcial extiende el TP de la librería (Unidades 1 a 4) llevando la API asincrónica hasta el Capítulo 6: reorganiza todos los módulos bajo el patrón **Repository + Unit of Work** compartiendo la sesión del request, incorpora **autenticación con `bcrypt` (en `to_thread` + semáforo) y JWT en cookie `HttpOnly`**, **autorización consultando roles vigentes en la base en cada petición**, **baja lógica de libros e inventario de sólo agregado (`movimiento_stock` protegido por trigger en PostgreSQL)**, y contempla aparte el **despliegue en contenedor Docker (`python:3.12-alpine`) en el VPS** del TP original.
