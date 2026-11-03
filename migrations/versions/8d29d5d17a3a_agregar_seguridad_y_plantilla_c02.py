"""agregar seguridad, cliente.usuario_id y libro.borrado_en

Revision ID: 8d29d5d17a3a
Revises: d29720c70b22
Create Date: 2026-11-03 17:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8d29d5d17a3a'
down_revision: Union[str, Sequence[str], None] = 'd29720c70b22'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'usuario',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=254), nullable=False),
        sa.Column('nombre', sa.String(length=200), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('activo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('debe_cambiar_password', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_usuario_email'), 'usuario', ['email'], unique=True)

    op.create_table(
        'asignacion_rol',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('rol', sa.String(length=20), nullable=False),
        sa.Column('desde', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('vence_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revocada_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('otorgada_por', sa.Integer(), nullable=True),
        sa.CheckConstraint("rol IN ('ADMIN', 'VENDEDOR', 'CLIENTE')", name='ck_asignacion_rol_rol'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['otorgada_por'], ['usuario.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_asignacion_rol_usuario_id'), 'asignacion_rol', ['usuario_id'], unique=False)
    op.create_index(op.f('ix_asignacion_rol_otorgada_por'), 'asignacion_rol', ['otorgada_por'], unique=False)
    op.create_index(
        'uq_asignacion_rol_abierta',
        'asignacion_rol',
        ['usuario_id', 'rol'],
        unique=True,
        postgresql_where='revocada_en IS NULL',
    )

    op.create_table(
        'intento_acceso',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cuando', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('email', sa.String(length=254), nullable=False),
        sa.Column('ip', sa.String(length=45), nullable=False),
        sa.Column('exito', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_intento_acceso_email_ip_cuando', 'intento_acceso', ['email', 'ip', 'cuando'])

    op.create_table(
        'evento_seguridad',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cuando', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('actor', sa.String(length=200), nullable=False),
        sa.Column('accion', sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.add_column('cliente', sa.Column('usuario_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_cliente_usuario_id'), 'cliente', ['usuario_id'], unique=True)
    op.create_foreign_key('fk_cliente_usuario_id', 'cliente', 'usuario', ['usuario_id'], ['id'], ondelete='SET NULL')

    op.add_column('libro', sa.Column('borrado_en', sa.DateTime(timezone=True), nullable=True))
    op.drop_index(op.f('ix_libro_isbn'), table_name='libro')
    op.create_index('uq_libro_isbn_vigente', 'libro', ['isbn'], unique=True, postgresql_where='borrado_en IS NULL')

    op.create_table(
        'movimiento_stock',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('libro_id', sa.Integer(), nullable=False),
        sa.Column('venta_id', sa.Integer(), nullable=True),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('cantidad', sa.Integer(), nullable=False),
        sa.Column('motivo', sa.String(length=100), nullable=False),
        sa.Column('cuando', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('cantidad <> 0', name='ck_movimiento_stock_cantidad'),
        sa.ForeignKeyConstraint(['libro_id'], ['libro.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['venta_id'], ['venta.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_movimiento_stock_libro_id'), 'movimiento_stock', ['libro_id'], unique=False)
    op.create_index(op.f('ix_movimiento_stock_venta_id'), 'movimiento_stock', ['venta_id'], unique=False)
    op.create_index(op.f('ix_movimiento_stock_usuario_id'), 'movimiento_stock', ['usuario_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_movimiento_stock_usuario_id'), table_name='movimiento_stock')
    op.drop_index(op.f('ix_movimiento_stock_venta_id'), table_name='movimiento_stock')
    op.drop_index(op.f('ix_movimiento_stock_libro_id'), table_name='movimiento_stock')
    op.drop_table('movimiento_stock')

    op.drop_index('uq_libro_isbn_vigente', table_name='libro')
    op.drop_column('libro', 'borrado_en')
    op.create_index(op.f('ix_libro_isbn'), 'libro', ['isbn'], unique=True)

    op.drop_constraint('fk_cliente_usuario_id', 'cliente', type_='foreignkey')
    op.drop_index(op.f('ix_cliente_usuario_id'), table_name='cliente')
    op.drop_column('cliente', 'usuario_id')

    op.drop_table('evento_seguridad')
    op.drop_index('ix_intento_acceso_email_ip_cuando', table_name='intento_acceso')
    op.drop_table('intento_acceso')
    op.drop_index('uq_asignacion_rol_abierta', table_name='asignacion_rol')
    op.drop_index(op.f('ix_asignacion_rol_otorgada_por'), table_name='asignacion_rol')
    op.drop_index(op.f('ix_asignacion_rol_usuario_id'), table_name='asignacion_rol')
    op.drop_table('asignacion_rol')
    op.drop_index(op.f('ix_usuario_email'), table_name='usuario')
    op.drop_table('usuario')
