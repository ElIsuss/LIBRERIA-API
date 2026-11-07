#!/usr/bin/env python3
"""Script de carga inicial de datos (Seed).

Carga el estado inicial del proyecto Librería API según la consigna oficial del Parcial.
Uso desde la raíz del proyecto:
    python seed.py
"""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

# Asegurar que la raíz del proyecto esté en sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import text
from app.core.database import create_engine, create_session_factory
from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, LibroAutor, MovimientoStock
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, Usuario
from app.modules.ventas.models import RenglonVenta, Venta

# Hash de bcrypt válido para la contraseña por defecto 'password123'
DEFAULT_PASSWORD_HASH = "$2b$12$Es1N.sORv9.ytYYmjo2jJeigmCEh15RIeE78iT3KLgmpL2t8gQ/dW"


async def seed() -> None:
    engine = create_engine()
    session_factory = create_session_factory(engine)

    print("🌱 Iniciando carga de datos iniciales (seed)...")

    async with session_factory() as session:
        async with session.begin():
            # 0. Vaciado limpio de tablas para garantizar idempotencia
            # TRUNCATE CASCADE reinicia secuencias y no dispara el trigger append-only de UPDATE/DELETE
            print("  -> Vaciando tablas previas...")
            await session.execute(
                text(
                    """
                    TRUNCATE TABLE 
                        evento_seguridad, 
                        intento_acceso, 
                        movimiento_stock, 
                        renglon_venta, 
                        venta, 
                        perfil_cliente, 
                        cliente, 
                        libro_autor, 
                        libro, 
                        autor, 
                        genero, 
                        editorial, 
                        asignacion_rol, 
                        usuario 
                    RESTART IDENTITY CASCADE;
                    """
                )
            )

            # 1. Editoriales (3)
            print("  -> Insertando editoriales...")
            e1 = Editorial(nombre="Sudamericana", pais="Argentina")
            e2 = Editorial(nombre="Planeta", pais="España")
            e3 = Editorial(nombre="Siglo XXI", pais="México")
            session.add_all([e1, e2, e3])
            await session.flush()

            # 2. Géneros (3)
            print("  -> Insertando géneros...")
            g1 = Genero(nombre="Novela")
            g2 = Genero(nombre="Cuento")
            g3 = Genero(nombre="Ensayo")
            session.add_all([g1, g2, g3])
            await session.flush()

            # 3. Autores (6)
            print("  -> Insertando autores...")
            a1 = Autor(nombre="Julio Cortázar", nacionalidad="Argentina")
            a2 = Autor(nombre="Jorge Luis Borges", nacionalidad="Argentina")
            a3 = Autor(nombre="Mario Vargas Llosa", nacionalidad="Peru")
            a4 = Autor(nombre="Isabel Allende", nacionalidad="Chile")
            a5 = Autor(nombre="Carlos Ruiz Zafón", nacionalidad="España")
            a6 = Autor(nombre="Gabriel García Márquez", nacionalidad="Colombia")
            session.add_all([a1, a2, a3, a4, a5, a6])
            await session.flush()

            # 4. Libros (5) con sus stocks finales esperados
            # Rayuela (stock 10: 11 inicial - 1 venta)
            # Antología (stock 5: 5 inicial)
            # Ficciones (stock 8: 10 inicial - 2 venta)
            # Respiración artificial (stock 3: 3 inicial)
            # Bestiario (stock 1: 1 inicial)
            print("  -> Insertando catálogo de libros...")
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
                titulo="Antología de la literatura fantástica",
                precio=Decimal("22000.00"),
                stock=5,
                editorial_id=e1.id,
                genero_id=g2.id,
            )
            l3 = Libro(
                isbn="978-950-07-0003-3",
                titulo="Ficciones",
                precio=Decimal("22000.00"),
                stock=8,
                editorial_id=e2.id,
                genero_id=g2.id,
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

            # 5. Asociaciones LibroAutor
            la1 = LibroAutor(libro_id=l1.id, autor_id=a1.id, rol="autor", orden=1)
            la2 = LibroAutor(libro_id=l2.id, autor_id=a2.id, rol="autor", orden=1)
            la3 = LibroAutor(libro_id=l3.id, autor_id=a2.id, rol="autor", orden=1)
            la4 = LibroAutor(libro_id=l4.id, autor_id=a3.id, rol="autor", orden=1)
            la5 = LibroAutor(libro_id=l5.id, autor_id=a1.id, rol="autor", orden=1)
            session.add_all([la1, la2, la3, la4, la5])
            await session.flush()

            # 6. Usuarios (5) y Roles
            print("  -> Insertando usuarios y roles...")
            u1 = Usuario(
                email="admin@example.com",
                nombre="Admin Principal",
                password_hash=DEFAULT_PASSWORD_HASH,
                activo=True,
                debe_cambiar_password=False,
            )
            u2 = Usuario(
                email="admin2@example.com",
                nombre="Admin Segunda",
                password_hash=DEFAULT_PASSWORD_HASH,
                activo=True,
                debe_cambiar_password=False,
            )
            u3 = Usuario(
                email="vendedor@example.com",
                nombre="Vendedor",
                password_hash=DEFAULT_PASSWORD_HASH,
                activo=True,
                debe_cambiar_password=False,
            )
            u4 = Usuario(
                email="ana@example.com",
                nombre="Ana",
                password_hash=DEFAULT_PASSWORD_HASH,
                activo=True,
                debe_cambiar_password=False,
            )
            u5 = Usuario(
                email="nuevo@example.com",
                nombre="Nuevo",
                password_hash=DEFAULT_PASSWORD_HASH,
                activo=True,
                debe_cambiar_password=True,
            )
            session.add_all([u1, u2, u3, u4, u5])
            await session.flush()

            rol_u1 = AsignacionRol(usuario_id=u1.id, rol="ADMIN", otorgada_por=None)
            rol_u2 = AsignacionRol(usuario_id=u2.id, rol="ADMIN", otorgada_por=None)
            rol_u3 = AsignacionRol(usuario_id=u3.id, rol="VENDEDOR", otorgada_por=None)
            rol_u4 = AsignacionRol(usuario_id=u4.id, rol="CLIENTE", otorgada_por=None)
            rol_u5 = AsignacionRol(usuario_id=u5.id, rol="VENDEDOR", otorgada_por=None)
            session.add_all([rol_u1, rol_u2, rol_u3, rol_u4, rol_u5])
            await session.flush()

            # 7. Clientes (3)
            # Lucía (con perfil, sin usuario_id)
            # Tomás (sin perfil, sin usuario_id)
            # Ana (vinculada al usuario ana@example.com)
            print("  -> Insertando clientes...")
            c1 = Cliente(nombre="Lucía Fernández", email="lucia@example.com", usuario_id=None)
            c2 = Cliente(nombre="Tomás Ríos", email="tomas@example.com", usuario_id=None)
            c3 = Cliente(nombre="Ana Paz", email="ana@example.com", usuario_id=u4.id)
            session.add_all([c1, c2, c3])
            await session.flush()

            p1 = PerfilCliente(
                cliente_id=c1.id,
                telefono="1166554433",
                direccion="Av. Figueroa Alcorta 1234",
            )
            session.add(p1)
            await session.flush()

            # 8. Venta inicial (1) de Lucía registrada por vendedor
            # 1 Rayuela ($25.000) + 2 Ficciones ($22.000 x 2 = $44.000) = $69.000
            print("  -> Insertando venta 1 con renglones...")
            v1 = Venta(cliente_id=c1.id, total=Decimal("69000.00"))
            session.add(v1)
            await session.flush()

            r1 = RenglonVenta(
                venta_id=v1.id,
                libro_id=l1.id,
                cantidad=1,
                precio_unitario=l1.precio,
            )
            r2 = RenglonVenta(
                venta_id=v1.id,
                libro_id=l3.id,
                cantidad=2,
                precio_unitario=l3.precio,
            )
            session.add_all([r1, r2])
            await session.flush()

            # 9. Movimientos de stock (7) consistentes:
            # 5 iniciales + 2 salidas por la venta 1
            print("  -> Insertando 7 movimientos de stock auditados...")
            m1 = MovimientoStock(
                libro_id=l1.id,
                cantidad=11,
                motivo="Stock inicial",
                venta_id=None,
                usuario_id=u1.id,
            )
            m2 = MovimientoStock(
                libro_id=l2.id,
                cantidad=5,
                motivo="Stock inicial",
                venta_id=None,
                usuario_id=u1.id,
            )
            m3 = MovimientoStock(
                libro_id=l3.id,
                cantidad=10,
                motivo="Stock inicial",
                venta_id=None,
                usuario_id=u1.id,
            )
            m4 = MovimientoStock(
                libro_id=l4.id,
                cantidad=3,
                motivo="Stock inicial",
                venta_id=None,
                usuario_id=u1.id,
            )
            m5 = MovimientoStock(
                libro_id=l5.id,
                cantidad=1,
                motivo="Stock inicial",
                venta_id=None,
                usuario_id=u1.id,
            )
            # Salidas por la venta 1:
            m6 = MovimientoStock(
                libro_id=l1.id,
                cantidad=-1,
                motivo="Venta",
                venta_id=v1.id,
                usuario_id=u3.id,
            )
            m7 = MovimientoStock(
                libro_id=l3.id,
                cantidad=-2,
                motivo="Venta",
                venta_id=v1.id,
                usuario_id=u3.id,
            )
            session.add_all([m1, m2, m3, m4, m5, m6, m7])
            await session.flush()

            # 10. Evento de auditoría de seguridad
            print("  -> Registrando evento de seguridad inicial...")
            evento1 = EventoSeguridad(
                actor="SISTEMA",
                accion="Carga de los datos iniciales",
            )
            session.add(evento1)
            await session.flush()

    await engine.dispose()
    print("✅ Carga inicial (seed) completada exitosamente.")


if __name__ == "__main__":
    asyncio.run(seed())
