"""
Database configuration and session management module for Chatbot Flow Builder.
Connects to PostgreSQL using SQLAlchemy 2.x and psycopg.
Manages database sessions, connection pooling, and idempotent seed initialization.
"""

from datetime import datetime, timezone
import os
from pathlib import Path
import sys
from typing import Generator, List, Optional

# 1. On Windows, ensure PostgreSQL bin directory is in PATH and DLL search path for libpq.dll
pg_bin = r"C:\Program Files\PostgreSQL\18\bin"
if os.path.exists(pg_bin):
    if pg_bin not in os.environ.get("PATH", ""):
        os.environ["PATH"] = pg_bin + ";" + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(pg_bin)
        except Exception:
            pass

# 2. Load DATABASE_URL from backend/.env
BASE_DIR = Path(__file__).resolve().parent.parent
from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set. Please check backend/.env.")

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base, Chatbot, Flow, NodeDefinition

# SQLAlchemy Engine with connection pool recycling and health pre-ping
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Session factory for generating isolated database sessions per request
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

DEFAULT_CHATBOT_ID = "default-chatbot"


def get_utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


def get_utc_now_iso() -> str:
    """Return ISO 8601 formatted UTC timestamp string."""
    return datetime.now(timezone.utc).isoformat()


# Master registry of prebuilt node definitions seeded into PostgreSQL.
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


def ensure_default_chatbot(db: Session) -> None:
    """Ensure the default chatbot exists so unassigned flows have a valid parent."""
    existing = db.get(Chatbot, DEFAULT_CHATBOT_ID)
    if existing is None:
        now = get_utc_now()
        default_bot = Chatbot(
            id=DEFAULT_CHATBOT_ID,
            name="Default Chatbot",
            description="Default system chatbot for flows",
            status="active",
            created_at=now,
            updated_at=now,
        )
        db.add(default_bot)
        db.commit()


def seed_prebuilt_nodes(db: Session) -> None:
    """
    Idempotently seeds prebuilt node definitions into PostgreSQL.
    If a definition does not exist, it is inserted.
    If it already exists as prebuilt, its metadata is updated without changing
    its created_at timestamp or active state.
    """
    now = get_utc_now()
    for node in PREBUILT_NODE_DEFINITIONS:
        stmt = select(NodeDefinition).where(NodeDefinition.node_type == node["node_type"])
        existing = db.execute(stmt).scalar_one_or_none()

        if existing is None:
            new_node = NodeDefinition(
                id=node["id"],
                name=node["name"],
                node_type=node["node_type"],
                category=node["category"],
                description=node.get("description", ""),
                node_source="prebuilt",
                input_schema=node.get("input_schema", {}),
                output_schema=node.get("output_schema", {}),
                config_schema=node.get("config_schema", {}),
                executor_type=node.get("executor_type"),
                executor_config=node.get("executor_config", {}),
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            db.add(new_node)
        elif existing.node_source == "prebuilt":
            existing.name = node["name"]
            existing.category = node["category"]
            existing.description = node.get("description", "")
            existing.input_schema = node.get("input_schema", {})
            existing.output_schema = node.get("output_schema", {})
            existing.config_schema = node.get("config_schema", {})
            existing.executor_type = node.get("executor_type")
            existing.executor_config = node.get("executor_config", {})
            existing.updated_at = now

    db.commit()


def init_db() -> None:
    """
    Idempotent startup database initialization.
    Ensures default chatbot exists and prebuilt node definitions are seeded.
    Schema creation itself is handled by Alembic migrations.
    """
    with SessionLocal() as db:
        ensure_default_chatbot(db)
        seed_prebuilt_nodes(db)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding an isolated SQLAlchemy Session per request.
    Automatically commits on successful response, rolls back on exceptions,
    and safely closes the session in all scenarios.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
