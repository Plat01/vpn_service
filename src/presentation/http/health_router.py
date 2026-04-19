from datetime import datetime, timezone

from fastapi import APIRouter

from src.infrastructure.db.database import database_health_check

router = APIRouter()


@router.get("/health")
async def health_check():
    db_status = await database_health_check()
    return {"status": "ok", "database": db_status}
