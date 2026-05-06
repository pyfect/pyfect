"""Tests for effect.repeat."""

import pytest

from pyfect import context, effect, pipe, schedule

# ============================================================================
# Helpers
# ============================================================================


class Counter:
    """Mutable counter to track how many times an effect body runs."""

    def __init__(self) -> None:
        self.n = 0

    def inc(self) -> int:
        self.n += 1
        return self.n


# ============================================================================
# Basic repetition count
# ============================================================================


def test_repeat_recurs_0_runs_effect_once() -> None:
    """recurs(0) fires Done on the first step — effect runs exactly once."""
    c = Counter()
    result = pipe(effect.sync(c.inc), effect.repeat(schedule.recurs(0)))
    assert effect.run_sync(result) == 1
    assert c.n == 1


def test_repeat_recurs_n_runs_effect_n_plus_1_times() -> None:
    """recurs(n) allows n extra recurrences — total runs = n + 1."""
    c = Counter()
    effect.run_sync(pipe(effect.sync(c.inc), effect.repeat(schedule.recurs(3))))
    assert c.n == 4  # noqa: PLR2004


def test_repeat_once_schedule_runs_effect_twice() -> None:
    """schedule.once recurs exactly once after the initial run."""
    c = Counter()
    effect.run_sync(pipe(effect.sync(c.inc), effect.repeat(schedule.once)))
    assert c.n == 2  # noqa: PLR2004


# ============================================================================
# Return value
# ============================================================================


def test_repeat_returns_last_success_value() -> None:
    """repeat returns the value from the final execution, not the first."""
    c = Counter()
    result = effect.run_sync(pipe(effect.sync(c.inc), effect.repeat(schedule.recurs(2))))
    assert result == 3  # noqa: PLR2004  — third run


def test_repeat_recurs_0_returns_sole_value() -> None:
    """With recurs(0) the single run's value is returned directly."""
    result = effect.run_sync(pipe(effect.succeed(99), effect.repeat(schedule.recurs(0))))
    assert result == 99  # noqa: PLR2004


# ============================================================================
# Failure propagation
# ============================================================================


def test_repeat_stops_on_first_failure() -> None:
    """If the effect fails, repeat surfaces the error and stops."""
    c = Counter()

    def _body() -> int:
        c.inc()
        if c.n == 2:  # noqa: PLR2004
            raise ValueError("second run fails")  # noqa: EM101
        return c.n

    eff = pipe(effect.try_sync(_body), effect.repeat(schedule.recurs(5)))
    with pytest.raises(ValueError, match="second run fails"):
        effect.run_sync(eff)
    assert c.n == 2  # noqa: PLR2004  — stopped after the failing run


def test_repeat_failure_on_first_run_propagates() -> None:
    """A failure on the very first run is surfaced immediately."""
    eff = pipe(effect.fail("boom"), effect.repeat(schedule.recurs(3)))
    with pytest.raises(Exception, match="boom"):
        effect.run_sync(eff)


def test_repeat_with_typed_failure() -> None:
    """repeat preserves the typed error channel E."""
    eff: effect.Effect[int, str, effect.Never] = pipe(
        effect.fail("typed-error"),
        effect.repeat(schedule.recurs(1)),
    )
    exit_ = effect.run_sync_exit(eff)
    match exit_:
        case effect.Failure(e):
            assert e == "typed-error"
        case effect.Success(_):
            raise AssertionError("Expected failure")  # noqa: EM101


# ============================================================================
# Service requirements
# ============================================================================


class Greeter:
    def __init__(self, name: str) -> None:
        self.name = name

    def greet(self) -> str:
        return f"hello, {self.name}"


def test_repeat_propagates_service_requirement() -> None:
    """R from the inner effect is preserved in the repeat return type."""
    c = Counter()

    def _body(g: Greeter) -> str:
        c.inc()
        return g.greet()

    eff = pipe(
        effect.service(Greeter),
        effect.flat_map(lambda g: effect.sync(lambda: _body(g))),
        effect.repeat(schedule.recurs(2)),
        effect.provide(context.make((Greeter, Greeter("world")))),
    )
    result = effect.run_sync(eff)
    assert result == "hello, world"
    assert c.n == 3  # noqa: PLR2004


# ============================================================================
# Type inference
# ============================================================================


def test_repeat_type_inference() -> None:
    """Hover over `result` — Pyright should show Effect[int, Never, Never]."""
    result = pipe(
        effect.succeed(42),
        effect.repeat(schedule.recurs(1)),
    )
    assert effect.run_sync(result) == 42  # noqa: PLR2004
