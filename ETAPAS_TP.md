================================================================================
 TP PROGRAMACION III - LIBRERIA API
 Plan de etapas y registro de avance
================================================================================

 Consigna : TP_Cap1a4_Consigna.pdf
 Materia  : Programacion III (Unidades 1 a 4 - Del objeto a la persistencia)
 Stack    : FastAPI + SQLModel + PostgreSQL + Alembic
 Inicio   : 2026-10-10


--------------------------------------------------------------------------------
 ESTADOS
--------------------------------------------------------------------------------
   [X] COMPLETADA      Etapa terminada y verificada
   [>] EN CURSO        Etapa iniciada, pendiente de terminar
   [ ] PENDIENTE       Todavia no se empezo


--------------------------------------------------------------------------------
 AVANCE
--------------------------------------------------------------------------------

    Etapas completadas : 9 de 14
    Peso acumulado     : 100 de 100 puntos


--------------------------------------------------------------------------------
 ETAPAS
--------------------------------------------------------------------------------

[X] ETAPA 0 - Dependencias, credenciales y base de datos      [PRERREQUISITO]

     Objetivo: dejar la infraestructura lista antes de escribir dominio.

       - requirements.txt con sqlmodel, SQLAlchemy[asyncio], asyncpg,
         alembic, python-dotenv
       - env.example con la forma de DATABASE_URL y sin secretos
       - .gitignore que excluye .env, .venv y __pycache__
       - .env con las credenciales reales
       - Instalacion en el venv
       - Base libreria_api creada y vacia en PostgreSQL

     Verificado:
       - SELECT 1 via asyncpg devolvio 1
       - La base tiene 0 tablas (correcto: las crea Alembic, no create_all)
       - git check-ignore confirma que .env no se versiona

     Versions instaladas:
       sqlmodel 0.0.48 | SQLAlchemy 2.1.4 | asyncpg 0.32.0
       alembic 1.20.0  | greenlet 3.5.6  | Python 3.14.2
       PostgreSQL 17


[X] ETAPA 1 - Proyecto, conexion y ciclo de vida                     [  10%]

     Objetivo: que la app levante y se conecte a la base.

     Archivos:
       - app/core/config.py       lectura de DATABASE_URL desde el entorno
       - app/core/database.py     motor, fabrica de sesiones, get_session
       - app/main.py              lifespan y registro de routers

     Conceptos clave:
       - lifespan: los recursos se crean al arrancar y se cierran al apagar
       - el motor y la fabrica se guardan en app.state
       - Depends(get_session): una sesion nueva por peticion
       - expire_on_commit=False: evita consultas implicitas al commit

     Endpoints:
       - GET /health/live    no toca la base
       - GET /health/ready   ejecuta SELECT 1

     Verificado:
       - Ambos endpoints responden 200
       - /health/live NO abre conexion a la base (pool perezoso confirmado)
       - /health/ready abre 1 conexion
       - 3 llamadas seguidas a /ready reutilizan la misma conexion (pool)
       - Al apagar el server, la conexion se libera (engine.dispose)

     Estado: COMPLETADA el 2026-10-10


[X] ETAPA 2 - Modelos simples: autores, editoriales, generos           [ 25%]

     Objetivo: los modelos de tabla sin relaciones complejas.

     Archivos:
       - app/modules/autores/models.py
       - app/modules/editoriales/models.py
       - app/modules/generos/models.py

     Conceptos clave:
       - table=True convierte la clase en tabla
       - id: int | None = Field(default=None, primary_key=True)
         el None es lo que habilita el autoincremental
       - __tablename__ explicito: sin el, SQLModel deriva el nombre de la
         clase en minusculas y LibroAutor daria "libroautor" en vez de
         "libro_autor"
       - Las restricciones van en __table_args__, no en Field
       - Las relaciones de estas 3 tablas viven todas del lado de libro,
         por eso no tienen ninguna FK

     Verificado:
       - Los 3 modelos importan sin error
       - DDL compilado con dialecto postgresql, sin tocar la base:
           autor      -> sin UNIQUE (la consigna no pide ninguna)
           editorial  -> CONSTRAINT uq_editorial_nombre UNIQUE (nombre)
           genero     -> CONSTRAINT uq_genero_nombre UNIQUE (nombre)
       - Todas las columnas NOT NULL, PRIMARY KEY (id) con SERIAL
       - La base sigue con 0 tablas: las crea Alembic en la etapa 5

     Decisiones tomadas:
       - autor.nacionalidad y editorial.pais son obligatorios
         (el diagrama los declara str, no str | None)

     Estado: COMPLETADA el 2026-10-10


