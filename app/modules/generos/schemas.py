from pydantic import BaseModel, ConfigDict


class GeneroCreate(BaseModel):
    nombre: str


class GeneroRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str