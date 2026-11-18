"""
API routes for Node Answer management.
Handles CRUD operations for multi-language node answers and their associated content blocks.
"""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db, get_utc_now
from app.models import AnswerBlock, Flow, MediaAsset, NodeAnswer, format_utc_iso
from app.schemas import (
    AnswerBlockResponse,
    BlockType,
    NodeAnswerCreate,
    NodeAnswerDeleteResponse,
    NodeAnswerResponse,
    NodeAnswerUpdate,
)

router = APIRouter(tags=["Node Answers"])


def _validate_flow_and_node(db: Session, flow_id: str, node_id: str) -> Flow:
    """
    Validate that the specified flow exists and contains the given node_id.
    Raises HTTP 404 if the flow or node is not found.
    """
    flow = db.get(Flow, flow_id)
    if flow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flow with id '{flow_id}' not found.",
        )

    flow_data = flow.flow_data or {}
    nodes = flow_data.get("nodes", [])
    node_exists = any(
        isinstance(n, dict) and str(n.get("id")) == str(node_id) for n in nodes
    )
    if not node_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node with id '{node_id}' not found in flow '{flow_id}'.",
        )

    return flow


def _validate_media_assets(db: Session, blocks: List) -> None:
    """
    Validate that any referenced media_id exists in the media_assets table.
    Raises HTTP 404 if a referenced media asset does not exist.
    """
    for b in blocks:
        if b.media_id:
            try:
                media_uuid = uuid.UUID(str(b.media_id))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid UUID for media_id: '{b.media_id}'.",
                )
            media_asset = db.get(MediaAsset, media_uuid)
            if media_asset is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Media asset with id '{b.media_id}' not found.",
                )


def _format_node_answer_response(answer: NodeAnswer, db: Session) -> NodeAnswerResponse:
    """
    Query answer blocks ordered by position ASC and assemble NodeAnswerResponse.
    """
    blocks = (
        db.query(AnswerBlock)
        .filter(AnswerBlock.answer_id == answer.id)
        .order_by(AnswerBlock.position.asc())
        .all()
    )
    block_responses = [
        AnswerBlockResponse(
            id=str(b.id),
            answer_id=str(b.answer_id),
            block_type=b.block_type,
            content=b.content,
            media_id=str(b.media_id) if b.media_id else None,
            position=b.position,
            metadata=b.block_metadata,
            created_at=format_utc_iso(b.created_at),
            updated_at=format_utc_iso(b.updated_at),
        )
        for b in blocks
    ]
    return NodeAnswerResponse(
        id=str(answer.id),
        flow_id=answer.flow_id,
        node_id=answer.node_id,
        language=answer.language,
        blocks=block_responses,
        created_at=format_utc_iso(answer.created_at),
        updated_at=format_utc_iso(answer.updated_at),
    )


@router.post(
    "/flows/{flow_id}/nodes/{node_id}/answer",
    response_model=NodeAnswerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_node_answer(
    flow_id: str,
    node_id: str,
    payload: NodeAnswerCreate,
    db: Session = Depends(get_db),
) -> NodeAnswerResponse:
    """
    Create a new answer for a specific node in a flow.

    - Verifies that the flow and node_id exist.
    - Validates block types and content.
    - Validates that referenced media assets exist.
    - Prevents duplicate answers for the same (flow_id, node_id, language).
    - Persists the answer and all blocks transactionally.
    """
    _validate_flow_and_node(db, flow_id, node_id)
    _validate_media_assets(db, payload.blocks)

    # Check for existing answer with the same language
    existing = db.scalar(
        select(NodeAnswer).where(
            NodeAnswer.flow_id == flow_id,
            NodeAnswer.node_id == node_id,
            NodeAnswer.language == payload.language,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Answer already exists for flow '{flow_id}', node '{node_id}', language '{payload.language}'.",
        )

    now = get_utc_now()
    answer_id = uuid.uuid4()
    answer = NodeAnswer(
        id=answer_id,
        flow_id=flow_id,
        node_id=node_id,
        language=payload.language,
        created_at=now,
        updated_at=now,
    )
    db.add(answer)
    db.flush()

    # Sort blocks by position before insertion
    sorted_blocks = sorted(payload.blocks, key=lambda b: b.position)
    for b in sorted_blocks:
        media_uuid = uuid.UUID(str(b.media_id)) if b.media_id else None
        block = AnswerBlock(
            id=uuid.uuid4(),
            answer_id=answer_id,
            block_type=b.block_type.value,
            content=b.content,
            media_id=media_uuid,
            position=b.position,
            block_metadata=b.metadata,
            created_at=now,
            updated_at=now,
        )
        db.add(block)

    db.commit()
    db.refresh(answer)
    return _format_node_answer_response(answer, db)


@router.get(
    "/flows/{flow_id}/nodes/{node_id}/answer",
    response_model=NodeAnswerResponse,
    status_code=status.HTTP_200_OK,
)
def get_node_answer(
    flow_id: str,
    node_id: str,
    language: str = Query("en", description="Language code for the answer"),
    db: Session = Depends(get_db),
) -> NodeAnswerResponse:
    """
    Retrieve the answer and all its blocks in ascending position order for a specific node and language.
    """
    target_lang = language.strip() if language else "en"
    if not target_lang:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Language query parameter cannot be empty.",
        )

    _validate_flow_and_node(db, flow_id, node_id)

    answer = db.scalar(
        select(NodeAnswer).where(
            NodeAnswer.flow_id == flow_id,
            NodeAnswer.node_id == node_id,
            NodeAnswer.language == target_lang,
        )
    )
    if answer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Answer not found for flow '{flow_id}', node '{node_id}', language '{target_lang}'.",
        )

    return _format_node_answer_response(answer, db)


