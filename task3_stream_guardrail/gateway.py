import asyncio
import re
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse


app = FastAPI(title="LLM Streaming Guardrail")


EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

SSN_PATTERN = re.compile(
    r"\b\d{3}-\d{2}-\d{4}\b"
)

CARD_PATTERN = re.compile(
    r"\b(?:\d[ -]*?){13,19}\b"
)


BUFFER_SIZE = 128

def redact_pii(text: str) -> str:
    text = EMAIL_PATTERN.sub("[REDACTED]", text)
    text = SSN_PATTERN.sub("[REDACTED]", text)
    text = CARD_PATTERN.sub("[REDACTED]", text)
    return text


async def fake_llm_stream(prompt: str) -> AsyncIterator[str]:
    chunks = [
        "Here is the response. ",
        "Contact me at satya@",
        "example.com. ",
        "My SSN is 123-45-",
        "6789. ",
        "Card: 4111 1111 ",
        "1111 1111.",
    ]

    for chunk in chunks:
        await asyncio.sleep(0.1)
        yield chunk


    


async def redact_stream(
    upstream: AsyncIterator[str],
) -> AsyncIterator[str]:
    buffer = ""

    async for chunk in upstream:
        buffer += chunk

        if len(buffer) <= BUFFER_SIZE:
            continue

        safe_cutoff = len(buffer) - BUFFER_SIZE
        safe_part = buffer[:safe_cutoff]

        yield redact_pii(safe_part)

        buffer = buffer[safe_cutoff:]

    if buffer:
        yield redact_pii(buffer)


@app.post("/generate")
async def generate(request: Request):
    body = await request.json()
    prompt = body.get("prompt", "")

    upstream = fake_llm_stream(prompt)

    return StreamingResponse(
        redact_stream(upstream),
        media_type="text/plain",
    )