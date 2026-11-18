"""
Unit and integration tests for the Google Gemini LLM API and GeminiService.
Covers:
- Successful generation with and without conversation history
- Missing API key / unconfigured state (HTTP 503)
- Empty or whitespace message validation (HTTP 422)
- Upstream Gemini API error handling (HTTP 502)
- Upstream Gemini API timeout handling (HTTP 504)
- Invalid conversation history role / empty content validation (HTTP 422)
- /llm/status endpoint response validation
- Direct unit tests for GeminiService logic, redaction, and client mocking
"""

import asyncio
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure backend and project root are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app, lifespan
from app.schemas import ChatMessage, GeminiChatRequest
from app.services.llm_service import (
    GeminiService,
    LLMAPIError,
    LLMConfigError,
    LLMTimeoutError,
    get_llm_service,
    init_llm_service,
    reset_llm_service,
)


async def invoke_asgi(
    method: str,
    path: str,
    body: dict = None,
    raw_body: bytes = None,
    custom_headers: dict = None,
) -> tuple:
    """
    Simulate an HTTP request against the ASGI FastAPI application using Python standard library.
    """
    if raw_body is not None:
        payload_bytes = raw_body
    elif body is not None:
        payload_bytes = json.dumps(body).encode("utf-8")
    else:
        payload_bytes = b""

    headers = [
        (b"host", b"testserver"),
        (b"content-type", b"application/json"),
        (b"content-length", str(len(payload_bytes)).encode("latin1")),
    ]

    if custom_headers:
        for k, v in custom_headers.items():
            headers.append((k.lower().encode("latin1"), v.encode("latin1")))

    messages = []
    has_sent_body = False

    async def receive():
        nonlocal has_sent_body
        if not has_sent_body:
            has_sent_body = True
            return {"type": "http.request", "body": payload_bytes, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    parsed_path = path.split("?", 1)
    raw_path = parsed_path[0].encode("latin1")
    query_string = parsed_path[1].encode("latin1") if len(parsed_path) > 1 else b""

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": parsed_path[0],
        "raw_path": raw_path,
        "query_string": query_string,
        "root_path": "",
        "headers": headers,
        "server": ("127.0.0.1", 80),
        "client": ("127.0.0.1", 12345),
    }

    await app(scope, receive, send)

    status_code = None
    resp_headers = {}
    resp_body = b""

    for msg in messages:
        if msg["type"] == "http.response.start":
            status_code = msg["status"]
            for h_key, h_val in msg.get("headers", []):
                resp_headers[h_key.decode("latin1").lower()] = h_val.decode("latin1")
        elif msg["type"] == "http.response.body":
            resp_body += msg.get("body", b"")

    try:
        json_data = json.loads(resp_body.decode("utf-8")) if resp_body else None
    except Exception:
        json_data = resp_body.decode("utf-8", errors="replace")

    return status_code, json_data


