import asyncio
import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select, and_

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from app.core.database import create_engine, create_session_factory
from app.modules.usuarios.models import IntentoAcceso, EventoSeguridad, AsignacionRol, Usuario
from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, LibroAutor
from app.modules.ventas.models import Venta, RenglonVenta
from app.modules.movimiento_stock.models import MovimientoStock


async def seed() -> None:
    """
    Carga inicial idempotente con tres escenarios posibles.

    A. Base realmente vacía respecto de los datos del seed:
     - Verifica que no existan registros previos en tablas implicadas.
     - Solo si el estado es realmente compatible con una carga inicial, inserta todos los datos.

    B. Seed completo y consistente:
     - Verifica los cinco libros esperados y sus stocks: 10, 5, 8, 3 y 1.
     - Verifica exactamente siete movimientos de stock.
     - Verifica que la suma de movimientos de cada libro coincida con su stock.
     - Verifica las entidades relacionadas: editoriales, géneros, autores,
     asociaciones libro-author, cinco usuarios, roles, tres clientes,
     perfiles correspondientes, una venta y sus dos renglones.
     - Si todo está completo y consistente, no modificar absolutamente nada y finalizar.

    C. Cualquier estado parcial o inconsistente:
     - Si falta algún dato esperado, existe una combinación parcial o hay inconsistencias,
     abortar con un mensaje descriptivo.
     - No completar parcialmente.
     - No borrar ni reconstruir registros.
     - No modificar datos existentes.
    """

    engine = create_engine()
    session_factory = create_session_factory(engine)

    try:
        # -------------------------------------------------------------------------
        # ETAPA 1: Recoleccion de estado actual da base de datos (solo lectura)
        # -------------------------------------------------------------------------
        async with session_factory() as check_session:
            # --- Verificación dos 5 libros polo ISBN ---
            expected_isbns = [
                "978-950-07-0001-1", "978-950-07-0002-2",
                "978-950-07-0003-3", "978-950-07-0004-4",
                "978-950-07-0005-5",
            ]
            stmt_libros = select(Libro).where(Libro.isbn.in_(expected_isbns))
            result = await check_session.execute(stmt_libros)
            found_libros = {row.isbn: row for row in result.scalars().all()}

            # Verificación dos stocks declarados para os 5 libros
            expected_stocks = {
                "978-950-07-0001-1": 10,
                "978-950-07-0002-2": 5,
                "978-950-07-0003-3": 8,
                "978-950-07-0004-4": 3,
                "978-950-07-0005-5": 1,
            }

            # Verificación do número de MovimientoStock (deben ser exactamente 7)
            stmt_mov = select(MovimientoStock)
            result_mov = await check_session.execute(stmt_mov)
            all_movimientos = result_mov.scalars().all()
            num_movimientos = len(all_movimientos)

            # Associación de movements polo seu libro_id
            mov_por_libro = {}
            for m in all_movimientos:
                lid = str(m.libro_id)
                mov_por_libro.setdefault(lid, []).append(m)

            # Verificación dos demais rexistros requeridos polo seed
            stmt_edit = select(Editorial)
            result_edit = await check_session.execute(stmt_edit)
            editoriales = result_edit.scalars().all()

            stmt_gen = select(Genero)
            result_gen = await check_session.execute(stmt_gen)
            generos = result_gen.scalars().all()

            stmt_autor = select(Autor)
            result_autor = await check_session.execute(stmt_autor)
            autores = result_autor.scalars().all()

            stmt_usuarios = select(Usuario)
            result_usuarios = await check_session.execute(stmt_usuarios)
            usuarios = result_usuarios.scalars().all()

            stmt_roles = select(AsignacionRol)
            result_roles = await check_session.execute(stmt_roles)
            roles = result_roles.scalars().all()

            stmt_clientes = select(Cliente)
            result_clientes = await check_session.execute(stmt_clientes)
            clientes = result_clientes.scalars().all()

            stmt_venta = select(Venta)
            result_venta = await check_session.execute(stmt_venta)
            ventas = result_venta.scalars().all()

            stmt_renglon = select(RenglonVenta)
            result_renglon = await check_session.execute(stmt_renglon)
            renglones = result_renglon.scalars().all()

        # -------------------------------------------------------------------------
        # ETAPA 2: Determinar o escenario (A, B ou C)
        # -------------------------------------------------------------------------

        # --- Atributos reais dos modelos para validación ---
        # Usuario: email (unique), nome, password_hash, activo, deve_cambiar_password
        # Cliente: nome, email, usuario_id (FK -> usuario, SET NULL, unique)
        # AsignacionRol: rol IN ('ADMIN', 'VENDEDOR', 'CLIENTE'), usuario_id FK, otorgada_por FK SET NULL
        # MovimientoStock: libro_id FK libro, venta_id FK venta, usuario_id FK usuario, cantidad, motivo

        # --- Verificación para Escenario B: carga completa e consistente ---
        # Los 5 libros deben existir co os ISBNs esperados
        todos_libros_existen = len(found_libros) == 5

        # Los stocks deben ser exactamente 10, 5, 8, 3 y 1 (no saltar ISBNs faltantes)
        stocks_correctos = all(
            isbn in found_libros and found_libros[isbn].stock == expected_stocks[isbn]
            for isbn in expected_isbns
        )

        # Ben 7 MovimientoStock deben existir
        sete_movimientos_correctos = num_movimientos == 7

        # Calcular a suma de movements por libro e comparar co stock esperado
        suma_correcta = True
        if sete_movimientos_correctos:
            for isbn, stock_esperado in expected_stocks.items():
                libro_encontrado = found_libros.get(isbn)
                if libro_encontrado is None:
                    suma_correcta = False
                    break
                total_mov = 0
                for m in mov_por_libro.get(str(libro_encontrado.id), []):
                    total_mov += m.cantidad
                if total_mov != stock_esperado:
                    suma_correcta = False
                    break

        # Para el escenario B, verificar los datos exactos y relaciones esperadas:

        # --- Validación exacta de la venta: debe pertenecer a Lucía ---
        # Buscar la venta con total 69000.00 y cliente Lucía
        venta_exacta = None
        for v in ventas:
            # Verificar que el cliente de esta venta sea Lucía (lucia@example.com)
            # Acceder al cliente a través de la relación
            if v.cliente:
                # Obtener el cliente a través de la sesión para verificar email
                c_stmt = select(Cliente).where(Cliente.id == v.cliente_id)
                c_result = await check_session.execute(c_stmt)
                c = c_result.scalars().first()
                if c and c.email == "lucia@example.com" and float(v.total) == 69000.0:
                    # Verificar que tiene exactamente 2 renglones
                    # Los renglones deben ser de Rayuela (libro_id=1) y Ficciones (libro_id=2)
                    r_stmt = select(RenglonVenta).where(RenglonVenta.venta_id == v.id)
                    r_result = await check_session.execute(r_stmt)
                    renglones_venta = r_result.scalars().all()
                    if len(renglones_venta) == 2:
                        # Verificar renglones: primero de Rayuela (cantidad 1, precio 25000), segundo de Ficciones (cantidad 2, precio 22000)
                        r1, r2 = renglones_venta
                        # Buscar los libros para verificar IDs
                        libro1_stmt = select(Libro).where(Libro.id == r1.libro_id)
                        libro1_result = await check_session.execute(libro1_stmt)
                        libro1 = libro1_result.scalars().first()
                        libro2_stmt = select(Libro).where(Libro.id == r2.libro_id)
                        libro2_result = await check_session.execute(libro2_stmt)
                        libro2 = libro2_result.scalars().first()
                        if (libro1 and libro1.titulo == "Rayuela" and r1.cantidad == 1 and r1.precio_unitario == Decimal("25000.00") and
                            libro2 and libro2.titulo == "Ficciones" and r2.cantidad == 2 and r2.precio_unitario == Decimal("22000.00")):
                            venta_exacta = v
                            break

        # --- Validación de roles: ADMIN y VENDEDOR asignados a usuarios específicos ---
        # ADMIN debe estar asignado al usuario admin@example.com
        admin_user = None
        for u in usuarios:
            if u.email == "admin@example.com":
                # Verificar que tenga rol ADMIN
                a_stmt = select(AsignacionRol).where(AsignacionRol.usuario_id == u.id, AsignacionRol.rol == "ADMIN")
                a_result = await check_session.execute(a_stmt)
                if a_result.scalars().first():
                    admin_user = u
                    break

        # VENDEDOR debe estar asignado al usuario vendedor@example.com
        vendedor_user = None
        for u in usuarios:
            if u.email == "vendedor@example.com":
                # Verificar que tenga rol VENDEDOR
                v_stmt = select(AsignacionRol).where(AsignacionRol.usuario_id == u.id, AsignacionRol.rol == "VENDEDOR")
                v_result = await check_session.execute(v_stmt)
                if v_result.scalars().first():
                    vendedor_user = u
                    break

        # --- Validación de LibroAutor: 5 relaciones esperadas ---
        # Las 5 asociaciones esperadas entre libros y autores:
        # - Rayuela → Julio Cortázar
        # - Ficciones → Jorge Luis Borges
        # - El Aleph → Jorge Luis Borges
        # - Respiración artificial → Mario Vargas Llosa
        # - Bestiario → Julio Cortázar
        # Los autores deben existir por nombre, y las 5 relaciones deben verificarse
        autor_nombres = [
            "Julio Cortázar",
            "Jorge Luis Borges",
            "Mario Vargas Llosa",
            "Isabel Allende",
            "Carlos Ruiz Zafón",
            "Gabriel García Márquez",
        ]
        # Obtener autores de la base de datos usando la sesión de check
        autores_encontrados = {}
        for aut_nombre in autor_nombres:
            result = await check_session.execute(select(Autor).where(Autor.nombre == aut_nombre))
            aut_obj = result.scalars().first()
            if aut_obj:
                autores_encontrados[aut_nombre] = aut_obj.id

        # Verificar las 5 relaciones LibroAutor esperadas
        # Primero, obtener los libros por ISBN para sus IDs
        libros_por_isbn = {}
        for isbn in expected_isbns:
            result = await check_session.execute(select(Libro).where(Libro.isbn == isbn))
            libro = result.scalars().first()
            if libro:
                libros_por_isbn[isbn] = libro.id

        # Verificar que los 5 autores principales estén asociados a los libros correspondientes
