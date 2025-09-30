"""Customer account routes."""

from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.users.schemas import MeOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=MeOut)
async def me(current: MeOut = Depends(get_current_user)) -> MeOut:
    return current
