import uuid

import httpx
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

from task4_model_router.db import (
    check_and_record_usage,
    init_db,
)


app = FastAPI(title="LLM Model Router")

PRIMARY_URL = "http://127.0.0.1:8101/generate"
BACKUP_URL = "http://127.0.0.1:8102/generate"


@app.on_event("startup")
async def startup():
    await init_db()


def gateway_error(
    code: str,
    message: str,
    status_code: int,
    request_id: str,
):
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
            }
        },
    )


def estimate_tokens(text: str) -> int:
    # Lightweight estimate for this assessment.
    # A production gateway would use the model's tokenizer.
    return max(1, len(text) // 4)


async def call_provider(
    url: str,
    payload: dict,
    timeout_seconds: float,
):
    async with httpx.AsyncClient() as client:
        return await client.post(
            url,
            json=payload,
            timeout=timeout_seconds,
        )


@app.post("/complete")
async def complete(
    request: Request,
    x_api_key: str | None = Header(default=None),
):
    request_id = str(uuid.uuid4())

    if not x_api_key:
        return gateway_error(
            code="MISSING_API_KEY",
            message="Tenant API key is required",
            status_code=401,
            request_id=request_id,
        )

    try:
        body = await request.json()
    except Exception:
        return gateway_error(
            code="INVALID_REQUEST",
            message="Request body must be valid JSON",
            status_code=400,
            request_id=request_id,
        )

    prompt = body.get("prompt", "")
    max_tokens = body.get("max_tokens", 0)

    if not isinstance(prompt, str):
        return gateway_error(
            code="INVALID_REQUEST",
            message="prompt must be a string",
            status_code=400,
            request_id=request_id,
        )

    if not isinstance(max_tokens, int) or max_tokens <= 0:
        return gateway_error(
            code="INVALID_REQUEST",
            message="max_tokens must be a positive integer",
            status_code=400,
            request_id=request_id,
        )

    prompt_tokens = estimate_tokens(prompt)
    estimated_tokens = prompt_tokens + max_tokens

    allowed, current_usage = await check_and_record_usage(
        x_api_key,
        estimated_tokens,
    )

    if not allowed:
        return gateway_error(
            code="RATE_LIMIT_EXCEEDED",
            message="Token limit exceeded for this tenant",
            status_code=429,
            request_id=request_id,
        )

    upstream_payload = {
        "prompt": prompt,
        "max_tokens": max_tokens,
    }

    try:
        primary_response = await call_provider(
            PRIMARY_URL,
            upstream_payload,
            timeout_seconds=3.0,
        )

        if primary_response.status_code == 429:
            try:
                backup_response = await call_provider(
                    BACKUP_URL,
                    upstream_payload,
                    timeout_seconds=3.0,
                )
            except httpx.RequestError:
                return gateway_error(
                    code="UPSTREAM_UNAVAILABLE",
                    message="Model service is temporarily unavailable",
                    status_code=502,
                    request_id=request_id,
                )

            if backup_response.is_success:
                return backup_response.json()

            return gateway_error(
                code="UPSTREAM_UNAVAILABLE",
                message="Model service is temporarily unavailable",
                status_code=502,
                request_id=request_id,
            )

        if primary_response.is_success:
            return primary_response.json()

        return gateway_error(
            code="UPSTREAM_ERROR",
            message="Primary model returned an error",
            status_code=502,
            request_id=request_id,
        )

    except httpx.TimeoutException:
        try:
            backup_response = await call_provider(
                BACKUP_URL,
                upstream_payload,
                timeout_seconds=3.0,
            )

            if backup_response.is_success:
                return backup_response.json()

        except httpx.RequestError:
            pass

        return gateway_error(
            code="UPSTREAM_UNAVAILABLE",
            message="Model service is temporarily unavailable",
            status_code=502,
            request_id=request_id,
        )

    except httpx.RequestError:
        return gateway_error(
            code="UPSTREAM_UNAVAILABLE",
            message="Model service is temporarily unavailable",
            status_code=502,
            request_id=request_id,
        )