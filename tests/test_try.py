"""Tests for try_sync and try_async constructors."""

import asyncio

import pytest

from pyfect import effect


def test_try_sync_success() -> None:
    """Test that try_sync works with successful computation."""
    eff = effect.try_sync(lambda: 42)
    result = effect.run_sync(eff)
    assert result == 42  # noqa: PLR2004


def test_try_sync_throws_with_run_sync() -> None:
    """Test that try_sync propagates exceptions with run_sync."""
    eff = effect.try_sync(lambda: int("not a number"))

    with pytest.raises(ValueError):  # noqa: PT011
        effect.run_sync(eff)


def test_try_sync_throws_with_run_sync_exit() -> None:
    """Test that try_sync returns ExitFailure with run_sync_exit."""
    eff = effect.try_sync(lambda: int("not a number"))

    result = effect.run_sync_exit(eff)

    match result:
        case effect.ExitSuccess(_):
            pytest.fail("Expected ExitFailure")
        case effect.ExitFailure(error):
            assert isinstance(error, ValueError)
            assert "invalid literal" in str(error)


def test_try_sync_different_exceptions() -> None:
    """Test that try_sync catches different exception types."""
    # ZeroDivisionError
    eff1 = effect.try_sync(lambda: 1 / 0)
    result1 = effect.run_sync_exit(eff1)
    assert isinstance(result1, effect.ExitFailure)
    assert isinstance(result1.error, ZeroDivisionError)

    # KeyError
    eff2 = effect.try_sync(lambda: {}["missing"])
    result2 = effect.run_sync_exit(eff2)
    assert isinstance(result2, effect.ExitFailure)
    assert isinstance(result2.error, KeyError)

    # Custom exception
    class CustomError(Exception):
        pass

    eff3 = effect.try_sync(lambda: (_ for _ in ()).throw(CustomError("custom")))
    result3 = effect.run_sync_exit(eff3)
    assert isinstance(result3, effect.ExitFailure)
    assert isinstance(result3.error, CustomError)


def test_try_sync_with_tap() -> None:
    """Test that try_sync works with tap."""
    executed = []

    eff = effect.tap(lambda x: effect.sync(lambda: executed.append(x)))(
        effect.try_sync(lambda: 100)
    )

    result = effect.run_sync(eff)
    assert result == 100  # noqa: PLR2004
    assert executed == [100]


def test_try_sync_with_tap_error() -> None:
    """Test that try_sync works with tap_error."""
    executed = []

    eff = effect.tap_error(lambda e: effect.sync(lambda: executed.append(str(e))))(
        effect.try_sync(lambda: int("bad"))
    )

    result = effect.run_sync_exit(eff)

    match result:
        case effect.ExitFailure(error):
            assert isinstance(error, ValueError)
            assert len(executed) == 1
        case effect.ExitSuccess(_):
            pytest.fail("Expected ExitFailure")


@pytest.mark.asyncio
async def test_try_async_success() -> None:
    """Test that try_async works with successful async computation."""

    async def async_computation() -> int:
        await asyncio.sleep(0.01)
        return 42

    eff = effect.try_async(async_computation)
    result = await effect.run_async(eff)
    assert result == 42  # noqa: PLR2004


@pytest.mark.asyncio
async def test_try_async_throws_with_run_async() -> None:
    """Test that try_async propagates exceptions with run_async."""

    async def failing_computation() -> int:
        await asyncio.sleep(0.01)
        return int("not a number")

    eff = effect.try_async(failing_computation)

    with pytest.raises(ValueError):  # noqa: PT011
        await effect.run_async(eff)


@pytest.mark.asyncio
async def test_try_async_throws_with_run_async_exit() -> None:
    """Test that try_async returns ExitFailure with run_async_exit."""

    async def failing_computation() -> int:
        await asyncio.sleep(0.01)
        msg = "async error"
        raise RuntimeError(msg)

    eff = effect.try_async(failing_computation)

    result = await effect.run_async_exit(eff)

    match result:
        case effect.ExitSuccess(_):
            pytest.fail("Expected ExitFailure")
        case effect.ExitFailure(error):
            assert isinstance(error, RuntimeError)
            assert str(error) == "async error"


@pytest.mark.asyncio
async def test_try_async_different_exceptions() -> None:
    """Test that try_async catches different exception types."""

    async def zero_div() -> float:
        await asyncio.sleep(0.01)
        return 1 / 0

    eff = effect.try_async(zero_div)
    result = await effect.run_async_exit(eff)
    assert isinstance(result, effect.ExitFailure)
    assert isinstance(result.error, ZeroDivisionError)


@pytest.mark.asyncio
async def test_try_async_with_tap() -> None:
    """Test that try_async works with tap."""
    executed = []

    async def async_computation() -> int:
        await asyncio.sleep(0.01)
        return 100

    async def async_log(x: int) -> None:
        await asyncio.sleep(0.01)
        executed.append(x)

    eff = effect.tap(lambda x: effect.async_(lambda: async_log(x)))(  # type: ignore[arg-type]
        effect.try_async(async_computation)
    )

    result = await effect.run_async(eff)
    assert result == 100  # noqa: PLR2004
    assert executed == [100]


def test_try_sync_vs_sync() -> None:
    """Test the difference between sync and try_sync."""
    # sync - exception propagates even with run_sync_exit
    # (because Sync can't fail, so exception is unexpected)
    sync_eff = effect.sync(lambda: int("bad"))

    with pytest.raises(ValueError):  # noqa: PT011
        effect.run_sync_exit(sync_eff)

    # try_sync - exception is caught with run_sync_exit
    try_sync_eff = effect.try_sync(lambda: int("bad"))

    result = effect.run_sync_exit(try_sync_eff)
    assert isinstance(result, effect.ExitFailure)
    assert isinstance(result.error, ValueError)


def test_try_sync_lazy_evaluation() -> None:
    """Test that try_sync doesn't execute immediately."""
    executed = []

    eff = effect.try_sync(lambda: executed.append(1))

    # Not executed yet
    assert len(executed) == 0

    # Execute now
    effect.run_sync(eff)
    assert len(executed) == 1


@pytest.mark.asyncio
async def test_try_async_lazy_evaluation() -> None:
    """Test that try_async doesn't execute immediately."""
    executed = []

    async def async_computation() -> None:
        executed.append(1)

    eff = effect.try_async(async_computation)

    # Not executed yet
    assert len(executed) == 0

    # Execute now
    await effect.run_async(eff)
    assert len(executed) == 1
