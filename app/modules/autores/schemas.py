from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AutorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str
    nacionalidad: str


class AutorUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str | None = None
    nacionalidad: str | None = None


class AutorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    nacionalidad: str


class AutoriaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    rol: str
    orden: int
