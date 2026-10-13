from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AutorCreate(BaseModel):
    nombre: str
    nacionalidad: str


class AutorUpdate(BaseModel):
    nombre: str | None = None
    nacionalidad: str | None = None


class AutorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    nacionalidad: str


class AutoriaRead(BaseModel):
    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    rol: str
    orden: int