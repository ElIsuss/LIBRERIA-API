from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, Numeric, String
from sqlmodel import Field, Relationship, SQLModel

from app.modules.autores.models import Autor
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero

if TYPE_CHECKING:
    from app.modules.ventas.models import RenglonVenta


class Libro(SQLModel, table=True):
    __tablename__ = "libro"
    __table_args__ = (
        CheckConstraint("precio > 0", name="ck_libro_precio"),
        CheckConstraint("stock >= 0", name="ck_libro_stock"),
    )

    id: int | None = Field(default=None, primary_key=True)
    isbn: str = Field(sa_column=Column(String(20), unique=True, index=True, nullable=False))
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

    editorial: Editorial | None = Relationship(back_populates="libros")
    genero: Genero | None = Relationship(back_populates="libros")
    autorias: list["LibroAutor"] = Relationship(back_populates="libro")
    renglones_venta: list["RenglonVenta"] = Relationship(back_populates="libro")


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