import asyncio
from decimal import Decimal
from app.core.database import create_engine, create_session_factory
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.autores.models import Autor
from app.modules.libros.models import Libro, LibroAutor
from app.modules.clientes.models import Cliente, PerfilCliente


async def seed() -> None:
    engine = create_engine()
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        print("🌱 Iniciando carga de datos iniciales (seed)...")

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
        session.add_all([a1, a2])
        await session.flush()

        # 4. Libros
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
            stock=15,
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
        session.add_all([l1, l2, l3])
        await session.flush()

        # 5. LibroAutor (asociación)
        la1 = LibroAutor(libro_id=l1.id, autor_id=a1.id, rol="autor", orden=1)
        la2 = LibroAutor(libro_id=l2.id, autor_id=a2.id, rol="autor", orden=1)
        la3 = LibroAutor(libro_id=l3.id, autor_id=a2.id, rol="autor", orden=1)
        session.add_all([la1, la2, la3])
        await session.flush()

        # 6. Clientes y Perfil
        c1 = Cliente(nombre="Tomás Ríos", email="tomas@example.com")
        session.add(c1)
        await session.flush()

        p1 = PerfilCliente(
            cliente_id=c1.id,
            telefono="1155443322",
            direccion="Av. Corrientes 1234",
        )
        session.add(p1)

        await session.commit()
        print("✅ Datos iniciales cargados con éxito (3 libros creados).")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
