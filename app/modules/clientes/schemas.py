from pydantic import BaseModel, ConfigDict, EmailStr


class ClienteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str
    email: EmailStr


class ClienteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str | None = None
    email: EmailStr | None = None


class PerfilCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    telefono: str
    direccion: str


class PerfilRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    telefono: str
    direccion: str


class ClienteRead(BaseModel):
    id: int
    nombre: str
    email: EmailStr
    perfil: PerfilRead | None = None
