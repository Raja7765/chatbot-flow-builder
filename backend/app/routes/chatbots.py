"""
API routes for Chatbot management.
Provides endpoints for creating, retrieving, updating, and safely deleting chatbots,
as well as listing flows associated with a specific chatbot.
Uses SQLAlchemy 2.x and PostgreSQL.
"""

from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database import get_db, get_utc_now
from app.models import Chatbot, Flow
from app.schemas import (
    ChatbotCreate,
    ChatbotDeleteResponse,
    ChatbotResponse,
    ChatbotUpdate,
    FlowResponse,
)

router = APIRouter(prefix="/chatbots", tags=["Chatbots"])


@router.post("", response_model=ChatbotResponse, status_code=status.HTTP_201_CREATED)
def create_chatbot(
    payload: ChatbotCreate,
    db: Session = Depends(get_db),
) -> ChatbotResponse:
    """
    Create a new chatbot.

    - Validates that 'name' is non-empty.
    - Validates that 'status' is either 'active' or 'inactive'.
    - Generates a unique UUID for the chatbot.
    - Records timezone-aware UTC timestamps for created_at and updated_at.
    - Stores the chatbot in the PostgreSQL 'chatbots' table.
    - Returns HTTP 201 with the created chatbot resource.
    """
    chatbot_id = str(uuid.uuid4())
    now = get_utc_now()

    chatbot = Chatbot(
        id=chatbot_id,
        name=payload.name,
        description=payload.description,
        status=payload.status.value,
        created_at=now,
        updated_at=now,
    )
    db.add(chatbot)
    db.flush()

    return ChatbotResponse(**chatbot.to_dict())


@router.get("", response_model=List[ChatbotResponse], status_code=status.HTTP_200_OK)
def list_chatbots(
    db: Session = Depends(get_db),
) -> List[ChatbotResponse]:
    """
    Retrieve all chatbots.

    - Queries all records from the PostgreSQL 'chatbots' table ordered by newest first.
    - Returns a JSON array of chatbots, or an empty list if none exist.
    """
    stmt = select(Chatbot).order_by(desc(Chatbot.created_at))
    chatbots = db.execute(stmt).scalars().all()
    return [ChatbotResponse(**b.to_dict()) for b in chatbots]


@router.get("/{chatbot_id}", response_model=ChatbotResponse, status_code=status.HTTP_200_OK)
def get_chatbot(
    chatbot_id: str,
    db: Session = Depends(get_db),
) -> ChatbotResponse:
    """
    Retrieve a single chatbot by its unique ID.

    - Accepts 'chatbot_id' as a path parameter.
    - Validates that 'chatbot_id' is non-empty.
    - Queries the 'chatbots' table.
    - Returns HTTP 200 with the chatbot data if found.
    - Raises HTTP 404 if no chatbot with the specified ID exists.
    """
    cleaned_id = chatbot_id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot ID cannot be empty or whitespace.",
        )

    chatbot = db.get(Chatbot, cleaned_id)
    if chatbot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chatbot with id '{chatbot_id}' was not found.",
        )

    return ChatbotResponse(**chatbot.to_dict())


@router.put("/{chatbot_id}", response_model=ChatbotResponse, status_code=status.HTTP_200_OK)
def update_chatbot(
    chatbot_id: str,
    payload: ChatbotUpdate,
    db: Session = Depends(get_db),
) -> ChatbotResponse:
    """
    Update an existing chatbot by its unique ID.

    - Accepts 'chatbot_id' as a path parameter.
    - Checks whether the chatbot exists. If not found, raises HTTP 404.
    - Updates name, description, status, and updated_at.
    - Preserves the original created_at timestamp.
    - Returns HTTP 200 with the updated chatbot resource.
    """
    cleaned_id = chatbot_id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot ID cannot be empty or whitespace.",
        )

    chatbot = db.get(Chatbot, cleaned_id)
    if chatbot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chatbot with id '{chatbot_id}' was not found.",
        )

    chatbot.name = payload.name
    chatbot.description = payload.description
    chatbot.status = payload.status.value
    chatbot.updated_at = get_utc_now()
    db.flush()

    return ChatbotResponse(**chatbot.to_dict())


@router.delete("/{chatbot_id}", response_model=ChatbotDeleteResponse, status_code=status.HTTP_200_OK)
def delete_chatbot(
    chatbot_id: str,
    db: Session = Depends(get_db),
) -> ChatbotDeleteResponse:
    """
    Delete an existing chatbot by its unique ID with safe deletion policy.

    - Accepts 'chatbot_id' as a path parameter.
    - Checks whether the chatbot exists. If not, raises HTTP 404.
    - Inspects associated flows in 'flows' table.
    - If associated flows exist, rejects deletion with HTTP 400 Bad Request
      to prevent accidental cascade or orphan flows.
    - If no flows are associated, deletes the chatbot record.
    - Returns HTTP 200 OK with confirmation.
    """
    cleaned_id = chatbot_id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found. It may have already been deleted.",
        )

    chatbot = db.get(Chatbot, cleaned_id)
    if chatbot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found. It may have already been deleted.",
        )

    # Safe deletion check: prevent deletion if flows exist
    stmt = select(Flow).where(Flow.chatbot_id == cleaned_id)
    associated_flows_count = len(db.execute(stmt).scalars().all())

    if associated_flows_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete chatbot with id '{cleaned_id}' because it has {associated_flows_count} associated flow(s). Please delete or reassign its flows first.",
        )

    db.delete(chatbot)
    db.flush()

    return ChatbotDeleteResponse(
        message="Chatbot deleted successfully.",
        id=cleaned_id,
    )


@router.get("/{chatbot_id}/flows", response_model=List[FlowResponse], status_code=status.HTTP_200_OK)
def list_flows_by_chatbot(
    chatbot_id: str,
    db: Session = Depends(get_db),
) -> List[FlowResponse]:
    """
    Retrieve all flows associated with a specific chatbot.

    - Validates that the chatbot exists. If not, raises HTTP 404.
    - Retrieves matching flows ordered by newest first.
    - Returns a JSON array of flows.
    """
    cleaned_id = chatbot_id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot ID cannot be empty or whitespace.",
        )

    chatbot = db.get(Chatbot, cleaned_id)
    if chatbot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chatbot with id '{chatbot_id}' was not found.",
        )

    stmt = select(Flow).where(Flow.chatbot_id == cleaned_id).order_by(desc(Flow.created_at))
    flows = db.execute(stmt).scalars().all()

    return [FlowResponse(**f.to_dict()) for f in flows]
