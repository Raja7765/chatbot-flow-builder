"""
API routes for chatbot flow management.
Handles endpoints for creating, retrieving, updating, and deleting chatbot flows.
"""

import json
import sqlite3
from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_db, get_utc_now_iso
from app.schemas import FlowCreate, FlowDeleteResponse, FlowResponse, FlowUpdate

router = APIRouter(prefix="/flows", tags=["Flows"])


@router.post("", response_model=FlowResponse, status_code=status.HTTP_201_CREATED)
def create_flow(
    payload: FlowCreate,
    conn: sqlite3.Connection = Depends(get_db),
) -> FlowResponse:
    """
    Create a new chatbot flow.

    - Validates that 'name' is non-empty.
    - Validates that 'flow_data' contains 'nodes' and 'edges' arrays.
    - Generates a unique UUID for the flow.
    - Records ISO 8601 UTC timestamps for created_at and updated_at.
    - Stores the flow in the SQLite 'flows' table using parameterized queries.
    - Returns HTTP 201 with the created flow resource.
    """
    flow_id = str(uuid.uuid4())
    now_iso = get_utc_now_iso()
    # Serialize the validated flow_data dictionary to JSON string for SQLite storage
    flow_data_json = json.dumps(payload.flow_data.model_dump())

    insert_sql = """
    INSERT INTO flows (id, name, description, flow_data, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?);
    """
    conn.execute(
        insert_sql,
        (
            flow_id,
            payload.name,
            payload.description,
            flow_data_json,
            now_iso,
            now_iso,
        ),
    )

    return FlowResponse(
        id=flow_id,
        name=payload.name,
        description=payload.description,
        flow_data=payload.flow_data,
        created_at=now_iso,
        updated_at=now_iso,
    )


@router.get("", response_model=List[FlowResponse], status_code=status.HTTP_200_OK)
def list_flows(
    conn: sqlite3.Connection = Depends(get_db),
) -> List[FlowResponse]:
    """
    Retrieve all saved chatbot flows.

    - Queries all records from the SQLite 'flows' table ordered by newest first.
    - Parses stored JSON string in 'flow_data' back into structured JSON objects.
    - Returns a JSON array of flows, or an empty list if no flows exist.
    """
    select_sql = """
    SELECT id, name, description, flow_data, created_at, updated_at
    FROM flows
    ORDER BY created_at DESC;
    """
    cursor = conn.execute(select_sql)
    rows = cursor.fetchall()

    flows: List[FlowResponse] = []
    for row in rows:
        flows.append(
            FlowResponse(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                flow_data=json.loads(row["flow_data"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )

    return flows


@router.get("/{flow_id}", response_model=FlowResponse, status_code=status.HTTP_200_OK)
def get_flow(
    flow_id: str,
    conn: sqlite3.Connection = Depends(get_db),
) -> FlowResponse:
    """
    Retrieve a single chatbot flow by its unique ID.

    - Accepts 'flow_id' as a path parameter.
    - Validates that 'flow_id' is non-empty.
    - Queries the 'flows' table using a parameterized SQL query.
    - Parses the stored 'flow_data' JSON string into a structured JSON object.
    - Returns HTTP 200 with the flow data if found.
    - Raises HTTP 404 if no flow with the specified ID exists.
    """
    cleaned_id = flow_id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow ID cannot be empty or whitespace.",
        )

    select_sql = """
    SELECT id, name, description, flow_data, created_at, updated_at
    FROM flows
    WHERE id = ?;
    """
    cursor = conn.execute(select_sql, (cleaned_id,))
    row = cursor.fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flow with id '{flow_id}' was not found.",
        )

    return FlowResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        flow_data=json.loads(row["flow_data"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.put("/{flow_id}", response_model=FlowResponse, status_code=status.HTTP_200_OK)
def update_flow(
    flow_id: str,
    payload: FlowUpdate,
    conn: sqlite3.Connection = Depends(get_db),
) -> FlowResponse:
    """
    Update an existing chatbot flow by its unique ID.

    - Accepts 'flow_id' as a path parameter.
    - Validates request body using FlowUpdate schema.
    - Checks whether the flow exists in SQLite 'flows' table.
    - If not found, raises HTTP 404.
    - Updates name, description, flow_data, and updated_at (UTC ISO 8601).
    - Preserves the original created_at timestamp.
    - Returns HTTP 200 with the updated flow resource.
    """
    cleaned_id = flow_id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow ID cannot be empty or whitespace.",
        )

    # Check existence and fetch the original created_at timestamp
    check_sql = "SELECT created_at FROM flows WHERE id = ?;"
    cursor = conn.execute(check_sql, (cleaned_id,))
    row = cursor.fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flow with id '{flow_id}' was not found.",
        )

    original_created_at = row["created_at"]
    updated_at_iso = get_utc_now_iso()
    flow_data_json = json.dumps(payload.flow_data.model_dump())

    update_sql = """
    UPDATE flows
    SET name = ?, description = ?, flow_data = ?, updated_at = ?
    WHERE id = ?;
    """
    conn.execute(
        update_sql,
        (
            payload.name,
            payload.description,
            flow_data_json,
            updated_at_iso,
            cleaned_id,
        ),
    )

    return FlowResponse(
        id=cleaned_id,
        name=payload.name,
        description=payload.description,
        flow_data=payload.flow_data,
        created_at=original_created_at,
        updated_at=updated_at_iso,
    )


@router.delete("/{flow_id}", response_model=FlowDeleteResponse, status_code=status.HTTP_200_OK)
def delete_flow(
    flow_id: str,
    conn: sqlite3.Connection = Depends(get_db),
) -> FlowDeleteResponse:
    """
    Delete an existing chatbot flow by its unique ID.

    - Accepts 'flow_id' as a path parameter.
    - Validates that 'flow_id' is non-empty.
    - Checks whether the flow exists in SQLite 'flows' table.
    - If not found, raises HTTP 404 with a user-friendly message.
    - Deletes only that specific flow using a parameterized query.
    - Returns HTTP 200 OK with a confirmation message and the deleted flow ID.
    """
    cleaned_id = flow_id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow not found. It may have already been deleted.",
        )

    # Check if flow exists
    check_sql = "SELECT 1 FROM flows WHERE id = ?;"
    cursor = conn.execute(check_sql, (cleaned_id,))
    if cursor.fetchone() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow not found. It may have already been deleted.",
        )

    # Delete specific flow
    delete_sql = "DELETE FROM flows WHERE id = ?;"
    conn.execute(delete_sql, (cleaned_id,))

    return FlowDeleteResponse(
        message="Flow deleted successfully.",
        id=cleaned_id,
    )
