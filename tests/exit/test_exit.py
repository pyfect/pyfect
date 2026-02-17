"""Tests for Exit runtime functions."""

import asyncio

import pytest

from pyfect import effect


def test_run_sync_exit_success() -> None:
    """Test that run_sync_exit returns Success for successful effects."""
    result = effect.run_sync_exit(effect.succeed(42))

    assert isinstance(result, effect.Success)
    assert result.value == 42  # noqa: PLR2004


def test_run_sync_exit_failure() -> None:
    """Test that run_sync_exit returns Failure for failed effects."""
    result = effect.run_sync_exit(effect.fail(ValueError("oops")))

    assert isinstance(result, effect.Failure)
    assert isinstance(result.error, ValueError)
    assert str(result.error) == "oops"


def test_run_sync_exit_with_sync_effect() -> None:
    """Test run_sync_exit with a Sync effect."""
    result = effect.run_sync_exit(effect.sync(lambda: 100))

    assert isinstance(result, effect.Success)
    assert result.value == 100  # noqa: PLR2004


def test_run_sync_exit_with_tap() -> None:
    """Test that run_sync_exit works with tap."""
    executed = []

    eff = effect.tap(lambda x: effect.sync(lambda: executed.append(x)))(effect.succeed(42))

    result = effect.run_sync_exit(eff)

    assert isinstance(result, effect.Success)
    assert result.value == 42  # noqa: PLR2004
    assert executed == [42]


def test_run_sync_exit_with_tap_error_on_failure() -> None:
    """Test that run_sync_exit works with tap_error when effect fails."""
    executed = []

    eff = effect.tap_error(lambda e: effect.sync(lambda: executed.append(str(e))))(
        effect.fail(ValueError("error"))
    )

    result = effect.run_sync_exit(eff)

    assert isinstance(result, effect.Failure)
    assert isinstance(result.error, ValueError)
    assert len(executed) == 1
    assert "error" in executed[0]


def test_run_sync_exit_with_tap_error_on_success() -> None:
    """Test that tap_error doesn't run when effect succeeds."""
    executed = []

    eff = effect.tap_error(lambda e: effect.sync(lambda: executed.append("should not run")))(
        effect.succeed(42)
    )

    result = effect.run_sync_exit(eff)

    assert isinstance(result, effect.Success)
    assert result.value == 42  # noqa: PLR2004
    assert executed == []  # tap_error was not called


@pytest.mark.asyncio
async def test_run_async_exit_success() -> None:
    """Test that run_async_exit returns Success for successful effects."""
    result = await effect.run_async_exit(effect.succeed(42))

    assert isinstance(result, effect.Success)
    assert result.value == 42  # noqa: PLR2004


@pytest.mark.asyncio
async def test_run_async_exit_failure() -> None:
    """Test that run_async_exit returns Failure for failed effects."""
    result = await effect.run_async_exit(effect.fail(RuntimeError("oops")))

    assert isinstance(result, effect.Failure)
    assert isinstance(result.error, RuntimeError)
    assert str(result.error) == "oops"


@pytest.mark.asyncio
async def test_run_async_exit_with_async_effect() -> None:
    """Test run_async_exit with an async effect."""

    async def async_computation() -> int:
        await asyncio.sleep(0.01)
        return 100

    result = await effect.run_async_exit(effect.async_(async_computation))

    assert isinstance(result, effect.Success)
    assert result.value == 100  # noqa: PLR2004


@pytest.mark.asyncio
async def test_run_async_exit_with_sync_effect() -> None:
    """Test that run_async_exit can run sync effects."""
    result = await effect.run_async_exit(effect.sync(lambda: 42))

    assert isinstance(result, effect.Success)
    assert result.value == 42  # noqa: PLR2004


@pytest.mark.asyncio
async def test_run_async_exit_with_tap() -> None:
    """Test that run_async_exit works with tap."""
    executed = []

    async def async_log(x: int) -> None:
        await asyncio.sleep(0.01)
        executed.append(x)

    def do_log(x: int) -> effect.Effect[None]:
        return effect.async_(lambda: async_log(x))

    eff = effect.tap(do_log)(effect.succeed(42))

    result = await effect.run_async_exit(eff)

    assert isinstance(result, effect.Success)
    assert result.value == 42  # noqa: PLR2004
    assert executed == [42]


def test_exit_isinstance_checks() -> None:
    """Test isinstance checks on Exit types."""
    success_result = effect.run_sync_exit(effect.succeed("hello"))
    failure_result = effect.run_sync_exit(effect.fail("error"))

    # Test success path
    assert isinstance(success_result, effect.Success)
    assert success_result.value == "hello"

    # Test failure path
    assert isinstance(failure_result, effect.Failure)
    assert failure_result.error == "error"


def test_exit_no_exceptions_thrown() -> None:
    """Test that run_sync_exit never throws for Fail effects."""
    # This should not throw, even though the error is an exception
    result = effect.run_sync_exit(effect.fail(ValueError("this should not throw")))

    # Verify we got Failure, not an exception
    assert isinstance(result, effect.Failure)
    assert isinstance(result.error, ValueError)
