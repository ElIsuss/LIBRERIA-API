from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.security import PasswordStr


class RegistroRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: PasswordStr


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: PasswordStr


class CambiarPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password_actual: PasswordStr
    password_nueva: PasswordStr


class LoginResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mensaje: str = "Sesión iniciada"
    debe_cambiar_password: bool
    expira_en_segundos: int


class YoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    email: str
    nombre: str
    debe_cambiar_password: bool
    roles_vigentes: list[str]
    roles_token: list[str]


class MensajeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mensaje: str


class UsuarioAuthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    email: str
    nombre: str
    activo: bool
    debe_cambiar_password: bool
