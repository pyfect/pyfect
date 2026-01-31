"""Basic tests for effect primitives and runtime."""

import asyncio

import pytest

from pyfect import effect


def test_succeed_sync() -> None:
    """Test that succeed creates a value and run_sync executes it."""
    eff = effect.succeed(42)
    result = effect.run_sync(eff)
    assert result == 42  # noqa: PLR2004


def test_fail_sync() -> None:
    """Test that fail raises an exception when run."""
    eff = effect.fail(ValueError("oops"))

    with pytest.raises(ValueError, match="oops"):
        effect.run_sync(eff)


def test_fail_with_non_exception() -> None:
    """Test that fail with a non-exception wraps in RuntimeError."""
    eff = effect.fail("just a string")

    with pytest.raises(RuntimeError, match="effect failed: just a string"):
        effect.run_sync(eff)


def test_sync_effect() -> None:
    """Test that sync defers computation until run."""
    executed = []

    def side_effect() -> int:
        executed.append(1)
        return 42

    # Create effect - should not execute yet
    eff = effect.sync(side_effect)
    assert len(executed) == 0

    # Run effect - now it executes
    result = effect.run_sync(eff)
    assert result == 42  # noqa: PLR2004
    assert len(executed) == 1


@pytest.mark.asyncio
async def test_async_effect() -> None:
    """Test that async_ works with run_async."""
    executed = []

    async def async_computation() -> int:
        executed.append(1)
        await asyncio.sleep(0.01)
        return 42

    # Create effect - should not execute yet
    eff = effect.async_(async_computation)
    assert len(executed) == 0

    # Run effect - now it executes
    result = await effect.run_async(eff)
    assert result == 42  # noqa: PLR2004
    assert len(executed) == 1


@pytest.mark.asyncio
async def test_run_async_with_sync_effect() -> None:
    """Test that run_async can also run synchronous effects."""
    eff = effect.succeed(42)
    result = await effect.run_async(eff)
    assert result == 42  # noqa: PLR2004


@pytest.mark.asyncio
async def test_run_async_with_sync_computation() -> None:
    """Test that run_async can run Sync effects."""
    eff = effect.sync(lambda: 42)
    result = await effect.run_async(eff)
    assert result == 42  # noqa: PLR2004


def test_cannot_run_async_effect_with_run_sync() -> None:
    """Test that async effects cannot be run with run_sync."""
    eff = effect.async_(lambda: asyncio.sleep(0))

    with pytest.raises(RuntimeError, match="Cannot run Async synchronously"):
        effect.run_sync(eff)