[X] ETAPA 3 - Modelos con relaciones: libros y clientes               [ 25%]

     Objetivo: los modelos que definen el nucleo del dominio.

     Se hizo JUNTO con la etapa 4 a proposito: Libro necesita navegar a
     RenglonVenta y RenglonVenta necesita navegar a Libro. Separarlas
     obligaba a dejar una relacion sin declarar o romper una importacion
     circular.

     Archivos:
       - app/modules/libros/models.py      Libro, LibroAutor
       - app/modules/clientes/models.py    Cliente, PerfilCliente
       - app/modules/ventas/models.py      Venta, RenglonVenta  (etapa 4)

     Conceptos clave:
       - Agregacion: libro.editorial_id NOT NULL, ON DELETE RESTRICT
       - Agregacion opcional: libro.genero_id NULL, ON DELETE SET NULL
       - Objeto de asociacion: libro_autor con rol y orden propios,
         PK compuesta (libro_id, autor_id)
       - Composicion: renglon_venta.venta_id, ON DELETE CASCADE
       - Composicion vs asociacion se distinguen por el ON DELETE
       - Uno a uno: uq_perfil_cliente_cliente_id UNIQUE
       - Cliente.perfil es un objeto, no una lista
       - El dinero es NUMERIC + Decimal, nunca float
       - fecha es TIMESTAMP WITH TIME ZONE

     Verificado:
       - configure_mappers() sin errores: las referencias adelantadas
         entre modulos resuelven bien
       - Las 8 FK con su ON DELETE correcto
       - Los 8 indices de FK presentes (los de libro_autor los cubre
         la PK compuesta)
       - Navegacion declarada en los 2 extremos de las 7 relaciones
       - La base sigue con 0 tablas

     Estado: COMPLETADA el 2026-10-10


[X] ETAPA 4 - Modelos de venta: composicion                           [ 25%]

     Objetivo: la entidad que registra un hecho inmutable.

     Archivos:
       - app/modules/ventas/models.py    Venta, RenglonVenta

     Conceptos clave:
       - Composicion: renglon_venta.venta_id, ON DELETE CASCADE
       - Asociacion: venta.cliente_id, ON DELETE RESTRICT
       - El total y el precio_unitario los calcula el servidor (RN-06, RN-07)
       - fecha la pone el servidor con server_default now()

     Verificado:
       - CHECK total >= 0, CHECK cantidad > 0, CHECK precio_unitario > 0
       - NUMERIC(12,2) en venta.total, NUMERIC(10,2) en renglon_venta

     Estado: COMPLETADA el 2026-10-10


[X] ETAPA 5 - Migraciones con Alembic                                  [ 10%]

     Objetivo: versionar el esquema. Prohibido usar create_all.

     Archivos:
       - alembic.ini                  con sqlalchemy.url VACIO
       - migrations/env.py            plantilla asincronica, lee el .env
       - migrations/versions/b469c2e9997b_crear_tablas_iniciales.py
       - migrations/versions/d29720c70b22_agregar_tabla_genero_y_columna_libro_.py

     Conceptos clave:
       - target_metadata = SQLModel.metadata es lo que hace que el
         autogenerate sepa que comparar
       - El autogenerate compara MODELOS contra BASE, asi que hay que
         aplicar la migracion N antes de generar la N+1
       - alembic downgrade -1 deshace la ultima migracion

     Migraciones entregadas (las dos que pide la consigna):
       - 1: las 8 tablas menos genero
       - 2: agrega la tabla genero y la columna libro.genero_id

     Correcciones manuales hechas al leer las migraciones generadas:
       - Ambas tenian sqlmodel.sql.sqltypes.AutoString() pero sin
         import de sqlmodel: NameError al ejecutar. Cambiado a sa.String()
       - La 2 ademas generaba la FK sin nombre, por lo que el downgrade
         era op.drop_constraint(None, ...) y PostgreSQL lo rechaza.
         Se le dio el nombre fk_libro_genero_id.
       - Cada correccion esta explicada con un comentario en el propio
         archivo de migracion, como pide la consigna.

     Verificado:
       - upgrade head sobre la base vacia: 9 tablas creadas
       - downgrade -1: desaparece genero y libro.genero_id (0 columnas)
       - upgrade head de nuevo: vuelven las 9 tablas
       - alembic current: d29720c70b22 (head)
       - 21 pruebas de restriccion, 21 correctas, 0 fallidas:
         UNIQUE de isbn y email, CHECK de precio/stock/cantidad/
         precio_unitario/total/orden/rol, FK obligatorias y la opcional,
         UNIQUE del perfil (RN-09), y los 4 ON DELETE
         (CASCADE en composicion, RESTRICT en asociacion, SET NULL
         en la agregacion opcional)

     Estado: COMPLETADA el 2026-10-10