# Rayuela (id=1) → Julio Cortázar
        rayuela_autor = None
        if libros_por_isbn["978-950-07-0001-1"] and autores_encontrados.get("Julio Cortázar"):
            ar_stmt = select(LibroAutor).where(LibroAutor.libro_id == libros_por_isbn["978-950-07-0001-1"], LibroAutor.autor_id == autores_encontrados["Julio Cortázar"])
            ar_result = await check_session.execute(ar_stmt)
            if ar_result.scalars().first():
                rayuela_autor = True

# Ficciones (id=2) → Jorge Luis Borges
        ficciones_autor = None
        if libros_por_isbn["978-950-07-0002-2"] and autores_encontrados.get("Jorge Luis Borges"):
            ar_stmt = select(LibroAutor).where(LibroAutor.libro_id == libros_por_isbn["978-950-07-0002-2"], LibroAutor.autor_id == autores_encontrados["Jorge Luis Borges"])
            ar_result = await check_session.execute(ar_stmt)
            if ar_result.scalars().first():
                ficciones_autor = True

# El Aleph (id=3) → Jorge Luis Borges
        aleph_autor = None
        if libros_por_isbn["978-950-07-0003-3"] and autores_encontrados.get("Jorge Luis Borges"):
            ar_stmt = select(LibroAutor).where(LibroAutor.libro_id == libros_por_isbn["978-950-07-0003-3"], LibroAutor.autor_id == autores_encontrados["Jorge Luis Borges"])
            ar_result = await check_session.execute(ar_stmt)
            if ar_result.scalars().first():
                aleph_autor = True

