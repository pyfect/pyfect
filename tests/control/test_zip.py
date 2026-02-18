"""Tests for the effect.zip combinator."""

import time
from datetime import timedelta

import pytest

from pyfect import effect, pipe

# ── Sequential ────────────────────────────────────────────────────────────────


def test_zip_two_succeeds() -> None:
    """zip of two succeeding effects produces a tuple of their values."""
    result = effect.zip_(effect.succeed(1), effect.succeed("hello"))
    assert effect.run_sync(result) == (1, "hello")


def test_zip_three_succeeds() -> None:
    """zip of three effects produces a 3-tuple."""
    result = effect.zip_(effect.succeed(1), effect.succeed(2), effect.succeed(3))
    assert effect.run_sync(result) == (1, 2, 3)


def test_zip_four_succeeds() -> None:
    """zip of four effects produces a 4-tuple."""
    result = effect.zip_(
        effect.succeed("a"),
        effect.succeed("b"),
        effect.succeed("c"),
        effect.succeed("d"),
    )
    assert effect.run_sync(result) == ("a", "b", "c", "d")


def test_zip_five_succeeds() -> None:
    """zip of five effects produces a 5-tuple."""
    result = effect.zip_(
        effect.succeed(1),
        effect.succeed(2),
        effect.succeed(3),
        effect.succeed(4),
        effect.succeed(5),
    )
    assert effect.run_sync(result) == (1, 2, 3, 4, 5)


def test_zip_runs_sequentially_by_default() -> None:
    """Effects run left-to-right in the default sequential mode."""
    order: list[int] = []
    result = effect.zip_(
        effect.sync(lambda: order.append(1) or 1),  # type: ignore[func-returns-value]
        effect.sync(lambda: order.append(2) or 2),  # type: ignore[func-returns-value]
        effect.sync(lambda: order.append(3) or 3),  # type: ignore[func-returns-value]
    )
    effect.run_sync(result)
    assert order == [1, 2, 3]


def test_zip_first_failure_short_circuits() -> None:
    """When the first effect fails, subsequent effects do not run."""
    executed: list[int] = []
    result = effect.zip_(
        effect.fail(ValueError("first")),
        effect.sync(lambda: executed.append(2) or 2),  # type: ignore[func-returns-value]
    )
    with pytest.raises(ValueError, match="first"):
        effect.run_sync(result)
    assert executed == []


def test_zip_middle_failure_short_circuits() -> None:
    """When a middle effect fails, subsequent effects do not run."""
    executed: list[int] = []
    result = effect.zip_(
        effect.succeed(1),
        effect.fail(RuntimeError("middle")),
        effect.sync(lambda: executed.append(3) or 3),  # type: ignore[func-returns-value]
    )
    with pytest.raises(RuntimeError, match="middle"):
        effect.run_sync(result)
    assert executed == []


def test_zip_with_exit_success() -> None:
    """run_sync_exit returns Success(tuple) when all effects succeed."""
    result = effect.zip_(effect.succeed(10), effect.succeed(20))
    match effect.run_sync_exit(result):
        case effect.Success(value):
            assert value == (10, 20)
        case effect.Failure(e):
            msg = f"Unexpected failure: {e}"
            raise AssertionError(msg)


def test_zip_with_exit_failure() -> None:
    """run_sync_exit captures failure from the first failing effect."""
    result = effect.zip_(effect.succeed(1), effect.fail("bad"))
    match effect.run_sync_exit(result):
        case effect.Failure(e):
            assert e == "bad"
        case effect.Success(_):
            msg = "Expected failure"
            raise AssertionError(msg)


def test_zip_with_pipe_combinators() -> None:
    """zip composes naturally with pipe combinators on individual effects."""
    result = effect.zip_(
        pipe(effect.succeed(10), effect.map_(lambda x: x * 2)),
        pipe(effect.succeed("hi"), effect.map_(str.upper)),
    )
    assert effect.run_sync(result) == (20, "HI")


