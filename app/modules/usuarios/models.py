from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Boolean, func, text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.clientes.models import Cliente
    from app.modules.libros.models import MovimientoStock


class Usuario(SQLModel, table=True):
    __tablename__ = "usuario"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(sa_column=Column(String(254), unique=True, index=True, nullable=False))
    nombre: str = Field(sa_column=Column(String(200), nullable=False))
    password_hash: str = Field(sa_column=Column(String(255), nullable=False))
    activo: bool = Field(
        default=True,
        sa_column=Column(Boolean, nullable=False, server_default='true'),
    )
    debe_cambiar_password: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default='false'),
    )

    cliente: "Cliente" = Relationship(back_populates="usuario")
    asignaciones_rol: list["AsignacionRol"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={"foreign_keys": "AsignacionRol.usuario_id"},
    )
    movimientos_stock: list["MovimientoStock"] = Relationship(back_populates="usuario")


class AsignacionRol(SQLModel, table=True):
    __tablename__ = "asignacion_rol"
    __table_args__ = (
        CheckConstraint("rol IN ('ADMIN', 'VENDEDOR', 'CLIENTE')", name="ck_asignacion_rol_rol"),
        Index(
            "uq_asignacion_rol_abierta",
            "usuario_id",
            "rol",
            unique=True,
            postgresql_where=text("revocada_en IS NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("usuario.id", ondelete="RESTRICT"),
            index=True,
            nullable=False,
        )
    )
    rol: str = Field(sa_column=Column(String(20), nullable=False))
    desde: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    vence_en: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    revocada_en: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    otorgada_por: int | None = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("usuario.id", ondelete="SET NULL"), index=True, nullable=True),
    )

    usuario: Usuario = Relationship(
        back_populates="asignaciones_rol",
        sa_relationship_kwargs={"foreign_keys": "AsignacionRol.usuario_id"},
    )
    otorgada_por_usuario: "Usuario" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "AsignacionRol.otorgada_por"}
    )


class IntentoAcceso(SQLModel, table=True):
    __tablename__ = "intento_acceso"
    __table_args__ = (
        Index("ix_intento_acceso_email_ip_cuando", "email", "ip", "cuando"),
    )

    id: int | None = Field(default=None, primary_key=True)
    cuando: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    email: str = Field(sa_column=Column(String(254), nullable=False))
    ip: str = Field(sa_column=Column(String(45), nullable=False))
    exito: bool = Field(sa_column=Column(Boolean, nullable=False))


class EventoSeguridad(SQLModel, table=True):
    __tablename__ = "evento_seguridad"

    id: int | None = Field(default=None, primary_key=True)
    cuando: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    actor: str = Field(sa_column=Column(String(200), nullable=False))
    accion: str = Field(sa_column=Column(String(200), nullable=False))
