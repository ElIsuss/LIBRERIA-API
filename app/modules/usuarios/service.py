from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.paginacion import Page
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.modules.clientes.models import Cliente
from app.modules.usuarios.models import AsignacionRol, Usuario
from app.modules.usuarios.schemas import (
    AsignacionRolResponse,
    AsignarRolRequest,
    CambiarPasswordRequest,
    EventoSeguridadRead,
    LoginRequest,
    MensajeResponse,
    RegistroRequest,
    UsuarioAuthResponse,
    UsuarioCreateRequest,
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

    @staticmethod
    async def crear_personal(
        admin: Usuario,
        request: UsuarioCreateRequest,
        uow: UsuarioUnitOfWork,
    ) -> UsuarioAuthResponse:
        """Alta de personal por parte de un ADMIN con clave provisoria y auditoría (RN-16)."""
        password_hash = await hash_password(request.password_provisoria)

        async with uow:
            if await uow.usuarios.get_by_email(request.email) is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Ya existe un usuario registrado con este correo electrónico",
                )

            usuario = Usuario(
                email=request.email,
                nombre=request.nombre,
                password_hash=password_hash,
                activo=True,
                debe_cambiar_password=True,
            )
            usuario = await uow.usuarios.add(usuario)

            rol = AsignacionRol(
                usuario_id=usuario.id,
                rol=request.rol_inicial,
                desde=datetime.now(timezone.utc),
                otorgada_por=admin.id,
            )
            await uow.roles.add(rol)

            await uow.eventos.registrar(
                actor=f"admin:{admin.id}",
                accion=f"Alta de personal usuario:{usuario.id} con rol {request.rol_inicial}",
            )

        return UsuarioAuthResponse.model_validate(usuario)

    @staticmethod
    async def listar_roles_usuario(
        usuario_id: int,
        uow: UsuarioUnitOfWork,
    ) -> list[AsignacionRolResponse]:
        """Devuelve todas las asignaciones de rol del usuario."""
        usuario = await uow.usuarios.get_by_id(usuario_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        asignaciones = await uow.roles.get_asignaciones_por_usuario(usuario_id)
        return [AsignacionRolResponse.model_validate(a) for a in asignaciones]

    @staticmethod
    async def asignar_rol(
        admin: Usuario,
        usuario_id: int,
        request: AsignarRolRequest,
        uow: UsuarioUnitOfWork,
    ) -> AsignacionRolResponse:
        """
        Asigna un rol a un usuario (RN-03, RN-16).
        Si existía una asignación abierta ya vencida, la cierra antes para no violar el índice parcial.
        Si ya está vigente, responde 409 Conflict.
        """
        usuario = await uow.usuarios.get_by_id(usuario_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        now = datetime.now(timezone.utc)
        async with uow:
            abierta = await uow.roles.get_asignacion_abierta(usuario_id, request.rol)
            if abierta:
                if abierta.vence_en is None or abierta.vence_en > now:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"El usuario ya posee el rol '{request.rol}' vigente",
                    )
                # Ya venció: cerrar asignación previa para liberar el índice único parcial
                abierta.revocada_en = now
                await uow.roles.update(abierta)

            nueva_asignacion = AsignacionRol(
                usuario_id=usuario_id,
                rol=request.rol,
                desde=now,
                vence_en=request.vence_en,
                otorgada_por=admin.id,
            )
            nueva_asignacion = await uow.roles.add(nueva_asignacion)

            await uow.eventos.registrar(
                actor=f"admin:{admin.id}",
                accion=f"Asignación de rol {request.rol} a usuario:{usuario_id}",
            )

        return AsignacionRolResponse.model_validate(nueva_asignacion)

    @staticmethod
    async def revocar_rol(
        admin: Usuario,
        usuario_id: int,
        rol: str,
        uow: UsuarioUnitOfWork,
    ) -> MensajeResponse:
        """
        Revoca un rol aplicando la autoprotección de administradores (RN-05, RN-16).
        1. Prohibido auto-revocarse el rol ADMIN.
        2. Prohibido revocar ADMIN si queda 1 solo administrador vigente.
        """
        usuario = await uow.usuarios.get_by_id(usuario_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        if rol == "ADMIN" and admin.id == usuario_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un administrador no puede revocarse su propio rol de administrador",
            )

        now = datetime.now(timezone.utc)
        async with uow:
            abierta = await uow.roles.get_asignacion_abierta(usuario_id, rol)
            if not abierta:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"El usuario no tiene una asignación abierta para el rol '{rol}'",
                )

            if rol == "ADMIN":
                admins_vigentes = await uow.roles.contar_administradores_vigentes()
                if admins_vigentes <= 1:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="No se puede revocar el rol: el sistema no puede quedar sin administradores vigentes",
                    )

            abierta.revocada_en = now
            await uow.roles.update(abierta)

            await uow.eventos.registrar(
                actor=f"admin:{admin.id}",
                accion=f"Revocación de rol {rol} a usuario:{usuario_id}",
            )

        return MensajeResponse(mensaje=f"Rol '{rol}' revocado exitosamente")

    @staticmethod
    async def listar_eventos_paginado(
        page: int,
        size: int,
        uow: UsuarioUnitOfWork,
    ) -> Page[EventoSeguridadRead]:
        """Consulta paginada del historial de eventos de seguridad."""
        items, total = await uow.eventos.listar_paginado(page=page, size=size)
        eventos_dto = [EventoSeguridadRead.model_validate(e) for e in items]
        return Page.create(items=eventos_dto, total=total, page=page, size=size)
