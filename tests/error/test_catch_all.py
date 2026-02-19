"""Tests for effect.catch_all."""

import pytest

from pyfect import effect, pipe


def test_catch_all_success_passes_through() -> None:
    result = effect.run_sync(
        pipe(effect.succeed(42), effect.catch_all(lambda _: effect.succeed(0)))
    )
    assert result == 42  # noqa: PLR2004


def test_catch_all_failure_runs_fallback() -> None:
    result = effect.run_sync(
        pipe(effect.fail("oops"), effect.catch_all(lambda e: effect.succeed(f"Recovered: {e}")))
    )
    assert result == "Recovered: oops"


def test_catch_all_error_type_erased() -> None:
    """After catch_all with an infallible fallback, the effect never fails."""
    eff = pipe(effect.fail("gone"), effect.catch_all(lambda _: effect.succeed("default")))
    result = effect.run_sync_exit(eff)
    assert isinstance(result, effect.Success)
    assert result.value == "default"


def test_catch_all_fallback_can_fail() -> None:
    """The fallback effect itself may fail, producing a new error type."""
    eff = pipe(effect.fail("original"), effect.catch_all(lambda e: effect.fail(f"new: {e}")))
    result = effect.run_sync_exit(eff)
    assert isinstance(result, effect.Failure)
    assert result.error == "new: original"


def test_catch_all_handler_receives_error_value() -> None:
    class MyError:
        def __init__(self, code: int) -> None:
            self.code = code

    received: list[MyError] = []

    def handle(e: MyError) -> effect.Effect[str]:
        received.append(e)
        return effect.succeed("handled")

    effect.run_sync(pipe(effect.fail(MyError(404)), effect.catch_all(handle)))
    assert len(received) == 1
    assert received[0].code == 404  # noqa: PLR2004


def test_catch_all_not_called_on_success() -> None:
    called = False

    def handle(_: str) -> effect.Effect[str]:
        nonlocal called
        called = True
        return effect.succeed("fallback")

    effect.run_sync(pipe(effect.succeed("ok"), effect.catch_all(handle)))
    assert not called


@pytest.mark.asyncio
async def test_catch_all_async_success_passes_through() -> None:
    result = await effect.run_async(
        pipe(effect.succeed("hello"), effect.catch_all(lambda _: effect.succeed("fallback")))
    )
    assert result == "hello"


@pytest.mark.asyncio
async def test_catch_all_async_failure_runs_fallback() -> None:
    result = await effect.run_async(
        pipe(effect.fail("async error"), effect.catch_all(lambda e: effect.succeed(f"got: {e}")))
    )
    assert result == "got: async error"
