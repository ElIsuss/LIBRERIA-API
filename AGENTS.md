# Reglas obligatorias de trabajo del agente

## 1. Autorización antes de actuar

**Nunca realices cambios sin mi autorización explícita previa.**

Antes de crear, modificar, sobrescribir, mover o eliminar archivos, seguí este procedimiento:

1. Explicame qué problema o necesidad detectaste.
2. Proponé el cambio concreto que considerás conveniente.
3. Explicame por qué lo recomendás y qué consecuencias puede tener.
4. Indicame qué archivos, configuraciones o componentes se verían afectados.
5. Esperá a que yo responda explícitamente que autorizo el cambio.

No ejecutes el cambio hasta recibir mi autorización.

## 2. No tomes decisiones por mi cuenta

No supongas que quiero aplicar una modificación simplemente porque la sugeriste o porque considerás que es la mejor solución.

No interpretes expresiones como "¿qué opinás?", "¿cómo lo mejorarías?" o "¿qué podríamos hacer?" como una autorización para modificar archivos.

Primero respondé mi consulta, explicá las alternativas y preguntame si quiero que implementes alguna.

## 3. Consultame antes de ejecutar acciones

También necesitás mi autorización antes de:

- Instalar, actualizar o desinstalar dependencias.
- Modificar `requirements.txt`, `pyproject.toml` o archivos de configuración.
- Ejecutar migraciones o alterar una base de datos.
- Crear, eliminar o modificar tablas y registros.
- Ejecutar comandos Git que cambien el repositorio, el historial o las ramas.
- Sobrescribir archivos existentes o eliminar datos.
- Cambiar variables de entorno, credenciales o configuraciones del sistema.
- Ejecutar cualquier otra operación que modifique el estado del proyecto o del entorno.

Los comandos de lectura y diagnóstico que no alteren el estado pueden ejecutarse sin autorización previa, siempre que no expongan información sensible.

## 4. La autorización tiene un alcance limitado

Si autorizo un cambio específico, solo podés realizar ese cambio y las acciones expresamente incluidas en la autorización.

No aproveches esa autorización para introducir mejoras adicionales, refactorizar otras partes, instalar paquetes extra ni modificar archivos no contemplados.

Si durante la implementación descubrís que hace falta realizar un cambio adicional, detenete, explicámelo y solicitá una nueva autorización.

## 5. Trabajá como profesor

Mi objetivo es aprender programación y comprender el proyecto, no solamente obtener código que funcione.

Antes de proponer una implementación:

- Explicame el concepto involucrado con palabras sencillas.
- Mostrame la solución propuesta y por qué conviene.
- Señalame las alternativas relevantes.
- Indicame cómo vamos a comprobar que funciona.

Después de implementar un cambio autorizado, explicame qué hiciste, por qué lo hiciste y cómo puedo verificar el resultado.

## 6. No avances automáticamente

Trabajá por etapas pequeñas y verificables.

Después de completar una etapa autorizada, mostrame los resultados y esperá mis instrucciones antes de comenzar la siguiente.

**Regla final: podés analizar, investigar, explicar y proponer libremente dentro del alcance permitido. Para modificar, instalar, borrar, migrar o ejecutar acciones que cambien el estado, necesitás mi autorización previa y explícita.**

## 7. Seguimiento de etapas en ETAPAS_TP.txt

El archivo `ETAPAS_TP.txt`, en la raíz del proyecto, es la **única fuente de verdad del avance**. Las etapas se ejecutan en el orden y con los pesos que figuran ahí.

**Al cerrar cada etapa estás autorizado a actualizar `ETAPAS_TP.txt`** — es parte del cierre de la etapa y no requiere una autorización nueva. Lo que sí requiere autorización aparte es agregar, eliminar, reordenar etapas o cambiar pesos.

### Los dos contadores miden cosas distintas

No son intercambiables y no deben leerse como si lo fueran:

| Contador | Qué mide |
| --- | --- |
| **Etapas completadas** | El avance real: cuántas etapas del plan están hechas |
| **Peso acumulado** | Cuánta parte del TP *evaluable por la consigna* está lista |