[X] ETAPA 6 - Contratos y CRUD de editoriales                          [ 15%]

     Objetivo: la plantilla base que los demas modulos van a copiar.

     Archivos:
       - app/modules/editoriales/schemas.py    EditorialCreate / Update / Read
                                                + LibroResumen
       - app/modules/editoriales/service.py    logica y traduccion de errores
       - app/modules/editoriales/router.py     los 5 endpoints
       - app/main.py                           + registro del router

     Endpoints:
       POST   /editoriales/               201, 409, 422
       GET    /editoriales/               200, 422   (limit 1-100 def 20, offset >= 0)
       GET    /editoriales/{id}           200, 404, 422
       PATCH  /editoriales/{id}           200, 404, 409
       GET    /editoriales/{id}/libros    200, 404

     Conceptos clave:
       - Create no lleva id, Update no lleva id, Read si
       - model_dump(exclude_unset=True): solo toca los campos que el
         cliente envio. Sin esto, un PATCH borraria los campos no enviados
       - Query(ge=1, le=100) hace que FastAPI devuelva 422 sin ejecutar
         el handler
       - IntegrityError -> 409 con mensaje propio (RN-12), con rollback
         antes de levantar la excepcion
       - config.from_attributes=True para leer el objeto de tabla en el DTO
       - El router es fino: recibe, delega, declara. Logica en el service.

     Problemas encontrados y resueltos:
       - AsyncSession de SQLAlchemy no tiene .exec(): se cambio la clase
         de sesion en core/database.py a sqlmodel.ext.asyncio.session
       - Mapper de Libro no encontraba RenglonVenta al arrancar: los
         modelos no estaban todos registrados. Se creo el registro central
         en app/modules/__init__.py, que main.py importa.

     Correccion posterior (2026-10-13):
        - Los listados se hacian con LIMIT y OFFSET pero sin ORDER BY.
          PostgreSQL no garantiza un orden cuando no hay ORDER BY, asi que
          una pagina podia repetir filas o saltear otras.
        - listar ahora ordena por Editorial.nombre. Como nombre es UNIQUE,
          el orden es total y la paginacion queda estable.
        - listar_libros ordena por Libro.titulo y despues por Libro.id.
          El id va al final a proposito: dos libros pueden tener el mismo
          titulo, y el desempate por id es lo que vuelve total el orden.
        - Regla para las etapas 7 a 13: todo listado ordena antes de
          limitar. Si la columna por la que se ordena no es unica, el
          desempate va por id.

     Verificado: 29 pruebas, 29 correctas, 0 fallidas.
       Incluye 201, 404, 409, 422, paginacion con offset real, y que el
       409 no filtre nombres de restricciones ni texto de PostgreSQL.
       Ademas, tras la correccion del ORDER BY: las 4 editoriales salen en
       orden alfabetico, limit=1 recorre las 4 paginas sin repetir ni
       saltear, y limit=2 con offset 0, 2, 4 y 6 no se pisan entre si.
       Los 404 y los 422 siguen igual.

     Estado: COMPLETADA el 2026-10-10


