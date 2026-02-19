"""Tests for service() and provide()."""

import asyncio

import pytest

from pyfect import context, effect, pipe


class Database:
    def __init__(self, url: str) -> None:
        self.url = url


class Logger:
    def __init__(self, name: str) -> None:
        self.name = name


class Cache:
    def __init__(self, size: int) -> None:
        self.size = size


# ============================================================================
# service() - single tag
# ============================================================================


def test_service_single_resolved_by_provide() -> None:
    """Test that a single-tag service resolves to the provided instance."""
    db = Database("postgres://localhost/test")

    eff = pipe(
        effect.service(Database),
        effect.provide(context.make((Database, db))),
    )

    result = effect.run_sync(eff)
    assert result is db


def test_service_missing_raises() -> None:
    """Test that accessing a service without providing it raises."""
    eff = pipe(
        effect.service(Database),
        effect.provide(context.empty()),
    )

    with pytest.raises(context.MissingServiceError):
        effect.run_sync(eff)


def test_service_used_in_flat_map() -> None:
    """Test that a service can be used inside flat_map."""
    db = Database("postgres://localhost/test")

    eff = pipe(
        effect.service(Database),
        effect.flat_map(lambda d: effect.succeed(d.url)),
        effect.provide(context.make((Database, db))),
    )

    result = effect.run_sync(eff)
    assert result == "postgres://localhost/test"


# ============================================================================
# service() - multiple tags
# ============================================================================


def test_service_two_tags_returns_tuple() -> None:
    """Test that two-tag service resolves to a tuple."""
    db = Database("postgres://localhost/test")
    log = Logger("app")

    eff = pipe(
        effect.service(Database, Logger),
        effect.provide(context.make((Database, db), (Logger, log))),
    )

    result = effect.run_sync(eff)
    assert result == (db, log)


def test_service_three_tags_returns_tuple() -> None:
    """Test that three-tag service resolves to a tuple of three."""
    db = Database("postgres://localhost/test")
    log = Logger("app")
    cache = Cache(256)

    eff = pipe(
        effect.service(Database, Logger, Cache),
        effect.provide(context.make((Database, db), (Logger, log), (Cache, cache))),
    )

    result = effect.run_sync(eff)
    assert result == (db, log, cache)


# ============================================================================
# provide()  # noqa: ERA001
# ============================================================================


def test_provide_makes_effect_runnable() -> None:
    """Test that provide satisfies requirements so the effect can run."""
    db = Database("postgres://localhost/test")

    program = effect.service(Database)
    runnable = effect.provide(context.make((Database, db)))(program)

    result = effect.run_sync(runnable)
    assert result is db


def test_provide_with_pipe() -> None:
    """Test that provide works naturally with pipe."""
    db = Database("postgres://localhost/test")

    result = effect.run_sync(
        pipe(
            effect.service(Database),
            effect.provide(context.make((Database, db))),
        )
    )

    assert result is db


def test_provide_inner_context_takes_precedence() -> None:
    """Test that inner provide overrides outer context for the inner effect."""
    db_inner = Database("inner")
    db_outer = Database("outer")

    inner = pipe(
        effect.service(Database),
        effect.provide(context.make((Database, db_inner))),
    )

    # Wrapping an already-provided effect with another provide
    eff = effect.flat_map(lambda _: inner)(
        pipe(
            effect.service(Database),
            effect.provide(context.make((Database, db_outer))),
        )
    )

    result = effect.run_sync(eff)
    assert result is db_inner


# ============================================================================
# Async
# ============================================================================


@pytest.mark.asyncio
async def test_service_with_run_async() -> None:
    """Test that service and provide work with run_async."""
    db = Database("postgres://localhost/test")

    eff = pipe(
        effect.service(Database),
        effect.provide(context.make((Database, db))),
    )

    result = await effect.run_async(eff)
    assert result is db


@pytest.mark.asyncio
async def test_service_in_async_chain() -> None:
    """Test that service can be combined with async effects."""
    db = Database("postgres://localhost/test")

    async def fetch_url(d: Database) -> str:
        await asyncio.sleep(0.01)
        return d.url

    eff = pipe(
        effect.service(Database),
        effect.flat_map(lambda d: effect.async_(lambda: fetch_url(d))),
        effect.provide(context.make((Database, db))),
    )

    result = await effect.run_async(eff)
    assert result == "postgres://localhost/test"


@pytest.mark.asyncio
async def test_service_with_run_async_exit() -> None:
    """Test that service works with run_async_exit."""
    db = Database("postgres://localhost/test")

    eff = pipe(
        effect.service(Database),
        effect.provide(context.make((Database, db))),
    )

    result = await effect.run_async_exit(eff)
    match result:
        case effect.Success(value):
            assert value is db
        case effect.Failure(_):
            pytest.fail("Expected Success")


# ============================================================================
# run_sync_exit
# ============================================================================


def test_service_with_run_sync_exit_success() -> None:
    """Test that service and provide work with run_sync_exit."""
    db = Database("postgres://localhost/test")

    eff = pipe(
        effect.service(Database),
        effect.provide(context.make((Database, db))),
    )

    result = effect.run_sync_exit(eff)
    match result:
        case effect.Success(value):
            assert value is db
        case effect.Failure(_):
            pytest.fail("Expected Success")


def test_provide_with_run_sync_exit_missing_service() -> None:
    """Test that a missing service surfaces as Failure in run_sync_exit."""
    eff = pipe(
        effect.service(Database),
        effect.provide(context.empty()),
    )

    with pytest.raises(context.MissingServiceError):
        effect.run_sync_exit(eff)
