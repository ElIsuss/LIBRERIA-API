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
from datetime import datetime, timezone
from typing import Literal
from pydantic import field_validator

RolNombre = Literal["ADMIN", "VENDEDOR", "CLIENTE"]


class UsuarioCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password_provisoria: PasswordStr
    rol_inicial: RolNombre


class AsignarRolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rol: RolNombre
    vence_en: datetime | None = None

    @field_validator("vence_en")
    @classmethod
    def validar_vencimiento_futuro(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        if v.tzinfo is None:
            raise ValueError("La fecha de vencimiento debe incluir zona horaria")
        if v <= datetime.now(timezone.utc):
            raise ValueError("La fecha de vencimiento debe ser posterior al momento actual")
        return v


class AsignacionRolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    usuario_id: int
    rol: str
    desde: datetime
    vence_en: datetime | None = None
    revocada_en: datetime | None = None
    otorgada_por: int | None = None


class EventoSeguridadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    cuando: datetime
    actor: str
    accion: str