# ── Concurrent ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_zip_concurrent_produces_correct_values() -> None:
    """Concurrent zip returns the same values as sequential."""
    result = effect.zip_(
        effect.succeed(1),
        effect.succeed("hello"),
        concurrent=True,
    )
    assert await effect.run_async(result) == (1, "hello")


@pytest.mark.asyncio
async def test_zip_concurrent_runs_in_parallel() -> None:
    """Concurrent zip finishes faster than sequential when effects have delays."""
    delay = timedelta(milliseconds=100)
    sequential = effect.zip_(
        pipe(effect.succeed(1), effect.delay(delay)),
        pipe(effect.succeed(2), effect.delay(delay)),
    )
    concurrent = effect.zip_(
        pipe(effect.succeed(1), effect.delay(delay)),
        pipe(effect.succeed(2), effect.delay(delay)),
        concurrent=True,
    )

    start = time.monotonic()
    await effect.run_async(sequential)
    sequential_time = time.monotonic() - start

    start = time.monotonic()
    await effect.run_async(concurrent)
    concurrent_time = time.monotonic() - start

    # Concurrent should be meaningfully faster than sequential
    assert concurrent_time < sequential_time * 0.75


@pytest.mark.asyncio
async def test_zip_concurrent_failure_propagates() -> None:
    """A failing effect in concurrent zip propagates the error."""
    result = effect.zip_(
        effect.fail(ValueError("bad")),
        effect.succeed(2),
        concurrent=True,
    )
    with pytest.raises(ValueError, match="bad"):
        await effect.run_async(result)


@pytest.mark.asyncio
async def test_zip_concurrent_exit_success() -> None:
    """run_async_exit returns Success(tuple) for a successful concurrent zip."""
    result = effect.zip_(effect.succeed(1), effect.succeed(2), concurrent=True)
    match await effect.run_async_exit(result):
        case effect.Success(value):
            assert value == (1, 2)
        case effect.Failure(e):
            msg = f"Unexpected failure: {e}"
            raise AssertionError(msg)


@pytest.mark.asyncio
async def test_zip_concurrent_exit_failure() -> None:
    """run_async_exit captures failure from a concurrent zip."""
    result = effect.zip_(
        effect.fail(RuntimeError("concurrent error")),
        effect.succeed(2),
        concurrent=True,
    )
    match await effect.run_async_exit(result):
        case effect.Failure(e):
            assert isinstance(e, RuntimeError)
        case effect.Success(_):
            msg = "Expected failure"
            raise AssertionError(msg)


def test_zip_concurrent_sync_fallback_runs_sequentially() -> None:
    """concurrent=True in the sync runtime runs sequentially without error."""
    order: list[int] = []
    result = effect.zip_(
        effect.sync(lambda: order.append(1) or 1),  # type: ignore[func-returns-value]
        effect.sync(lambda: order.append(2) or 2),  # type: ignore[func-returns-value]
        concurrent=True,
    )
    values = effect.run_sync(result)
    assert values == (1, 2)
    assert order == [1, 2]


def test_zip_no_args_raises() -> None:
    """Calling zip with no effects raises ValueError."""
    with pytest.raises(ValueError, match="zip requires at least one effect"):
        effect.zip_()  # type: ignore[call-overload]


def test_zip_sync_exit_success() -> None:
    """run_sync_exit returns Success(tuple) for a successful concurrent=True zip."""
    result = effect.zip_(effect.succeed(1), effect.succeed(2), concurrent=True)
    match effect.run_sync_exit(result):
        case effect.Success(value):
            assert value == (1, 2)
        case effect.Failure(e):
            msg = f"Unexpected failure: {e}"
            raise AssertionError(msg)


def test_zip_sync_exit_failure() -> None:
    """run_sync_exit captures failure from ZipPar running sequentially."""
    result = effect.zip_(effect.succeed(1), effect.fail("bad"), concurrent=True)
    match effect.run_sync_exit(result):
        case effect.Failure(e):
            assert e == "bad"
        case effect.Success(_):
            msg = "Expected failure"
            raise AssertionError(msg)
