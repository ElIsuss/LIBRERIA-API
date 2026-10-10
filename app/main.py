from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import create_engine, create_session_factory
from app.modules import *  # noqa: F401,F403  registra todos los modelos en SQLModel.metadata
from app.modules.editoriales.router import router as editoriales_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_engine()
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="Libreria API", version="1.0.0", lifespan=lifespan)
app.include_router(editoriales_router)


@app.get("/health/live")
async def live() -> dict[str, str]:
    return {"estado": "vivo"}


@app.get("/health/ready")
async def ready(request: Request) -> dict[str, str]:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        await session.execute(text("SELECT 1"))
    return {"estado": "listo", "base": "accesible"}