@router.put(
    "/flows/{flow_id}/nodes/{node_id}/answer",
    response_model=NodeAnswerResponse,
    status_code=status.HTTP_200_OK,
)
def update_node_answer(
    flow_id: str,
    node_id: str,
    payload: NodeAnswerUpdate,
    db: Session = Depends(get_db),
) -> NodeAnswerResponse:
    """
    Update an existing answer and replace its blocks transactionally.
    """
    _validate_flow_and_node(db, flow_id, node_id)
    _validate_media_assets(db, payload.blocks)

    answer = db.scalar(
        select(NodeAnswer).where(
            NodeAnswer.flow_id == flow_id,
            NodeAnswer.node_id == node_id,
            NodeAnswer.language == payload.language,
        )
    )
    if answer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Answer not found for flow '{flow_id}', node '{node_id}', language '{payload.language}'.",
        )

    now = get_utc_now()

    # Safely remove existing blocks for this answer
    db.query(AnswerBlock).filter(AnswerBlock.answer_id == answer.id).delete()

    # Insert new blocks in sorted order
    sorted_blocks = sorted(payload.blocks, key=lambda b: b.position)
    for b in sorted_blocks:
        media_uuid = uuid.UUID(str(b.media_id)) if b.media_id else None
        block = AnswerBlock(
            id=uuid.uuid4(),
            answer_id=answer.id,
            block_type=b.block_type.value,
            content=b.content,
            media_id=media_uuid,
            position=b.position,
            block_metadata=b.metadata,
            created_at=now,
            updated_at=now,
        )
        db.add(block)

    answer.updated_at = now
    db.commit()
    db.refresh(answer)
    return _format_node_answer_response(answer, db)


@router.delete(
    "/flows/{flow_id}/nodes/{node_id}/answer",
    response_model=NodeAnswerDeleteResponse,
    status_code=status.HTTP_200_OK,
)
def delete_node_answer(
    flow_id: str,
    node_id: str,
    language: str = Query("en", description="Language code of the answer to delete"),
    db: Session = Depends(get_db),
) -> NodeAnswerDeleteResponse:
    """
    Delete a node answer and its associated blocks safely.
    """
    target_lang = language.strip() if language else "en"
    if not target_lang:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Language query parameter cannot be empty.",
        )

    _validate_flow_and_node(db, flow_id, node_id)

    answer = db.scalar(
        select(NodeAnswer).where(
            NodeAnswer.flow_id == flow_id,
            NodeAnswer.node_id == node_id,
            NodeAnswer.language == target_lang,
        )
    )
    if answer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Answer not found for flow '{flow_id}', node '{node_id}', language '{target_lang}'.",
        )

    answer_id_str = str(answer.id)
    db.delete(answer)
    db.commit()

    return NodeAnswerDeleteResponse(
        message=f"Answer successfully deleted for node '{node_id}' in language '{target_lang}'.",
        id=answer_id_str,
        flow_id=flow_id,
        node_id=node_id,
        language=target_lang,
    )

