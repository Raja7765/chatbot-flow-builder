"""
Database configuration and management module for the Chatbot Flow Builder.
This module uses Python's built-in sqlite3 module to manage database connections,
ensure safe connection cleanup, initialize the database directory, and create tables.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Generator, List, Optional, Union

# Define paths relative to this file to ensure predictability across working directories:
# __file__ -> backend/app/database.py
# .parent -> backend/app
# .parent.parent -> backend
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_DB_PATH = DATA_DIR / "flows.db"


def get_utc_now_iso() -> str:
    """
    Return the current UTC timestamp formatted as an ISO 8601 string.
    Example: '2026-10-21T06:07:35.123456+00:00'
    """
    return datetime.now(timezone.utc).isoformat()


def ensure_db_directory(db_path: Union[Path, str]) -> Path:
    """
    Ensure the parent directory for the database file exists.
    Creates parent directories if they do not exist.

    Args:
        db_path: The file path to the SQLite database.

    Returns:
        Path: The resolved absolute Path object.
    """
    resolved_path = Path(db_path).resolve()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    return resolved_path


@contextmanager
def get_db_connection(
    db_path: Optional[Union[Path, str]] = None
) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager providing a safely managed SQLite database connection.
    Configured with check_same_thread=False and a 30s busy timeout to support
    isolated per-request connection lifecycles across FastAPI's AnyIO thread pool.
    Automatically commits on success, rolls back on error, and ensures the
    connection is closed in all cases (including exceptions).

    Args:
        db_path: Optional path to the SQLite database file. Defaults to DEFAULT_DB_PATH.

    Yields:
        sqlite3.Connection: An open SQLite connection with Row factory enabled.
    """
    target_path = ensure_db_directory(db_path or DEFAULT_DB_PATH)
    conn = sqlite3.connect(
        target_path,
        check_same_thread=False,
        timeout=30.0,
    )
    # Enable dict-like column access by column name (e.g. row['name'])
    conn.row_factory = sqlite3.Row
    # Enable foreign keys support in SQLite
    conn.execute("PRAGMA foreign_keys = ON;")
    # Enable WAL mode for high concurrency between reader/writer threads
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA synchronous = NORMAL;")

    try:
        yield conn
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass



DEFAULT_CHATBOT_ID = "default-chatbot"

