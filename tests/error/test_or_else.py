"""Tests for effect.or_else."""

import pytest

from pyfect import effect, pipe


def test_or_else_success_passes_through() -> None:
    result = effect.run_sync(pipe(effect.succeed(42), effect.or_else(effect.succeed(0))))
    assert result == 42  # noqa: PLR2004


def test_or_else_failure_runs_fallback() -> None:
    result = effect.run_sync(
        pipe(effect.fail("something went wrong"), effect.or_else(effect.succeed("default")))
    )
    assert result == "default"


def test_or_else_fallback_can_fail() -> None:
    """The fallback effect itself may fail, producing E2 as the new error type."""
    eff = pipe(effect.fail("original"), effect.or_else(effect.fail("fallback error")))
    result = effect.run_sync_exit(eff)
    assert isinstance(result, effect.Failure)
    assert result.error == "fallback error"


def test_or_else_error_is_discarded() -> None:
    """The original error value is not passed to the fallback."""
    received: list[str] = []

    result = effect.run_sync(
        pipe(effect.fail("ignored"), effect.or_else(effect.succeed("recovered")))
    )
    assert result == "recovered"
    assert received == []


def test_or_else_fallback_not_run_on_success() -> None:
    executed: list[bool] = []

    fallback = effect.sync(lambda: (executed.append(True), 0)[1])

    effect.run_sync(pipe(effect.succeed(42), effect.or_else(fallback)))
    assert executed == []


def test_or_else_type_inference() -> None:
    """Hover over eff — should show Effect[int | str, ValueError, Never]."""

    def failing_effect() -> effect.Effect[int, str]:
        return effect.fail("oops")

    def fallback_effect() -> effect.Effect[str, ValueError]:
        return effect.succeed("default")

    eff = pipe(failing_effect(), effect.or_else(fallback_effect()))
    result = effect.run_sync(eff)
    assert result == "default"


@pytest.mark.asyncio
async def test_or_else_async_success_passes_through() -> None:
    result = await effect.run_async(
        pipe(effect.succeed("hello"), effect.or_else(effect.succeed("fallback")))
    )
    assert result == "hello"


@pytest.mark.asyncio
async def test_or_else_async_failure_runs_fallback() -> None:
    result = await effect.run_async(
        pipe(effect.fail("async error"), effect.or_else(effect.succeed("async fallback")))
    )
    assert result == "async fallback"
