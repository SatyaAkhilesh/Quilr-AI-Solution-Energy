import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


app = FastAPI(title="Primary Model Mock")


@app.post("/generate")
async def generate(request: Request):
    body = await request.json()

    prompt = body.get("prompt", "")

    if prompt == "rate-limit":
        return JSONResponse(
            status_code=429,
            content={
                "error": "primary rate limited",
            },
        )

    if prompt == "timeout":
        await asyncio.sleep(4)

    return {
        "provider": "primary",
        "text": f"Primary response for: {prompt}",
    }