Una etapa puede estar `[X] COMPLETADA` y aportar `0` al peso acumulado. Eso no es una contradicción: significa que es un prerrequisito, no una etapa puntuada.

### La Etapa 0 es un prerrequisito y no tiene peso propio

`ETAPAS_TP.txt` debe marcar la Etapa 0 como `[PRERREQUISITO]`, nunca como `0%`.

Motivo: la tabla de *Criterios de evaluación* de la consigna (página 11) tiene siete categorías que suman 100, y **ninguna corresponde a "instalar dependencias y crear la base"**. El trabajo real de esa etapa (el `.env`, `env.example`, `requirements.txt` y la base creada) se evalúa dentro de la categoría *"Proyecto, conexión y ciclo de vida"* (10 %), que corresponde a la **Etapa 1**. Por eso el peso acumulado recién se mueve cuando arranca la Etapa 1.

Marcar la Etapa 0 con `0%` es ambiguo y genera confusión: se presta a leer como "esta etapa no se hizo", cuando en realidad está terminada.

### Reglas sobre los pesos

- Los pesos por etapa **derivan de la consigna**, no de una estimación propia. No inventar categorías ni repartos.
- La Etapa 13 (entrega: seed, casos de prueba y README) tiene peso `0`: es material de entrega, no conocimiento evaluado.
- Si una etapa se agrupa o se parte, los pesos se reasignan según la categoría de la consigna que representa, y el cambio queda anotado en el archivo.

## 8. Portabilidad y secretos

**Ningún archivo del proyecto puede contener rutas absolutas de una máquina concreta ni credenciales.**

El proyecto se comparte con compañeros de grupo y se corrige en otra máquina. Todo lo que dependa de *dónde* esté el proyecto tiene que resolverse en tiempo de ejecución, nunca estar escrito.

### Rutas: siempre relativas al archivo, nunca absolutas

```python
# MAL: solo funciona en la PC donde se escribio
sys.path.insert(0, r"C:\Users\Alguien\Desktop\libreria-api")
load_dotenv(r"C:\Users\Alguien\Desktop\libreria-api\.env")

# BIEN: el archivo se localiza a si mismo
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
```

El criterio es simple: si al cambiar de carpeta o de computadora el archivo deja de funcionar, está mal. La consigna lo exige de forma explícita: *"Ninguna contraseña en el código, en `alembic.ini` ni en el repositorio"*.

### Credenciales

| Archivo | Qué lleva | ¿Se versiona? |
| --- | --- | --- |
| `env.example` | La forma del valor, con placeholders | Sí |
| `.env` | Las credenciales reales de quien lo usa | **No**, está en `.gitignore` |

Cada persona que clone el proyecto tiene que crear su propio `.env` a partir de `env.example`. Eso va documentado en el `README.md`.

### Valores de configuración que cambian entre máquinas

- `localhost:5432` y el nombre de la base pueden diferir → van en `.env`
- El puerto del servidor puede diferir → en los `.http`, usar una variable `{{baseUrl}}` definida una sola vez arriba
- `alembic.ini` **no** lleva la URL de la base: se lee del entorno en `migrations/env.py`

### Al agregar un archivo que se comparte

Antes de dar por terminado un archivo ejecutable —script de seed, caso de prueba, README— comprobar:

1. ¿Funciona si el proyecto está en otra carpeta?
2. ¿Funciona en la PC de otro compañero con otras credenciales?
3. ¿Aparece alguna ruta absoluta o password si se abre el archivo?


---

# Nuevas reglas del agente por el flujo SDD

*(Nota: Todo lo que se encuentra arriba de esta línea —secciones 1 a 8— corresponde a las reglas obligatorias originales conservadas íntegramente del TP anterior / fase previa, y sigue teniendo prioridad absoluta. Todo lo que sigue a continuación fue agregado por el flujo de fundación SDD / OpenSpec para el Parcial de las Unidades 1 a 6).*

## 9. Stack Tecnológico (`requirements.txt`)