class TestGeminiLLMApi(unittest.TestCase):
    """Test suite for the Gemini LLM FastAPI endpoints."""

    def tearDown(self):
        # Clear any dependency overrides after each test
        app.dependency_overrides.clear()

    def test_llm_status_configured(self):
        """GET /llm/status should return configured=True and model name when API key is present."""
        mock_service = MagicMock(spec=GeminiService)
        mock_service.is_configured.return_value = True
        mock_service.default_model = "gemini-2.5-flash"
        app.dependency_overrides[get_llm_service] = lambda: mock_service

        status_code, data = asyncio.run(invoke_asgi("GET", "/llm/status"))
        self.assertEqual(status_code, 200)
        self.assertTrue(data["configured"])
        self.assertEqual(data["model"], "gemini-2.5-flash")

    def test_llm_status_unconfigured(self):
        """GET /llm/status should return configured=False when API key is missing."""
        mock_service = MagicMock(spec=GeminiService)
        mock_service.is_configured.return_value = False
        mock_service.default_model = "gemini-2.5-flash"
        app.dependency_overrides[get_llm_service] = lambda: mock_service

        status_code, data = asyncio.run(invoke_asgi("GET", "/llm/status"))
        self.assertEqual(status_code, 200)
        self.assertFalse(data["configured"])
        self.assertEqual(data["model"], "gemini-2.5-flash")

    def test_llm_chat_success(self):
        """POST /llm/chat should return 200 with generated text and model name."""
        mock_service = MagicMock(spec=GeminiService)
        mock_service.generate_response.return_value = (
            "NABH stands for National Accreditation Board for Hospitals & Healthcare Providers.",
            "gemini-2.5-flash",
        )
        app.dependency_overrides[get_llm_service] = lambda: mock_service

        payload = {
            "message": "What is NABH?",
            "conversation_history": [],
        }
        status_code, data = asyncio.run(invoke_asgi("POST", "/llm/chat", body=payload))

        self.assertEqual(status_code, 200)
        self.assertIn("NABH stands for", data["response"])
        self.assertEqual(data["model"], "gemini-2.5-flash")
        mock_service.generate_response.assert_called_once_with(
            message="What is NABH?",
            conversation_history=[],
            model=None,
            system_instruction=None,
        )

    def test_llm_chat_with_conversation_history(self):
        """POST /llm/chat with multi-turn conversation history should pass history to service."""
        mock_service = MagicMock(spec=GeminiService)
        mock_service.generate_response.return_value = (
            "Yes, patient safety is a core focus of NABH PSQ standards.",
            "gemini-2.5-flash",
        )
        app.dependency_overrides[get_llm_service] = lambda: mock_service

        payload = {
            "message": "Does it cover patient safety?",
            "conversation_history": [
                {"role": "user", "content": "What is NABH accreditation?"},
                {"role": "model", "content": "It is a healthcare quality framework in India."},
            ],
            "model": "gemini-2.5-flash",
        }
        status_code, data = asyncio.run(invoke_asgi("POST", "/llm/chat", body=payload))

        self.assertEqual(status_code, 200)
        self.assertEqual(data["model"], "gemini-2.5-flash")
        self.assertIn("patient safety", data["response"])

        args, kwargs = mock_service.generate_response.call_args
        self.assertEqual(kwargs["message"], "Does it cover patient safety?")
        self.assertEqual(len(kwargs["conversation_history"]), 2)
        self.assertEqual(kwargs["conversation_history"][0].role, "user")
        self.assertEqual(kwargs["conversation_history"][0].content, "What is NABH accreditation?")
        self.assertEqual(kwargs["conversation_history"][1].role, "model")

    def test_llm_chat_missing_api_key_returns_503(self):
        """POST /llm/chat when unconfigured should return HTTP 503 Service Unavailable."""
        mock_service = MagicMock(spec=GeminiService)
        mock_service.generate_response.side_effect = LLMConfigError(
            "Gemini API key is not configured. Please configure GEMINI_API_KEY."
        )
        app.dependency_overrides[get_llm_service] = lambda: mock_service

        payload = {"message": "Hello QMitra"}
        status_code, data = asyncio.run(invoke_asgi("POST", "/llm/chat", body=payload))

        self.assertEqual(status_code, 503)
        self.assertIn("detail", data)
        self.assertIn("Gemini API key is not configured", data["detail"])

    def test_llm_chat_empty_message_returns_422(self):
        """POST /llm/chat with empty or whitespace message should return HTTP 422 Unprocessable Entity."""
        # Empty string
        status_code, data = asyncio.run(invoke_asgi("POST", "/llm/chat", body={"message": ""}))
        self.assertEqual(status_code, 422)

        # Whitespace-only string
        status_code, data = asyncio.run(invoke_asgi("POST", "/llm/chat", body={"message": "   \n\t  "}))
        self.assertEqual(status_code, 422)

    def test_llm_chat_missing_message_field_returns_422(self):
        """POST /llm/chat without message field should return HTTP 422."""
        status_code, data = asyncio.run(invoke_asgi("POST", "/llm/chat", body={}))
        self.assertEqual(status_code, 422)

    def test_llm_chat_invalid_history_role_returns_422(self):
        """POST /llm/chat with invalid role in conversation history should return HTTP 422."""
        payload = {
            "message": "Hello",
            "conversation_history": [
                {"role": "system_admin", "content": "Unauthorized role"},
            ],
        }
        status_code, data = asyncio.run(invoke_asgi("POST", "/llm/chat", body=payload))
        self.assertEqual(status_code, 422)

    def test_llm_chat_empty_history_content_returns_422(self):
        """POST /llm/chat with whitespace-only content in history should return HTTP 422."""
        payload = {
            "message": "Hello",
            "conversation_history": [
                {"role": "user", "content": "    "},
            ],
        }
        status_code, data = asyncio.run(invoke_asgi("POST", "/llm/chat", body=payload))
        self.assertEqual(status_code, 422)

    def test_llm_chat_upstream_api_error_returns_502(self):
        """POST /llm/chat when Gemini API fails should return HTTP 502 Bad Gateway."""
        mock_service = MagicMock(spec=GeminiService)
        mock_service.generate_response.side_effect = LLMAPIError("Gemini API error (429): Resource has been exhausted.")
        app.dependency_overrides[get_llm_service] = lambda: mock_service

        payload = {"message": "Test question"}
        status_code, data = asyncio.run(invoke_asgi("POST", "/llm/chat", body=payload))

        self.assertEqual(status_code, 502)
        self.assertIn("detail", data)
        self.assertIn("Gemini API error", data["detail"])

    def test_llm_chat_timeout_returns_504(self):
        """POST /llm/chat when Gemini API times out should return HTTP 504 Gateway Timeout."""
        mock_service = MagicMock(spec=GeminiService)
        mock_service.generate_response.side_effect = LLMTimeoutError("Request to Gemini API timed out.")
        app.dependency_overrides[get_llm_service] = lambda: mock_service

        payload = {"message": "Test question"}
        status_code, data = asyncio.run(invoke_asgi("POST", "/llm/chat", body=payload))

        self.assertEqual(status_code, 504)
        self.assertIn("detail", data)
        self.assertIn("timed out", data["detail"])


