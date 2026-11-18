"""
API route handlers for Node Definitions.
Manages listing, fetching, creating, updating, and safely deleting/deactivating
both prebuilt and custom node definitions for the Chatbot Flow Builder.
Uses SQLAlchemy 2.x and PostgreSQL.
"""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.database import get_db, get_utc_now
from app.models import Flow, NodeDefinition
from app.schemas import (
    NodeDefinitionCreate,
    NodeDefinitionDeleteResponse,
    NodeDefinitionResponse,
    NodeDefinitionUpdate,
)

router = APIRouter(
    prefix="/node-definitions",
    tags=["Node Definitions"],
)


@router.get("", response_model=List[NodeDefinitionResponse], status_code=status.HTTP_200_OK)
def list_node_definitions(
    node_source: Optional[str] = Query(None, description="Filter by node source ('prebuilt' or 'custom')"),
    category: Optional[str] = Query(None, description="Filter by node category (e.g. 'AI', 'Logic')"),
    is_active: Optional[bool] = Query(None, description="Filter by active status (true/false)"),
    db: Session = Depends(get_db),
) -> List[NodeDefinitionResponse]:
    """
    Retrieve all node definitions with optional filters for source, category, and active status.
    Ordered with prebuilt nodes first, then alphabetically by name.
    """
    stmt = select(NodeDefinition)

    if node_source is not None:
        cleaned_source = node_source.strip().lower()
        if cleaned_source in ("prebuilt", "custom"):
            stmt = stmt.where(NodeDefinition.node_source == cleaned_source)

    if category is not None:
        cleaned_category = category.strip()
        if cleaned_category:
            stmt = stmt.where(func.lower(NodeDefinition.category) == cleaned_category.lower())

    if is_active is not None:
        stmt = stmt.where(NodeDefinition.is_active == is_active)

    # Prebuilt nodes first, then alphabetically by name
    stmt = stmt.order_by(
        case((NodeDefinition.node_source == "prebuilt", 0), else_=1),
        NodeDefinition.name.asc(),
    )

    nodes = db.execute(stmt).scalars().all()
    return [NodeDefinitionResponse(**nd.to_dict()) for nd in nodes]


@router.get("/{id}", response_model=NodeDefinitionResponse, status_code=status.HTTP_200_OK)
def get_node_definition(
    id: str,
    db: Session = Depends(get_db),
) -> NodeDefinitionResponse:
    """
    Retrieve a single node definition by its ID or stable node_type.
    Returns HTTP 404 if not found.
    """
    cleaned_id = id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node definition ID cannot be empty.",
        )

    stmt = select(NodeDefinition).where(
        (NodeDefinition.id == cleaned_id) | (NodeDefinition.node_type == cleaned_id)
    )
    node_def = db.execute(stmt).scalar_one_or_none()

    if node_def is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node definition with identifier '{id}' was not found.",
        )

    return NodeDefinitionResponse(**node_def.to_dict())


