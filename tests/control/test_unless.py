"""Tests for the effect.unless combinator."""

import pytest

from pyfect import effect, option, pipe


def test_unless_false_returns_some() -> None:
    """When condition is False, the effect runs and its value is wrapped in Some."""
    result = pipe(
        effect.succeed(42),
        effect.unless(lambda: False),
    )
    match effect.run_sync(result):
        case option.Some(value):
            assert value == 42  # noqa: PLR2004
        case option.Nothing():
            msg = "Expected Some, got Nothing"
            raise AssertionError(msg)


def test_unless_true_returns_nothing() -> None:
    """When condition is True, the effect is skipped and Nothing is returned."""
    result = pipe(
        effect.succeed(42),
        effect.unless(lambda: True),
    )
    assert effect.run_sync(result) == option.nothing()


def test_unless_condition_evaluated_at_runtime() -> None:
    """Condition thunk is evaluated when the effect runs, not when unless() is called."""
    flag = True
    eff = pipe(
        effect.succeed(99),
        effect.unless(lambda: flag),
    )

    assert effect.run_sync(eff) == option.nothing()

    flag = False
    assert effect.run_sync(eff) == option.some(99)


def test_unless_effect_only_runs_if_condition_false() -> None:
    """The inner effect's side effects only execute when condition is False."""
    executed: list[int] = []

    eff = pipe(
        effect.sync(lambda: executed.append(1) or 1),
        effect.unless(lambda: True),
    )

    effect.run_sync(eff)
    assert executed == []


def test_unless_effect_runs_when_condition_false() -> None:
    """The inner effect's side effects execute when condition is False."""
    executed: list[int] = []

    eff = pipe(
        effect.sync(lambda: executed.append(1) or 1),
        effect.unless(lambda: False),
    )

    effect.run_sync(eff)
    assert executed == [1]


def test_unless_preserves_error_type() -> None:
    """Failures in the inner effect still propagate when condition is False."""
    result = pipe(
        effect.fail(ValueError("oops")),
        effect.unless(lambda: False),
    )
    with pytest.raises(ValueError, match="oops"):
        effect.run_sync(result)


def test_unless_true_skips_even_failing_effect() -> None:
    """When condition is True the inner effect is not executed, so no error."""
    result = pipe(
        effect.fail(ValueError("oops")),
        effect.unless(lambda: True),
    )
    assert effect.run_sync(result) == option.nothing()


def test_unless_with_exit_false() -> None:
    """run_sync_exit wraps a successful conditional execution correctly."""
    result = pipe(
        effect.succeed("hello"),
        effect.unless(lambda: False),
    )
    match effect.run_sync_exit(result):
        case effect.Success(value):
            assert value == option.some("hello")
        case effect.Failure(e):
            msg = f"Unexpected failure: {e}"
            raise AssertionError(msg)


def test_unless_with_exit_true() -> None:
    """run_sync_exit returns Success(Nothing) when condition is True."""
    result = pipe(
        effect.succeed("hello"),
        effect.unless(lambda: True),
    )
    match effect.run_sync_exit(result):
        case effect.Success(value):
            assert value == option.nothing()
        case effect.Failure(e):
            msg = f"Unexpected failure: {e}"
            raise AssertionError(msg)


def test_unless_with_closure_over_value() -> None:
    """Condition can close over runtime values."""

    def validate_weight(weight: float) -> effect.Effect[option.Option[float]]:
        return pipe(
            effect.succeed(weight),
            effect.unless(lambda: weight < 0),
        )

    assert effect.run_sync(validate_weight(100)) == option.some(100)
    assert effect.run_sync(validate_weight(-5)) == option.nothing()


@pytest.mark.asyncio
async def test_unless_async_false() -> None:
    """unless works with the async runtime when condition is False."""
    result = pipe(
        effect.succeed(7),
        effect.unless(lambda: False),
    )
    assert await effect.run_async(result) == option.some(7)


@pytest.mark.asyncio
async def test_unless_async_true() -> None:
    """unless returns Nothing via the async runtime when condition is True."""
    result = pipe(
        effect.succeed(7),
        effect.unless(lambda: True),
    )
    assert await effect.run_async(result) == option.nothing()
