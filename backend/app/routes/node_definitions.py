"""
API route handlers for Node Definitions.
Manages listing, fetching, creating, updating, and safely deleting/deactivating
both prebuilt and custom node definitions for the Chatbot Flow Builder.
"""

import json
import sqlite3
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import get_db, get_utc_now_iso
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


def _row_to_response(row: sqlite3.Row) -> NodeDefinitionResponse:
    """Helper to convert an SQLite node_definitions row into a NodeDefinitionResponse."""
    def _parse_json(val: Optional[str]) -> dict:
        if not val:
            return {}
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    return NodeDefinitionResponse(
        id=row["id"],
        name=row["name"],
        node_type=row["node_type"],
        category=row["category"],
        description=row["description"],
        node_source=row["node_source"],
        input_schema=_parse_json(row["input_schema"]),
        output_schema=_parse_json(row["output_schema"]),
        config_schema=_parse_json(row["config_schema"]),
        executor_type=row["executor_type"],
        executor_config=_parse_json(row["executor_config"]),
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("", response_model=List[NodeDefinitionResponse], status_code=status.HTTP_200_OK)
def list_node_definitions(
    node_source: Optional[str] = Query(None, description="Filter by node source ('prebuilt' or 'custom')"),
    category: Optional[str] = Query(None, description="Filter by node category (e.g. 'AI', 'Logic')"),
    is_active: Optional[bool] = Query(None, description="Filter by active status (true/false)"),
    conn: sqlite3.Connection = Depends(get_db),
) -> List[NodeDefinitionResponse]:
    """
    Retrieve all node definitions with optional filters for source, category, and active status.
    Ordered with prebuilt nodes first, then alphabetically by name.
    """
    conditions = []
    params = []

    if node_source is not None:
        cleaned_source = node_source.strip().lower()
        if cleaned_source in ("prebuilt", "custom"):
            conditions.append("node_source = ?")
            params.append(cleaned_source)

    if category is not None:
        cleaned_category = category.strip()
        if cleaned_category:
            conditions.append("LOWER(category) = LOWER(?)")
            params.append(cleaned_category)

    if is_active is not None:
        conditions.append("is_active = ?")
        params.append(1 if is_active else 0)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    select_sql = f"""
    SELECT id, name, node_type, category, description, node_source,
           input_schema, output_schema, config_schema,
           executor_type, executor_config, is_active, created_at, updated_at
    FROM node_definitions
    {where_clause}
    ORDER BY CASE WHEN node_source = 'prebuilt' THEN 0 ELSE 1 END, name ASC;
    """

    cursor = conn.execute(select_sql, tuple(params))
    rows = cursor.fetchall()
    cursor.close()
    return [_row_to_response(row) for row in rows]


@router.get("/{id}", response_model=NodeDefinitionResponse, status_code=status.HTTP_200_OK)
def get_node_definition(
    id: str,
    conn: sqlite3.Connection = Depends(get_db),
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

    select_sql = """
    SELECT id, name, node_type, category, description, node_source,
           input_schema, output_schema, config_schema,
           executor_type, executor_config, is_active, created_at, updated_at
    FROM node_definitions
    WHERE id = ? OR node_type = ?;
    """
    cursor = conn.execute(select_sql, (cleaned_id, cleaned_id))
    row = cursor.fetchone()
    cursor.close()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node definition with identifier '{id}' was not found.",
        )

    return _row_to_response(row)


@router.post("", response_model=NodeDefinitionResponse, status_code=status.HTTP_201_CREATED)
def create_custom_node_definition(
    payload: NodeDefinitionCreate,
    conn: sqlite3.Connection = Depends(get_db),
) -> NodeDefinitionResponse:
    """
    Create a new custom node definition.
    Enforces node_source='custom' and prevents conflicting duplicate node types.
    """
    # 1. Check whether node_type already exists to prevent conflicting overwrites
    check_sql = "SELECT id, name, node_source FROM node_definitions WHERE node_type = ?;"
    cursor = conn.execute(check_sql, (payload.node_type,))
    existing = cursor.fetchone()
    cursor.close()

    if existing is not None:
        source_label = "Prebuilt" if existing["node_source"] == "prebuilt" else "Custom"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A {source_label} node definition with type '{payload.node_type}' already exists "
                f"('{existing['name']}'). Please choose a different, unique node type identifier."
            ),
        )

    # 2. Generate unique identifier and timestamps
    node_id = f"custom-{payload.node_type}-{uuid.uuid4().hex[:8]}"
    now_iso = get_utc_now_iso()

    # 3. Validate and serialize JSON schemas
    input_schema_json = json.dumps(payload.input_schema or {})
    output_schema_json = json.dumps(payload.output_schema or {})
    config_schema_json = json.dumps(payload.config_schema or {})
    executor_config_json = json.dumps(payload.executor_config or {})

    insert_sql = """
    INSERT INTO node_definitions (
        id, name, node_type, category, description, node_source,
        input_schema, output_schema, config_schema,
        executor_type, executor_config, is_active, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, 'custom', ?, ?, ?, ?, ?, 1, ?, ?);
    """

    conn.execute(
        insert_sql,
        (
            node_id,
            payload.name,
            payload.node_type,
            payload.category,
            payload.description or "",
            input_schema_json,
            output_schema_json,
            config_schema_json,
            payload.executor_type,
            executor_config_json,
            now_iso,
            now_iso,
        ),
    )
    conn.commit()

    # 4. Fetch and return persisted record
    return get_node_definition(node_id, conn)


