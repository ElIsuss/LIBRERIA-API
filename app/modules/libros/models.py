from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, Numeric, String, func, text
from sqlmodel import Field, Relationship, SQLModel

from app.modules.autores.models import Autor
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero

if TYPE_CHECKING:
    from app.modules.usuarios.models import Usuario
    from app.modules.ventas.models import RenglonVenta, Venta


class Libro(SQLModel, table=True):
    __tablename__ = "libro"
    __table_args__ = (
        CheckConstraint("precio > 0", name="ck_libro_precio"),
        CheckConstraint("stock >= 0", name="ck_libro_stock"),
        Index("uq_libro_isbn_vigente", "isbn", unique=True, postgresql_where=text("borrado_en IS NULL")),
    )

    id: int | None = Field(default=None, primary_key=True)
    isbn: str = Field(sa_column=Column(String(20), index=True, nullable=False))
    titulo: str = Field(sa_column=Column(String(200), index=True, nullable=False))
    precio: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    stock: int = 0
    editorial_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("editorial.id", ondelete="RESTRICT"),
            index=True,
            nullable=False,
        )
    )
    genero_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("genero.id", ondelete="SET NULL"),
            index=True,
            nullable=True,
        ),
    )
    borrado_en: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))

    editorial: Editorial | None = Relationship(back_populates="libros")
    genero: Genero | None = Relationship(back_populates="libros")
    autorias: list["LibroAutor"] = Relationship(back_populates="libro")
    renglones_venta: list["RenglonVenta"] = Relationship(back_populates="libro")
    movimientos_stock: list["MovimientoStock"] = Relationship(back_populates="libro")


class LibroAutor(SQLModel, table=True):
    __tablename__ = "libro_autor"
    __table_args__ = (
        CheckConstraint("orden >= 1", name="ck_libro_autor_orden"),
        CheckConstraint(
            "rol IN ('autor','coautor','traductor','ilustrador')",
            name="ck_libro_autor_rol",
        ),
    )

    libro_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("libro.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        )
    )
    autor_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("autor.id", ondelete="CASCADE"),
            primary_key=True,
            index=True,
            nullable=False,
        )
    )
    rol: str = Field(sa_column=Column(String(20), nullable=False))
    orden: int

    libro: Libro = Relationship(back_populates="autorias")
    autor: Autor = Relationship(back_populates="autorias")


class MovimientoStock(SQLModel, table=True):
    __tablename__ = "movimiento_stock"
    __table_args__ = (CheckConstraint("cantidad <> 0", name="ck_movimiento_stock_cantidad"),)

    id: int | None = Field(default=None, primary_key=True)
    libro_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("libro.id", ondelete="RESTRICT"),
            index=True,
            nullable=False,
        )
    )
    venta_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("venta.id", ondelete="RESTRICT"),
            index=True,
            nullable=True,
        ),
    )
    usuario_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("usuario.id", ondelete="RESTRICT"),
            index=True,
            nullable=False,
        )
    )
    cantidad: int = Field(sa_column=Column(Integer, nullable=False))
    motivo: str = Field(sa_column=Column(String(100), nullable=False))
    cuando: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )

    libro: "Libro" = Relationship(back_populates="movimientos_stock")
    venta: "Venta" = Relationship(back_populates="movimientos_stock")
    usuario: "Usuario" = Relationship(back_populates="movimientos_stock")