| Capa | Paquete (`requirements.txt`) / Tecnología | Uso en el proyecto |
| --- | --- | --- |
| **Lenguaje** | Python 3.12+ | Tipado moderno, `asyncio`, `contextlib` |
| **Base de Datos** | PostgreSQL 16+ | Persistencia relacional, restricciones `CHECK`/`UNIQUE`, índices parciales y triggers |
| **Framework Web** | `fastapi[standard]` | API REST asincrónica (`async def`), inyección con `Depends()`, `BackgroundTasks` |
| **Servidor ASGI** | `uvicorn` | Ejecución del servidor HTTP asincrónico |
| **ORM / Modelos** | `sqlmodel` | Definición de modelos de tabla (`table=True`) |
| **Motor y Sesiones** | `sqlalchemy[asyncio]` | `AsyncEngine`, `async_sessionmaker`, `joinedload`, `selectinload`, índices parciales |
| **Driver DB** | `asyncpg` | Controlador asincrónico para PostgreSQL (`postgresql+asyncpg://`) |
| **Migraciones** | `alembic` | Versionado de esquema con plantilla asincrónica (4 migraciones en total) |
| **Seguridad (Hash)** | `bcrypt` | Hashing de contraseñas fuera del event loop (`to_thread` + `Semaphore`, máx. 72 bytes UTF-8) |
| **Seguridad (Tokens)** | `pyjwt` | Firma y verificación de tokens JWT transportados en cookie `HttpOnly` |
| **Entorno (.env)** | `python-dotenv` | Carga de variables desde `.env` (migraciones Alembic y scripts) |
| **Configuración** | `pydantic-settings` | `Settings(BaseSettings)` para validación de variables de entorno y `@computed_field` |

## 10. Base de Conocimiento y Discovery

- **Discovery del Parcial**: [`discovery/discovery.md`](discovery/discovery.md)
- **Índice de la Knowledge Base**: [`knowledge-base/README.md`](knowledge-base/README.md)
  - [`knowledge-base/01_vision_y_objetivos.md`](knowledge-base/01_vision_y_objetivos.md) — Propósito, objetivos por actor y alcance (Ejercicios 1 al 8; Ejercicios 9 y 10 ya completados sobre el TP 1-4).
  - [`knowledge-base/02_descripcion_general.md`](knowledge-base/02_descripcion_general.md) — Stack, arquitectura en 5 capas (`Router → Service → UoW → Repository → Model`), los 2 grupos de rutas y tabla de endpoints.
  - [`knowledge-base/03_actores_y_roles.md`](knowledge-base/03_actores_y_roles.md) — Vigencia de roles en `asignacion_rol`, matriz RBAC y rutas abiertas vs protegidas.
  - [`knowledge-base/04_modelo_de_datos.md`](knowledge-base/04_modelo_de_datos.md) — Las 14 tablas, ERD, índices únicos parciales, trigger append-only y dataset de `seed.py`.
  - [`knowledge-base/05_reglas_de_negocio.md`](knowledge-base/05_reglas_de_negocio.md) — Reglas `RN-01` a `RN-16`.
  - [`knowledge-base/06_funcionalidades.md`](knowledge-base/06_funcionalidades.md) — Épicas e historias de usuario (`US-001` a `US-008`).
  - [`knowledge-base/07_flujos_principales.md`](knowledge-base/07_flujos_principales.md) — Flujos E2E (Login con rate-limit y sesión independiente, Auto-registro, Autorización en BD, Venta con descuento de stock).
  - [`knowledge-base/08_arquitectura_propuesta.md`](knowledge-base/08_arquitectura_propuesta.md) — Patrones, estructura de directorios y variables de entorno.
  - [`knowledge-base/09_decisiones_y_supuestos.md`](knowledge-base/09_decisiones_y_supuestos.md) — Decisiones `DD-01` a `DD-06` y supuestos `SU-01`/`SU-02`.
  - [`knowledge-base/10_preguntas_abiertas.md`](knowledge-base/10_preguntas_abiertas.md) — Diferencias entre el TP (Caps 1-4) y el Parcial (Caps 1-6).

## 11. Skills Disponibles por Rol

