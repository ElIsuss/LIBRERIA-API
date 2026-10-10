from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class EditorialCreate(BaseModel):
    nombre: str
    pais: str


class EditorialUpdate(BaseModel):
    nombre: str | None = None
    pais: str | None = None


class EditorialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    pais: str


class LibroResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int