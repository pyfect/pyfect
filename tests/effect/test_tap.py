"""Tests for tap and tap_error combinators."""

import asyncio

import pytest

from pyfect import effect, pipe


def test_tap_sync() -> None:
    """Test that tap executes side effects without modifying the value."""
    executed = []

    def log_value(x: int) -> effect.Effect:
        return effect.sync(lambda: executed.append(f"Got: {x}"))

    eff = effect.tap(log_value)(effect.succeed(42))

    result = effect.run_sync(eff)

    assert result == 42  # noqa: PLR2004
    assert executed == ["Got: 42"]


def test_tap_preserves_value() -> None:
    """Test that tap returns the original value, not the tap result."""

    def on_success(x: int) -> effect.Effect[str]:
        return effect.succeed("ignored")

    eff = effect.tap(on_success)(effect.succeed(42))

    result = effect.run_sync(eff)
    assert result == 42  # noqa: PLR2004


def test_tap_with_sync_computation() -> None:
    """Test tap with a Sync effect."""
    executed = []

    eff = effect.tap(lambda x: effect.sync(lambda: executed.append(x)))(effect.sync(lambda: 100))

    result = effect.run_sync(eff)
    assert result == 100  # noqa: PLR2004
    assert executed == [100]


@pytest.mark.asyncio
async def test_tap_async() -> None:
    """Test that tap works with async effects."""
    executed = []

    async def async_log(x: int) -> None:
        await asyncio.sleep(0.01)
        executed.append(f"Async: {x}")

    def do_log(x: int) -> effect.Effect[None]:
        return effect.async_(lambda: async_log(x))

    eff = effect.tap(do_log)(effect.succeed(42))

    result = await effect.run_async(eff)

    assert result == 42  # noqa: PLR2004
    assert executed == ["Async: 42"]


def test_tap_error_sync() -> None:
    """Test that tap_error executes side effects on error."""
    executed = []

    def log_error(e: ValueError) -> effect.Effect:
        return effect.sync(lambda: executed.append(f"Error: {e}"))

    eff = effect.tap_error(log_error)(effect.fail(ValueError("oops")))

    with pytest.raises(ValueError, match="oops"):
        effect.run_sync(eff)

    assert len(executed) == 1
    assert "Error: oops" in executed[0]


def test_tap_error_preserves_error() -> None:
    """Test that tap_error re-raises the original error."""

    def on_error(e: ValueError) -> effect.Effect[None]:
        return effect.sync(lambda: None)

    eff = effect.tap_error(on_error)(effect.fail(ValueError("original")))

    with pytest.raises(ValueError, match="original"):
        effect.run_sync(eff)


def test_tap_error_does_not_run_on_success() -> None:
    """Test that tap_error is not executed when the effect succeeds."""
    executed = []

    eff = effect.tap_error(lambda e: effect.sync(lambda: executed.append("should not run")))(
        effect.succeed(42)
    )

    result = effect.run_sync(eff)
    assert result == 42  # noqa: PLR2004
    assert executed == []  # tap_error was not called


@pytest.mark.asyncio
async def test_tap_error_async() -> None:
    """Test that tap_error works with async effects."""
    executed = []

    async def async_log_error(e: RuntimeError) -> None:
        await asyncio.sleep(0.01)
        executed.append(f"Async error: {e}")

    def do_log_error(e: RuntimeError) -> effect.Effect[None]:
        return effect.async_(lambda: async_log_error(e))

    eff = effect.tap_error(do_log_error)(effect.fail(RuntimeError("async error")))

    with pytest.raises(RuntimeError, match="async error"):
        await effect.run_async(eff)

    assert len(executed) == 1
    assert "Async error: async error" in executed[0]


def test_tap_error_ignores_tap_function_errors() -> None:
    """Test that errors in the tap_error function are ignored."""

    def failing_tap(e: ValueError) -> effect.Effect:
        return effect.sync(lambda: 1 / 0)  # This will raise ZeroDivisionError

    eff = effect.tap_error(failing_tap)(effect.fail(ValueError("original")))

    # Should still raise the original error, not ZeroDivisionError
    with pytest.raises(ValueError, match="original"):
        effect.run_sync(eff)


def test_multiple_taps() -> None:
    """Test chaining multiple tap operations."""
    executed = []

    eff = effect.tap(lambda x: effect.sync(lambda: executed.append(f"Second: {x}")))(
        effect.tap(lambda x: effect.sync(lambda: executed.append(f"First: {x}")))(
            effect.succeed(42)
        )
    )

    result = effect.run_sync(eff)
    assert result == 42  # noqa: PLR2004
    assert executed == ["First: 42", "Second: 42"]


def test_tap_with_pipe() -> None:
    """Test that curried tap works beautifully with pipe."""
    executed = []

    def log_first(x: int) -> effect.Effect[None]:
        return effect.sync(lambda: executed.append(f"First: {x}"))

    def log_second(x: int) -> effect.Effect[None]:
        return effect.sync(lambda: executed.append(f"Second: {x}"))

    result_effect = pipe(
        effect.succeed(42),
        effect.tap(log_first),
        effect.tap(log_second),
    )

    result = effect.run_sync(result_effect)
    assert result == 42  # noqa: PLR2004
    assert executed == ["First: 42", "Second: 42"]