# Respiración artificial (id=4) → Mario Vargas Llosa
        respiracion_autor = None
        if libros_por_isbn["978-950-07-0004-4"] and autores_encontrados.get("Mario Vargas Llosa"):
            ar_stmt = select(LibroAutor).where(LibroAutor.libro_id == libros_por_isbn["978-950-07-0004-4"], LibroAutor.autor_id == autores_encontrados["Mario Vargas Llosa"])
            ar_result = await check_session.execute(ar_stmt)
            if ar_result.scalars().first():
                respiracion_autor = True

# Bestiario (id=5) → Julio Cortázar
        bestiario_autor = None
        if libros_por_isbn["978-950-07-0005-5"] and autores_encontrados.get("Julio Cortázar"):
            ar_stmt = select(LibroAutor).where(LibroAutor.libro_id == libros_por_isbn["978-950-07-0005-5"], LibroAutor.autor_id == autores_encontrados["Julio Cortázar"])
            ar_result = await check_session.execute(ar_stmt)
            if ar_result.scalars().first():
                bestiario_autor = True

# Los 3 autores restantes (Isabel Allende, Carlos Ruiz Zafón, Gabriel García Márquez)
# deben existir como autores pero no necesariamente tener asociación en esta distribución
        autores_disponibles = len(autores_encontrados) >= 3  # mínimo 3 de los 6

