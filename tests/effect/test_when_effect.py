"""Tests for the effect.when_effect combinator."""

import pytest

from pyfect import effect, option, pipe


def test_when_effect_true_returns_some() -> None:
    """When condition effect produces True, the effect runs and its value is wrapped in Some."""
    result = pipe(
        effect.succeed(42),
        effect.when_effect(effect.succeed(True)),
    )
    match effect.run_sync(result):
        case option.Some(value):
            assert value == 42  # noqa: PLR2004
        case option.Nothing():
            msg = "Expected Some, got Nothing"
            raise AssertionError(msg)


def test_when_effect_false_returns_nothing() -> None:
    """When condition effect produces False, the effect is skipped and Nothing is returned."""
    result = pipe(
        effect.succeed(42),
        effect.when_effect(effect.succeed(False)),
    )
    assert effect.run_sync(result) == option.nothing()


def test_when_effect_condition_evaluated_at_runtime() -> None:
    """Condition effect is evaluated when the effect runs, not when when_effect() is called."""
    toggle: list[bool] = [False]
    eff = pipe(
        effect.succeed(99),
        effect.when_effect(effect.sync(lambda: toggle[0])),
    )

    assert effect.run_sync(eff) == option.nothing()

    toggle[0] = True
    assert effect.run_sync(eff) == option.some(99)


def test_when_effect_inner_only_runs_if_condition_true() -> None:
    """The inner effect's side effects only execute when condition produces True."""
    executed: list[int] = []

    eff = pipe(
        effect.sync(lambda: executed.append(1) or 1),
        effect.when_effect(effect.succeed(False)),
    )

    effect.run_sync(eff)
    assert executed == []


def test_when_effect_inner_runs_when_condition_true() -> None:
    """The inner effect's side effects execute when condition produces True."""
    executed: list[int] = []

    eff = pipe(
        effect.sync(lambda: executed.append(1) or 1),
        effect.when_effect(effect.succeed(True)),
    )

    effect.run_sync(eff)
    assert executed == [1]


def test_when_effect_condition_failure_propagates() -> None:
    """If the condition effect fails, the error propagates and the inner effect is skipped."""
    executed: list[int] = []

    result = pipe(
        effect.sync(lambda: executed.append(1) or 1),
        effect.when_effect(effect.fail(ValueError("condition error"))),
    )

    with pytest.raises(ValueError, match="condition error"):
        effect.run_sync(result)

    assert executed == []


def test_when_effect_inner_failure_propagates_when_true() -> None:
    """If condition is True but the inner effect fails, that error propagates."""
    result = pipe(
        effect.fail(RuntimeError("inner error")),
        effect.when_effect(effect.succeed(True)),
    )
    with pytest.raises(RuntimeError, match="inner error"):
        effect.run_sync(result)


def test_when_effect_false_skips_even_failing_inner_effect() -> None:
    """When condition is False, the inner effect is not executed so no error."""
    result = pipe(
        effect.fail(RuntimeError("inner error")),
        effect.when_effect(effect.succeed(False)),
    )
    assert effect.run_sync(result) == option.nothing()


def test_when_effect_condition_from_sync() -> None:
    """Condition can be any boolean-producing effect."""
    result = pipe(
        effect.succeed(10),
        effect.when_effect(effect.sync(lambda: 1 + 1 == 2)),  # noqa: PLR2004
    )
    assert effect.run_sync(result) == option.some(10)


def test_when_effect_with_exit_true() -> None:
    """run_sync_exit wraps a successful conditional execution correctly."""
    result = pipe(
        effect.succeed("hello"),
        effect.when_effect(effect.succeed(True)),
    )
    match effect.run_sync_exit(result):
        case effect.Success(value):
            assert value == option.some("hello")
        case effect.Failure(e):
            msg = f"Unexpected failure: {e}"
            raise AssertionError(msg)


def test_when_effect_with_exit_false() -> None:
    """run_sync_exit returns Success(Nothing) when condition produces False."""
    result = pipe(
        effect.succeed("hello"),
        effect.when_effect(effect.succeed(False)),
    )
    match effect.run_sync_exit(result):
        case effect.Success(value):
            assert value == option.nothing()
        case effect.Failure(e):
            msg = f"Unexpected failure: {e}"
            raise AssertionError(msg)


def test_when_effect_with_exit_condition_failure() -> None:
    """run_sync_exit captures condition failure as Exit.Failure."""
    result = pipe(
        effect.succeed(42),
        effect.when_effect(effect.fail("condition failed")),
    )
    match effect.run_sync_exit(result):
        case effect.Failure(e):
            assert e == "condition failed"
        case effect.Success(_):
            msg = "Expected failure"
            raise AssertionError(msg)


@pytest.mark.asyncio
async def test_when_effect_async_true() -> None:
    """when_effect works with the async runtime when condition is True."""
    result = pipe(
        effect.succeed(7),
        effect.when_effect(effect.succeed(True)),
    )
    assert await effect.run_async(result) == option.some(7)


@pytest.mark.asyncio
async def test_when_effect_async_false() -> None:
    """when_effect returns Nothing via the async runtime when condition is False."""
    result = pipe(
        effect.succeed(7),
        effect.when_effect(effect.succeed(False)),
    )
    assert await effect.run_async(result) == option.nothing()


@pytest.mark.asyncio
async def test_when_effect_async_condition_failure() -> None:
    """when_effect propagates condition failure in async runtime."""
    result = pipe(
        effect.succeed(7),
        effect.when_effect(effect.fail(ValueError("async condition error"))),
    )
    with pytest.raises(ValueError, match="async condition error"):
        await effect.run_async(result)
