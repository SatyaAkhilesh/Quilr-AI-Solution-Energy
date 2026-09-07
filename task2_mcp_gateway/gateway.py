import httpx

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

from task2_mcp_gateway.auth import get_role


app = FastAPI(title="MCP Security Gateway")

DOWNSTREAM_URL = "http://127.0.0.1:8001/mcp"


def jsonrpc_error(request_id, code: int, message: str):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


@app.post("/mcp")
async def gateway(
    request: Request,
    authorization: str | None = Header(default=None),
):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            status_code=200,
            content=jsonrpc_error(
                None,
                -32700,
                "Parse error",
            ),
        )

    request_id = payload.get("id")
    method = payload.get("method")

    if payload.get("jsonrpc") != "2.0":
        return JSONResponse(
            status_code=200,
            content=jsonrpc_error(
                request_id,
                -32600,
                "Invalid Request",
            ),
        )

    role = get_role(authorization)

    if method == "tools/call":
        params = payload.get("params")

        if not isinstance(params, dict):
            return JSONResponse(
                status_code=200,
                content=jsonrpc_error(
                    request_id,
                    -32602,
                    "Invalid params",
                ),
            )

        tool_name = params.get("name")

        if not isinstance(tool_name, str):
            return JSONResponse(
                status_code=200,
                content=jsonrpc_error(
                    request_id,
                    -32602,
                    "Invalid params",
                ),
            )

        if tool_name.startswith("admin_") and role != "admin":
            return JSONResponse(
                status_code=200,
                content=jsonrpc_error(
                    request_id,
                    -32001,
                    "Unauthorized Tool Call",
                ),
            )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                DOWNSTREAM_URL,
                json=payload,
            )

        return JSONResponse(
            status_code=response.status_code,
            content=response.json(),
        )

    except httpx.RequestError:
        return JSONResponse(
            status_code=502,
            content=jsonrpc_error(
                request_id,
                -32000,
                "Downstream MCP server unavailable",
            ),
        )