"""Public shopping assistant endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.schemas import (
    AssistantAskIn,
    AssistantAskOut,
    AssistantConversationOut,
    AssistantHandoffIn,
    AssistantHandoffOut,
    AssistantStatusOut,
)
from app.assistant.service import AssistantService
from app.deps import get_current_user_id, get_optional_user_id
from app.session import get_session

router = APIRouter(tags=["assistant"])


def get_assistant_service(session: AsyncSession = Depends(get_session)) -> AssistantService:
    return AssistantService(session)


@router.get("/assistant/status", response_model=AssistantStatusOut)
async def assistant_status(
    service: AssistantService = Depends(get_assistant_service),
) -> AssistantStatusOut:
    return await service.status()


@router.post("/assistant/ask", response_model=AssistantAskOut)
async def assistant_ask(
    body: AssistantAskIn,
    user_id: UUID | None = Depends(get_optional_user_id),
    service: AssistantService = Depends(get_assistant_service),
) -> AssistantAskOut:
    return await service.ask(body, user_id=user_id)


@router.post("/assistant/handoff", response_model=AssistantHandoffOut)
async def assistant_handoff(
    body: AssistantHandoffIn,
    user_id: UUID = Depends(get_current_user_id),
    service: AssistantService = Depends(get_assistant_service),
) -> AssistantHandoffOut:
    return await service.handoff(body, user_id=user_id)


@router.get("/assistant/conversations/{conversation_id}", response_model=AssistantConversationOut)
async def get_assistant_conversation(
    conversation_id: UUID,
    user_id: UUID | None = Depends(get_optional_user_id),
    service: AssistantService = Depends(get_assistant_service),
) -> AssistantConversationOut:
    return await service.get_conversation(conversation_id, user_id=user_id)
