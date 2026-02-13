"""Tests for Exit runtime functions."""

import asyncio
from typing import Never

import pytest

from pyfect import effect


def test_run_sync_exit_success() -> None:
    """Test that run_sync_exit returns Success for successful effects."""
    result = effect.run_sync_exit(effect.succeed(42))

    match result:
        case effect.Success(value):
            assert value == 42  # noqa: PLR2004
        case effect.Failure(_):
            pytest.fail("Expected Success, got Failure")


def test_run_sync_exit_failure() -> None:
    """Test that run_sync_exit returns Failure for failed effects."""
    result = effect.run_sync_exit(effect.fail(ValueError("oops")))

    match result:
        case effect.Success(_):
            pytest.fail("Expected Failure, got Success")
        case effect.Failure(error):
            assert isinstance(error, ValueError)
            assert str(error) == "oops"


def test_run_sync_exit_with_sync_effect() -> None:
    """Test run_sync_exit with a Sync effect."""
    result = effect.run_sync_exit(effect.sync(lambda: 100))

    match result:
        case effect.Success(value):
            assert value == 100  # noqa: PLR2004
        case effect.Failure(_):
            pytest.fail("Expected Success")


def test_run_sync_exit_with_tap() -> None:
    """Test that run_sync_exit works with tap."""
    executed = []

    eff = effect.tap(lambda x: effect.sync(lambda: executed.append(x)))(effect.succeed(42))

    result = effect.run_sync_exit(eff)

    match result:
        case effect.Success(value):
            assert value == 42  # noqa: PLR2004
            assert executed == [42]
        case effect.Failure(_):
            pytest.fail("Expected Success")


def test_run_sync_exit_with_tap_error_on_failure() -> None:
    """Test that run_sync_exit works with tap_error when effect fails."""
    executed = []

    eff = effect.tap_error(lambda e: effect.sync(lambda: executed.append(str(e))))(
        effect.fail(ValueError("error"))
    )

    result = effect.run_sync_exit(eff)

    match result:
        case effect.Success(_):
            pytest.fail("Expected Failure")
        case effect.Failure(error):
            assert isinstance(error, ValueError)
            assert len(executed) == 1
            assert "error" in executed[0]


def test_run_sync_exit_with_tap_error_on_success() -> None:
    """Test that tap_error doesn't run when effect succeeds."""
    executed = []

    eff = effect.tap_error(lambda e: effect.sync(lambda: executed.append("should not run")))(
        effect.succeed(42)
    )

    result = effect.run_sync_exit(eff)

    match result:
        case effect.Success(value):
            assert value == 42  # noqa: PLR2004
            assert executed == []  # tap_error was not called
        case effect.Failure(_):
            pytest.fail("Expected Success")


@pytest.mark.asyncio
async def test_run_async_exit_success() -> None:
    """Test that run_async_exit returns Success for successful effects."""
    result = await effect.run_async_exit(effect.succeed(42))

    match result:
        case effect.Success(value):
            assert value == 42  # noqa: PLR2004
        case effect.Failure(_):
            pytest.fail("Expected Success, got Failure")


@pytest.mark.asyncio
async def test_run_async_exit_failure() -> None:
    """Test that run_async_exit returns Failure for failed effects."""
    result = await effect.run_async_exit(effect.fail(RuntimeError("oops")))

    match result:
        case effect.Success(_):
            pytest.fail("Expected Failure, got Success")
        case effect.Failure(error):
            assert isinstance(error, RuntimeError)
            assert str(error) == "oops"


@pytest.mark.asyncio
async def test_run_async_exit_with_async_effect() -> None:
    """Test run_async_exit with an async effect."""

    async def async_computation() -> int:
        await asyncio.sleep(0.01)
        return 100

    result = await effect.run_async_exit(effect.async_(async_computation))

    match result:
        case effect.Success(value):
            assert value == 100  # noqa: PLR2004
        case effect.Failure(_):
            pytest.fail("Expected Success")


@pytest.mark.asyncio
async def test_run_async_exit_with_sync_effect() -> None:
    """Test that run_async_exit can run sync effects."""
    result = await effect.run_async_exit(effect.sync(lambda: 42))

    match result:
        case effect.Success(value):
            assert value == 42  # noqa: PLR2004
        case effect.Failure(_):
            pytest.fail("Expected Success")


@pytest.mark.asyncio
async def test_run_async_exit_with_tap() -> None:
    """Test that run_async_exit works with tap."""
    executed = []

    async def async_log(x: int) -> None:
        await asyncio.sleep(0.01)
        executed.append(x)

    def do_log(x: int) -> effect.Effect[None, Never, None]:
        return effect.async_(lambda: async_log(x))

    eff = effect.tap(do_log)(effect.succeed(42))

    result = await effect.run_async_exit(eff)

    match result:
        case effect.Success(value):
            assert value == 42  # noqa: PLR2004
            assert executed == [42]
        case effect.Failure(_):
            pytest.fail("Expected Success")


def test_exit_pattern_matching() -> None:
    """Test pattern matching on Exit types."""
    success_result = effect.run_sync_exit(effect.succeed("hello"))
    failure_result = effect.run_sync_exit(effect.fail("error"))

    # Test success path
    match success_result:
        case effect.Success(value):
            assert value == "hello"
            success_matched = True
        case effect.Failure(_):
            success_matched = False

    assert success_matched

    # Test failure path
    match failure_result:
        case effect.Success(_):
            failure_matched = False
        case effect.Failure(error):
            assert error == "error"
            failure_matched = True

    assert failure_matched


def test_exit_no_exceptions_thrown() -> None:
    """Test that run_sync_exit never throws for Fail effects."""
    # This should not throw, even though the error is an exception
    result = effect.run_sync_exit(effect.fail(ValueError("this should not throw")))

    # Verify we got Failure, not an exception
    assert isinstance(result, effect.Failure)
    assert isinstance(result.error, ValueError)
