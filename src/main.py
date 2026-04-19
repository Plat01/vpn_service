from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config import settings
from src.infrastructure.db.database import database_health_check, engine
from src.presentation.http.admin_router import router as admin_router
from src.presentation.http.health_router import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title="VPN Subscription Service",
    description="HAPP-compatible encrypted subscription link service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
