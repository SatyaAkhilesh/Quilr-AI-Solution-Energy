from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


app = FastAPI(title="Mock MCP Server")


TOOLS = [
    {
        "name": "get_customer_record",
        "description": "Get a customer record",
    },
    {
        "name": "admin_reset_key",
        "description": "Reset an internal admin key",
    },
]


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    payload = await request.json()

    request_id = payload.get("id")
    method = payload.get("method")

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": TOOLS,
            },
        }

    if method == "tools/call":
        params = payload.get("params", {})
        tool_name = params.get("name")

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": f"Executed {tool_name}",
                    }
                ]
            },
        }

    return JSONResponse(
        status_code=200,
        content={
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": "Method not found",
            },
        },
    )