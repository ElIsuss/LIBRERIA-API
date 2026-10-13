from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class LibroResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int