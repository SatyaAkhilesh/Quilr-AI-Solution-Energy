import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from task4_model_router import db
from task4_model_router.router import app


client = TestClient(app)


@pytest.mark.asyncio
async def test_allows_usage_under_limit(tmp_path, monkeypatch):
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)

    await db.init_db()

    allowed, usage = await db.check_and_record_usage(
        "tenant-a",
        10_000,
    )

    assert allowed is True
    assert usage == 10_000


@pytest.mark.asyncio
async def test_blocks_usage_over_limit(tmp_path, monkeypatch):
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)

    await db.init_db()

    allowed, usage = await db.check_and_record_usage(
        "tenant-limit",
        49_000,
    )

    assert allowed is True
    assert usage == 49_000

    allowed, usage = await db.check_and_record_usage(
        "tenant-limit",
        2_000,
    )

    assert allowed is False
    assert usage == 49_000


@pytest.mark.asyncio
async def test_tenants_have_separate_limits(tmp_path, monkeypatch):
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)

    await db.init_db()

    allowed_a, _ = await db.check_and_record_usage(
        "tenant-a",
        49_000,
    )

    allowed_b, _ = await db.check_and_record_usage(
        "tenant-b",
        49_000,
    )

    assert allowed_a is True
    assert allowed_b is True


@pytest.mark.asyncio
async def test_recent_usage_is_returned(tmp_path, monkeypatch):
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)

    await db.init_db()

    await db.check_and_record_usage(
        "tenant-a",
        5_000,
    )

    usage = await db.get_recent_usage("tenant-a")

    assert usage == 5_000


@pytest.mark.asyncio
async def test_concurrent_requests_respect_limit(tmp_path, monkeypatch):
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)

    await db.init_db()

    await db.check_and_record_usage(
        "tenant-a",
        45_000,
    )

    results = await asyncio.gather(
        db.check_and_record_usage("tenant-a", 4_000),
        db.check_and_record_usage("tenant-a", 4_000),
    )

    allowed_count = sum(
        1 for allowed, _ in results if allowed
    )

    assert allowed_count == 1


def test_primary_success(monkeypatch):
    async def fake_check(*args, **kwargs):
        return True, 100

    class Response:
        status_code = 200
        is_success = True

        def json(self):
            return {
                "provider": "primary",
                "text": "ok",
            }

    async def fake_provider(*args, **kwargs):
        return Response()

    monkeypatch.setattr(
        "task4_model_router.router.check_and_record_usage",
        fake_check,
    )

    monkeypatch.setattr(
        "task4_model_router.router.call_provider",
        fake_provider,
    )

    response = client.post(
        "/complete",
        headers={"X-API-Key": "tenant-test"},
        json={
            "prompt": "hello",
            "max_tokens": 100,
        },
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "primary"


def test_primary_429_uses_backup(monkeypatch):
    async def fake_check(*args, **kwargs):
        return True, 100

    calls = 0

    class PrimaryResponse:
        status_code = 429
        is_success = False

    class BackupResponse:
        status_code = 200
        is_success = True

        def json(self):
            return {
                "provider": "backup",
                "text": "fallback",
            }

    async def fake_provider(*args, **kwargs):
        nonlocal calls
        calls += 1

        if calls == 1:
            return PrimaryResponse()

        return BackupResponse()

    monkeypatch.setattr(
        "task4_model_router.router.check_and_record_usage",
        fake_check,
    )

    monkeypatch.setattr(
        "task4_model_router.router.call_provider",
        fake_provider,
    )

    response = client.post(
        "/complete",
        headers={"X-API-Key": "tenant-test"},
        json={
            "prompt": "hello",
            "max_tokens": 100,
        },
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "backup"


def test_primary_timeout_uses_backup(monkeypatch):
    async def fake_check(*args, **kwargs):
        return True, 100

    calls = 0

    class BackupResponse:
        status_code = 200
        is_success = True

        def json(self):
            return {
                "provider": "backup",
                "text": "timeout fallback",
            }

    async def fake_provider(*args, **kwargs):
        nonlocal calls
        calls += 1

        if calls == 1:
            raise httpx.ReadTimeout("primary timed out")

        return BackupResponse()

    monkeypatch.setattr(
        "task4_model_router.router.check_and_record_usage",
        fake_check,
    )

    monkeypatch.setattr(
        "task4_model_router.router.call_provider",
        fake_provider,
    )

    response = client.post(
        "/complete",
        headers={"X-API-Key": "tenant-test"},
        json={
            "prompt": "hello",
            "max_tokens": 100,
        },
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "backup"


def test_provider_failure_returns_safe_error(monkeypatch):
    async def fake_check(*args, **kwargs):
        return True, 100

    async def fake_provider(*args, **kwargs):
        raise httpx.ConnectError(
            "internal provider connection details"
        )

    monkeypatch.setattr(
        "task4_model_router.router.check_and_record_usage",
        fake_check,
    )

    monkeypatch.setattr(
        "task4_model_router.router.call_provider",
        fake_provider,
    )

    response = client.post(
        "/complete",
        headers={"X-API-Key": "tenant-test"},
        json={
            "prompt": "hello",
            "max_tokens": 100,
        },
    )

    body = response.json()

    assert response.status_code == 502
    assert body["error"]["code"] == "UPSTREAM_UNAVAILABLE"
    assert "request_id" in body["error"]
    assert "internal provider connection details" not in str(body)