class TestGeminiServiceUnit(unittest.TestCase):
    """Direct unit tests for GeminiService class methods."""

    def test_is_configured_true_and_false(self):
        """is_configured should accurately reflect presence of API key."""
        srv_configured = GeminiService(api_key="AIzaSyTestKey123")
        self.assertTrue(srv_configured.is_configured())

        srv_unconfigured = GeminiService(api_key="")
        self.assertFalse(srv_unconfigured.is_configured())

        srv_whitespace = GeminiService(api_key="   ")
        self.assertFalse(srv_whitespace.is_configured())

    def test_generate_response_unconfigured_raises_error(self):
        """generate_response without API key must raise LLMConfigError."""
        srv = GeminiService(api_key="")
        with self.assertRaises(LLMConfigError):
            srv.generate_response(message="Hello")

    def test_generate_response_empty_message_raises_value_error(self):
        """generate_response with empty string must raise ValueError."""
        srv = GeminiService(api_key="dummy_key")
        with self.assertRaises(ValueError):
            srv.generate_response(message="   ")

    def test_api_key_redaction_in_errors(self):
        """_sanitize_error must redact raw API key from error strings."""
        raw_key = "AIzaSySecretTestKey999"
        srv = GeminiService(api_key=raw_key)

        leak_message = f"Call failed with key {raw_key} at endpoint https://generativelanguage.googleapis.com"
        sanitized = srv._sanitize_error(leak_message)

        self.assertNotIn(raw_key, sanitized)
        self.assertIn("[REDACTED_API_KEY]", sanitized)

    def test_generate_response_mocked_genai_call(self):
        """generate_response should properly call client.models.generate_content."""
        srv = GeminiService(
            api_key="test_key_abc",
            default_model="gemini-2.5-flash",
            system_instruction="You are QMitra",
        )

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "This is a mock answer from Gemini."
        mock_client.models.generate_content.return_value = mock_response

        # Inject mock client directly
        srv._client = mock_client

        history = [
            ChatMessage(role="user", content="Hi"),
            ChatMessage(role="assistant", content="Hello! How can I help?"),
        ]

        text, model = srv.generate_response(
            message="Explain patient rights under PRE standard",
            conversation_history=history,
        )

        self.assertEqual(text, "This is a mock answer from Gemini.")
        self.assertEqual(model, "gemini-2.5-flash")
        self.assertTrue(mock_client.models.generate_content.called)

        call_kwargs = mock_client.models.generate_content.call_args[1]
        self.assertEqual(call_kwargs["model"], "gemini-2.5-flash")
        # 2 history messages + 1 current message = 3 contents
        self.assertEqual(len(call_kwargs["contents"]), 3)
        self.assertEqual(call_kwargs["config"].system_instruction, "You are QMitra")


