from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    func,
)
from sqlmodel import Field, Relationship, SQLModel

from app.modules.clientes.models import Cliente
from app.modules.libros.models import Libro


class Venta(SQLModel, table=True):
    __tablename__ = "venta"
    __table_args__ = (CheckConstraint("total >= 0", name="ck_venta_total"),)

    id: int | None = Field(default=None, primary_key=True)
    fecha: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        )
    )
    total: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    cliente_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("cliente.id", ondelete="RESTRICT"),
            index=True,
            nullable=False,
        )
    )

    cliente: Cliente = Relationship(back_populates="ventas")
    renglones: list["RenglonVenta"] = Relationship(back_populates="venta")


class RenglonVenta(SQLModel, table=True):
    __tablename__ = "renglon_venta"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_renglon_venta_cantidad"),
        CheckConstraint("precio_unitario > 0", name="ck_renglon_venta_precio_unitario"),
    )

    id: int | None = Field(default=None, primary_key=True)
    venta_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("venta.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        )
    )
    libro_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("libro.id", ondelete="RESTRICT"),
            index=True,
            nullable=False,
        )
    )
    cantidad: int
    precio_unitario: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))

    venta: Venta = Relationship(back_populates="renglones")
    libro: Libro = Relationship(back_populates="renglones_venta")