[X] ETAPA 7 - Contratos y CRUD de generos y autores                   [ 15%]

     Objetivo: replicar la plantilla de la etapa 6.

     Archivos:
       - app/modules/generos/schemas.py   GeneroCreate, GeneroRead
       - app/modules/generos/service.py   crear, listar, obtener_por_id,
                                          listar_libros
       - app/modules/generos/router.py    3 endpoints
       - app/modules/autores/schemas.py   AutorCreate, AutorUpdate,
                                          AutorRead, AutoriaRead
       - app/modules/autores/service.py   crear, obtener_por_id,
                                          actualizar, listar_libros
       - app/modules/autores/router.py    4 endpoints
       - app/modules/libros/schemas.py    LibroResumen (DTO compartido)
       - app/main.py                      +2 routers

     Endpoints:
       POST   /generos/               201, 409, 422
       GET    /generos/               200, 422  (limit 1-100 def 20, offset >= 0)
       GET    /generos/{id}/libros    200, 404, 422
       POST   /autores/               201, 422
       GET    /autores/{id}           200, 404, 422
       PATCH  /autores/{id}           200, 404, 422
       GET    /autores/{id}/libros    200, 404, 422

     Conceptos clave:
       - GET /autores/{id}/libros devuelve rol y orden
       - Sin unicidad en autor, por eso no hay 409
       - Rol y orden NO viven en libro ni en autor: viven en libro_autor.
         Por eso la consulta no puede ser "los libros del autor 3" sino
         un select que trae Libro mas las dos columnas de libro_autor,
         united por un join en la misma consulta.
       - AutoriaRead no lleva from_attributes: sus datos salen de dos
         tablas, asi que no hay un solo objeto del cual leerlos y se
         construye campo por campo. Los demas Read si lo llevan.
       - session.exec() acepta un select de varias tablas y devuelve
         tuplas; se comprobo antes de escribir el service.
       - El 409 es la TRADUCCION de una negativa de la base. Sin
         restriccion que la base pueda aplicar, no hay nada que
         traducir. Por eso autores/service.py:crear no tiene el
         try/except IntegrityError que si tiene generos.
       - Sin try/except no se pierde nada: la unica barrera posible en
         el alta de un autor es el DTO, y ahi el codigo es 422.

     Decisiones tomadas:
       - GET /generos/ se pagina aunque la consigna lo liste "sin
         cuerpo": manda RN-10. Por el mismo motivo los dos listados de
         sub-recursos (/generos/{id}/libros y /autores/{id}/libros)
         tambien llevan limit y offset.
       - No se agregan GET /generos/{id} ni GET /autores/ porque la
         consigna no los pide y el criterio es "modulos minimos".
       - No hay GeneroUpdate: sin PATCH /generos/{id} seria un DTO
         muerto.
       - LibroResumen ahora vive en libros/schemas.py, que es su
         lugar natural. Queda una copia identica en
         editoriales/schemas.py sin tocar, porque la etapa 6 esta
         cerrada; consolidar es un cambio de un minuto.
       - Los campos desconocidos se ignoran en silencio, que es el
         comportamiento por defecto de Pydantic. No se aplica
         extra="forbid": cambiaria el contrato de los modulos ya
         cerrados y la consigna no lo pide.

     Verificado:
       - 201 en POST /generos/ y en POST /autores/
       - 409 con genero repetido: mensaje propio, sin una sola palabra
         del texto de la base, y sin dejar fila (asi se prueba que el
         rollback de service.py funciona)
       - Dos autores identicos se crean los dos (201 y 201). No es un
         olvido: lo confirman tres lugares de la consigna, la tabla del
         modelo dice "Sin restricciones extra" para autor, RN-01 y
         RN-02 solo mencionan ISBN y email, y la tabla de endpoints
         lista 201, 422 para POST /autores/ contra 201, 409 para
         POST /generos/.
       - PATCH parcial: cambia el nombre y deja la nacionalidad
         intacta. Sin exclude_unset=True la nacionalidad volveria a
         None y la base la rechazaria por NOT NULL. PATCH {} tampoco
         toca nada.
       - 404 en GET, PATCH y /libros sobre id inexistente
       - 422 con id no entero (C-01) y con limit 0, limit 101 u
         offset negativo
       - El 404 corta antes del join: la peticion emite 1 sola
         consulta SQL, el SELECT del autor. El join con libro_autor no
         llega a ejecutarse.
       - C-07: /autores/{id}/libros con 3 libros y con 1 libro emite 2
         consultas en los dos casos. El numero no crece con la cantidad
         de libros.
       - Paginacion de /autores/{id}/libros: limit=1 recorre las 3
         paginas sin repetir ni saltear; offset fuera de rango da [].
       - El precio se serializa como '1000.00', string, no float.

     Estado: COMPLETADA el 2026-10-13


