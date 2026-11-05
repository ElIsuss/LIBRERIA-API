import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pydantic import ValidationError

from app.modules.clientes.schemas import ClienteCreate, ClienteUpdate, PerfilCreate
from app.modules.ventas.schemas import RenglonVentaCreate, VentaCreate


class TestContratosEstrictos(unittest.TestCase):
    def test_venta_create_valida_con_dos_renglones(self):
        venta = VentaCreate(
            cliente_id=1,
            renglones=[
                {"libro_id": 1, "cantidad": 2},
                {"libro_id": 2, "cantidad": 1},
            ],
        )
        self.assertEqual(len(venta.renglones), 2)

    def test_cliente_create_rechaza_campo_extra(self):
        with self.assertRaises(ValidationError):
            ClienteCreate(nombre="Ana", email="ana@example.com", extra="no permitido")

    def test_cliente_create_rechaza_email_invalido(self):
        with self.assertRaises(ValidationError):
            ClienteCreate(nombre="Ana", email="no-es-un-email")

    def test_cliente_update_rechaza_campo_extra(self):
        with self.assertRaises(ValidationError):
            ClienteUpdate(nombre="Ana", extra="no permitido")

    def test_perfil_create_rechaza_campo_extra(self):
        with self.assertRaises(ValidationError):
            PerfilCreate(telefono="123456", direccion="Calle 1", extra="no permitido")

    def test_venta_create_rechaza_total_enviado_por_cliente(self):
        with self.assertRaises(ValidationError):
            VentaCreate(
                cliente_id=1,
                renglones=[{"libro_id": 1, "cantidad": 1}],
                total=100,
            )

    def test_renglon_venta_create_rechaza_precio_unitario(self):
        with self.assertRaises(ValidationError):
            RenglonVentaCreate(libro_id=1, cantidad=1, precio_unitario=10)

        with self.assertRaises(ValidationError):
            VentaCreate(
                cliente_id=1,
                renglones=[{"libro_id": 1, "cantidad": 1, "precio_unitario": 10}],
            )

    def test_venta_create_rechaza_renglones_vacios(self):
        with self.assertRaises(ValidationError):
            VentaCreate(cliente_id=1, renglones=[])

    def test_venta_create_rechaza_cantidad_no_positiva(self):
        with self.assertRaises(ValidationError):
            VentaCreate(cliente_id=1, renglones=[{"libro_id": 1, "cantidad": 0}])

        with self.assertRaises(ValidationError):
            VentaCreate(cliente_id=1, renglones=[{"libro_id": 1, "cantidad": -3}])

    def test_venta_create_rechaza_identificadores_no_positivos(self):
        with self.assertRaises(ValidationError):
            VentaCreate(cliente_id=0, renglones=[{"libro_id": 1, "cantidad": 1}])

        with self.assertRaises(ValidationError):
            VentaCreate(cliente_id=1, renglones=[{"libro_id": 0, "cantidad": 1}])

    def test_venta_create_rechaza_libro_repetido(self):
        with self.assertRaises(ValidationError):
            VentaCreate(
                cliente_id=1,
                renglones=[
                    {"libro_id": 7, "cantidad": 1},
                    {"libro_id": 7, "cantidad": 2},
                ],
            )


if __name__ == "__main__":
    unittest.main()
