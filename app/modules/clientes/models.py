from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.ventas.models import Venta


class Cliente(SQLModel, table=True):
    __tablename__ = "cliente"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(sa_column=Column(String(200), nullable=False))
    email: str = Field(sa_column=Column(String(254), unique=True, index=True, nullable=False))

    perfil: "PerfilCliente" = Relationship(back_populates="cliente")
    ventas: list["Venta"] = Relationship(back_populates="cliente")


class PerfilCliente(SQLModel, table=True):
    __tablename__ = "perfil_cliente"
    __table_args__ = (UniqueConstraint("cliente_id", name="uq_perfil_cliente_cliente_id"),)

    id: int | None = Field(default=None, primary_key=True)
    cliente_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("cliente.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    telefono: str = Field(sa_column=Column(String(50), nullable=False))
    direccion: str = Field(sa_column=Column(String(300), nullable=False))

    cliente: Cliente = Relationship(back_populates="perfil")