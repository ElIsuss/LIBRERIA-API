import sys
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from unittest.mock import AsyncMock, patch

from sqlalchemy import event, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import create_engine, create_session_factory
from app.modules.clientes.models import Cliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, MovimientoStock
from app.modules.libros.unit_of_work import LibrosUnitOfWork
from app.modules.usuarios.models import Usuario
from app.modules.ventas.models import RenglonVenta, Venta
from app.modules.ventas.repository import VentaRepository
from app.modules.ventas.unit_of_work import VentasUnitOfWork


class TestVentaRepository(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_engine()
        self.session_factory = create_session_factory(self.engine)
        self.session = self.session_factory()
        sufijo = uuid4().hex[:12]
        ahora = datetime.now(timezone.utc)

        editorial = Editorial(nombre=f"Editorial Unit {sufijo}", pais="Argentina")
        genero = Genero(nombre=f"Genero Unit {sufijo}")
        self.session.add(editorial)
        self.session.add(genero)
        await self.session.flush()

        self.usuario = Usuario(
            email=f"usuario_ventas_{sufijo}@test.com",
            nombre="Usuario Ventas Unit",
            password_hash="hash-de-prueba",
            activo=True,
            debe_cambiar_password=False,
        )
        self.session.add(self.usuario)
        await self.session.flush()

        self.cliente_a = Cliente(
            nombre="Cliente A Unit",
            email=f"cliente_a_{sufijo}@test.com",
        )
        self.cliente_b = Cliente(
            nombre="Cliente B Unit",
            email=f"cliente_b_{sufijo}@test.com",
        )
        self.session.add(self.cliente_a)
        self.session.add(self.cliente_b)
        await self.session.flush()

        self.libro_activo = Libro(
            isbn=f"978-unit-a-{sufijo[:6]}",
            titulo="Libro Activo Unit",
            precio=Decimal("100.00"),
            stock=10,
            editorial_id=editorial.id,
            genero_id=genero.id,
        )
        self.libro_baja = Libro(
            isbn=f"978-unit-b-{sufijo[:6]}",
            titulo="Libro Dado de Baja Unit",
            precio=Decimal("50.00"),
            stock=5,
            editorial_id=editorial.id,
            genero_id=genero.id,
            borrado_en=ahora,
        )
        self.session.add(self.libro_activo)
        self.session.add(self.libro_baja)
        await self.session.flush()

        self.venta_a = Venta(
            cliente_id=self.cliente_a.id,
            total=Decimal("250.00"),
            fecha=ahora - timedelta(hours=2),
        )
        self.venta_b = Venta(
            cliente_id=self.cliente_b.id,
            total=Decimal("100.00"),
            fecha=ahora - timedelta(hours=1),
        )
        self.session.add(self.venta_a)
        self.session.add(self.venta_b)
        await self.session.flush()

        self.session.add_all(
            [
                RenglonVenta(
                    venta_id=self.venta_a.id,
                    libro_id=self.libro_activo.id,
                    cantidad=2,
                    precio_unitario=Decimal("100.00"),
                ),
                RenglonVenta(
                    venta_id=self.venta_a.id,
                    libro_id=self.libro_baja.id,
                    cantidad=1,
                    precio_unitario=Decimal("50.00"),
                ),
                RenglonVenta(
                    venta_id=self.venta_b.id,
                    libro_id=self.libro_activo.id,
                    cantidad=1,
                    precio_unitario=Decimal("100.00"),
                ),
            ]
        )
        await self.session.flush()

        self.cliente_a_id = self.cliente_a.id
        self.cliente_b_id = self.cliente_b.id
        self.venta_a_id = self.venta_a.id
        self.venta_b_id = self.venta_b.id
        self.libro_activo_id = self.libro_activo.id
        self.libro_baja_id = self.libro_baja.id
        self.libro_baja_titulo = self.libro_baja.titulo
        self.usuario_id = self.usuario.id
        self.session.expire_all()

    async def asyncTearDown(self):
        await self.session.rollback()
        await self.session.close()
        await self.engine.dispose()

    async def test_get_detalle_precarga_cliente_y_renglones_con_libro_dado_de_baja(self):
        repo = VentaRepository(self.session)
        venta = await repo.get_detalle(self.venta_a_id)

        self.assertIsNotNone(venta)
        self.assertEqual(venta.cliente.id, self.cliente_a_id)
        self.assertEqual(venta.cliente.nombre, "Cliente A Unit")
        self.assertEqual(len(venta.renglones), 2)
        titulos = {renglon.libro.titulo for renglon in venta.renglones}
        self.assertIn(self.libro_baja_titulo, titulos)

    async def test_listar_paginado_devuelve_items_total_y_filtra_por_cliente(self):
        repo = VentaRepository(self.session)
        items, total = await repo.listar_paginado(
            page=1,
            size=10,
            cliente_id=self.cliente_a_id,
        )

        self.assertEqual(total, 1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, self.venta_a_id)
        self.assertEqual(items[0].cliente.id, self.cliente_a_id)
        self.assertEqual(len(items[0].renglones), 2)

    async def test_listar_paginado_sin_filtro_incluye_las_ventas_sembradas(self):
        repo = VentaRepository(self.session)
        items, total = await repo.listar_paginado(page=1, size=10)

        ids = {venta.id for venta in items}
        self.assertIn(self.venta_a_id, ids)
        self.assertIn(self.venta_b_id, ids)
        self.assertEqual(total, len(items))
        self.assertGreaterEqual(total, 2)

    async def test_listar_por_cliente_devuelve_solo_sus_ventas_ordenadas_desc(self):
        venta_antigua = Venta(
            cliente_id=self.cliente_a_id,
            total=Decimal("100.00"),
            fecha=datetime.now(timezone.utc) - timedelta(days=2),
        )
        self.session.add(venta_antigua)
        await self.session.flush()
        self.session.add(
            RenglonVenta(
                venta_id=venta_antigua.id,
                libro_id=self.libro_activo_id,
                cantidad=1,
                precio_unitario=Decimal("100.00"),
            )
        )
        await self.session.flush()
        self.session.expire_all()

        repo = VentaRepository(self.session)
        ventas = await repo.listar_por_cliente(self.cliente_a_id)

        self.assertEqual([venta.id for venta in ventas], [self.venta_a_id, venta_antigua.id])
        self.assertEqual({venta.cliente_id for venta in ventas}, {self.cliente_a_id})
        self.assertTrue(all(len(venta.renglones) >= 1 for venta in ventas))

    async def test_cantidad_de_consultas_de_get_detalle_no_crece_con_los_renglones(self):
        repo = VentaRepository(self.session)
        consultas = []

        def registrar(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                consultas.append(statement)

        event.listen(self.engine.sync_engine, "before_cursor_execute", registrar)
        try:
            self.session.expire_all()
            await repo.get_detalle(self.venta_b_id)
            consultas_un_renglon = len(consultas)

            consultas.clear()
            self.session.expire_all()
            await repo.get_detalle(self.venta_a_id)
            consultas_dos_renglones = len(consultas)
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", registrar)

        self.assertEqual(consultas_un_renglon, consultas_dos_renglones)

    async def test_ventas_uow_reutiliza_el_punto_unico_de_stock_de_libros(self):
        self.assertIs(
            VentasUnitOfWork.registrar_movimiento_stock,
            LibrosUnitOfWork.registrar_movimiento_stock,
        )

        uow = VentasUnitOfWork(self.session)
        libro = await self.session.get(Libro, self.libro_activo_id)
        stock_inicial = libro.stock

        with (
            patch.object(AsyncSession, "commit", new=AsyncMock()) as commit_mock,
            patch.object(AsyncSession, "rollback", new=AsyncMock()) as rollback_mock,
        ):
            movimiento = await uow.registrar_movimiento_stock(
                libro=libro,
                usuario_id=self.usuario_id,
                cantidad=-3,
                motivo="Venta",
                venta_id=self.venta_a_id,
            )

        commit_mock.assert_not_awaited()
        rollback_mock.assert_not_awaited()

        self.assertEqual(libro.stock, stock_inicial - 3)
        self.assertIsNotNone(movimiento.id)
        self.assertEqual(movimiento.libro_id, self.libro_activo_id)
        self.assertEqual(movimiento.usuario_id, self.usuario_id)
        self.assertEqual(movimiento.cantidad, -3)
        self.assertEqual(movimiento.motivo, "Venta")
        self.assertEqual(movimiento.venta_id, self.venta_a_id)

        resultado = await self.session.execute(
            select(MovimientoStock).where(MovimientoStock.id == movimiento.id)
        )
        persistido = resultado.scalar_one()
        self.assertEqual(persistido.cantidad, -3)
        self.assertEqual(persistido.venta_id, self.venta_a_id)


if __name__ == "__main__":
    unittest.main()
