from fastapi.testclient import TestClient

from task2_mcp_gateway.gateway import app


client = TestClient(app)


def test_viewer_can_list_tools(monkeypatch):
    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "tools": [
                        {"name": "get_customer_record"},
                        {"name": "admin_reset_key"},
                    ]
                },
            }

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def post(self, url, json):
            return MockResponse()

    monkeypatch.setattr(
        "task2_mcp_gateway.gateway.httpx.AsyncClient",
        lambda *args, **kwargs: MockClient(),
    )

    response = client.post(
        "/mcp",
        headers={"Authorization": "Bearer viewer-token"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["id"] == 1
    assert "result" in body


def test_viewer_can_call_normal_tool(monkeypatch):
    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": "Executed get_customer_record",
                        }
                    ]
                },
            }

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def post(self, url, json):
            return MockResponse()

    monkeypatch.setattr(
        "task2_mcp_gateway.gateway.httpx.AsyncClient",
        lambda *args, **kwargs: MockClient(),
    )

    response = client.post(
        "/mcp",
        headers={"Authorization": "Bearer viewer-token"},
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "get_customer_record",
                "arguments": {
                    "customer_id": "CUST-12345",
                },
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["id"] == 2
    assert "result" in body


def test_viewer_cannot_call_admin_tool():
    response = client.post(
        "/mcp",
        headers={"Authorization": "Bearer viewer-token"},
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "admin_reset_key",
                "arguments": {},
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["id"] == 3
    assert body["error"]["code"] == -32001
    assert body["error"]["message"] == "Unauthorized Tool Call"


def test_admin_can_call_admin_tool(monkeypatch):
    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "jsonrpc": "2.0",
                "id": 4,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": "Executed admin_reset_key",
                        }
                    ]
                },
            }

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def post(self, url, json):
            return MockResponse()

    monkeypatch.setattr(
        "task2_mcp_gateway.gateway.httpx.AsyncClient",
        lambda *args, **kwargs: MockClient(),
    )

    response = client.post(
        "/mcp",
        headers={"Authorization": "Bearer admin-token"},
        json={
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "admin_reset_key",
                "arguments": {},
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["id"] == 4
    assert "result" in body


def test_missing_token_blocks_admin_tool():
    response = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "admin_reset_key",
                "arguments": {},
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["id"] == 5
    assert body["error"]["code"] == -32001
    assert body["error"]["message"] == "Unauthorized Tool Call"


def test_invalid_jsonrpc_version():
    response = client.post(
        "/mcp",
        json={
            "jsonrpc": "1.0",
            "id": 6,
            "method": "tools/list",
            "params": {},
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["id"] == 6
    assert body["error"]["code"] == -32600
    assert body["error"]["message"] == "Invalid Request"


def test_invalid_tool_params():
    response = client.post(
        "/mcp",
        headers={"Authorization": "Bearer admin-token"},
        json={
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {},
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["id"] == 7
    assert body["error"]["code"] == -32602
    assert body["error"]["message"] == "Invalid params"


def test_blocked_admin_call_is_not_forwarded(monkeypatch):
    called = False

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def post(self, url, json):
            nonlocal called
            called = True
            raise AssertionError("Downstream should not be called")

    monkeypatch.setattr(
        "task2_mcp_gateway.gateway.httpx.AsyncClient",
        lambda *args, **kwargs: MockClient(),
    )

    response = client.post(
        "/mcp",
        headers={"Authorization": "Bearer viewer-token"},
        json={
            "jsonrpc": "2.0",
            "id": 20,
            "method": "tools/call",
            "params": {
                "name": "admin_reset_key",
                "arguments": {},
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["id"] == 20
    assert body["error"]["code"] == -32001
    assert body["error"]["message"] == "Unauthorized Tool Call"
    assert called is False