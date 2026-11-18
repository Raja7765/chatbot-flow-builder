"""
Dedicated LLM service module for Google Gemini integration in Chatbot Flow Builder.
Encapsulates Gemini client initialization, prompt assembly, conversation history formatting,
and robust error handling without exposing API keys or internal stack traces.
"""

import logging
from typing import List, Optional, Tuple

from app.config import (
    DEFAULT_SYSTEM_INSTRUCTION,
    get_settings,
)
from app.schemas import ChatMessage

logger = logging.getLogger("app.services.llm_service")


# ============================================================================
# Custom LLM Exceptions
# ============================================================================

class LLMError(Exception):
    """Base exception for all LLM service errors."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class LLMConfigError(LLMError):
    """Raised when the LLM service is misconfigured or missing credentials."""
    pass


class LLMAPIError(LLMError):
    """Raised when an upstream call to the Gemini API fails."""
    pass


class LLMTimeoutError(LLMError):
    """Raised when a request to the Gemini API times out."""
    pass


# ============================================================================
# Gemini Service
# ============================================================================

class GeminiService:
    """
    Dedicated service for interacting with Google Gemini LLM models.
    Supports single-turn prompts, multi-turn conversation context, and
    configurable system instructions.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        system_instruction: Optional[str] = None,
    ):
        settings = get_settings()
        self.api_key: str = (
            api_key if api_key is not None else settings.gemini_api_key
        ).strip()
        self.default_model: str = (
            default_model if default_model is not None else settings.gemini_model
        ).strip() or "gemini-2.5-flash"
        self.system_instruction: str = (
            system_instruction
            if system_instruction is not None
            else settings.gemini_system_instruction
        )
        self._client = None

    def is_configured(self) -> bool:
        """
        Check whether the Gemini service has a non-empty API key configured.
        """
        return bool(self.api_key)

    def _get_client(self):
        """
        Lazily initialize and return the official google-genai Client.
        Raises LLMConfigError if API key is not configured.
        """
        if not self.is_configured():
            raise LLMConfigError(
                "Gemini API key is not configured. "
                "Please configure GEMINI_API_KEY in the backend environment."
            )
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error("Failed to initialize Google GenAI client: %s", str(e))
                raise LLMConfigError(f"Failed to initialize Gemini client: {self._sanitize_error(str(e))}") from e
        return self._client

    def _sanitize_error(self, error_msg: str) -> str:
        """
        Remove any accidental exposure of the API key from error strings.
        """
        if self.api_key and self.api_key in error_msg:
            return error_msg.replace(self.api_key, "[REDACTED_API_KEY]")
        return error_msg

    def generate_response(
        self,
        message: str,
        conversation_history: Optional[List[ChatMessage]] = None,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Send a user message with optional conversation history to Gemini and return the response.

        Args:
            message: The current user message string (must be non-empty).
            conversation_history: Optional list of previous ChatMessage instances.
            model: Optional model override (e.g. 'gemini-2.5-flash').
            system_instruction: Optional system instruction override.

        Returns:
            Tuple of (response_text, model_name_used).

        Raises:
            LLMConfigError: When the API key is not set.
            LLMAPIError: When the Gemini API call fails upstream.
            LLMTimeoutError: When the Gemini API call times out.
        """
        clean_message = message.strip()
        if not clean_message:
            raise ValueError("Message cannot be empty or whitespace only.")

        client = self._get_client()
        target_model = (model or self.default_model).strip()
        target_instruction = (
            system_instruction
            if system_instruction is not None
            else self.system_instruction
        )

        from google.genai import errors, types

        # Build contents structure: previous history + current user message
        contents = []
        if conversation_history:
            for item in conversation_history:
                # Map role: assistant/model -> 'model', user -> 'user'
                role = "model" if item.role in ("model", "assistant") else "user"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=item.content)],
                    )
                )

        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=clean_message)],
            )
        )

        config = types.GenerateContentConfig(
            system_instruction=target_instruction,
        )

        try:
            response = client.models.generate_content(
                model=target_model,
                contents=contents,
                config=config,
            )

            # Extract response text safely
            response_text = ""
            if response and getattr(response, "text", None):
                response_text = response.text
            elif response and getattr(response, "candidates", None) and response.candidates:
                candidate = response.candidates[0]
                if getattr(candidate, "finish_reason", None):
                    response_text = f"[Response ended: {candidate.finish_reason}]"

            return response_text, target_model

        except errors.APIError as exc:
            sanitized = self._sanitize_error(str(exc.message or exc))
            code = getattr(exc, "code", "UNKNOWN")
            logger.error("Gemini API error (code=%s): %s", code, sanitized)
            raise LLMAPIError(f"Gemini API error ({code}): {sanitized}") from exc

        except Exception as exc:
            err_str = str(exc)
            sanitized = self._sanitize_error(err_str)
            if "timeout" in err_str.lower() or "timed out" in err_str.lower():
                logger.error("Gemini API request timed out: %s", sanitized)
                raise LLMTimeoutError("Request to Gemini API timed out.") from exc

            logger.error("Unexpected error calling Gemini API: %s", sanitized)
            raise LLMAPIError(f"Gemini API request failed: {sanitized}") from exc


_service_instance: Optional[GeminiService] = None


def get_llm_service() -> GeminiService:
    """
    FastAPI dependency provider for GeminiService.
    Reuses the shared singleton instance created during initialization or on-demand.
    Can be overridden in test suites using app.dependency_overrides[get_llm_service].
    """
    global _service_instance
    if _service_instance is None:
        settings = get_settings()
        _service_instance = GeminiService(
            api_key=settings.gemini_api_key,
            default_model=settings.gemini_model,
            system_instruction=settings.gemini_system_instruction,
        )
    return _service_instance


def init_llm_service() -> GeminiService:
    """
    Initialize the LLM service during application startup lifecycle.
    Ensures the client is initialized once and reused across the application.

    Raises:
        LLMConfigError: If the Gemini API key is missing or client initialization fails.
    """
    service = get_llm_service()
    if not service.is_configured():
        raise LLMConfigError(
            "Gemini API key is not configured. "
            "Please configure GEMINI_API_KEY in the backend environment."
        )
    # Eagerly initialize the client to verify configuration and avoid duplicate init
    service._get_client()
    return service


def reset_llm_service() -> None:
    """
    Reset the singleton instance (useful in test fixtures).
    """
    global _service_instance
    _service_instance = None