@router.put("/{id}", response_model=NodeDefinitionResponse, status_code=status.HTTP_200_OK)
def update_custom_node_definition(
    id: str,
    payload: NodeDefinitionUpdate,
    conn: sqlite3.Connection = Depends(get_db),
) -> NodeDefinitionResponse:
    """
    Update an existing custom node definition.
    Protected prebuilt node definitions cannot be modified.
    """
    cleaned_id = id.strip()
    select_sql = "SELECT * FROM node_definitions WHERE id = ?;"
    cursor = conn.execute(select_sql, (cleaned_id,))
    row = cursor.fetchone()
    cursor.close()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node definition with id '{id}' was not found.",
        )

    # Protect prebuilt definitions from modification
    if row["node_source"] == "prebuilt":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Prebuilt node definitions are core system templates and cannot be modified.",
        )

    now_iso = get_utc_now_iso()

    # Determine updated values, preserving existing if omitted
    new_name = payload.name if payload.name is not None else row["name"]
    new_category = payload.category if payload.category is not None else row["category"]
    new_description = payload.description if payload.description is not None else row["description"]
    new_input_schema = (
        json.dumps(payload.input_schema) if payload.input_schema is not None else row["input_schema"]
    )
    new_output_schema = (
        json.dumps(payload.output_schema) if payload.output_schema is not None else row["output_schema"]
    )
    new_config_schema = (
        json.dumps(payload.config_schema) if payload.config_schema is not None else row["config_schema"]
    )
    new_executor_type = payload.executor_type if payload.executor_type is not None else row["executor_type"]
    new_executor_config = (
        json.dumps(payload.executor_config) if payload.executor_config is not None else row["executor_config"]
    )
    new_is_active = (
        (1 if payload.is_active else 0) if payload.is_active is not None else row["is_active"]
    )

    update_sql = """
    UPDATE node_definitions
    SET name = ?, category = ?, description = ?,
        input_schema = ?, output_schema = ?, config_schema = ?,
        executor_type = ?, executor_config = ?, is_active = ?, updated_at = ?
    WHERE id = ?;
    """

    conn.execute(
        update_sql,
        (
            new_name,
            new_category,
            new_description,
            new_input_schema,
            new_output_schema,
            new_config_schema,
            new_executor_type,
            new_executor_config,
            new_is_active,
            now_iso,
            cleaned_id,
        ),
    )
    conn.commit()

    return get_node_definition(cleaned_id, conn)


@router.delete("/{id}", response_model=NodeDefinitionDeleteResponse, status_code=status.HTTP_200_OK)
def delete_or_deactivate_node_definition(
    id: str,
    conn: sqlite3.Connection = Depends(get_db),
) -> NodeDefinitionDeleteResponse:
    """
    Safely delete or deactivate a custom node definition.
    - Prebuilt node definitions cannot be deleted (returns HTTP 403).
    - If any existing saved flows reference this node type, it is safely DEACTIVATED
      instead of deleted to prevent breaking existing flows.
    - If no flows reference this node type, it is permanently deleted.
    """
    cleaned_id = id.strip()
    select_sql = "SELECT id, name, node_type, node_source FROM node_definitions WHERE id = ?;"
    cursor = conn.execute(select_sql, (cleaned_id,))
    row = cursor.fetchone()
    cursor.close()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node definition with id '{id}' was not found.",
        )

    # Protect prebuilt definitions
    if row["node_source"] == "prebuilt":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Prebuilt node definitions are core system templates and cannot be deleted.",
        )

    target_type = row["node_type"]

    # Inspect all existing saved flows to check if any flow references this node type
    flows_cursor = conn.execute("SELECT id, name, flow_data FROM flows;")
    flow_rows = flows_cursor.fetchall()
    flows_cursor.close()
    referencing_flows = []

    for flow_row in flow_rows:
        try:
            flow_data = json.loads(flow_row["flow_data"])
            flow_nodes = flow_data.get("nodes", [])
            if any(
                isinstance(n, dict) and n.get("type") == target_type
                for n in flow_nodes
            ):
                referencing_flows.append(f"'{flow_row['name']}' ({flow_row['id'][:8]}...)")
        except Exception:
            continue

    now_iso = get_utc_now_iso()

    if referencing_flows:
        # Safe deactivation: do not break existing saved flows
        conn.execute(
            "UPDATE node_definitions SET is_active = 0, updated_at = ? WHERE id = ?;",
            (now_iso, cleaned_id),
        )
        conn.commit()

        flows_summary = ", ".join(referencing_flows[:3])
        if len(referencing_flows) > 3:
            flows_summary += f" and {len(referencing_flows) - 3} more"

        return NodeDefinitionDeleteResponse(
            message=(
                f"Custom node '{row['name']}' is referenced by {len(referencing_flows)} flow(s) "
                f"({flows_summary}). It has been safely deactivated instead of deleted to protect your flows."
            ),
            id=cleaned_id,
            deactivated=True,
        )

    # If no flows reference it, permanently delete
    conn.execute("DELETE FROM node_definitions WHERE id = ?;", (cleaned_id,))
    conn.commit()

    return NodeDefinitionDeleteResponse(
        message=f"Custom node definition '{row['name']}' was successfully deleted.",
        id=cleaned_id,
        deactivated=False,
    )
