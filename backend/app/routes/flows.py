"""
API routes for chatbot flow management.
Handles endpoints for creating, retrieving, updating, and deleting chatbot flows.
Uses SQLAlchemy 2.x and PostgreSQL JSONB.
"""

from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database import DEFAULT_CHATBOT_ID, get_db, get_utc_now
from app.models import Chatbot, Flow
from app.schemas import FlowCreate, FlowDeleteResponse, FlowResponse, FlowUpdate

router = APIRouter(prefix="/flows", tags=["Flows"])


@router.post("", response_model=FlowResponse, status_code=status.HTTP_201_CREATED)
def create_flow(
    payload: FlowCreate,
    db: Session = Depends(get_db),
) -> FlowResponse:
    """
    Create a new chatbot flow.

    - Validates that 'name' is non-empty.
    - Validates that 'flow_data' contains 'nodes' and 'edges' arrays.
    - Verifies that 'chatbot_id' exists if provided, or defaults to the default chatbot.
    - Generates a unique UUID for the flow.
    - Records timezone-aware UTC timestamps for created_at and updated_at.
    - Stores the flow in the PostgreSQL 'flows' table with JSONB flow_data.
    - Returns HTTP 201 with the created flow resource.
    """
    target_chatbot_id = payload.chatbot_id.strip() if payload.chatbot_id else DEFAULT_CHATBOT_ID

    # Ensure associated chatbot exists
    bot = db.get(Chatbot, target_chatbot_id)
    if bot is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chatbot with id '{target_chatbot_id}' does not exist.",
        )

    flow_id = str(uuid.uuid4())
    now = get_utc_now()
    flow_data_dict = payload.flow_data.model_dump()

    flow = Flow(
        id=flow_id,
        chatbot_id=target_chatbot_id,
        name=payload.name,
        description=payload.description,
        flow_data=flow_data_dict,
        created_at=now,
        updated_at=now,
    )
    db.add(flow)
    db.flush()

    return FlowResponse(**flow.to_dict())


@router.get("", response_model=List[FlowResponse], status_code=status.HTTP_200_OK)
def list_flows(
    db: Session = Depends(get_db),
) -> List[FlowResponse]:
    """
    Retrieve all saved chatbot flows.

    - Queries all records from the PostgreSQL 'flows' table ordered by newest first.
    - Returns a JSON array of flows, or an empty list if no flows exist.
    """
    stmt = select(Flow).order_by(desc(Flow.created_at))
    flows = db.execute(stmt).scalars().all()
    return [FlowResponse(**f.to_dict()) for f in flows]


@router.get("/{flow_id}", response_model=FlowResponse, status_code=status.HTTP_200_OK)
def get_flow(
    flow_id: str,
    db: Session = Depends(get_db),
) -> FlowResponse:
    """
    Retrieve a single chatbot flow by its unique ID.

    - Accepts 'flow_id' as a path parameter.
    - Validates that 'flow_id' is non-empty.
    - Queries the 'flows' table.
    - Returns HTTP 200 with the flow data if found.
    - Raises HTTP 404 if no flow with the specified ID exists.
    """
    cleaned_id = flow_id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow ID cannot be empty or whitespace.",
        )

    flow = db.get(Flow, cleaned_id)
    if flow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flow with id '{flow_id}' was not found.",
        )

    return FlowResponse(**flow.to_dict())


@router.put("/{flow_id}", response_model=FlowResponse, status_code=status.HTTP_200_OK)
def update_flow(
    flow_id: str,
    payload: FlowUpdate,
    db: Session = Depends(get_db),
) -> FlowResponse:
    """
    Update an existing chatbot flow by its unique ID.

    - Accepts 'flow_id' as a path parameter.
    - Validates request body using FlowUpdate schema.
    - Checks whether the flow exists.
    - If not found, raises HTTP 404.
    - If chatbot_id is provided, validates that the chatbot exists.
    - Updates name, description, flow_data, chatbot_id, and updated_at.
    - Preserves the original created_at timestamp.
    - Returns HTTP 200 with the updated flow resource.
    """
    cleaned_id = flow_id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow ID cannot be empty or whitespace.",
        )

    flow = db.get(Flow, cleaned_id)
    if flow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flow with id '{flow_id}' was not found.",
        )

    target_chatbot_id = flow.chatbot_id
    if payload.chatbot_id:
        cleaned_bot_id = payload.chatbot_id.strip()
        bot = db.get(Chatbot, cleaned_bot_id)
        if bot is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Chatbot with id '{cleaned_bot_id}' does not exist.",
            )
        target_chatbot_id = cleaned_bot_id

    flow.chatbot_id = target_chatbot_id
    flow.name = payload.name
    flow.description = payload.description
    flow.flow_data = payload.flow_data.model_dump()
    flow.updated_at = get_utc_now()
    db.flush()

    return FlowResponse(**flow.to_dict())


@router.delete("/{flow_id}", response_model=FlowDeleteResponse, status_code=status.HTTP_200_OK)
def delete_flow(
    flow_id: str,
    db: Session = Depends(get_db),
) -> FlowDeleteResponse:
    """
    Delete an existing chatbot flow by its unique ID.

    - Accepts 'flow_id' as a path parameter.
    - Validates that 'flow_id' is non-empty.
    - Checks whether the flow exists in 'flows' table.
    - If not found, raises HTTP 404 with a user-friendly message.
    - Deletes only that specific flow.
    - Returns HTTP 200 OK with confirmation message and deleted flow ID.
    """
    cleaned_id = flow_id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow not found. It may have already been deleted.",
        )

    flow = db.get(Flow, cleaned_id)
    if flow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow not found. It may have already been deleted.",
        )

    db.delete(flow)
    db.flush()

    return FlowDeleteResponse(
        message="Flow deleted successfully.",
        id=cleaned_id,
    )
