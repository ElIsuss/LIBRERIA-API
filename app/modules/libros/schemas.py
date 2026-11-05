from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RolAutoria = Literal["autor", "coautor", "traductor", "ilustrador"]


class AutoriaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    autor_id: int
    rol: RolAutoria
    orden: int = Field(ge=1)


class LibroCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    isbn: str
    titulo: str
    precio: Decimal = Field(gt=0)
    stock_inicial: int = Field(default=0, ge=0)
    editorial_id: int
    genero_id: int | None = None
    autores: list[AutoriaCreate] = []


class LibroUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    isbn: str | None = None
    titulo: str | None = None
    precio: Decimal | None = Field(default=None, gt=0)
    editorial_id: int | None = None
    genero_id: int | None = None


class ReponerStockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cantidad: int = Field(gt=0)
    motivo: str = Field(default="Reposición", max_length=100)


class MovimientoStockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    libro_id: int
    venta_id: int | None = None
    usuario_id: int
    cantidad: int
    motivo: str
    cuando: datetime


class EditorialEnLibro(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class GeneroEnLibro(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class AutorEnLibro(BaseModel):
    id: int
    nombre: str
    nacionalidad: str
    rol: str
    orden: int


class LibroDetalle(BaseModel):
    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    editorial: EditorialEnLibro
    genero: GeneroEnLibro | None = None
    autores: list[AutorEnLibro] = []
    borrado_en: datetime | None = None


class LibroLista(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    editorial: EditorialEnLibro
    genero: GeneroEnLibro | None = None
    borrado_en: datetime | None = None


class LibroResumen(BaseModel):
    """DTO compartido. Se conserva para compatibilidad."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