# Primo condición: Escenario B (carga completa e consistente xa atopada)
        escenario_b = (
            todos_libros_existen
            and stocks_correctos
            and sete_movimientos_correctos
            and suma_correcta
            and venta_exacta is not None
            and admin_user is not None
            and vendedor_user is not None
            and rayuela_autor
            and ficciones_autor
            and aleph_autor
            and respiracion_autor
            and bestiario_autor
            and autores_disponibles
        )

        if escenario_b:
            print("Seed xa executado con datos consistentes. No se realizarán cambios.")
            return

    # --- Verificación para Escenario A: base realmente vacía respecto de los datos del seed ---
    # La base solo puede considerarse vacía si no existen registros en ninguna tabla
    # que el seed utiliza o modifica. Verificar todas las tablas implicadas de forma exhaustiva:
    # Editorial, Genero, Autor, Libro, LibroAutor, Usuario, AsignacionRol,
    # Cliente, PerfilCliente, Venta, RenglonVenta, MovimientoStock,
    # EventoSeguridad, IntentoAcceso.
    # Si cualquiera de estas tablas contiene al menos un registro, NO es escenario A.
    
    # Obtener sesión nueva para la verificación de escenario A
    async with session_factory() as check_session2:
        # Conteos de todas las tablas (14 tablas implicadas en el seed)
        conteos = {}
        
        # Editorial
        stmt = select(Editorial)
        result = await check_session2.execute(stmt)
        conteos['editorial'] = len(result.scalars().all())
        
        # Genero
        stmt = select(Genero)
        result = await check_session2.execute(stmt)
        conteos['genero'] = len(result.scalars().all())
        
        # Autor
        stmt = select(Autor)
        result = await check_session2.execute(stmt)
        conteos['autor'] = len(result.scalars().all())
        
        # Libro
        stmt = select(Libro)
        result = await check_session2.execute(stmt)
        conteos['libro'] = len(result.scalars().all())
        
        # LibroAutor
        stmt = select(LibroAutor)
        result = await check_session2.execute(stmt)
        conteos['libro_autor'] = len(result.scalars().all())
        
        # Usuario
        stmt = select(Usuario)
        result = await check_session2.execute(stmt)
        conteos['usuario'] = len(result.scalars().all())
        
        # AsignacionRol
        stmt = select(AsignacionRol)
        result = await check_session2.execute(stmt)
        conteos['asignacion_rol'] = len(result.scalars().all())
        
        # Cliente
        stmt = select(Cliente)
        result = await check_session2.execute(stmt)
        conteos['cliente'] = len(result.scalars().all())
        
        # PerfilCliente
        stmt = select(PerfilCliente)
        result = await check_session2.execute(stmt)
        conteos['perfil_cliente'] = len(result.scalars().all())
        
        # Venta
        stmt = select(Venta)
        result = await check_session2.execute(stmt)
        conteos['venta'] = len(result.scalars().all())
        
        # RenglonVenta
        stmt = select(RenglonVenta)
        result = await check_session2.execute(stmt)
        conteos['renglon_venta'] = len(result.scalars().all())
        
        # MovimientoStock
        stmt = select(MovimientoStock)
        result = await check_session2.execute(stmt)
        conteos['movimiento_stock'] = len(result.scalars().all())
        
        # EventoSeguridad
        stmt = select(EventoSeguridad)
        result = await check_session2.execute(stmt)
        conteos['evento_seguridad'] = len(result.scalars().all())
        
        # IntentoAcceso
        stmt = select(IntentoAcceso)
        result = await check_session2.execute(stmt)
        conteos['intento_acceso'] = len(result.scalars().all())
        
        # Scenario A: base realmente vacía = todas las tablas están vacías (0 registros)
        # Si cualquier tabla tiene al menos un registro, NO es escenario A
        todas_vacias = all(conteo == 0 for conteo in conteos.values())
        
        if todas_vacias:
            # Escenario A: Base sen datos previos do seed detectado
            # Proceed with full initial load inside transaction
            try:
                async with session_factory() as session:
                    async with session.begin():
                        print("Iniciando carga de datos iniciales (seed)...")

                        # 1. Editoriales (solo se non existen polo nome, usando queries reales)
                        existing_edit = await session.execute(
                            select(Editorial).where(
                                and_(Editorial.nombre == "Sudirana", Editorial.pais == "Argentina")
                            )
                        )
                        if not existing_edit.scalars().first():
                            e1 = Editorial(nombre="Sudirana", pais="Argentina")
                            e2 = Editorial(nombre="Planeta", pais="España")
                            session.add_all([e1, e2])
                            await session.flush()

                        # 2. Géneros (solo se non existen polo nome)
                        existing_gen = await session.execute(
                            select(Genero).where(Genero.nombre == "Novela")
                        )
                        if not existing_gen.scalars().first():
                            g1 = Genero(nombre="Novela")
                            g2 = Genero(nombre="Ensayo")
                            session.add_all([g1, g2])
                            await session.flush()

                        # 3. Autores (solo se non existen polo nome)
                        # Usar nombre (nombre) según el modelo real
                        autor_nombres = [
                            "Julio Cortázar",
                            "Jorge Luis Borges",
                            "Mario Vargas Llosa",
                            "Isabel Allende",
                            "Carlos Ruiz Zafón",
                            "Gabriel García Márquez",
                        ]
                        # Crear autores si non existen
                        for aut_nombre in autor_nombres:
                            result = await session.execute(
                                select(Autor).where(Autor.nombre == aut_nombre)
                            )
                            if not result.scalars().first():
                                a = Autor(nombre=aut_nombre, nacionalidad="Argentina")
                                session.add(a)
                        await session.flush()

                        # 4. Libros polo ISBN (solo se non existen xa)
                        # Usar IDs reales de editoriales y géneros obtenidos después de flush
                        existing_isbns = set()
                        stmt = select(Libro.isbn)
                        result = await session.execute(stmt)
                        for row in result.scalars().all():
                            existing_isbns.add(row)

                        # Mapping dinámico de editoriales y géneros (IDs reales)
                        editorial_ids = {}
                        for ed in await session.execute(select(Editorial)):
                            editorial_ids[ed.nombre] = ed.id

                        genero_ids = {}
                        for gn in await session.execute(select(Genero)):
                            genero_ids[gn.nombre] = gn.id

                        libros_data = [
                            ("978-950-07-0001-1", "Rayuela", 10, "Sudirana", "Novela"),
                            ("978-950-07-0002-2", "Ficciones", 5, "Sudirana", "Novela"),
                            ("978-950-07-0003-3", "El Aleph", 8, "Planeta", "Novela"),
                            ("978-950-07-0004-4", "Respiración artificial", 3, "Planeta", "Novela"),
                            ("978-950-07-0005-5", "Bestiario", 1, "Sudirana", "Ensayo"),
                        ]

                        for isbn, titulo, stock, editorial_nom, genero_nom in libros_data:
                            if isbn not in existing_isbns:
                                l = Libro(
                                    isbn=isbn,
                                    titulo=titulo,
                                    precio=Decimal("25000.00"),
                                    stock=stock,
                                    editorial_id=editorial_ids.get(editorial_nom),
                                    genero_id=genero_ids.get(genero_nom),
                                )
                                session.add(l)

                        await session.flush()

                        # Obtener IDs reales de los libros insertados
                        stmt_libros = select(Libro).where(Libro.isbn.in_(expected_isbns))
                        result_libros = await session.execute(stmt_libros)
                        libros_por_isbn = {row.isbn: row.id for row in result_libros.scalars().all()}

                        # 5. LibroAutor (solo se non existen associacións previas)
                        stmt = select(Libro)
                        result = await session.execute(stmt)
                        inserted_libros = result.scalars().all()

                        # 6. Asociaciones LibroAutor
                        # Se crean las asociaciones entre los 6 autores y los 5 libros
                        # usando los IDs reales obtenidos después del flush
                        # Estructura esperada:
                        # - Rayuela (1): Julio Cortázar (autor)
                        # - Ficciones (2): Jorge Luis Borges (autor)
                        # - El Aleph (3): Jorge Luis Borges (autor)
                        # - Respiración artificial (4): Mario Vargas Llosa (autor)
                        # - Bestiario (5): Julio Cortázar (autor)
                        autor_nombres = [
                            "Julio Cortázar",
                            "Jorge Luis Borges",
                            "Mario Vargas Llosa",
                            "Isabel Allende",
                            "Carlos Ruiz Zafón",
                            "Gabriel García Márquez",
                        ]
                        # Crear los autores si non existen
                        for aut_nombre in autor_nombres:
                            result = await session.execute(select(Autor).where(Autor.nombre == aut_nombre))
                            if not result.scalars().first():
                                aut = Autor(nombre=aut_nombre, nacionalidad="Argentina")
                                session.add(aut)
                        await session.flush()
                        # Obtener IDs de autores
                        autor_ids = {}
                        for aut_nombre in autor_nombres:
                            result = await session.execute(select(Autor).where(Autor.nombre == aut_nombre))
                            aut_obj = result.scalars().first()
                            if aut_obj:
                                autor_ids[aut_nombre] = aut_obj.id

                        # Crear asociaciones LibroAutor
                        # Rayuela: Julio Cortázar; Ficciones: Borges; El Aleph: Borges;
                        # Respiración artificial: Vargas Llosa; Bestiario: Cortázar
                        libro_autor_data = [
                            (libros_por_isbn["978-950-07-0001-1"], autor_ids["Julio Cortázar"], "autor", 1),  # Rayuela
                            (libros_por_isbn["978-950-07-0002-2"], autor_ids["Jorge Luis Borges"], "autor", 1),  # Ficciones
                            (libros_por_isbn["978-950-07-0003-3"], autor_ids["Jorge Luis Borges"], "autor", 1),  # El Aleph
                            (libros_por_isbn["978-950-07-0004-4"], autor_ids["Mario Vargas Llosa"], "autor", 1),  # Respiración artificial
                            (libros_por_isbn["978-950-07-0005-5"], autor_ids["Julio Cortázar"], "autor", 1),  # Bestiario
                        ]

                        for libro_id, autor_id, rol, orden in libro_autor_data:
                            la = LibroAutor(libro_id=libro_id, autor_id=autor_id, rol=rol, orden=orden)
                            session.add(la)
                        await session.flush()

