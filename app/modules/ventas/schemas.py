from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RenglonVentaCreate(BaseModel):
    libro_id: int = Field(gt=0)
    cantidad: int = Field(gt=0)


class VentaCreate(BaseModel):
    cliente_id: int = Field(gt=0)
    renglones: list[RenglonVentaCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validar_libros_sin_repetir(self):
        ids_libros = [renglon.libro_id for renglon in self.renglones]

        if len(ids_libros) != len(set(ids_libros)):
            raise ValueError(
                "No se puede repetir un libro en la misma venta"
            )

        return self


class RenglonVentaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    libro_id: int
    cantidad: int
    precio_unitario: Decimal


class VentaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha: datetime
    total: Decimal
    cliente_id: int
    renglones: list[RenglonVentaRead]