| Rol de Agente | Responsabilidad | Skills que utiliza |
| --- | --- | --- |
| **Orquestación / Planificación SDD** | Exploración, propuesta, sincronización y archivo de changes | `openspec-explore`, `openspec-propose`, `openspec-update-change`, `openspec-sync-specs`, `openspec-archive-change` |
| **Implementación Backend (FastAPI / SQLModel / UoW)** | Ejecución de tareas de los changes `C-01` a `C-08` respetando autorización previa | `openspec-apply-change` |
| **Fundación y Documentación** | Discovery, Knowledge Base, Roadmap y Registro de Skills | `discovery-research`, `kb-creator`, `roadmap-generator`, `agents-md-generator` |

> Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry`; no versionado — está en `.gitignore`).

## 12. Roadmap de Changes (`CHANGES.md` — Ejercicios 1 al 8)

El mapa completo de implementación vive en [`CHANGES.md`](CHANGES.md). Abarca **exclusivamente los Ejercicios 1 al 8** (los Ejercicios 9 y 10 ya fueron realizados previamente sobre el estado anterior del TP):

- **Camino crítico (8 changes)**: `C-01` → `C-02` → `C-03` → `C-04` → `C-05` → `C-06` → `C-07` → `C-08`
  - `C-01` `config-lifespan-health` *(Ejercicio 1)* — **Primer change recomendado**
  - `C-02` `modelos-migraciones-trigger` *(Ejercicios 2 y 7a)*
  - `C-03` `core-repositorios-uow-paginacion` *(Ejercicios 3a y 6a)*
  - `C-04` `autenticacion-seguridad` *(Ejercicios 4 y 7b)*
  - `C-05` `autorizacion-usuarios-eventos` *(Ejercicio 5)*
  - `C-06` `catalogo-stock-baja-logica` *(Ejercicios 3b, 6b y 8a)*
  - `C-07` `clientes-ventas-transaccionales` *(Ejercicios 5, 6c y 8b)*
  - `C-08` `seed-casos-prueba-documentacion` *(Ejercicio 8c)*

## 13. Reglas Duras Específicas del Parcial (Unidades 1 a 6)

> Reglas globales de orquestación, governance y memoria persistente (Engram) ya definidas en el entorno global: el proyecto las hereda, supeditadas siempre a las **Reglas 1 a 8** de este archivo (autorización explícita previa antes de cualquier cambio).

- **NUNCA ejecutar `commit()` en un repositorio** → Los repositorios (`BaseRepository`, `SoftDeleteRepository` y repositorios de módulo) sólo hacen `await self.session.flush()`; el único que hace `commit()` o `rollback()` es el `UnitOfWork` al salir del bloque `async with uow:`.
- **NUNCA cerrar la sesión dentro del `UnitOfWork`** → La sesión se inyecta con `Depends(get_session)`, es compartida entre las dependencias de autenticación (`get_usuario_actual`, `requiere_rol`) y el `UnitOfWork`, y la cierra `get_session` al terminar la petición.
- **NUNCA usar el `UnitOfWork` de la petición para `intento_acceso`** → Es la única tabla que se graba en su propia sesión y transacción independiente para que el conteo de intentos fallidos sobreviva al error `401` del login (`RN-07`).
- **NUNCA ejecutar `bcrypt` en el hilo del event loop ni dentro de la transacción** → Siempre usar `await asyncio.to_thread(...)` bajo un `asyncio.Semaphore`, validando antes `len(password.encode("utf-8")) <= 72` en los schemas de entrada (`422`) y calculando el hash **antes** de abrir el `UnitOfWork`.
- **NUNCA enviar ni leer el JWT fuera de la cookie `access_token`** → El token viaja únicamente en cookie `HttpOnly` (`SameSite=Lax`, `Max-Age`, `Secure` configurable); nunca en el cuerpo JSON ni por cabecera `Authorization`.
- **NUNCA decidir permisos confiando en los roles del JWT** → `requiere_rol` consulta siempre `asignacion_rol` en la base de datos en cada petición (`RN-04`).
- **NUNCA modificar `libro.stock` por fuera del punto único de escritura** → Todo cambio de stock (alta con `stock_inicial`, reposición y venta) pasa por el mismo método que actualiza `libro.stock` e inserta en `movimiento_stock` (`RN-11`), protegido además por el trigger append-only en PostgreSQL (`RN-12`).
- **Usar siempre `model_config = ConfigDict(extra="forbid")`** en todos los esquemas Pydantic de entrada.
