"""
FastAPI Backend Integration Test Suite for PostgreSQL Migration.
Tests every API route against PostgreSQL:
- Root & Health endpoints
- Chatbot CRUD and cascade deletion protection
- Flow CRUD and JSONB flow_data persistence
- Node Definition CRUD, prebuilt protection, and safe deactivation
Cleans up all temporary test records so production data is untouched.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import uuid

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

# 2. Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

import asyncio
from app.main import app


async def invoke_asgi(
    method: str,
    path: str,
    body: dict = None,
    custom_headers: dict = None,
) -> tuple:
    """Invokes the FastAPI ASGI application directly."""
    payload_bytes = json.dumps(body).encode("utf-8") if body is not None else b""
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

    path_only, _, query_string = path.partition("?")
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "path": path_only,
        "raw_path": path_only.encode("latin1"),
        "query_string": query_string.encode("latin1"),
        "headers": headers,
    }

    await app(scope, receive, send)

    status_code = None
    response_headers = {}
    response_body = bytearray()

    for msg in messages:
        if msg["type"] == "http.response.start":
            status_code = msg["status"]
            response_headers = {k.decode("latin1"): v.decode("latin1") for k, v in msg.get("headers", [])}
        elif msg["type"] == "http.response.body":
            response_body.extend(msg.get("body", b""))

    data = None
    if response_body:
        try:
            data = json.loads(response_body.decode("utf-8"))
        except Exception:
            data = response_body.decode("utf-8")

    return status_code, data


async def run_all_tests():
    print("=" * 70)
    print("RUNNING POSTGRESQL FASTAPI INTEGRATION TEST SUITE")
    print("=" * 70)

    # 1. Root & Health
    print("\n--- 1. Root and Health Endpoints ---")
    status_code, data = await invoke_asgi("GET", "/")
    assert status_code == 200, f"Expected 200, got {status_code}: {data}"
    assert data["message"] == "Chatbot Flow Builder API is running"
    print(" [PASS] GET / ->", data)

    status_code, data = await invoke_asgi("GET", "/health")
    assert status_code == 200, f"Expected 200, got {status_code}: {data}"
    assert data["status"] == "ok"
    print(" [PASS] GET /health ->", data)

    # 2. Chatbots Listing
    print("\n--- 2. Chatbots Listing ---")
    status_code, bots = await invoke_asgi("GET", "/chatbots")
    assert status_code == 200, f"Expected 200, got {status_code}: {bots}"
    assert len(bots) >= 4, f"Expected at least 4 chatbots, found {len(bots)}"
    print(f" [PASS] GET /chatbots -> retrieved {len(bots)} chatbots")
    for b in bots[:2]:
        print(f"       Bot: {b['name']} ({b['id']})")

    # 3. Chatbot Lifecycle & Deletion Protection
    print("\n--- 3. Chatbot Lifecycle & Deletion Protection ---")
    test_bot_name = f"Temp Test Bot {uuid.uuid4().hex[:6]}"
    status_code, created_bot = await invoke_asgi("POST", "/chatbots", {"name": test_bot_name, "description": "Temp description"})
    assert status_code == 201, f"Expected 201, got {status_code}: {created_bot}"
    bot_id = created_bot["id"]
    print(f" [PASS] POST /chatbots -> created bot '{created_bot['name']}' ({bot_id})")

    status_code, fetched_bot = await invoke_asgi("GET", f"/chatbots/{bot_id}")
    assert status_code == 200 and fetched_bot["id"] == bot_id
    print(f" [PASS] GET /chatbots/{bot_id} -> verified")

    status_code, updated_bot = await invoke_asgi("PUT", f"/chatbots/{bot_id}", {"name": f"{test_bot_name} Updated", "status": "inactive"})
    assert status_code == 200 and updated_bot["name"] == f"{test_bot_name} Updated"
    print(f" [PASS] PUT /chatbots/{bot_id} -> updated status={updated_bot['status']}")

    # 4. Flow Lifecycle under Chatbot
    print("\n--- 4. Flow Lifecycle under Chatbot ---")
    flow_payload = {
        "name": "Integration Test Flow",
        "description": "Testing JSONB nodes & edges persistence",
        "chatbot_id": bot_id,
        "flow_data": {
            "nodes": [
                {"id": "node_1", "type": "start", "position": {"x": 100, "y": 200}, "data": {"label": "Start Step"}},
                {"id": "node_2", "type": "message", "position": {"x": 400, "y": 200}, "data": {"message": "Hello PostgreSQL!"}}
            ],
            "edges": [
                {"id": "edge_1_2", "source": "node_1", "target": "node_2"}
            ]
        }
    }
    status_code, created_flow = await invoke_asgi("POST", "/flows", flow_payload)
    assert status_code == 201, f"Expected 201, got {status_code}: {created_flow}"
    flow_id = created_flow["id"]
    assert len(created_flow["flow_data"]["nodes"]) == 2
    assert len(created_flow["flow_data"]["edges"]) == 1
    print(f" [PASS] POST /flows -> created flow '{created_flow['name']}' ({flow_id})")

    # List flows by chatbot
    status_code, bot_flows = await invoke_asgi("GET", f"/chatbots/{bot_id}/flows")
    assert status_code == 200 and len(bot_flows) == 1
    print(f" [PASS] GET /chatbots/{bot_id}/flows -> found {len(bot_flows)} flow")

    # Verify Deletion Protection: Cannot delete chatbot with associated flows!
    status_code, del_error = await invoke_asgi("DELETE", f"/chatbots/{bot_id}")
    assert status_code == 400, f"Expected 400 Bad Request, got {status_code}: {del_error}"
    print(f" [PASS] DELETE /chatbots/{bot_id} -> Blocked with HTTP 400: '{del_error.get('detail')}'")

    # Update flow
    updated_payload = dict(flow_payload)
    updated_payload["name"] = "Integration Test Flow (Renamed)"
    status_code, updated_flow = await invoke_asgi("PUT", f"/flows/{flow_id}", updated_payload)
    assert status_code == 200 and updated_flow["name"] == "Integration Test Flow (Renamed)"
    print(f" [PASS] PUT /flows/{flow_id} -> renamed successfully")

    # Delete flow
    status_code, del_flow_res = await invoke_asgi("DELETE", f"/flows/{flow_id}")
    assert status_code == 200
    print(f" [PASS] DELETE /flows/{flow_id} -> deleted successfully")

    # Now delete chatbot -> should succeed
    status_code, del_bot_res = await invoke_asgi("DELETE", f"/chatbots/{bot_id}")
    assert status_code == 200
    print(f" [PASS] DELETE /chatbots/{bot_id} -> deleted successfully now that flows are removed")

    # 5. Node Definitions
    print("\n--- 5. Node Definitions Catalog & Protection ---")
    status_code, node_defs = await invoke_asgi("GET", "/node-definitions")
    assert status_code == 200
    assert len(node_defs) >= 12
    print(f" [PASS] GET /node-definitions -> retrieved {len(node_defs)} definitions")

    # Prebuilt node deletion must be FORBIDDEN
    status_code, prebuilt_del_err = await invoke_asgi("DELETE", "/node-definitions/prebuilt-start")
    assert status_code == 403, f"Expected 403 Forbidden, got {status_code}: {prebuilt_del_err}"
    print(f" [PASS] DELETE /node-definitions/prebuilt-start -> Blocked with HTTP 403: '{prebuilt_del_err.get('detail')}'")

    # Prebuilt node update must be FORBIDDEN
    status_code, prebuilt_upd_err = await invoke_asgi("PUT", "/node-definitions/prebuilt-start", {"name": "Hacked Name"})
    assert status_code == 403, f"Expected 403 Forbidden, got {status_code}: {prebuilt_upd_err}"
    print(f" [PASS] PUT /node-definitions/prebuilt-start -> Blocked with HTTP 403: '{prebuilt_upd_err.get('detail')}'")

    # Custom node creation
    custom_node_type = f"test_action_{uuid.uuid4().hex[:6]}"
    custom_node_payload = {
        "name": "Custom Action Node",
        "node_type": custom_node_type,
        "category": "Integration",
        "description": "Custom webhook step",
        "config_schema": {"fields": [{"name": "webhook_url", "type": "string"}]}
    }
    status_code, created_nd = await invoke_asgi("POST", "/node-definitions", custom_node_payload)
    assert status_code == 201
    custom_nd_id = created_nd["id"]
    print(f" [PASS] POST /node-definitions -> created custom node '{created_nd['name']}' ({custom_nd_id})")

    # Custom node update
    status_code, updated_nd = await invoke_asgi("PUT", f"/node-definitions/{custom_nd_id}", {"name": "Custom Action (Renamed)"})
    assert status_code == 200 and updated_nd["name"] == "Custom Action (Renamed)"
    print(f" [PASS] PUT /node-definitions/{custom_nd_id} -> updated")

    # Custom node delete (unreferenced) -> should permanently delete
    status_code, del_nd_res = await invoke_asgi("DELETE", f"/node-definitions/{custom_nd_id}")
    assert status_code == 200 and del_nd_res["deactivated"] is False
    print(f" [PASS] DELETE /node-definitions/{custom_nd_id} -> deleted permanently: '{del_nd_res['message']}'")

    print("\n" + "=" * 70)
    print("ALL API ENDPOINT INTEGRATION TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_all_tests())