@router.post("", response_model=NodeDefinitionResponse, status_code=status.HTTP_201_CREATED)
def create_custom_node_definition(
    payload: NodeDefinitionCreate,
    db: Session = Depends(get_db),
) -> NodeDefinitionResponse:
    """
    Create a new custom node definition.
    Enforces node_source='custom' and prevents conflicting duplicate node types.
    """
    # 1. Check whether node_type already exists to prevent conflicting overwrites
    stmt = select(NodeDefinition).where(NodeDefinition.node_type == payload.node_type)
    existing = db.execute(stmt).scalar_one_or_none()

    if existing is not None:
        source_label = "Prebuilt" if existing.node_source == "prebuilt" else "Custom"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A {source_label} node definition with type '{payload.node_type}' already exists "
                f"('{existing.name}'). Please choose a different, unique node type identifier."
            ),
        )

    # 2. Generate unique identifier and timestamps
    node_id = f"custom-{payload.node_type}-{uuid.uuid4().hex[:8]}"
    now = get_utc_now()

    new_node = NodeDefinition(
        id=node_id,
        name=payload.name,
        node_type=payload.node_type,
        category=payload.category,
        description=payload.description or "",
        node_source="custom",
        input_schema=payload.input_schema or {},
        output_schema=payload.output_schema or {},
        config_schema=payload.config_schema or {},
        executor_type=payload.executor_type,
        executor_config=payload.executor_config or {},
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(new_node)
    db.flush()

    return NodeDefinitionResponse(**new_node.to_dict())


@router.put("/{id}", response_model=NodeDefinitionResponse, status_code=status.HTTP_200_OK)
def update_custom_node_definition(
    id: str,
    payload: NodeDefinitionUpdate,
    db: Session = Depends(get_db),
) -> NodeDefinitionResponse:
    """
    Update an existing custom node definition.
    Protected prebuilt node definitions cannot be modified.
    """
    cleaned_id = id.strip()
    node_def = db.get(NodeDefinition, cleaned_id)

    if node_def is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node definition with id '{id}' was not found.",
        )

    # Protect prebuilt definitions from modification
    if node_def.node_source == "prebuilt":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Prebuilt node definitions are core system templates and cannot be modified.",
        )

    if payload.name is not None:
        node_def.name = payload.name
    if payload.category is not None:
        node_def.category = payload.category
    if payload.description is not None:
        node_def.description = payload.description
    if payload.input_schema is not None:
        node_def.input_schema = payload.input_schema
    if payload.output_schema is not None:
        node_def.output_schema = payload.output_schema
    if payload.config_schema is not None:
        node_def.config_schema = payload.config_schema
    if payload.executor_type is not None:
        node_def.executor_type = payload.executor_type
    if payload.executor_config is not None:
        node_def.executor_config = payload.executor_config
    if payload.is_active is not None:
        node_def.is_active = payload.is_active

    node_def.updated_at = get_utc_now()
    db.flush()

    return NodeDefinitionResponse(**node_def.to_dict())


@router.delete("/{id}", response_model=NodeDefinitionDeleteResponse, status_code=status.HTTP_200_OK)
def delete_or_deactivate_node_definition(
    id: str,
    db: Session = Depends(get_db),
) -> NodeDefinitionDeleteResponse:
    """
    Safely delete or deactivate a custom node definition.
    - Prebuilt node definitions cannot be deleted (returns HTTP 403).
    - If any existing saved flows reference this node type, it is safely DEACTIVATED
      instead of deleted to prevent breaking existing flows.
    - If no flows reference this node type, it is permanently deleted.
    """
    cleaned_id = id.strip()
    node_def = db.get(NodeDefinition, cleaned_id)

    if node_def is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node definition with id '{id}' was not found.",
        )

    # Protect prebuilt definitions
    if node_def.node_source == "prebuilt":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Prebuilt node definitions are core system templates and cannot be deleted.",
        )

    target_type = node_def.node_type

    # Inspect all existing saved flows to check if any flow references this node type
    all_flows = db.query(Flow).all()
    referencing_flows = []

    for flow in all_flows:
        flow_data = flow.flow_data if isinstance(flow.flow_data, dict) else {}
        flow_nodes = flow_data.get("nodes", [])
        if any(
            isinstance(n, dict) and n.get("type") == target_type
            for n in flow_nodes
        ):
            referencing_flows.append(f"'{flow.name}' ({flow.id[:8]}...)")

    now = get_utc_now()

    if referencing_flows:
        # Safe deactivation: do not break existing saved flows
        node_def.is_active = False
        node_def.updated_at = now
        db.flush()

        flows_summary = ", ".join(referencing_flows[:3])
        if len(referencing_flows) > 3:
            flows_summary += f" and {len(referencing_flows) - 3} more"

        return NodeDefinitionDeleteResponse(
            message=(
                f"Custom node '{node_def.name}' is referenced by {len(referencing_flows)} flow(s) "
                f"({flows_summary}). It has been safely deactivated instead of deleted to protect your flows."
            ),
            id=cleaned_id,
            deactivated=True,
        )

    # If no flows reference it, permanently delete
    node_name = node_def.name
    db.delete(node_def)
    db.flush()

    return NodeDefinitionDeleteResponse(
        message=f"Custom node definition '{node_name}' was successfully deleted.",
        id=cleaned_id,
        deactivated=False,
    )