[X] ETAPA 8 - Libros: alta con autores y busqueda                    [ 20%]

      Objetivo: el primer caso de alta con relaciones.

      Archivos:
        - app/modules/libros/schemas.py     AutoriaCreate, LibroCreate,
                                             LibroUpdate, LibroDetalle,
                                             LibroLista (+ LibroResumen
                                             repuesto: lo importa
                                             generos/router.py)
        - app/modules/libros/service.py     crear, listar, obtener_por_id,
                                             actualizar
        - app/modules/libros/router.py      4 endpoints
        - app/main.py                        + registro del router

      Endpoints:
        POST   /libros/                201, 409, 422
        GET    /libros/                200, 422  (limit 1-100 def 20,
                                                 offset >= 0, titulo,
                                                 genero_id)
        GET    /libros/{id}            200, 404, 422
        PATCH  /libros/{id}            200, 404, 409, 422

      Conceptos clave:
        - El alta recibe editorial_id, genero_id y la lista de autores
        - Cada autor viaja con autor_id mas rol y orden
        - Sin if consultando antes: se escribe y la base rechaza (409)
        - Filtro por titulo con parametros ligados, sin SQL armado (RN-11)
        - Precargas: joinedload para editorial y genero,
          selectinload para las autorias y sus autores
        - El flush con autoflush=False es lo que asigna libro.id antes
          de insertar las filas de libro_autor
        - El PATCH no toca autores: LibroUpdate no tiene ese campo

      Decisiones tomadas:
        - Autor duplicado en la misma lista -> lo rechaza la PK
          (libro_id, autor_id) y se responde 409, sin validacion previa
          en Python. Coherente con "sin if consultando antes".
        - PATCH {} no toca nada; PATCH {"genero_id": null} desvincula
          el genero (se distingue con exclude_unset=True).
        - PATCH con isbn de otro libro -> 409.
        - Regla de la etapa 6 respetada: todo listado ordena por
          (titulo, id) antes de limitar.

      Verificado: 41 pruebas, 41 correctas, 0 fallidas (2026-10-13,
        PostgreSQL 18.4, base creada + upgrade head a d29720c70b22).
        Incluye 201 con detalle completo (editorial, genero, autores
        con rol y orden; precio como string '21000.00'), 409 con isbn
        repetido / editorial inexistente / autor inexistente / autor
        duplicado en lista (C-04, mensaje propio sin texto de la base,
        y sin dejar fila), 422 (precio 0, rol invalido, limit 0/101,
        offset negativo, id no entero C-01), 404 en GET y PATCH,
        filtro case-insensitive, filtro por genero_id, paginacion
        estable, C-08 (' OR '1'='1 -> 200 []), y N+1 fijo: el detalle
        emite 3 consultas con 2 autores y 3 con 5 autores.

      Datos de prueba que quedaron en la base: 2 editoriales, 1 genero,
        5 autores y 3 libros con nombre "TEST ...". Son de desarrollo;
        la Etapa 13 (seed) los puede reemplazar o convivir con ellos.

      Estado: COMPLETADA el 2026-10-13


[X] ETAPA 9 - Clientes y perfil uno a uno                              [ 20%]

      Objetivo: el caso del UNIQUE en una relacion uno a uno.

      Archivos:
        - app/modules/clientes/schemas.py    ClienteCreate / Update / Read,
                                             PerfilCreate / PerfilRead
                                             (email con EmailStr)
        - app/modules/clientes/service.py    crear_cliente, obtener_por_id,
                                             actualizar, crear_perfil
        - app/modules/clientes/router.py     4 endpoints
        - app/main.py                        + registro del router

      Endpoints:
        POST   /clientes/               201, 409, 422
        GET    /clientes/{id}           200, 404, 422
        PATCH  /clientes/{id}           200, 404, 409, 422
        POST   /clientes/{id}/perfil    201, 404, 409, 422

      Conceptos clave:
        - POST /clientes/{id}/perfil: el segundo perfil da 409 (RN-09)
        - Cliente.perfil es un objeto, no una lista
        - GET /clientes/{id} devuelve el cliente con su perfil
        - joinedload para el uno a uno: el detalle sale en 1 consulta
        - El 404 del cliente va ANTES de insertar el perfil: sin
          cliente no hay perfil que crear, y el codigo correcto es
          404 aunque la FK tambien rechazaria

      Problemas encontrados y resueltos:
        - crear_cliente armaba el DTO sobre el objeto recien creado,
          que nunca habia cargado perfil: leer cliente.perfil
          disparaba una carga perezosa (prohibida por la consigna y
          que en async falla con MissingGreenlet). Se agrego
          await session.refresh(cliente, ["perfil"]) tras el commit:
          1 consulta eager, nada perezoso.

      Decisiones tomadas:
        - GET /clientes/{id}/ventas queda para la Etapa 10: su
          respuesta necesita los DTOs de venta, que viven ahi.
        - Email con formato validado (EmailStr de Pydantic): el 422
          por formato invalido sale antes de tocar la base.

      Verificado: 24 pruebas, 24 correctas, 0 fallidas (2026-10-13).
        Incluye 201 de cliente (con perfil null) y de perfil, C-02
        (email repetido, 409 con mensaje propio sin texto de la base),
        C-03 (segundo perfil, 409, sin dejar fila: el GET sigue
        mostrando el primero), 404 en GET/PATCH/perfil sobre id
        inexistente, 409 en PATCH con email de otro cliente, 422
        (email invalido, cuerpo incompleto, id no entero C-01),
        PATCH {} sin cambios, y detalle en 1 sola consulta con y
        sin perfil.

      Datos de prueba que quedaron en la base: 3 clientes "TEST ..."
        (uno con perfil). Se suman a los de la Etapa 8.

      Estado: COMPLETADA el 2026-10-13


