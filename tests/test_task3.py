import pytest

from task3_stream_guardrail.gateway import (
    redact_pii,
    redact_stream,
)


def test_redacts_email():
    text = "Contact me at satya@example.com"

    result = redact_pii(text)

    assert "satya@example.com" not in result
    assert "[REDACTED]" in result


def test_redacts_ssn():
    text = "My SSN is 123-45-6789"

    result = redact_pii(text)

    assert "123-45-6789" not in result
    assert "[REDACTED]" in result


def test_redacts_credit_card():
    text = "Card number is 4111 1111 1111 1111"

    result = redact_pii(text)

    assert "4111 1111 1111 1111" not in result
    assert "[REDACTED]" in result


def test_normal_text_is_unchanged():
    text = "This response does not contain sensitive data."

    assert redact_pii(text) == text


@pytest.mark.asyncio
async def test_email_split_across_chunks():
    async def upstream():
        yield "Please email satya@"
        yield "example.com for help."

    output = ""

    async for chunk in redact_stream(upstream()):
        output += chunk

    assert "satya@example.com" not in output
    assert "[REDACTED]" in output


@pytest.mark.asyncio
async def test_ssn_split_across_chunks():
    async def upstream():
        yield "SSN: 123-45-"
        yield "6789"

    output = ""

    async for chunk in redact_stream(upstream()):
        output += chunk

    assert "123-45-6789" not in output
    assert "[REDACTED]" in output


@pytest.mark.asyncio
async def test_card_split_across_chunks():
    async def upstream():
        yield "Card: 4111 1111 "
        yield "1111 1111"

    output = ""

    async for chunk in redact_stream(upstream()):
        output += chunk

    assert "4111 1111 1111 1111" not in output
    assert "[REDACTED]" in output