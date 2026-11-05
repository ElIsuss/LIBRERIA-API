import sys
import unittest
from pathlib import Path
from uuid import uuid4

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import event

from app.core.database import create_engine, create_session_factory
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.clientes.repository import ClienteRepository
from app.modules.usuarios.models import Usuario


class TestClienteRepository(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_engine()
        self.session_factory = create_session_factory(self.engine)
        self.session = self.session_factory()
        sufijo = uuid4().hex[:12]

        self.usuario = Usuario(
            email=f"usuario_{sufijo}@test.com",
            nombre="Usuario de Prueba",
            password_hash="hash-de-prueba",
            activo=True,
            debe_cambiar_password=False,
        )
        self.session.add(self.usuario)
        await self.session.flush()

        self.cliente_con_perfil = Cliente(
            nombre="Cliente Con Perfil",
            email=f"conperfil_{sufijo}@test.com",
            usuario_id=self.usuario.id,
        )
        self.session.add(self.cliente_con_perfil)
        await self.session.flush()

        self.perfil = PerfilCliente(
            cliente_id=self.cliente_con_perfil.id,
            telefono="1144556677",
            direccion="Av. Siempre Viva 123",
        )
        self.session.add(self.perfil)

        self.cliente_sin_perfil = Cliente(
            nombre="Cliente Sin Perfil",
            email=f"sinperfil_{sufijo}@test.com",
        )
        self.session.add(self.cliente_sin_perfil)
        await self.session.flush()

        self.usuario_id = self.usuario.id
        self.cliente_con_perfil_id = self.cliente_con_perfil.id
        self.cliente_sin_perfil_id = self.cliente_sin_perfil.id
        self.session.expire_all()

    async def asyncTearDown(self):
        await self.session.rollback()
        await self.session.close()
        await self.engine.dispose()

    def _escuchar_selects(self):
        consultas = []

        def registrar(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                consultas.append(statement)

        event.listen(self.engine.sync_engine, "before_cursor_execute", registrar)
        return consultas, registrar

    def _dejar_de_escuchar(self, registrar):
        event.remove(self.engine.sync_engine, "before_cursor_execute", registrar)

    async def test_get_detalle_precarga_perfil_sin_consulta_adicional(self):
        repo = ClienteRepository(self.session)
        consultas, registrar = self._escuchar_selects()
        try:
            cliente = await repo.get_detalle(self.cliente_con_perfil_id)
            self.assertIsNotNone(cliente)
            self.assertIsNotNone(cliente.perfil)
            self.assertEqual(cliente.perfil.telefono, "1144556677")
        finally:
            self._dejar_de_escuchar(registrar)

        self.assertEqual(len(consultas), 1)

    async def test_get_detalle_sin_perfil_devuelve_none(self):
        repo = ClienteRepository(self.session)
        consultas, registrar = self._escuchar_selects()
        try:
            cliente = await repo.get_detalle(self.cliente_sin_perfil_id)
            self.assertIsNotNone(cliente)
            self.assertIsNone(cliente.perfil)
        finally:
            self._dejar_de_escuchar(registrar)

        self.assertEqual(len(consultas), 1)

    async def test_get_by_usuario_id_encuentra_la_ficha_vinculada(self):
        repo = ClienteRepository(self.session)
        cliente = await repo.get_by_usuario_id(self.usuario_id)

        self.assertIsNotNone(cliente)
        self.assertEqual(cliente.id, self.cliente_con_perfil_id)

    async def test_get_by_usuario_id_sin_ficha_devuelve_none(self):
        repo = ClienteRepository(self.session)
        cliente = await repo.get_by_usuario_id(self.usuario_id + 999999)

        self.assertIsNone(cliente)

    async def test_repositorio_y_uow_no_ejecutan_commit_ni_rollback(self):
        from unittest.mock import AsyncMock, patch

        from sqlmodel.ext.asyncio.session import AsyncSession

        from app.modules.clientes.unit_of_work import ClientesUnitOfWork

        uow = ClientesUnitOfWork(self.session)
        email = f"espia_{uuid4().hex[:12]}@test.com"

        with patch.object(AsyncSession, "commit", new=AsyncMock()) as commit_mock:
            with patch.object(AsyncSession, "rollback", new=AsyncMock()) as rollback_mock:
                creado = await uow.clientes.add(
                    Cliente(nombre="Cliente Espía", email=email)
                )
                encontrado = await uow.clientes.get_detalle(creado.id)
                encontrado.nombre = "Cliente Espía Actualizado"
                await uow.clientes.update(encontrado)
                await uow.clientes.get_by_usuario_id(self.usuario_id)

        commit_mock.assert_not_awaited()
        rollback_mock.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
