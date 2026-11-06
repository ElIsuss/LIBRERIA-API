import asyncio
import sys
from decimal import Decimal
from pathlib import Path

# Detectar raíz del proyecto: si seed.py está en la raíz, usamos cwd;
# si está en app/, usamos la lógica original de parents[1].
# Esto permite ejecutar desde la raíz: python seed.py
# O desde app/: python -m app.seed (compatibilidad)
ROOT = Path.cwd()
APP_DIR = ROOT / "app"

# Aseguramos que tanto la raíz como app/ estén en el path
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from app.core.database import create_engine, create_session_factory
from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.libros.models import Libro, LibroAutor


async def seed() -> None:
    engine = create_engine()
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        print("Iniciando carga de datos iniciales (seed)...")

        # 1. Editoriales
        e1 = Editorial(nombre="Sudamericana", pais="Argentina")
        e2 = Editorial(nombre="Planeta", pais="España")
        session.add_all([e1, e2])
        await session.flush()

        # 2. Generos
        g1 = Genero(nombre="Novela")
        g2 = Genero(nombre="Ensayo")
        session.add_all([g1, g2])
        await session.flush()

        # 3. Autores
        a1 = Autor(nombre="Julio Cortázar", nacionalidad="Argentina")
        a2 = Autor(nombre="Jorge Luis Borges", nacionalidad="Argentina")
        a3 = Autor(nombre="Mario Vargas Llosa", nacionalidad="Peru")
        a4 = Autor(nombre="Isabel Allende", nacionalidad="Chile")
        a5 = Autor(nombre="Carlos Ruiz Zafón", nacionalidad="España")
        a6 = Autor(nombre="Gabriel García Márquez", nacionalidad="Colombia")
        session.add_all([a1, a2, a3, a4, a5, a6])
        await session.flush()

        # 4. Libros con stock inicial
        l1 = Libro(
            isbn="978-950-07-0001-1",
            titulo="Rayuela",
            precio=Decimal("25000.00"),
            stock=10,
            editorial_id=e1.id,
            genero_id=g1.id,
        )
        l2 = Libro(
            isbn="978-950-07-0002-2",
            titulo="Ficciones",
            precio=Decimal("22000.00"),
            stock=5,
            editorial_id=e1.id,
            genero_id=g1.id,
        )
        l3 = Libro(
            isbn="978-950-07-0003-3",
            titulo="El Aleph",
            precio=Decimal("20000.00"),
            stock=8,
            editorial_id=e2.id,
            genero_id=g1.id,
        )
        l4 = Libro(
            isbn="978-950-07-0004-4",
            titulo="Respiración artificial",
            precio=Decimal("18000.00"),
            stock=3,
            editorial_id=e2.id,
            genero_id=g1.id,
        )
        l5 = Libro(
            isbn="978-950-07-0005-5",
            titulo="Bestiario",
            precio=Decimal("15000.00"),
            stock=1,
            editorial_id=e1.id,
            genero_id=g2.id,
        )
        session.add_all([l1, l2, l3, l4, l5])
        await session.flush()

        # 5. LibroAutor (asociación)
        la1 = LibroAutor(libro_id=l1.id, autor_id=a1.id, rol="autor", orden=1)
        la2 = LibroAutor(libro_id=l2.id, autor_id=a2.id, rol="autor", orden=1)
        la3 = LibroAutor(libro_id=l3.id, autor_id=a2.id, rol="autor", orden=1)
        la4 = LibroAutor(libro_id=l4.id, autor_id=a3.id, rol="autor", orden=1)
        la5 = LibroAutor(libro_id=l5.id, autor_id=a4.id, rol="autor", orden=1)
        session.add_all([la1, la2, la3, la4, la5])
        await session.flush()

        # 6. Clientes y Usuarios
        # Usuario 1: admin
        u1 = Usuario(email="admin@example.com", nombre="Admin Principal", password_hash="hash_admin", activo=True, debe_cambiar_password=False)
        session.add(u1)
        await session.flush()
        a1_rol = AsignacionRol(usuario_id=u1.id, rol="ADMIN", otorgada_por=None)
        session.add(a1_rol)
        await session.flush()

        # Usuario 2: admin2
        u2 = Usuario(email="admin2@example.com", nombre="Admin Segunda", password_hash="hash_admin2", activo=True, debe_cambiar_password=False)
        session.add(u2)
        await session.flush()
        a2_rol = AsignacionRol(usuario_id=u2.id, rol="ADMIN", otorgada_por=None)
        session.add(a2_rol)
        await session.flush()

        # Usuario 3: vendedor
        u3 = Usuario(email="vendedor@example.com", nombre="Vendedor", password_hash="hash_vendedor", activo=True, debe_cambiar_password=False)
        session.add(u3)
        await session.flush()
        a3_rol = AsignacionRol(usuario_id=u3.id, rol="VENDEDOR", otorgada_por=None)
        session.add(a3_rol)
        await session.flush()

        # Usuario 4: ana (sin debe_cambiar_password)
        u4 = Usuario(email="ana@example.com", nombre="Ana", password_hash="hash_ana", activo=True, debe_cambiar_password=False)
        session.add(u4)
        await session.flush()
        a4_rol = AsignacionRol(usuario_id=u4.id, rol="CLIENTE", otorgada_por=None)
        session.add(a4_rol)
        await session.flush()

        # Usuario 5: nuevo (con debe_cambiar_password=True)
        u5 = Usuario(email="nuevo@example.com", nombre="Nuevo", password_hash="hash_nuevo", activo=True, debe_cambiar_password=True)
        session.add(u5)
        await session.flush()
        a5_rol = AsignacionRol(usuario_id=u5.id, rol="VENDEDOR", otorgada_por=None)
        session.add(a5_rol)
        await session.flush()

        # Clientes: Lucía (with perfil, sin usuario_id), Tomás (sin perfil, sin usuario), Ana (vinculada a ana@example.com)
        # Cliente 1: Lucía - tiene perfil pero usuario_id NULL
        c1 = Cliente(nombre="Lucía Fernández", email="lucia@example.com", usuario_id=None)
        session.add(c1)
        await session.flush()
        p1 = PerfilCliente(cliente_id=c1.id, telefono="1166554433", direccion="Av. Figueroa Alcorta 1234")
        session.add(p1)
        await session.flush()

        # Cliente 2: Tomás - sin perfil, sin usuario
        c2 = Cliente(nombre="Tomás Ríos", email="tomas@example.com", usuario_id=None)
        session.add(c2)
        await session.flush()

        # Cliente 3: Ana - vinculada a ana@example.com (usuario u4)
        c3 = Cliente(nombre="Ana Pérez", email="ana@example.com", usuario_id=u4.id)
        session.add(c3)
        await session.flush()
        # Ana puede tener perfil o no, opcional - no añadimos PerfilCliente para mantener el escenario "Ana vinculada por usuario"

        # 7. Venta de ejemplo de Lucía
        # Los libros: Rayuela (l1, precio 25000) y Ficciones (l2, precio 22000)
        # 1 * Rayuela + 2 * Ficciones = 25000 + 2*22000 = 69000.00
        from app.modules.ventas.models import Venta, RenglonVenta
        v1 = Venta(cliente_id=c1.id, total=Decimal("69000.00"))
        session.add(v1)
        await session.flush()
        r1 = RenglonVenta(venta_id=v1.id, libro_id=l1.id, cantidad=1, precio_unitario=l1.precio)
        session.add(r1)
        r2 = RenglonVenta(venta_id=v1.id, libro_id=l2.id, cantidad=2, precio_unitario=l2.precio)
        session.add(r2)
        await session.flush()

        # Movimiento de stock: 7 movimientos cumpliendo libro.stock == SUM(movimiento_stock.cantidad)
        # Distribution: 5 movimientos positivos (stock inicial) + 2 movimientos adicionales
        # para cerrar el total de 7 movimientos registrados.

        # Movimiento 1: Stock inicial Rayuela (+10)
        mov1 = MovimientoStock(libro_id=l1.id, cantidad=10, motivo="Stock inicial", venta_id=None, usuario_id=u1.id)
        session.add(mov1)
        # Movimiento 2: Stock inicial Ficciones (+5)
        mov2 = MovimientoStock(libro_id=l2.id, cantidad=5, motivo="Stock inicial", venta_id=None, usuario_id=u1.id)
        session.add(mov2)
        # Movimiento 3: Stock inicial El Aleph (+8)
        mov3 = MovimientoStock(libro_id=l3.id, cantidad=8, motivo="Stock inicial", venta_id=None, usuario_id=u1.id)
        session.add(mov3)
        # Movimiento 4: Stock inicial Respiración artificial (+3)
        mov4 = MovimientoStock(libro_id=l4.id, cantidad=3, motivo="Stock inicial", venta_id=None, usuario_id=u1.id)
        session.add(mov4)
        # Movimiento 5: Stock inicial Bestiario (+1)
        mov5 = MovimientoStock(libro_id=l5.id, cantidad=1, motivo="Stock inicial", venta_id=None, usuario_id=u1.id)
        session.add(mov5)
        # Movimiento 6: Ajuste de stock adicional (Rayuela)
        mov6 = MovimientoStock(libro_id=l1.id, cantidad=2, motivo="Ajuste de inventario", venta_id=None, usuario_id=u1.id)
        session.add(mov6)
        # Movimiento 7: Ajuste de stock adicional (Ficciones)
        mov7 = MovimientoStock(libro_id=l2.id, cantidad=1, motivo="Ajuste de inventario", venta_id=None, usuario_id=u1.id)
        session.add(mov7)
        await session.flush()

        # 8. 1 evento de seguridad
        from app.modules.usuarios.models import EventoSeguridad
        evento1 = EventoSeguridad(actor="SISTEMA", accion="Carga de los datos iniciales")
        session.add(evento1)
        await session.flush()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())