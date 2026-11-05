from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.modules.clientes.models import Cliente
from app.modules.usuarios.models import AsignacionRol, Usuario
from app.modules.usuarios.schemas import (
    CambiarPasswordRequest,
    LoginRequest,
    MensajeResponse,
    RegistroRequest,
    UsuarioAuthResponse,
    YoResponse,
)
from app.modules.usuarios.unit_of_work import (
    UsuarioUnitOfWork,
    registrar_intento_acceso,
)


class UsuarioService:
    @staticmethod
    async def registrar_cliente(
        request: RegistroRequest,
        uow: UsuarioUnitOfWork,
    ) -> UsuarioAuthResponse:
        """
        Auto-registro atómico de cliente (RN-01, RN-02).
        Calcula el hash fuera de la transacción y crea en un solo UoW:
        Usuario, AsignacionRol('CLIENTE') y Cliente(usuario_id=...).
        """
        # 1. Hashing bcrypt fuera de la transacción
        password_hash = await hash_password(request.password)

        # 2. Transacción atómica
        async with uow:
            # Comprobar unicidad en usuario y cliente
            if await uow.usuarios.get_by_email(request.email) is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Ya existe un usuario registrado con este correo electrónico",
                )
            if await uow.clientes.get_by_email(request.email) is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Ya existe una ficha de cliente con este correo electrónico",
                )

            try:
                usuario = Usuario(
                    email=request.email,
                    nombre=request.nombre,
                    password_hash=password_hash,
                    activo=True,
                    debe_cambiar_password=False,
                )
                usuario = await uow.usuarios.add(usuario)

                rol = AsignacionRol(
                    usuario_id=usuario.id,
                    rol="CLIENTE",
                    desde=datetime.now(timezone.utc),
                )
                await uow.roles.add(rol)

                cliente = Cliente(
                    nombre=request.nombre,
                    email=request.email,
                    usuario_id=usuario.id,
                )
                await uow.clientes.add(cliente)

            except IntegrityError as exc:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Conflicto de unicidad al registrar usuario o cliente",
                ) from exc

        return UsuarioAuthResponse.model_validate(usuario)

    @staticmethod
    async def login(
        request: LoginRequest,
        client_ip: str,
        session_factory: async_sessionmaker[AsyncSession],
        uow: UsuarioUnitOfWork,
        dummy_hash: str,
    ) -> tuple[str, bool, int]:
        """
        Inicio de sesión seguro (RN-07, RN-08).
        1. Comprueba límite de 5 fallos en 60s -> 429 Retry-After sin bcrypt.
        2. Verifica contraseña o dummy_hash en tiempo constante.
        3. Registra intento_acceso en sesión independiente.
        4. Si es exitoso, emite JWT con roles vigentes.
        """
        # 1. Rate Limiting Check
        fallos, primer_fallo = await uow.intentos.contar_fallos_recientes(
            email=request.email,
            ip=client_ip,
            ventana_segundos=60,
        )
        if fallos >= 5:
            now = datetime.now(timezone.utc)
            if primer_fallo is not None:
                delta = (now - primer_fallo).total_seconds()
                segundos_restantes = max(1, int(60 - delta))
            else:
                segundos_restantes = 60

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Demasiados intentos fallidos. Intente nuevamente en {segundos_restantes} segundos.",
                headers={"Retry-After": str(segundos_restantes)},
            )

        # 2. Búsqueda de usuario y verificación en tiempo constante
        usuario = await uow.usuarios.get_by_email(request.email)
        if usuario is None or not usuario.activo:
            await verify_password(request.password, dummy_hash)
            await registrar_intento_acceso(
                session_factory,
                email=request.email,
                ip=client_ip,
                exito=False,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas",
            )

        is_valid = await verify_password(request.password, usuario.password_hash)
        if not is_valid:
            await registrar_intento_acceso(
                session_factory,
                email=request.email,
                ip=client_ip,
                exito=False,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas",
            )

        # 3. Registro de éxito en sesión independiente
        await registrar_intento_acceso(
            session_factory,
            email=request.email,
            ip=client_ip,
            exito=True,
        )

        # 4. Generación de Token JWT con roles vigentes
        roles_vigentes = await uow.roles.get_roles_vigentes(usuario.id)
        token = create_access_token(subject=usuario.id, roles=roles_vigentes)
        return token, usuario.debe_cambiar_password, settings.jwt_expire_seconds

    @staticmethod
    async def obtener_perfil_yo(
        usuario: Usuario,
        roles_token: list[str],
        uow: UsuarioUnitOfWork,
    ) -> YoResponse:
        """Devuelve el perfil del usuario con roles vigentes en BD y roles informativos del token."""
        roles_vigentes = await uow.roles.get_roles_vigentes(usuario.id)
        return YoResponse(
            id=usuario.id,
            email=usuario.email,
            nombre=usuario.nombre,
            debe_cambiar_password=usuario.debe_cambiar_password,
            roles_vigentes=roles_vigentes,
            roles_token=roles_token,
        )

    @staticmethod
    async def cambiar_password(
        usuario: Usuario,
        request: CambiarPasswordRequest,
        uow: UsuarioUnitOfWork,
    ) -> MensajeResponse:
        """
        Cambio de contraseña voluntario u obligatorio (RN-06, RN-16).
        Verifica clave actual, calcula nuevo hash fuera de la tx y actualiza usuario + evento_seguridad.
        """
        is_valid = await verify_password(request.password_actual, usuario.password_hash)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="La contraseña actual es incorrecta",
            )

        # Hash fuera de la transacción
        nuevo_hash = await hash_password(request.password_nueva)

        async with uow:
            usuario.password_hash = nuevo_hash
            usuario.debe_cambiar_password = False
            await uow.usuarios.update(usuario)

            await uow.eventos.registrar(
                actor=f"usuario:{usuario.id}",
                accion="Cambio de contraseña",
            )

        return MensajeResponse(mensaje="Contraseña actualizada exitosamente")