# Master registry of prebuilt node definitions seeded into the SQLite database.
# Preserves existing flow node types ('start', 'message', 'router', 'employee_search', 'rag', 'response', 'tts')
# and introduces standard prebuilt types ('llm', 'api_request', 'condition', 'database').
PREBUILT_NODE_DEFINITIONS = [
    {
        "id": "prebuilt-start",
        "name": "Start Step",
        "node_type": "start",
        "category": "Core",
        "description": "Flow entrypoint that receives user query and trigger context tokens",
        "input_schema": {"properties": {"user_query": {"type": "string", "description": "Incoming user prompt"}}},
        "output_schema": {"properties": {"query": {"type": "string", "description": "Trigger query text"}}},
        "config_schema": {
            "fields": [
                {"name": "text", "label": "Trigger Description", "type": "string", "required": False, "default": "Flow entrypoint step"}
            ]
        },
        "executor_type": "entrypoint",
        "executor_config": {},
    },
    {
        "id": "prebuilt-message",
        "name": "Message",
        "node_type": "message",
        "category": "Communication",
        "description": "Automated message response to the user",
        "input_schema": {"properties": {"text": {"type": "string"}}},
        "output_schema": {"properties": {"delivered": {"type": "boolean"}}},
        "config_schema": {
            "fields": [
                {"name": "text", "label": "Message Content", "type": "string", "required": True, "default": "Hello! How can I assist you today?"}
            ]
        },
        "executor_type": "message_sender",
        "executor_config": {},
    },
    {
        "id": "prebuilt-answer",
        "name": "Answer",
        "node_type": "answer",
        "category": "Communication",
        "description": "Static response with optional manual source citation metadata",
        "input_schema": {"properties": {"trigger": {"type": "any"}}},
        "output_schema": {"properties": {"text": {"type": "string"}}},
        "config_schema": {
            "fields": [
                {"name": "answer_text", "label": "Answer Text", "type": "textarea", "required": True, "default": ""},
                {"name": "source_document", "label": "Source Document", "type": "string", "required": False, "default": ""},
                {"name": "page_number", "label": "Page Number", "type": "string", "required": False, "default": ""},
                {"name": "source_url", "label": "Source URL", "type": "string", "required": False, "default": ""}
            ]
        },
        "executor_type": "answer_responder",
        "executor_config": {},
    },
    {
        "id": "prebuilt-router",
        "name": "Query Router",
        "node_type": "router",
        "category": "AI",
        "description": "Classify user intent using DSPy & Gemini to route to specialized handlers",
        "input_schema": {"properties": {"query": {"type": "string"}}},
        "output_schema": {"properties": {"route": {"type": "string"}}},
        "config_schema": {
            "fields": [
                {"name": "classifier_engine", "label": "Classifier Engine", "type": "string", "required": True, "default": "DSPy + Gemini"},
                {"name": "default_route", "label": "Default Route", "type": "string", "required": False, "default": "faq-rag"}
            ]
        },
        "executor_type": "dspy_router",
        "executor_config": {"service": "application/core/query_router.py"},
    },
    {
        "id": "prebuilt-llm",
        "name": "LLM Generation",
        "node_type": "llm",
        "category": "AI",
        "description": "Generate conversational or structured responses using an LLM model",
        "input_schema": {"properties": {"prompt": {"type": "string"}}},
        "output_schema": {"properties": {"completion": {"type": "string"}}},
        "config_schema": {
            "fields": [
                {"name": "model", "label": "Model Name", "type": "select", "required": True, "default": "gemini-1.5-flash", "options": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-ultra"]},
                {"name": "temperature", "label": "Temperature", "type": "number", "required": False, "default": 0.7},
                {"name": "system_prompt", "label": "System Prompt", "type": "string", "required": False, "default": "You are a helpful assistant."}
            ]
        },
        "executor_type": "llm_generator",
        "executor_config": {},
    },
    {
        "id": "prebuilt-api-request",
        "name": "API Request",
        "node_type": "api_request",
        "category": "Integration",
        "description": "Perform HTTP REST API requests to external services",
        "input_schema": {"properties": {"body": {"type": "object"}}},
        "output_schema": {"properties": {"response_body": {"type": "object"}, "status_code": {"type": "integer"}}},
        "config_schema": {
            "fields": [
                {"name": "method", "label": "HTTP Method", "type": "select", "required": True, "default": "GET", "options": ["GET", "POST", "PUT", "DELETE"]},
                {"name": "endpoint_url", "label": "Endpoint URL", "type": "string", "required": True, "default": "https://api.example.com/data"},
                {"name": "timeout", "label": "Timeout (seconds)", "type": "number", "required": False, "default": 30}
            ]
        },
        "executor_type": "http_client",
        "executor_config": {},
    },
    {
        "id": "prebuilt-condition",
        "name": "Condition",
        "node_type": "condition",
        "category": "Logic",
        "description": "Evaluate conditions and branch flow execution based on variables",
        "input_schema": {"properties": {"value": {"type": "any"}}},
        "output_schema": {"properties": {"result": {"type": "boolean"}}},
        "config_schema": {
            "fields": [
                {"name": "variable", "label": "Variable Name", "type": "string", "required": True, "default": "status"},
                {"name": "operator", "label": "Operator", "type": "select", "required": True, "default": "equals", "options": ["equals", "not_equals", "contains", "greater_than", "less_than"]},
                {"name": "value", "label": "Comparison Value", "type": "string", "required": True, "default": "active"}
            ]
        },
        "executor_type": "rule_evaluator",
        "executor_config": {},
    },
    {
        "id": "prebuilt-database",
        "name": "Database Query",
        "node_type": "database",
        "category": "Data",
        "description": "Execute structured queries against internal database",
        "input_schema": {"properties": {"parameters": {"type": "object"}}},
        "output_schema": {"properties": {"rows": {"type": "array"}}},
        "config_schema": {
            "fields": [
                {"name": "query_type", "label": "Query Type", "type": "select", "required": True, "default": "SELECT", "options": ["SELECT", "INSERT", "UPDATE"]},
                {"name": "table_name", "label": "Table Name", "type": "string", "required": True, "default": "users"},
                {"name": "limit", "label": "Result Limit", "type": "number", "required": False, "default": 10}
            ]
        },
        "executor_type": "sql_executor",
        "executor_config": {},
    },
    {
        "id": "prebuilt-response",
        "name": "SSE Streaming Response",
        "node_type": "response",
        "category": "Communication",
        "description": "Stream generated answer chunks to client widget via Server-Sent Events (SSE)",
        "input_schema": {"properties": {"text_chunk": {"type": "string"}}},
        "output_schema": {"properties": {"completed": {"type": "boolean"}}},
        "config_schema": {
            "fields": [
                {"name": "stream_mode", "label": "Stream Mode", "type": "string", "required": True, "default": "Server-Sent Events (SSE)"},
                {"name": "include_metadata", "label": "Include Metadata", "type": "boolean", "required": False, "default": True}
            ]
        },
        "executor_type": "sse_streamer",
        "executor_config": {},
    },
    {
        "id": "prebuilt-employee-search",
        "name": "Employee Search",
        "node_type": "employee_search",
        "category": "Integration",
        "description": "Search internal employee directory by name or department filter",
        "input_schema": {"properties": {"employee_name": {"type": "string"}}},
        "output_schema": {"properties": {"records": {"type": "array"}}},
        "config_schema": {
            "fields": [
                {"name": "search_mode", "label": "Search Mode", "type": "string", "required": True, "default": "Exact & Department Filter"},
                {"name": "max_results", "label": "Max Results", "type": "number", "required": False, "default": 5}
            ]
        },
        "executor_type": "directory_search",
        "executor_config": {"service": "application/services/employee_service.py"},
    },
    {
        "id": "prebuilt-rag",
        "name": "RAG / Source",
        "node_type": "rag",
        "category": "AI",
        "description": "Retrieve knowledge embeddings and generate answer with LLM",
        "input_schema": {"properties": {"query": {"type": "string"}}},
        "output_schema": {"properties": {"answer": {"type": "string"}, "citations": {"type": "array"}}},
        "config_schema": {
            "fields": [
                {"name": "vector_store", "label": "Vector Store", "type": "string", "required": True, "default": "ChromaDB"},
                {"name": "llm", "label": "LLM Engine", "type": "string", "required": True, "default": "Gemini"},
                {"name": "top_k", "label": "Top K Passages", "type": "number", "required": False, "default": 3},
                {"name": "similarity_threshold", "label": "Similarity Threshold", "type": "number", "required": False, "default": 0.7}
            ]
        },
        "executor_type": "rag_pipeline",
        "executor_config": {"service": "application/services/rag_service.py"},
    },
    {
        "id": "prebuilt-tts",
        "name": "TTS Audio Generation",
        "node_type": "tts",
        "category": "Audio",
        "description": "Generate speech audio stream from response text",
        "input_schema": {"properties": {"text": {"type": "string"}}},
        "output_schema": {"properties": {"audio_url": {"type": "string"}}},
        "config_schema": {
            "fields": [
                {"name": "audio_format", "label": "Audio Format", "type": "string", "required": True, "default": "wav"},
                {"name": "voice", "label": "Voice Identifier", "type": "string", "required": True, "default": "en-IN-Wavenet-A"}
            ]
        },
        "executor_type": "tts_service",
        "executor_config": {"service": "application/services/tts_service.py"},
    },
]


def seed_prebuilt_nodes(conn: sqlite3.Connection, now_iso: str) -> None:
    """
    Idempotently seeds prebuilt node definitions into the SQLite database.
    If a definition does not exist, it is inserted.
    If it already exists as prebuilt, its definition metadata is safely updated
    while preserving its original creation timestamp and active state.
    """
    for node in PREBUILT_NODE_DEFINITIONS:
        input_schema_json = json.dumps(node.get("input_schema", {}))
        output_schema_json = json.dumps(node.get("output_schema", {}))
        config_schema_json = json.dumps(node.get("config_schema", {}))
        executor_config_json = json.dumps(node.get("executor_config", {}))

        cursor = conn.execute(
            "SELECT id, node_source FROM node_definitions WHERE node_type = ?;",
            (node["node_type"],),
        )
        existing = cursor.fetchone()
        cursor.close()

        if existing is None:
            conn.execute(
                """
                INSERT INTO node_definitions (
                    id, name, node_type, category, description, node_source,
                    input_schema, output_schema, config_schema,
                    executor_type, executor_config, is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?);
                """,
                (
                    node["id"],
                    node["name"],
                    node["node_type"],
                    node["category"],
                    node.get("description", ""),
                    "prebuilt",
                    input_schema_json,
                    output_schema_json,
                    config_schema_json,
                    node.get("executor_type"),
                    executor_config_json,
                    now_iso,
                    now_iso,
                ),
            )
        elif existing["node_source"] == "prebuilt":
            conn.execute(
                """
                UPDATE node_definitions
                SET name = ?, category = ?, description = ?,
                    input_schema = ?, output_schema = ?, config_schema = ?,
                    executor_type = ?, executor_config = ?, updated_at = ?
                WHERE id = ?;
                """,
                (
                    node["name"],
                    node["category"],
                    node.get("description", ""),
                    input_schema_json,
                    output_schema_json,
                    config_schema_json,
                    node.get("executor_type"),
                    executor_config_json,
                    now_iso,
                    existing["id"],
                ),
            )


def init_db(db_path: Optional[Union[Path, str]] = None) -> None:
    """
    Initialize the SQLite database by creating the required tables and performing
    safe, idempotent migrations.

    Tables:
    1. 'chatbots':
       - id: TEXT PRIMARY KEY (unique identifier for each chatbot)
       - name: TEXT NOT NULL (display name)
       - description: TEXT (optional description)
       - status: TEXT NOT NULL DEFAULT 'active' ('active' or 'inactive')
       - created_at: TEXT NOT NULL (ISO 8601 UTC creation timestamp)
       - updated_at: TEXT NOT NULL (ISO 8601 UTC last update timestamp)

    2. 'flows':
       - id: TEXT PRIMARY KEY (unique identifier for each flow)
       - chatbot_id: TEXT (foreign key referencing chatbots.id)
       - name: TEXT NOT NULL (display name of the flow)
       - description: TEXT (optional description)
       - flow_data: TEXT NOT NULL (JSON-serialized flow configuration)
       - created_at: TEXT NOT NULL (ISO 8601 UTC creation timestamp)
       - updated_at: TEXT NOT NULL (ISO 8601 UTC last update timestamp)
    """
    create_chatbots_sql = """
    CREATE TABLE IF NOT EXISTS chatbots (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """

    create_flows_sql = """
    CREATE TABLE IF NOT EXISTS flows (
        id TEXT PRIMARY KEY,
        chatbot_id TEXT,
        name TEXT NOT NULL,
        description TEXT,
        flow_data TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (chatbot_id) REFERENCES chatbots (id)
    );
    """

    create_node_definitions_sql = """
    CREATE TABLE IF NOT EXISTS node_definitions (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        node_type TEXT NOT NULL UNIQUE,
        category TEXT NOT NULL,
        description TEXT,
        node_source TEXT NOT NULL CHECK(node_source IN ('prebuilt', 'custom')),
        input_schema TEXT NOT NULL DEFAULT '{}',
        output_schema TEXT NOT NULL DEFAULT '{}',
        config_schema TEXT NOT NULL DEFAULT '{}',
        executor_type TEXT,
        executor_config TEXT NOT NULL DEFAULT '{}',
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """

    create_node_index_sql = """
    CREATE INDEX IF NOT EXISTS idx_node_definitions_filter
    ON node_definitions (is_active, category, node_source);
    """

    now_iso = get_utc_now_iso()

    with get_db_connection(db_path) as conn:
        # 1. Create chatbots table first
        conn.execute(create_chatbots_sql)

        # 2. Create flows table if it does not exist
        conn.execute(create_flows_sql)

        # 3. Create node_definitions table and index
        conn.execute(create_node_definitions_sql)
        conn.execute(create_node_index_sql)

        # 4. Safe repeatable migration: check if 'chatbot_id' column exists in 'flows'
        cursor = conn.execute("PRAGMA table_info(flows);")
        columns = [row["name"] for row in cursor.fetchall()]
        cursor.close()

        if "chatbot_id" not in columns:
            conn.execute("ALTER TABLE flows ADD COLUMN chatbot_id TEXT REFERENCES chatbots(id);")

        # 5. Ensure a default chatbot exists so legacy/unlinked flows are safely associated
        conn.execute(
            """
            INSERT OR IGNORE INTO chatbots (id, name, description, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (
                DEFAULT_CHATBOT_ID,
                "Default Chatbot",
                "Default system chatbot for flows",
                "active",
                now_iso,
                now_iso,
            ),
        )

        # 6. Non-destructive backfill: assign existing flows without chatbot_id to default-chatbot
        conn.execute(
            "UPDATE flows SET chatbot_id = ? WHERE chatbot_id IS NULL OR chatbot_id = '';",
            (DEFAULT_CHATBOT_ID,),
        )

        # 7. Seed prebuilt node definitions (idempotent, safe restart)
        seed_prebuilt_nodes(conn, now_iso)


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """
    FastAPI dependency that yields a managed SQLite database connection.
    Automatically commits upon request completion, rolls back on errors,
    and safely closes the connection in all scenarios.
    """
    with get_db_connection() as conn:
        yield conn

