"""Tests for the effect.delay combinator."""

import time
from datetime import timedelta

import pytest

from pyfect import effect, pipe


def test_delay_returns_correct_value() -> None:
    """delay preserves the value of the inner effect."""
    result = pipe(
        effect.succeed(42),
        effect.delay(timedelta(milliseconds=1)),
    )
    assert effect.run_sync(result) == 42  # noqa: PLR2004


def test_delay_waits_at_least_duration() -> None:
    """run_sync waits at least the requested duration before returning."""
    duration = timedelta(milliseconds=50)
    eff = pipe(
        effect.succeed("done"),
        effect.delay(duration),
    )
    start = time.monotonic()
    effect.run_sync(eff)
    elapsed = time.monotonic() - start
    assert elapsed >= duration.total_seconds()


def test_delay_preserves_error() -> None:
    """delay propagates failures from the inner effect."""
    result = pipe(
        effect.fail(ValueError("oops")),
        effect.delay(timedelta(milliseconds=1)),
    )
    with pytest.raises(ValueError, match="oops"):
        effect.run_sync(result)


def test_delay_with_exit_success() -> None:
    """run_sync_exit returns Success after the delay."""
    result = pipe(
        effect.succeed("hello"),
        effect.delay(timedelta(milliseconds=1)),
    )
    match effect.run_sync_exit(result):
        case effect.Success(value):
            assert value == "hello"
        case effect.Failure(e):
            msg = f"Unexpected failure: {e}"
            raise AssertionError(msg)


def test_delay_with_exit_failure() -> None:
    """run_sync_exit captures failure after the delay."""
    result = pipe(
        effect.fail("bad"),
        effect.delay(timedelta(milliseconds=1)),
    )
    match effect.run_sync_exit(result):
        case effect.Failure(e):
            assert e == "bad"
        case effect.Success(_):
            msg = "Expected failure"
            raise AssertionError(msg)


def test_delay_zero_duration() -> None:
    """A zero-duration delay still returns the correct value."""
    result = pipe(
        effect.succeed(99),
        effect.delay(timedelta(0)),
    )
    assert effect.run_sync(result) == 99  # noqa: PLR2004


def test_delay_chained() -> None:
    """Multiple delays chain correctly and the final value is preserved."""
    result = pipe(
        effect.succeed(1),
        effect.delay(timedelta(milliseconds=1)),
        effect.delay(timedelta(milliseconds=1)),
    )
    assert effect.run_sync(result) == 1


@pytest.mark.asyncio
async def test_delay_async_returns_correct_value() -> None:
    """delay works with the async runtime and returns the correct value."""
    result = pipe(
        effect.succeed(7),
        effect.delay(timedelta(milliseconds=1)),
    )
    assert await effect.run_async(result) == 7  # noqa: PLR2004


@pytest.mark.asyncio
async def test_delay_async_waits_at_least_duration() -> None:
    """run_async uses asyncio.sleep and waits at least the requested duration."""
    duration = timedelta(milliseconds=50)
    eff = pipe(
        effect.succeed("done"),
        effect.delay(duration),
    )
    start = time.monotonic()
    await effect.run_async(eff)
    elapsed = time.monotonic() - start
    assert elapsed >= duration.total_seconds()


@pytest.mark.asyncio
async def test_delay_async_preserves_error() -> None:
    """delay propagates failures in the async runtime."""
    result = pipe(
        effect.fail(RuntimeError("async error")),
        effect.delay(timedelta(milliseconds=1)),
    )
    with pytest.raises(RuntimeError, match="async error"):
        await effect.run_async(result)


@pytest.mark.asyncio
async def test_delay_async_exit_success() -> None:
    """run_async_exit returns Success after the delay."""
    result = pipe(
        effect.succeed("hello"),
        effect.delay(timedelta(milliseconds=1)),
    )
    match await effect.run_async_exit(result):
        case effect.Success(value):
            assert value == "hello"
        case effect.Failure(e):
            msg = f"Unexpected failure: {e}"
            raise AssertionError(msg)