[ ] ETAPA 10 - Ventas: alta con renglones anidados                     [ 20%]

     Objetivo: el caso de composicion y de reglas calculadas.

     Reglas que se implementan aca:
       - RN-04  los renglones viajan dentro del cuerpo de la venta
       - RN-05  al menos un renglón y sin libros repetidos (422)
       - RN-06  el precio se copia del libro, nunca viaja en el DTO
       - RN-07  el total lo calcula el servidor
       - RN-08  las ventas no se modifican: no hay PATCH

     Estado: pendiente


[ ] ETAPA 11 - Lecturas sin N+1                                       [ 10%]

     Objetivo: que el detalle de un libro y de una venta use una cantidad
               FIJA de consultas, sin importar cuantos autores o renglones
               tenga.

     Como se verifica:
       - Poner ECHO_SQL=true en el .env
       - Comparar la cantidad de consultas con 1 autor y con 5 autores
       - El numero tiene que ser el mismo (evidencia del caso C-07)

     Estado: pendiente


[ ] ETAPA 12 - Asincronia sin bloqueos y aviso en segundo plano        [ 10%]

     Objetivo: que ningun handler bloquee el event loop.

     Conceptos clave:
       - Todos los handlers son async def
       - BackgroundTasks para el aviso del comprobante
       - El aviso simula espera con await asyncio.sleep(0.5) y un log
       - Corre DESPUES de enviar la respuesta

     Estado: pendiente


[ ] ETAPA 13 - Seed, casos de prueba y README                         [   -]

     Objetivo: dejar el proyecto entregable.

     Archivos:
       - script de carga de datos iniciales
       - test/*.http con los casos C-01 a C-08
       - README.md con los pasos para levantar desde cero
       - Evidencia del caso C-07 (captura de la consola)

     Estado: pendiente


================================================================================
 NOTAS
================================================================================

 - Reparto en el grupo:
     etapas 0 a 7  : primer integrador (este repo, avance actual)  [completo]
     etapas 8 a 13 : companeros de grupo
   Las etapas 0 a 6 ya cubren el 100% de los criterios de evaluacion
   de la consigna. La etapa 7 no suma criterios nuevos: es mas de la
   categoria "Contratos y CRUD", asi que el peso acumulado no se mueve.

 - Al cerrar cada etapa, actualizar el estado y los contadores de este
   archivo.

 - El archivo .env NUNCA se versiona. env.example es la unica fuente de la
   forma de la variable.

 - La Etapa 0 se marca [PRERREQUISITO] y no "0%": la consigna no tiene una
   categoria de evaluacion para "instalar dependencias". Su trabajo real se
   evalua dentro de "Proyecto, conexion y ciclo de vida" (10%), que es la
   Etapa 1. Por eso el peso acumulado se movio recien al cerrar la Etapa 1.

 - Si en cualquier momento una migracion autogenerada sale mal, se corrige a
   mano y se explica con un comentario en el propio archivo de migracion.

 - La consigna prohibe: autenticacion, repositorios/Unit of Work, y colas
   con Redis. No hacen falta.

================================================================================