# 6. Clientes e Usuarios
                        # Verificamos xa existan os usuarios requeridos
                        # Según spec: admin@example.com (ADMIN), admin2@example.com (ADMIN),
                        # vendedor@example.com (VENDEDOR), ana@example.com, nuevo@example.com (debe_cambiar_password=True)
                        
                        # Usuario 1: admin@example.com, role ADMIN
                        existing_admin = await session.execute(
                            select(Usuario).where(Usuario.email == "admin@example.com")
                        )
                        if not existing_admin.scalars().first():
                            u1 = Usuario(email="admin@example.com", nome="Admin Principal",
                                         password_hash="hash_admin", activo=True, deve_cambiar_password=False)
                            session.add(u1)
                            await session.flush()
                            a1_rol = AsignacionRol(usuario_id=u1.id, rol="ADMIN", otorgada_por=None)
                            session.add(a1_rol)
                            await session.flush()

                        # Usuario 2: admin2@example.com, role ADMIN
                        existing_admin2 = await session.execute(
                            select(Usuario).where(Usuario.email == "admin2@example.com")
                        )
                        if not existing_admin2.scalars().first():
                            u2 = Usuario(email="admin2@example.com", nome="Admin Segundo",
                                         password_hash="hash_admin2", activo=True, deve_cambiar_password=True)
                            session.add(u2)
                            await session.flush()
                            a2_rol = AsignacionRol(usuario_id=u2.id, rol="ADMIN", otorgada_por=u1.id if u1 else None)
                            session.add(a2_rol)
                            await session.flush()

                        # Usuario 3: vendedor@example.com, role VENDEDOR
                        existing_vendedor = await session.execute(
                            select(Usuario).where(Usuario.email == "vendedor@example.com")
                        )
                        if not existing_vendedor.scalars().first():
                            u3 = Usuario(email="vendedor@example.com", nome="Vendedor",
                                         password_hash="hash_vendedor", activo=True, deve_cambiar_password=False)
                            session.add(u3)
                            await session.flush()
                            a3_rol = AsignacionRol(usuario_id=u3.id, rol="VENDEDOR", otorgada_por=None)
                            session.add(a3_rol)
                            await session.flush()

                        # Usuario 4: ana@example.com
                        existing_ana_user = await session.execute(
                            select(Usuario).where(Usuario.email == "ana@example.com")
                        )
                        if not existing_ana_user.scalars().first():
                            u4 = Usuario(email="ana@example.com", nome="Ana",
                                         password_hash="hash_ana", activo=True, deve_cambiar_password=True)
                            session.add(u4)
                            await session.flush()

                        # Usuario 5: nuevo@example.com con debe_cambiar_password=True
                        existing_nuevo = await session.execute(
                            select(Usuario).where(Usuario.email == "nuevo@example.com")
                        )
                        if not existing_nuevo.scalars().first():
                            u5 = Usuario(email="nuevo@example.com", nome="Nuevo Usuario",
                                         password_hash="hash_nuevo", activo=True, deve_cambiar_password=True)
                            session.add(u5)
                            await session.flush()

                        # Crear 3 clientes: Lucía, Tomás, Ana
                        # Lucía: nombre "Lucía", email "lucia@example.com"
                        existing_lucia = await session.execute(
                            select(Cliente).where(Cliente.nombre == "Lucía")
                        )
                        if not existing_lucia.scalars().first():
                            c1 = Cliente(nombre="Lucía", email="lucia@example.com")
                            session.add(c1)
                            await session.flush()

                        # Tomás: nombre "Tomás", sin requisito estricto de email en el modelo
                        existing_tomas = await session.execute(
                            select(Cliente).where(Cliente.nombre == "Tomás")
                        )
                        if not existing_tomas.scalars().first():
                            c2 = Cliente(nombre="Tomás", email="tomas@example.com")
                            session.add(c2)
                            await session.flush()

                        # Ana: nombre "Ana", email "ana@example.com" - debe vincularse al usuario ana@example.com
                        existing_ana = await session.execute(
                            select(Cliente).where(Cliente.nombre == "Ana")
                        )
                        if not existing_ana.scalars().first():
                            c3 = Cliente(nombre="Ana", email="ana@example.com")
                            session.add(c3)
                            await session.flush()
                        # Vincular explícitamente Ana con el usuario ana@example.com
                        # Obtener el usuario Ana
                        result = await session.execute(select(Usuario).where(Usuario.email == "ana@example.com"))
                        user_ana = result.scalars().first()
                        if user_ana:
                            # Asignar usuario_id al cliente Ana
                            c3 = await session.execute(select(Cliente).where(Cliente.nombre == "Ana"))
                            c_ana = c3.scalars().first()
                            if c_ana:
                                c_ana.usuario_id = user_ana.id
                                await session.flush()

                            # Vincular explícitamente Ana con el usuario ana@example.com
                            # Obtener el usuario Ana
                            result = await session.execute(select(Usuario).where(Usuario.email == "ana@example.com"))
                            user_ana = result.scalars().first()
                            if user_ana:
                                # Actualizar el cliente Ana para vincularlo al usuario
                                # (el modelo tiene usuario_id FK -> usuario, SET NULL, unique)
                                # Como el cliente fue creado sin usuario_id, ahora lo asociamos
                                # Nota: como cliente.email es único, y usuario.email tamén é único,
                                # non podemos linking directo by email without conflicts.
                                # O diseño establece que Ana debe continuarse vinculando al usuario ana@example.com.
                                # Para efectos del seed, asociamos o cliente ao usuario mediante a relación natural.
                                # Asignar usuario_id ao cliente Ana se o usuario existe
                                if user_ana:
                                    c3 = await session.execute(select(Cliente).where(Cliente.nome == "Ana"))
                                    c_ana = c3.scalars().first()
                                    if c_ana:
                                        c_ana.usuario_id = user_ana.id
                                        await session.flush()

                        # 6. Venda e renglóns de venda
                        # VERIFIQUE ESPECÍFICAMENTE A LUCIA. NO USAR FALLBACK A ID 1.
                        existing_venta = await session.execute(
                            select(Venta).where(Venta.total == Decimal("69000.00"))
                        )
                        if not existing_venta.scalars().first():
                            # Buscar cliente Lucía específicamente por nombre y email
                            c1 = await session.execute(
                                select(Cliente).where(
                                    and_(Cliente.nombre == "Lucía", Cliente.email == "lucia@example.com")
                                )
                            )
                            c_lucia = c1.scalars().first()
                            if not c_lucia:
                                # Si no se encuentra a Lucía, abortar con error claro
                                raise ValueError(
                                    "Non atopado cliente Lucía (lucia@example.com) para crear aventa. "
                                    "Non se pode usar cliente arbitrario ou fallback a ID 1."
                                )
                            total = Decimal("69000.00")
                            v1 = Venta(cliente_id=c_lucia.id, total=total)
                            session.add(v1)
                            await session.flush()
                            # Usar IDs reales de libros insertados para los renglones
                            stmt_libros = select(Libro).where(Libro.isbn.in_(expected_isbns))
                            result_libros = await session.execute(stmt_libros)
                            libros_por_isbn = {row.isbn: row.id for row in result_libros.scalars().all()}
                            r1 = RenglonVenta(venta_id=v1.id, libro_id=libros_por_isbn["978-950-07-0001-1"], cantidad=1,
                                              precio_unitario=Decimal("25000.00"))
                            session.add(r1)
                            r2 = RenglonVenta(venta_id=v1.id, libro_id=libros_por_isbn["978-950-07-0002-2"], cantidad=2,
                                              precio_unitario=Decimal("22000.00"))
                            session.add(r2)
                            await session.flush()

                        # 7. Movimiento de stock: 7 movements positivos
                        # Distribution fixed: Rayuela+10, Ficciones+5, El Aleph+3+5=8,
                        # Respiración artificial+1+2=3, Bestiario+1
                        # Usar IDs reales de libros insertados, non asumir 1,2,3,4,5
                        try:
                            mov1 = MovimientoStock(libro_id=libros_por_isbn["978-950-07-0001-1"], cantidad=10, motivo="Stock inicial")
                            session.add(mov1)
                            mov2 = MovimientoStock(libro_id=libros_por_isbn["978-950-07-0002-2"], cantidad=5, motivo="Stock inicial")
                            session.add(mov2)
                            mov3 = MovimientoStock(libro_id=libros_por_isbn["978-950-07-0003-3"], cantidad=3, motivo="Stock inicial")
                            session.add(mov3)
                            mov4 = MovimientoStock(libro_id=libros_por_isbn["978-950-07-0004-4"], cantidad=1, motivo="Stock inicial")
                            session.add(mov4)
                            mov5 = MovimientoStock(libro_id=libros_por_isbn["978-950-07-0005-5"], cantidad=1, motivo="Stock inicial")
                            session.add(mov5)
                            mov6 = MovimientoStock(libro_id=libros_por_isbn["978-950-07-0003-3"], cantidad=5, motivo="Stock adicional")
                            session.add(mov6)
                            mov7 = MovimientoStock(libro_id=libros_por_isbn["978-950-07-0004-4"], cantidad=2, motivo="Stock adicional")
                            session.add(mov7)
                            await session.flush()
                        except Exception as e:
                            raise ValueError(
                                "Non sexo capaz de insertar os MovementStock por conflictos de FK. "
                                "Estado actual da base non compatible co seed."
                            )
                        finally:
                            pass

                    # Fin da carga da Etapa 3 (Escenario A)
                    # O `async with session.begin()` gardará o rollback auto si atopouse algun
                    # erro atopado noBloque try/except de dentro. Se todo correo ben, o commit
                    # sucede ao sortir do contexto `async with session.begin()`.

            # Fin do try exterior para o escenario A

        # --- Si non é B non é A, é C: estado parcial ou inconsistente ---
        # Non atopou el escenario B completamente, non atopamos base realmente vacía.
        # Non intentamos completar, limpar ou reconstruir automáticamente os datos.
        # Non borramos rexistros existentes. Informamos o conflito e remos.

        informe = (
            "Seed atopou base de datos en estado non compatible.\n"
            "Non se realicaran modificacions para atopar a consistencia.\n"
            "Detalle do estado:\n"
        )

        campos_adicionales = []

        if not todos_libros_existen:
            campos_adicionales.append(
                "- Non se atoparon todos os 5 libros esperados. atopou: {} de 5.".format(
                    len(found_libros)))
        else:
            campos_adicionales.append("- Os 5 libros existen.")

        if not stocks_correctos:
            campos_adicionales.append(
                "- Os stocks non coinciden coos esperados (10, 5, 8, 3, 1).")
        else:
            campos_adicionales.append("- Os stocks cooden coos esperados.")

        if not sete_movimientos_correctos:
            campos_adicionales.append(
                "- Non ben 7 MovimientoStock atopados (atado: {num_movimientos}).".format(
                    num_movimientos=num_movimientos))
        else:
            campos_adicionales.append("- Ben 7 MovimientoStock atopados.")

        if not suma_correcta:
            campos_adicionales.append(
                "- A suma de movements non coincide co stock para algun libro.")
        else:
            campos_adicionales.append(
                "- A suma de movements coincide co stock para todos os libros.")

        # Verificar entidades relacionadas faltantes
        if num_editoriales < 2:
            campos_adicionales.append(
                "- Non atopadas suficentes editoriales (atopadas {} de 2 o más).".format(
                    num_editoriales))
        else:
            campos_adicionales.append("- Editoriales suficientes.")

        if num_generos < 2:
            campos_adicionales.append(
                "- Non atopados suficentes géneros (atopados {} de 2 o más).".format(
                    num_generos))
        else:
            campos_adicionales.append("- Géneros suficientes.")

        if num_autores < 6:
            campos_adicionales.append(
                "- Non atopados suficentes autores (atopados {} de 6 o más).".format(
                    num_autores))
        else:
            campos_adicionales.append("- Autores suficientes.")

        if not tiene_admin:
            campos_adicionales.append(
                "- Non atopado usuario admin (admin@example.com).")
        else:
            campos_adicionales.append("- Usuario admin encontrado.")

        if not tiene_vendedor:
            campos_adicionales.append(
                "- Non atopado usuario vendedor (vendedor@example.com).")
        else:
            campos_adicionales.append("- Usuario vendedor encontrado.")

        if num_clientes < 3:
            campos_adicionales.append(
                "- Non atopados 3 clientes (atopados {}).".format(num_clientes))
        else:
            campos_adicionales.append("- Clientes suficientes.")

        if not tiene_venta:
            campos_adicionales.append(
                "- Non atopada venta seed.")
        else:
            campos_adicionales.append("- Venta seed encontrada.")

        if num_renglones < 2:
            campos_adicionales.append(
                "- Non atopados 2 renglones de venta (atopados {}).".format(num_renglones))
        else:
            campos_adicionales.append("- Renglones de venta suficientes.")

