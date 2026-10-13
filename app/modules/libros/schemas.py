from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RolAutoria = Literal["autor", "coautor", "traductor", "ilustrador"]


class AutoriaCreate(BaseModel):
    autor_id: int
    rol: RolAutoria
    orden: int = Field(ge=1)


class LibroCreate(BaseModel):
    isbn: str
    titulo: str
    precio: Decimal = Field(gt=0)
    stock: int = Field(default=0, ge=0)
    editorial_id: int
    genero_id: int | None = None
    autores: list[AutoriaCreate] = []


class LibroUpdate(BaseModel):
    isbn: str | None = None
    titulo: str | None = None
    precio: Decimal | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    editorial_id: int | None = None
    genero_id: int | None = None


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


class LibroLista(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    editorial: EditorialEnLibro
    genero: GeneroEnLibro | None = None


class LibroResumen(BaseModel):
    """DTO compartido (etapa 7). Se conserva para no romper generos/router."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int