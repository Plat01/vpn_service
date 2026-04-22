import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config import settings
from src.infrastructure.db.database import database_health_check, engine
from src.infrastructure.logging_config import setup_logging
from src.presentation.http.admin_router import router as admin_router
from src.presentation.http.health_router import router as health_router
from src.presentation.http.subscription_router import router as subscription_router
from src.presentation.http.subscription_issuance_router import (
    router as subscription_issuance_router,
)
from src.presentation.http.vpn_sources_router import router as vpn_sources_router
from src.presentation.http.vpn_source_tags_router import (
    router as vpn_source_tags_router,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level, settings.library_log_level)
    logger.info("Application starting up")
    yield
    logger.info("Application shutting down")
    await engine.dispose()


app = FastAPI(
    title="VPN Subscription Service",
    description="HAPP-compatible encrypted subscription link service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(subscription_router, prefix="/api/v1", tags=["subscriptions"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(
    subscription_issuance_router, prefix="/api/v1/admin", tags=["subscription-issuance"]
)
app.include_router(vpn_sources_router, prefix="/api/v1/admin", tags=["vpn-sources"])
app.include_router(
    vpn_source_tags_router, prefix="/api/v1/admin", tags=["vpn-source-tags"]
)
