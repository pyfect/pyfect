"""Tests for suspend constructor."""

import asyncio
from typing import Never

import pytest

from pyfect import effect


def test_suspend_basic() -> None:
    """Test basic suspend functionality."""
    eff = effect.suspend(lambda: effect.succeed(42))
    result = effect.run_sync(eff)
    assert result == 42  # noqa: PLR2004


def test_suspend_re_executes_each_time() -> None:
    """Test that suspend creates fresh effect on each run."""
    counter = 0

    def increment() -> effect.Effect:
        nonlocal counter
        counter += 1
        return effect.succeed(counter)

    eff = effect.suspend(increment)

    # First run
    result1 = effect.run_sync(eff)
    assert result1 == 1

    # Second run - thunk called again, fresh effect
    result2 = effect.run_sync(eff)
    assert result2 == 2  # noqa: PLR2004

    # Third run
    result3 = effect.run_sync(eff)
    assert result3 == 3  # noqa: PLR2004


def test_suspend_vs_direct_creation() -> None:
    """Test the difference between suspend and direct effect creation."""
    counter = 0

    def increment() -> int:
        nonlocal counter
        counter += 1
        return counter

    # Direct creation - effect created once
    direct = effect.succeed(increment())
    assert effect.run_sync(direct) == 1
    assert effect.run_sync(direct) == 1  # Same effect, same value

    # Suspend - effect created fresh each time
    suspended = effect.suspend(lambda: effect.succeed(increment()))
    assert effect.run_sync(suspended) == 2  # noqa: PLR2004
    assert effect.run_sync(suspended) == 3  # noqa: PLR2004, Fresh effect each time!


def test_suspend_with_side_effects() -> None:
    """Test that side effects in suspended effects are re-executed."""
    executed = []

    def make_effect() -> effect.Effect:
        executed.append("created")
        return effect.sync(lambda: executed.append("run"))

    eff = effect.suspend(make_effect)

    # Not executed yet
    assert len(executed) == 0

    # First run
    effect.run_sync(eff)
    assert executed == ["created", "run"]

    # Second run - both creation and execution happen again
    effect.run_sync(eff)
    assert executed == ["created", "run", "created", "run"]


def test_suspend_with_failure() -> None:
    """Test that suspend works with failing effects."""
    counter = 0

    def make_effect() -> effect.Effect[Never, ValueError]:
        nonlocal counter
        counter += 1
        return effect.fail(ValueError(f"error {counter}"))

    eff = effect.suspend(make_effect)

    # First run
    with pytest.raises(ValueError, match="error 1"):
        effect.run_sync(eff)

    # Second run - fresh error
    with pytest.raises(ValueError, match="error 2"):
        effect.run_sync(eff)


def test_suspend_with_exit() -> None:
    """Test that suspend works with run_sync_exit."""
    counter = 0

    def make_effect() -> effect.Effect:
        nonlocal counter
        counter += 1
        return effect.succeed(counter)

    eff = effect.suspend(make_effect)

    result1 = effect.run_sync_exit(eff)
    match result1:
        case effect.Success(value):
            assert value == 1
        case effect.Failure(_):
            pytest.fail("Expected success")

    result2 = effect.run_sync_exit(eff)
    match result2:
        case effect.Success(value):
            assert value == 2  # noqa: PLR2004, Fresh effect!
        case effect.Failure(_):
            pytest.fail("Expected success")


def test_suspend_lazy_evaluation() -> None:
    """Test that suspend doesn't execute the thunk until run."""
    executed = []

    eff = effect.suspend(lambda: (executed.append("called"), effect.succeed(42))[1])

    # Thunk not called yet
    assert len(executed) == 0

    # Now it's called
    result = effect.run_sync(eff)
    assert result == 42  # noqa: PLR2004
    assert executed == ["called"]


def test_suspend_with_tap() -> None:
    """Test that suspend works with tap."""
    counter = 0
    tapped = []

    def make_effect() -> effect.Effect:
        nonlocal counter
        counter += 1
        return effect.succeed(counter)

    eff = effect.tap(lambda x: effect.sync(lambda: tapped.append(x)))(effect.suspend(make_effect))

    effect.run_sync(eff)
    assert tapped == [1]

    effect.run_sync(eff)
    assert tapped == [1, 2]  # Fresh effect, fresh value!


def test_suspend_nested() -> None:
    """Test nested suspend calls."""
    counter = 0

    def make_inner() -> effect.Effect:
        nonlocal counter
        counter += 1
        return effect.succeed(counter)

    def make_outer() -> effect.Effect:
        return effect.suspend(make_inner)

    eff = effect.suspend(make_outer)

    # Each run creates fresh outer, which creates fresh inner
    assert effect.run_sync(eff) == 1
    assert effect.run_sync(eff) == 2  # noqa: PLR2004
    assert effect.run_sync(eff) == 3  # noqa: PLR2004


@pytest.mark.asyncio
async def test_suspend_async() -> None:
    """Test suspend with async effects."""
    counter = 0

    async def async_increment() -> int:
        nonlocal counter
        await asyncio.sleep(0.01)
        counter += 1
        return counter

    def make_effect() -> effect.Effect:
        return effect.async_(async_increment)

    eff = effect.suspend(make_effect)

    result1 = await effect.run_async(eff)
    assert result1 == 1

    result2 = await effect.run_async(eff)
    assert result2 == 2  # noqa: PLR2004, Fresh effect!


@pytest.mark.asyncio
async def test_suspend_async_exit() -> None:
    """Test suspend with run_async_exit."""
    counter = 0

    def make_effect() -> effect.Effect:
        nonlocal counter
        counter += 1
        return effect.succeed(counter)

    eff = effect.suspend(make_effect)

    result1 = await effect.run_async_exit(eff)
    match result1:
        case effect.Success(value):
            assert value == 1
        case effect.Failure(_):
            pytest.fail("Expected success")

    result2 = await effect.run_async_exit(eff)
    match result2:
        case effect.Success(value):
            assert value == 2  # noqa: PLR2004
        case effect.Failure(_):
            pytest.fail("Expected success")


def test_suspend_captures_fresh_state() -> None:
    """Test the canonical example from Effect TS docs."""

    class Counter:
        def __init__(self) -> None:
            self.i = 0

        def increment(self) -> int:
            self.i += 1
            return self.i

    counter = Counter()

    # Bad - effect created once, captures result of first increment
    bad = effect.succeed(counter.increment())

    # Good - effect created fresh each time
    good = effect.suspend(lambda: effect.succeed(counter.increment()))

    # Bad always returns 1 (same effect, same value)
    assert effect.run_sync(bad) == 1
    assert effect.run_sync(bad) == 1

    # Good captures fresh value each time
    assert effect.run_sync(good) == 2  # noqa: PLR2004
    assert effect.run_sync(good) == 3  # noqa: PLR2004
