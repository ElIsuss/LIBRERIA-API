"""append-only trigger para movimiento_stock

Revision ID: f22d38b1dde0
Revises: 8d29d5d17a3a
Create Date: 2026-11-03 17:45:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'f22d38b1dde0'
down_revision: Union[str, Sequence[str], None] = '8d29d5d17a3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION impedir_modificacion_movimiento_stock()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'No se permite modificar ni eliminar movimientos de stock';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_movimiento_stock_append_only
        BEFORE UPDATE OR DELETE ON movimiento_stock
        FOR EACH ROW EXECUTE FUNCTION impedir_modificacion_movimiento_stock();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_movimiento_stock_append_only ON movimiento_stock;
        """
    )
    op.execute(
        """
        DROP FUNCTION IF EXISTS impedir_modificacion_movimiento_stock();
        """
    )
