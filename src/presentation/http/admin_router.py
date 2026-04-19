from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from src.presentation.http.dependencies import get_current_admin

router = APIRouter()


@router.get("/test")
async def admin_test(admin: str = Depends(get_current_admin)):
    return {
        "message": "Admin access confirmed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
