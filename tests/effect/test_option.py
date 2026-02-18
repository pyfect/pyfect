"""Tests for effect.option."""

import pytest

from pyfect import effect, option, pipe


def test_option_success_returns_some() -> None:
    eff = effect.option(effect.succeed(42))
    result = effect.run_sync(eff)
    assert isinstance(result, option.Some)
    assert result.value == 42  # noqa: PLR2004


def test_option_failure_returns_nothing() -> None:
    eff = effect.option(effect.fail("oops"))
    result = effect.run_sync(eff)
    assert result is option.NOTHING


def test_option_never_fails_on_error() -> None:
    """The resulting effect succeeds even when the inner effect fails."""
    eff = effect.option(effect.fail("boom"))
    result = effect.run_sync_exit(eff)
    assert isinstance(result, effect.Success)


def test_option_discards_error_value() -> None:
    """Nothing carries no error information — the error type is erased."""
    eff1 = effect.option(effect.fail("oops"))
    eff2 = effect.option(effect.fail(ValueError("bad")))
    assert effect.run_sync(eff1) is option.NOTHING
    assert effect.run_sync(eff2) is option.NOTHING


def test_option_in_pipe() -> None:
    program = effect.succeed("hello")
    result = effect.run_sync(pipe(program, effect.option))
    assert isinstance(result, option.Some)
    assert result.value == "hello"


def test_option_failure_in_pipe() -> None:
    program = effect.fail("gone")
    result = effect.run_sync(pipe(program, effect.option))
    assert result is option.NOTHING


@pytest.mark.asyncio
async def test_option_async_success_returns_some() -> None:
    eff = effect.option(effect.succeed("world"))
    result = await effect.run_async(eff)
    assert isinstance(result, option.Some)
    assert result.value == "world"


@pytest.mark.asyncio
async def test_option_async_failure_returns_nothing() -> None:
    eff = effect.option(effect.fail("async oops"))
    result = await effect.run_async(eff)
    assert result is option.NOTHING
