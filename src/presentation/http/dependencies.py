from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from src.config import settings

security = HTTPBasic()


async def get_current_admin(
    credentials: HTTPBasicCredentials = Depends(security),
) -> str:
    is_correct_username = credentials.username == settings.admin_username
    is_correct_password = credentials.password == settings.admin_password

    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username
