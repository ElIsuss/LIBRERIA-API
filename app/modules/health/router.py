from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request) -> dict[str, str]:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {exc}",
        ) from exc

    return {"status": "ok"}