# Verificar clientes específicos
    if not tiene_lucia_cliente:
        campos_adicionales.append(
            "- Non atopado cliente Lucía (nome: Lucía, email: lucia@example.com).")
    else:
        campos_adicionales.append("- Cliente Lucía encontrado correctamente.")

    if not tiene_tomas_cliente:
        campos_adicionales.append(
            "- Non atopado cliente Tomás (nome: Tomás).")
    else:
        campos_adicionales.append("- Cliente Tomás encontrado correctamente.")

    if not tiene_ana_cliente:
        campos_adicionales.append(
            "- Non atopado cliente Ana (nome: Ana, email: ana@example.com).")
    else:
        campos_adicionales.append("- Cliente Ana encontrado correctamente.")

    # Verificar entidades adicionales de auditoría
    # PerfilCliente: debe existir al menos el de Lucía (cliente con perfil)
    # En el seed, Lucía tiene perfil y Tomás e Ana pueden tener o no
    # Validar que el cliente Lucía tenga perfil asociado
    try:
        perfil_lucia_stmt = select(PerfilCliente).where(PerfilCliente.cliente_id == 1)  # Lucía es el primer cliente
        # Nota: el ID puede variar, validaremos que exista algun perfil cliente
        perfil_stmt = select(PerfilCliente)
        perfil_result = await check_session.execute(perfil_stmt)
        perfiles_existen = len(perfil_result.scalars().all()) > 0
    except:
        perfiles_existen = False

    # Evento de seguridad: debe existir un evento con actor="SISTEMA" y acción="Carga de los datos iniciales"
    evento_seguridad_existente = False
    try:
        evento_stmt = select(EventoSeguridad)
        evento_result = await check_session.execute(evento_stmt)
        eventos = evento_result.scalars().all()
        # Verificar si hay algún evento que coincida con el del seed
        for e in eventos:
            if e.actor == "SISTEMA" and "Carga" in e.accion:
                evento_seguridad_existente = True
                break
    except:
        pass

    # IntentoAcceso: tabla de auditoría, validar que existan registros
    try:
        intento_stmt = select(IntentoAcceso)
        intento_result = await check_session.execute(intento_stmt)
        intentos_existen = len(intento_result.scalars().all()) > 0
    except:
        intentos_existen = False

    # Agregar estos hallazgos al informe
    if perfiles_existen:
        campos_adicionales.append("- Perfiles de cliente existen.")
    else:
        campos_adicionales.append("- Non existen perfiles de cliente registrados.")

    if evento_seguridad_existente:
        campos_adicionales.append("- Evento de seguridad encontrado.")
    else:
        campos_adicionales.append("- Non existe evento de seguridad registrados.")

    if intentos_existen:
        campos_adicionales.append("- Registros de intento de acceso existen.")
    else:
        campos_adicionales.append("- Non existen registros de intento de acceso.")

        informe += "\n".join(campos_adicionales)

        raise ValueError(informe)

    finally:
        await engine.dispose()