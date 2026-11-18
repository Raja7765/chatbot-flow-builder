"""
API routes for Google Gemini LLM interaction.
Exposes endpoints for chat message generation and integration status inspection.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas import (
    GeminiChatRequest,
    GeminiChatResponse,
    GeminiStatusResponse,
)
from app.services.llm_service import (
    GeminiService,
    LLMAPIError,
    LLMConfigError,
    LLMTimeoutError,
    get_llm_service,
)

logger = logging.getLogger("app.routes.llm")

router = APIRouter(
    prefix="/llm",
    tags=["LLM"],
)


@router.get(
    "/status",
    response_model=GeminiStatusResponse,
    summary="Check Gemini LLM integration status",
    description="Returns whether the Gemini API key is configured and the active default model.",
)
def get_llm_status(
    service: GeminiService = Depends(get_llm_service),
) -> GeminiStatusResponse:
    """
    Check the configuration status of the Gemini LLM service.
    """
    return GeminiStatusResponse(
        configured=service.is_configured(),
        model=service.default_model,
    )


@router.post(
    "/chat",
    response_model=GeminiChatResponse,
    summary="Generate a chat response using Google Gemini",
    description=(
        "Sends a user message (with optional multi-turn conversation history) to Google Gemini "
        "and returns the generated assistant response."
    ),
    responses={
        200: {"description": "Successful Gemini generation"},
        422: {"description": "Validation error (e.g. empty message or invalid role)"},
        502: {"description": "Upstream Gemini API error"},
        503: {"description": "Gemini LLM is not configured on this server"},
        504: {"description": "Gemini LLM request timed out"},
    },
)
def chat_with_gemini(
    request: GeminiChatRequest,
    service: GeminiService = Depends(get_llm_service),
) -> GeminiChatResponse:
    """
    Generate an LLM response from Google Gemini for a user message.
    """
    try:
        response_text, model_used = service.generate_response(
            message=request.message,
            conversation_history=request.conversation_history,
            model=request.model,
            system_instruction=request.system_instruction,
        )
        return GeminiChatResponse(
            response=response_text,
            model=model_used,
        )

    except LLMConfigError as e:
        logger.warning("LLM request rejected: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=e.message,
        )

    except LLMTimeoutError as e:
        logger.error("LLM request timed out: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The Gemini LLM service timed out while processing your request.",
        )

    except LLMAPIError as e:
        logger.error("LLM upstream API error: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini API error: {e.message}",
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Unexpected error during LLM generation: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal error occurred while communicating with the LLM service.",
        )

