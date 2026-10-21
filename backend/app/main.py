"""
Main application module for the Chatbot Flow Builder API.
This file initializes the FastAPI application, sets up the lifespan event
for automatic database initialization, and includes route modules.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_db
from app.routes.flows import router as flows_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI application.
    Runs startup logic before the application begins accepting requests,
    and shutdown logic after the application stops.
    """
    # Startup: Ensure the SQLite database and 'flows' table are initialized
    init_db()
    yield
    # Shutdown: Clean up resources if needed in future phases


# Create the FastAPI application instance with lifespan handler
app = FastAPI(
    title="Chatbot Flow Builder API",
    description="Backend API for building and managing chatbot flows",
    version="0.1.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(flows_router)


# Root endpoint: returns a welcome message confirming the server is running
@app.get("/")
def read_root():
    """
    Root endpoint to verify that the API server is up and accessible.
    """
    return {"message": "Chatbot Flow Builder API is running"}


# Health check endpoint: returns operational status
@app.get("/health")
def read_health():
    """
    Health check endpoint for monitoring service availability.
    """
    return {"status": "ok"}
