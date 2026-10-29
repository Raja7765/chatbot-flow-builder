"""
API routes for Chatbot management.
Provides endpoints for creating, retrieving, updating, and safely deleting chatbots,
as well as listing flows associated with a specific chatbot.
"""

import json
import sqlite3
from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_db, get_utc_now_iso
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
    conn: sqlite3.Connection = Depends(get_db),
) -> ChatbotResponse:
    """
    Create a new chatbot.

    - Validates that 'name' is non-empty.
    - Validates that 'status' is either 'active' or 'inactive'.
    - Generates a unique UUID for the chatbot.
    - Records ISO 8601 UTC timestamps for created_at and updated_at.
    - Stores the chatbot in the SQLite 'chatbots' table using parameterized queries.
    - Returns HTTP 201 with the created chatbot resource.
    """
    chatbot_id = str(uuid.uuid4())
    now_iso = get_utc_now_iso()

    insert_sql = """
    INSERT INTO chatbots (id, name, description, status, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?);
    """
    conn.execute(
        insert_sql,
        (
            chatbot_id,
            payload.name,
            payload.description,
            payload.status.value,
            now_iso,
            now_iso,
        ),
    )
    conn.commit()

    return ChatbotResponse(
        id=chatbot_id,
        name=payload.name,
        description=payload.description,
        status=payload.status.value,
        created_at=now_iso,
        updated_at=now_iso,
    )


@router.get("", response_model=List[ChatbotResponse], status_code=status.HTTP_200_OK)
def list_chatbots(
    conn: sqlite3.Connection = Depends(get_db),
) -> List[ChatbotResponse]:
    """
    Retrieve all chatbots.

    - Queries all records from the SQLite 'chatbots' table ordered by newest first.
    - Returns a JSON array of chatbots, or an empty list if none exist.
    """
    select_sql = """
    SELECT id, name, description, status, created_at, updated_at
    FROM chatbots
    ORDER BY created_at DESC;
    """
    cursor = conn.execute(select_sql)
    rows = cursor.fetchall()
    cursor.close()

    chatbots: List[ChatbotResponse] = []
    for row in rows:
        chatbots.append(
            ChatbotResponse(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                status=row["status"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )

    return chatbots


@router.get("/{chatbot_id}", response_model=ChatbotResponse, status_code=status.HTTP_200_OK)
def get_chatbot(
    chatbot_id: str,
    conn: sqlite3.Connection = Depends(get_db),
) -> ChatbotResponse:
    """
    Retrieve a single chatbot by its unique ID.

    - Accepts 'chatbot_id' as a path parameter.
    - Validates that 'chatbot_id' is non-empty.
    - Queries the 'chatbots' table using a parameterized query.
    - Returns HTTP 200 with the chatbot data if found.
    - Raises HTTP 404 if no chatbot with the specified ID exists.
    """
    cleaned_id = chatbot_id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot ID cannot be empty or whitespace.",
        )

    select_sql = """
    SELECT id, name, description, status, created_at, updated_at
    FROM chatbots
    WHERE id = ?;
    """
    cursor = conn.execute(select_sql, (cleaned_id,))
    row = cursor.fetchone()
    cursor.close()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chatbot with id '{chatbot_id}' was not found.",
        )

    return ChatbotResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.put("/{chatbot_id}", response_model=ChatbotResponse, status_code=status.HTTP_200_OK)
def update_chatbot(
    chatbot_id: str,
    payload: ChatbotUpdate,
    conn: sqlite3.Connection = Depends(get_db),
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

    check_sql = "SELECT created_at FROM chatbots WHERE id = ?;"
    cursor = conn.execute(check_sql, (cleaned_id,))
    row = cursor.fetchone()
    cursor.close()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chatbot with id '{chatbot_id}' was not found.",
        )

    original_created_at = row["created_at"]
    updated_at_iso = get_utc_now_iso()

    update_sql = """
    UPDATE chatbots
    SET name = ?, description = ?, status = ?, updated_at = ?
    WHERE id = ?;
    """
    conn.execute(
        update_sql,
        (
            payload.name,
            payload.description,
            payload.status.value,
            updated_at_iso,
            cleaned_id,
        ),
    )
    conn.commit()

    return ChatbotResponse(
        id=cleaned_id,
        name=payload.name,
        description=payload.description,
        status=payload.status.value,
        created_at=original_created_at,
        updated_at=updated_at_iso,
    )


@router.delete("/{chatbot_id}", response_model=ChatbotDeleteResponse, status_code=status.HTTP_200_OK)
def delete_chatbot(
    chatbot_id: str,
    conn: sqlite3.Connection = Depends(get_db),
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

    # Check existence
    check_sql = "SELECT 1 FROM chatbots WHERE id = ?;"
    cursor = conn.execute(check_sql, (cleaned_id,))
    exists = cursor.fetchone() is not None
    cursor.close()
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found. It may have already been deleted.",
        )

    # Safe deletion check: prevent deletion if flows exist
    count_sql = "SELECT COUNT(*) as flow_count FROM flows WHERE chatbot_id = ?;"
    cursor = conn.execute(count_sql, (cleaned_id,))
    flow_count = cursor.fetchone()["flow_count"]
    cursor.close()

    if flow_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete chatbot with id '{cleaned_id}' because it has {flow_count} associated flow(s). Please delete or reassign its flows first.",
        )

    delete_sql = "DELETE FROM chatbots WHERE id = ?;"
    conn.execute(delete_sql, (cleaned_id,))
    conn.commit()

    return ChatbotDeleteResponse(
        message="Chatbot deleted successfully.",
        id=cleaned_id,
    )


@router.get("/{chatbot_id}/flows", response_model=List[FlowResponse], status_code=status.HTTP_200_OK)
def list_flows_by_chatbot(
    chatbot_id: str,
    conn: sqlite3.Connection = Depends(get_db),
) -> List[FlowResponse]:
    """
    Retrieve all flows associated with a specific chatbot.

    - Validates that the chatbot exists. If not, raises HTTP 404.
    - Retrieves matching flows ordered by newest first.
    - Parses stored flow_data JSON text.
    - Returns a JSON array of flows.
    """
    cleaned_id = chatbot_id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot ID cannot be empty or whitespace.",
        )

    # Verify chatbot exists
    check_sql = "SELECT 1 FROM chatbots WHERE id = ?;"
    cursor = conn.execute(check_sql, (cleaned_id,))
    exists = cursor.fetchone() is not None
    cursor.close()
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chatbot with id '{chatbot_id}' was not found.",
        )

    select_sql = """
    SELECT id, chatbot_id, name, description, flow_data, created_at, updated_at
    FROM flows
    WHERE chatbot_id = ?
    ORDER BY created_at DESC;
    """
    cursor = conn.execute(select_sql, (cleaned_id,))
    rows = cursor.fetchall()
    cursor.close()

    flows: List[FlowResponse] = []
    for row in rows:
        flows.append(
            FlowResponse(
                id=row["id"],
                chatbot_id=row["chatbot_id"],
                name=row["name"],
                description=row["description"],
                flow_data=json.loads(row["flow_data"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )

    return flows
