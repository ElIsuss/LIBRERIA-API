import asyncio
import logging
from contextlib import asynccontextmanager

import bcrypt
from fastapi import APIRouter, Depends, FastAPI

from app.core.config import settings
from app.core.database import create_engine, create_session_factory
from app.core.dependencies import verificar_password_actualizada
from app.modules import *  # noqa: F401,F403  registra todos los modelos en SQLModel.metadata
from app.modules.autores.router import autores_admin_router, router as autores_router
from app.modules.clientes.router import router as clientes_router
from app.modules.editoriales.router import editoriales_admin_router, router as editoriales_router
from app.modules.generos.router import generos_admin_router, router as generos_router
from app.modules.health.router import router as health_router
from app.modules.libros.router import libros_admin_router, router as libros_router
from app.modules.usuarios.router import (
    eventos_router,
    router as auth_router,
    usuarios_admin_router,
)
from app.modules.ventas.router import router as ventas_router

logging.basicConfig(
    level=logging.INFO if settings.sql_echo else logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_engine()
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.dummy_hash = await asyncio.to_thread(
        lambda: bcrypt.hashpw(b"dummy-password", bcrypt.gensalt(rounds=settings.bcrypt_rounds)).decode("utf-8")
    )
    try:
        yield
    finally:
        await engine.dispose()


open_router = APIRouter()
protected_router = APIRouter(dependencies=[Depends(verificar_password_actualizada)])

open_router.include_router(health_router)
open_router.include_router(auth_router)
open_router.include_router(editoriales_router)
open_router.include_router(generos_router)
open_router.include_router(autores_router)
open_router.include_router(libros_router)
protected_router.include_router(usuarios_admin_router)
protected_router.include_router(eventos_router)
protected_router.include_router(editoriales_admin_router)
protected_router.include_router(generos_admin_router)
protected_router.include_router(autores_admin_router)
protected_router.include_router(libros_admin_router)
protected_router.include_router(clientes_router)
protected_router.include_router(ventas_router)

app = FastAPI(title="Libreria API", version="1.0.0", lifespan=lifespan)
app.include_router(open_router)
app.include_router(protected_router)