class TestLifespanStartup(unittest.TestCase):
    """Tests for application startup lifecycle and LLM initialization terminal logs."""

    def setUp(self):
        reset_llm_service()

    def tearDown(self):
        reset_llm_service()

    def test_init_llm_service_prevents_duplicate_initialization(self):
        """init_llm_service should reuse the existing client and not re-initialize."""
        with patch("google.genai.Client") as mock_client_cls:
            mock_client_instance = MagicMock()
            mock_client_cls.return_value = mock_client_instance

            with patch("app.services.llm_service.get_settings") as mock_settings:
                mock_settings.return_value.gemini_api_key = "test_api_key_valid"
                mock_settings.return_value.gemini_model = "gemini-2.5-flash"
                mock_settings.return_value.gemini_system_instruction = "test_instruction"

                # First call
                service1 = init_llm_service()
                self.assertEqual(mock_client_cls.call_count, 1)

                # Second call should reuse the same service and client without re-invoking genai.Client
                service2 = init_llm_service()
                self.assertIs(service1, service2)
                self.assertEqual(mock_client_cls.call_count, 1)

    def test_lifespan_startup_prints_expected_messages(self):
        """lifespan startup should print all status indicators including LLM initialization."""
        import io
        from unittest.mock import patch

        captured_output = io.StringIO()

        with patch("sys.stdout", captured_output), \
             patch("app.main.engine.connect"), \
             patch("app.main.ensure_upload_dirs"), \
             patch("app.main.init_db"), \
             patch("app.main.init_llm_service"):

            async def run_startup():
                async with lifespan(app):
                    pass

            asyncio.run(run_startup())

        output = captured_output.getvalue()
        self.assertIn("🚀 Starting Chatbot Flow Builder...", output)
        self.assertIn("✅ PostgreSQL connected successfully", output)
        self.assertIn("✅ Upload directories initialized", output)
        self.assertIn("✅ Database initialization completed", output)
        self.assertIn("🤖 LLM initialized successfully", output)

    def test_lifespan_startup_llm_failure(self):
        """lifespan startup should log critical error and raise when LLM initialization fails."""
        import io
        from unittest.mock import patch

        captured_output = io.StringIO()

        with patch("sys.stdout", captured_output), \
             patch("app.main.engine.connect"), \
             patch("app.main.ensure_upload_dirs"), \
             patch("app.main.init_db"), \
             patch("app.main.init_llm_service", side_effect=LLMConfigError("Missing key")):

            async def run_startup():
                async with lifespan(app):
                    pass

            with self.assertRaises(LLMConfigError):
                asyncio.run(run_startup())

        output = captured_output.getvalue()
        self.assertIn("Failed to initialize LLM during startup: Missing key", output)


if __name__ == "__main__":
    unittest.main()


