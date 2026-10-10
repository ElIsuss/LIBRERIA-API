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