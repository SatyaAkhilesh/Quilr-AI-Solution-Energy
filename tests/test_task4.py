import asyncio

import pytest

from task4_model_router import db


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