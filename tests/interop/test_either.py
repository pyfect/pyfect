"""Tests for effect.either."""

import pytest

from pyfect import effect, either, pipe


def test_either_success_returns_right() -> None:
    eff = effect.either(effect.succeed(42))
    result = effect.run_sync(eff)
    assert isinstance(result, either.Right)
    assert result.value == 42  # noqa: PLR2004


def test_either_failure_returns_left() -> None:
    eff = effect.either(effect.fail("oops"))
    result = effect.run_sync(eff)
    assert isinstance(result, either.Left)
    assert result.value == "oops"


def test_either_never_fails_on_error() -> None:
    """The resulting effect succeeds even when the inner effect fails."""
    eff = effect.either(effect.fail("boom"))
    result = effect.run_sync_exit(eff)
    assert isinstance(result, effect.Success)


def test_either_in_pipe_with_match() -> None:
    program = effect.fail("something went wrong")
    recovered = pipe(
        program,
        effect.either,
        effect.map_(
            either.match_(
                on_left=lambda e: f"Recovered: {e}",
                on_right=str,
            )
        ),
    )
    assert effect.run_sync(recovered) == "Recovered: something went wrong"


def test_either_success_in_pipe_with_match() -> None:
    program = effect.succeed(99)
    recovered = pipe(
        program,
        effect.either,
        effect.map_(
            either.match_(
                on_left=lambda _: "error",
                on_right=lambda v: f"ok: {v}",
            )
        ),
    )
    assert effect.run_sync(recovered) == "ok: 99"


@pytest.mark.asyncio
async def test_either_async_success_returns_right() -> None:
    eff = effect.either(effect.succeed("hello"))
    result = await effect.run_async(eff)
    assert isinstance(result, either.Right)
    assert result.value == "hello"


@pytest.mark.asyncio
async def test_either_async_failure_returns_left() -> None:
    eff = effect.either(effect.fail(ValueError("bad")))
    result = await effect.run_async(eff)
    assert isinstance(result, either.Left)
    assert isinstance(result.value, ValueError)
