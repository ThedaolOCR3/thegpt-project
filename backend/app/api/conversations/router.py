from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.generated import Users
from app.schemas.conversation import ConversationRenameRequest, ConversationResponse
from app.schemas.message import MessageCreateRequest, MessageResponse
from app.services.conversation import ConversationService
from app.services.message import MessageService

router = APIRouter()


@router.get("", response_model=list[ConversationResponse])
def list_conversations(
    current_user: Annotated[Users, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ConversationResponse]:
    return ConversationService(db).list_conversations(current_user.id)


@router.post("", response_model=ConversationResponse, status_code=201)
def create_conversation(
    current_user: Annotated[Users, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ConversationResponse:
    return ConversationService(db).create_conversation(current_user.id)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def rename_conversation(
    conversation_id: str,
    payload: ConversationRenameRequest,
    current_user: Annotated[Users, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ConversationResponse:
    return ConversationService(db).rename_conversation(conversation_id, current_user.id, payload.title)


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    current_user: Annotated[Users, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    ConversationService(db).delete_conversation(conversation_id, current_user.id)
    return {"status": "ok"}


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
def list_messages(
    conversation_id: str,
    current_user: Annotated[Users, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[MessageResponse]:
    return MessageService(db).list_messages(conversation_id, current_user.id)


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
def send_message(
    conversation_id: str,
    payload: MessageCreateRequest,
    current_user: Annotated[Users, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    return MessageService(db).send_message(conversation_id, current_user, payload.content)
