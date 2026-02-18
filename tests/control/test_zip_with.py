"""Tests for the effect.zip_with combinator."""

import time
from datetime import timedelta

import pytest

from pyfect import effect, pipe

# ── Sequential ────────────────────────────────────────────────────────────────


def test_zip_with_applies_function() -> None:
    """zip_with applies f to the two success values."""
    result = effect.zip_with(
        effect.succeed(1),
        effect.succeed("hello"),
        lambda n, s: n + len(s),
    )
    assert effect.run_sync(result) == 6  # noqa: PLR2004


def test_zip_with_int_addition() -> None:
    """zip_with can combine two integers."""
    result = effect.zip_with(
        effect.succeed(10),
        effect.succeed(32),
        lambda a, b: a + b,
    )
    assert effect.run_sync(result) == 42  # noqa: PLR2004


def test_zip_with_runs_sequentially_by_default() -> None:
    """Effects run left-to-right in the default sequential mode."""
    order: list[int] = []
    result = effect.zip_with(
        effect.sync(lambda: order.append(1) or 10),  # type: ignore[func-returns-value]
        effect.sync(lambda: order.append(2) or 20),  # type: ignore[func-returns-value]
        lambda a, b: a + b,
    )
    assert effect.run_sync(result) == 30  # noqa: PLR2004
    assert order == [1, 2]


def test_zip_with_first_failure_short_circuits() -> None:
    """When the first effect fails, the second does not run and f is not called."""
    executed: list[int] = []
    result = effect.zip_with(
        effect.fail(ValueError("first")),
        effect.sync(lambda: executed.append(2) or 2),  # type: ignore[func-returns-value]
        lambda a, b: a + b,
    )
    with pytest.raises(ValueError, match="first"):
        effect.run_sync(result)
    assert executed == []


def test_zip_with_second_failure_propagates() -> None:
    """When the second effect fails, that error propagates."""
    result = effect.zip_with(
        effect.succeed(1),
        effect.fail(RuntimeError("second")),
        lambda a, b: a + b,
    )
    with pytest.raises(RuntimeError, match="second"):
        effect.run_sync(result)


def test_zip_with_exit_success() -> None:
    """run_sync_exit returns Success with the combined value."""
    result = effect.zip_with(
        effect.succeed(3),
        effect.succeed(4),
        lambda a, b: a * b,
    )
    match effect.run_sync_exit(result):
        case effect.Success(value):
            assert value == 12  # noqa: PLR2004
        case effect.Failure(e):
            msg = f"Unexpected failure: {e}"
            raise AssertionError(msg)


def test_zip_with_exit_failure() -> None:
    """run_sync_exit captures failure from either effect."""
    result = effect.zip_with(
        effect.succeed(1),
        effect.fail("bad"),
        lambda a, b: a + b,
    )
    match effect.run_sync_exit(result):
        case effect.Failure(e):
            assert e == "bad"
        case effect.Success(_):
            msg = "Expected failure"
            raise AssertionError(msg)


def test_zip_with_pipe_combinators() -> None:
    """zip_with composes naturally with pipe combinators on individual effects."""
    result = effect.zip_with(
        pipe(effect.succeed(10), effect.map_(lambda x: x * 2)),
        pipe(effect.succeed("hi"), effect.map_(str.upper)),
        lambda n, s: f"{s}-{n}",
    )
    assert effect.run_sync(result) == "HI-20"


# ── Concurrent ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_zip_with_concurrent_applies_function() -> None:
    """Concurrent zip_with still applies f to both results."""
    result = effect.zip_with(
        effect.succeed(1),
        effect.succeed("hello"),
        lambda n, s: n + len(s),
        concurrent=True,
    )
    assert await effect.run_async(result) == 6  # noqa: PLR2004


@pytest.mark.asyncio
async def test_zip_with_concurrent_runs_in_parallel() -> None:
    """Concurrent zip_with finishes faster than sequential when effects have delays."""
    delay = timedelta(milliseconds=100)

    sequential = effect.zip_with(
        pipe(effect.succeed(1), effect.delay(delay)),
        pipe(effect.succeed(2), effect.delay(delay)),
        lambda a, b: a + b,
    )
    concurrent = effect.zip_with(
        pipe(effect.succeed(1), effect.delay(delay)),
        pipe(effect.succeed(2), effect.delay(delay)),
        lambda a, b: a + b,
        concurrent=True,
    )

    start = time.monotonic()
    await effect.run_async(sequential)
    sequential_time = time.monotonic() - start

    start = time.monotonic()
    await effect.run_async(concurrent)
    concurrent_time = time.monotonic() - start

    assert concurrent_time < sequential_time * 0.75


@pytest.mark.asyncio
async def test_zip_with_concurrent_failure_propagates() -> None:
    """A failing effect in concurrent zip_with propagates the error."""
    result = effect.zip_with(
        effect.fail(ValueError("bad")),
        effect.succeed(2),
        lambda a, b: a + b,
        concurrent=True,
    )
    with pytest.raises(ValueError, match="bad"):
        await effect.run_async(result)


@pytest.mark.asyncio
async def test_zip_with_concurrent_exit_success() -> None:
    """run_async_exit returns Success with the combined value for concurrent zip_with."""
    result = effect.zip_with(
        effect.succeed(6),
        effect.succeed(7),
        lambda a, b: a * b,
        concurrent=True,
    )
    match await effect.run_async_exit(result):
        case effect.Success(value):
            assert value == 42  # noqa: PLR2004
        case effect.Failure(e):
            msg = f"Unexpected failure: {e}"
            raise AssertionError(msg)
