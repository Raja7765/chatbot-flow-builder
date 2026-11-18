"""
Main application module for the Chatbot Flow Builder API.
This file initializes the FastAPI application, sets up the lifespan event
for automatic database connection verification and seed initialization,
and includes route modules.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.database import engine, init_db
from app.media_storage import ensure_upload_dirs
from app.routes.chatbots import router as chatbots_router
from app.routes.flows import router as flows_router
from app.routes.node_definitions import router as node_definitions_router
from app.routes.node_answers import router as node_answers_router
from app.routes.media import router as media_router
from app.routes.llm import router as llm_router
from app.services.llm_service import init_llm_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI application.
    Runs startup logic before the application begins accepting requests,
    and shutdown logic after the application stops.
    """
    # Startup: Verify PostgreSQL connection, ensure upload directories, initialize DB seed data, and initialize LLM
    try:
        print("🚀 Starting Chatbot Flow Builder...")
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
        print("✅ PostgreSQL connected successfully")

        ensure_upload_dirs()
        print("✅ Upload directories initialized")

        init_db()
        print("✅ Database initialization completed")

        try:
            init_llm_service()
            print("🤖 LLM initialized successfully")
        except Exception as e:
            print(f"[CRITICAL] Failed to initialize LLM during startup: {e}")
            raise
    except Exception as e:
        print(f"[CRITICAL] Failed during application startup: {e}")
        raise

    yield

    # Shutdown: Dispose engine connection pool cleanly
    try:
        engine.dispose()
    except Exception:
        pass


# Create the FastAPI application instance with lifespan handler
app = FastAPI(
    title="Chatbot Flow Builder API",
    description="Backend API for building and managing chatbot flows with PostgreSQL",
    version="0.2.0",
    lifespan=lifespan,
)

# Configure CORS for local development with the Vite frontend
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chatbots_router)
app.include_router(flows_router)
app.include_router(node_definitions_router)
app.include_router(node_answers_router)
app.include_router(media_router)
app.include_router(llm_router)


# Root endpoint: returns a welcome message confirming the server is running
@app.get("/")
def read_root():
    """
    Root endpoint to verify that the API server is up and accessible.
    """
    return {"message": "Chatbot Flow Builder API is running"}


# Health check endpoint: returns operational status and checks database
@app.get("/health")
def read_health():
    """
    Health check endpoint for monitoring service and database availability.
    Preserves exact contract: {"status": "ok"} when healthy.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "error", "detail": f"Database unavailable: {str(e)}"},
        )
