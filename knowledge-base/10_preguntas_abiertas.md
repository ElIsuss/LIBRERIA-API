# Preguntas Abiertas

## Inconsistencias y diferencias detectadas entre el TP (Caps 1-4) y el Parcial (Caps 1-6)

*(Nota: No son contradicciones del enunciado, sino evoluciones explícitas entre la primera entrega y el parcial que deben tenerse presentes durante la implementación).*

### IN-01 — Paginación: de `limit`/`offset` a envoltorio `{items, total, page, size, pages}`
- **TP (Capítulos 1 a 4) decía**: Paginación por parámetros `limit` y `offset` devolviendo directamente una lista JSON `[...]`.
- **Parcial (Capítulos 1 a 6) dice**: Los listados paginados reciben `page` (desde 1) y `size` (1 a 100, por defecto 20) y devuelven el envoltorio `{items, total, page, size, pages}` (`app/core/paginacion.py`). Si se pide una página mayor que `pages`, responde `422 Unprocessable Entity` (con 0 resultados hay 1 página vacía: `total: 0, page: 1, pages: 1, items: []`).
- **Impacto**: Todos los listados paginados indicados en la tabla de endpoints (`GET /libros`, `GET /editoriales`, `GET /generos`, `GET /eventos`, `GET /ventas`, `GET /mis-ventas`) deben migrar al nuevo envoltorio.
- **Resolución propuesta**: Implementar el helper genérico en `app/core/paginacion.py` junto con `count()` en `BaseRepository` y `SoftDeleteRepository`.

### IN-02 — Configuración de `DATABASE_URL` vs variables `POSTGRES_*` separadas
- **TP (Capítulos 1 a 4) decía**: Se lee `DATABASE_URL` directa con `os.environ` y `python-dotenv`, y `ECHO_SQL`.
- **Parcial (Capítulos 1 a 6) dice**: En `parcial/`, `app/core/config.py` usa `Settings(BaseSettings)` de `pydantic-settings`, lee `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST` y `POSTGRES_PORT` y arma la URL con `@computed_field`, además de usar `SQL_ECHO` (o aceptar ambos alias). En cambio, en `despliegue/` (que empaqueta el TP 1-4) el contenedor sigue recibiendo `DATABASE_URL` por `--env-file`.
- **Resolución propuesta**: Actualizar `app/core/config.py` y `env.example` en `parcial/` con `pydantic-settings` y `@computed_field`, soportando `SQL_ECHO` (y alias `ECHO_SQL` si fuera necesario).

### IN-03 — Alta y edición de stock en `Libro` (`stock` vs `stock_inicial`)
- **TP (Capítulos 1 a 4) decía**: `LibroCreate` recibía `stock` y `LibroUpdate` permitía editar `stock` por `PATCH /libros/{id}`.
- **Parcial (Capítulos 1 a 6) dice**: `LibroCreate` recibe `stock_inicial` (creando el movimiento `"Stock inicial"` en `movimiento_stock`), y `LibroUpdate` **no** tiene `stock` y usa `extra="forbid"`, de modo que enviar `stock` en `PATCH /libros/{id}` responde `422` (Caso C-16).

---

## Estado de Preguntas Abiertas / Alcance Confirmado

| Estado | Tema | Resolución confirmada |
|---|---|---|
| **Resuelto** | Alcance de `CHANGES.md` (Ejercicios 1 al 8 vs 9 y 10) | Los **Ejercicios 9 y 10** (Docker y despliegue en VPS sobre el estado anterior del TP 1-4) **ya están hechos** antes de iniciar el flujo SDD. Todo lo relativo a `CHANGES.md` abarca únicamente del **Ejercicio 1 al 8**. |
