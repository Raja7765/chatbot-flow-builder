"""
Configuration module for the Chatbot Flow Builder backend.
Loads settings from environment variables and backend/.env.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:1234@localhost:5432/chatbot_flow_builder",
)

# Gemini LLM settings
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"

DEFAULT_SYSTEM_INSTRUCTION: str = (
    "You are QMitra, a helpful and professional AI assistant for hospital accreditation and quality management. "
    "Provide clear, accurate, and professional answers to healthcare providers and staff. "
    "Do not invent facts, regulations, or standards. If you do not know an answer or if specific guidance is unavailable, "
    "clearly acknowledge that you do not have sufficient information. "
    "Do not claim that any statement is officially endorsed or approved by NABH unless explicitly confirmed. "
    "Note that direct document retrieval and official NABH source standard document lookup are not currently connected."
)

GEMINI_SYSTEM_INSTRUCTION: str = (
    os.getenv("GEMINI_SYSTEM_INSTRUCTION", DEFAULT_SYSTEM_INSTRUCTION).strip()
    or DEFAULT_SYSTEM_INSTRUCTION
)


class Settings:
    """Settings accessor class to allow programmatic inspection or overrides in testing."""

    def __init__(
        self,
        gemini_api_key: str = GEMINI_API_KEY,
        gemini_model: str = GEMINI_MODEL,
        gemini_system_instruction: str = GEMINI_SYSTEM_INSTRUCTION,
        database_url: str = DATABASE_URL,
    ):
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model
        self.gemini_system_instruction = gemini_system_instruction
        self.database_url = database_url

    @property
    def is_gemini_configured(self) -> bool:
        return bool(self.gemini_api_key)


def get_settings() -> Settings:
    """Return current configuration settings, freshly reading environment if needed."""
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash",
        gemini_system_instruction=os.getenv(
            "GEMINI_SYSTEM_INSTRUCTION", DEFAULT_SYSTEM_INSTRUCTION
        ).strip()
        or DEFAULT_SYSTEM_INSTRUCTION,
        database_url=os.getenv("DATABASE_URL", DATABASE_URL),
    )

