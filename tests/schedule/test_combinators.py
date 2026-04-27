"""Tests for schedule combinators."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch

import pytest

from pyfect import context, effect, schedule
from pyfect.pipe import pipe
from pyfect.primitives import FlatMap, Service, Succeed
from pyfect.schedule import Continue, Done, Schedule

# ============================================================================
# Helpers
# ============================================================================

_NOW = datetime(2024, 1, 1, tzinfo=UTC)
_1S = timedelta(seconds=1)
_2S = timedelta(seconds=2)


def _step(sched, input_val, state, now=_NOW):
    """Run one step, return (new_state, out, decision)."""
    return effect.run_sync(sched.step(now, input_val, state))


def _step_provided(sched, input_val, state, ctx, now=_NOW):
    """Run one step with a provided context (for schedules with R != Never)."""
    step_eff = sched.step(now, input_val, state)
    return effect.run_sync(pipe(step_eff, effect.provide(ctx)))


def _steps(sched, n, input_val=None, now=_NOW):
    """Run up to n steps, returning list of (out, decision)."""
    state = sched.initial
    results = []
    for _ in range(n):
        state, out, decision = _step(sched, input_val, state, now)
        results.append((out, decision))
        if isinstance(decision, Done):
            break
    return results


def _steps_with_inputs(sched, inputs, now=_NOW):
    """Run steps with a specific list of inputs (one per step)."""
    state = sched.initial
    results = []
    for inp in inputs:
        state, out, decision = _step(sched, inp, state, now)
        results.append((out, decision))
        if isinstance(decision, Done):
            break
    return results


# ============================================================================
# union
# ============================================================================


def test_union_continues_while_either_continues() -> None:
    # recurs(2) stops after 2, forever never stops — union should run forever
    sched = schedule.union(schedule.recurs(2), schedule.forever)
    results = _steps(sched, 6)
    # All 6 steps continue since forever keeps going
    assert all(isinstance(d, Continue) for _, d in results)


def test_union_stops_only_when_both_done() -> None:
    # Both recurs(2) — union stops after 2
    sched = schedule.union(schedule.recurs(2), schedule.recurs(2))
    results = _steps(sched, 10)
    continues = [r for r in results if isinstance(r[1], Continue)]
    dones = [r for r in results if isinstance(r[1], Done)]
    assert len(continues) == 2  # noqa: PLR2004
    assert len(dones) == 1


def test_union_uses_shorter_delay() -> None:
    sched = schedule.union(schedule.spaced(_2S), schedule.spaced(_1S))
    results = _steps(sched, 3)
    for _, decision in results:
        assert isinstance(decision, Continue)
        assert decision.delay == _1S


def test_union_uses_s1_delay_when_s2_is_done() -> None:
    # spaced(2s) continues; recurs(1) stops after 1 — after recurs done,
    # union should use spaced's delay (s1 still going, s2 done)
    sched = schedule.union(schedule.spaced(_2S), schedule.recurs(1))
    state = sched.initial
    # Step 1: both continue — spaced delay=2s, recurs delay=0s → min = 0s
    state, _, d1 = _step(sched, None, state)
    assert isinstance(d1, Continue)
    assert d1.delay == timedelta(0)
    # Step 2: spaced continues at 2s, recurs is Done → use spaced's delay
    _, _, d2 = _step(sched, None, state)
    assert isinstance(d2, Continue)
    assert d2.delay == _2S


def test_union_uses_continuing_schedules_delay_when_one_is_done() -> None:
    # recurs(1) stops after 1 step; spaced(2s) continues — after recurs done,
    # union should use spaced's delay
    sched = schedule.union(schedule.recurs(1), schedule.spaced(_2S))
    state = sched.initial
    # Step 1: both continue — recurs delay=0s, spaced delay=2s → min = 0s
    state, _, d1 = _step(sched, None, state)
    assert isinstance(d1, Continue)
    assert d1.delay == timedelta(0)
    # Step 2: recurs is Done, spaced continues at 2s → use spaced's delay
    _, _, d2 = _step(sched, None, state)
    assert isinstance(d2, Continue)
    assert d2.delay == _2S


def test_union_type_inference() -> None:
    """Hover over sched — should show Schedule[tuple[int, int], Any, Never]."""
    sched = schedule.union(schedule.recurs(3), schedule.forever)
    _, (out1, out2), _ = _step(sched, None, sched.initial)
    assert out1 == 0
    assert out2 == 0


def test_union_exponential_capped_by_spaced() -> None:
    # union(exponential, spaced(cap)) → delays follow exponential until they
    # exceed cap, then settle at cap
    cap = timedelta(seconds=1)
    sched = schedule.union(
        schedule.exponential(timedelta(milliseconds=100)),
        schedule.spaced(cap),
    )
    results = _steps(sched, 6)
    delays = [d.delay for _, d in results if isinstance(d, Continue)]
    # First few delays come from exponential (< 1s), later from spaced (1s)
    assert delays[0] < cap  # exponential starts small
    assert all(d <= cap for d in delays)  # never exceeds cap


# ============================================================================
# intersect
# ============================================================================


def test_intersect_stops_when_either_done() -> None:
    # recurs(3) + recurs(5) → stops at 3 (the shorter one)
    sched = schedule.intersect(schedule.recurs(3), schedule.recurs(5))
    results = _steps(sched, 10)
    continues = [r for r in results if isinstance(r[1], Continue)]
    dones = [r for r in results if isinstance(r[1], Done)]
    assert len(continues) == 3  # noqa: PLR2004
    assert len(dones) == 1


def test_intersect_uses_longer_delay() -> None:
    sched = schedule.intersect(schedule.spaced(_1S), schedule.spaced(_2S))
    results = _steps(sched, 3)
    for _, decision in results:
        assert isinstance(decision, Continue)
        assert decision.delay == _2S


def test_intersect_canonical_exponential_with_cap() -> None:
    # intersect(exponential, recurs(3)) → exponential backoff, stops after 3
    base = timedelta(milliseconds=10)
    sched = schedule.intersect(schedule.exponential(base), schedule.recurs(3))
    results = _steps(sched, 10)
    continues = [r for r in results if isinstance(r[1], Continue)]
    dones = [r for r in results if isinstance(r[1], Done)]
    assert len(continues) == 3  # noqa: PLR2004
    assert len(dones) == 1
    # Delays follow exponential
    delays = [d.delay.total_seconds() for _, d in continues]
    base_s = base.total_seconds()
    assert delays == pytest.approx([base_s, base_s * 2, base_s * 4])


def test_intersect_type_inference() -> None:
    """Hover over sched — should show Schedule[tuple[timedelta, int], Any, Never]."""
    sched = schedule.intersect(
        schedule.exponential(timedelta(milliseconds=10)),
        schedule.recurs(5),
    )
    _, (exp_out, rec_out), _ = _step(sched, None, sched.initial)
    assert isinstance(exp_out, timedelta)
    assert isinstance(rec_out, int)


# ============================================================================
# and_then
# ============================================================================


def test_and_then_runs_s1_then_s2() -> None:
    sched = schedule.and_then(schedule.recurs(3), schedule.spaced(_1S))
    results = _steps(sched, 8)
    # Steps 1-3: recurs → Continue(0s)
    for _, decision in results[:3]:
        assert isinstance(decision, Continue)
        assert decision.delay == timedelta(0)
    # Step 4: transition — recurs Done, immediately run spaced → Continue(1s)
    _, d4 = results[3]
    assert isinstance(d4, Continue)
    assert d4.delay == _1S


def test_and_then_continues_with_s2_indefinitely() -> None:
    sched = schedule.and_then(schedule.recurs(2), schedule.forever)
    results = _steps(sched, 10)
    assert all(isinstance(d, Continue) for _, d in results)


def test_and_then_s2_done_terminates() -> None:
    sched = schedule.and_then(schedule.recurs(2), schedule.recurs(2))
    results = _steps(sched, 10)
    continues = [r for r in results if isinstance(r[1], Continue)]
    dones = [r for r in results if isinstance(r[1], Done)]
    # recurs(2) + recurs(2) → 2 from s1 + 2 from s2 = 4 continues
    assert len(continues) == 4  # noqa: PLR2004
    assert len(dones) == 1


def test_and_then_immediate_s1_done_goes_to_s2() -> None:
    # and_then(recurs(0), spaced(1s)) → s1 is immediately done,
    # first step should already be s2's Continue(1s)
    sched = schedule.and_then(schedule.recurs(0), schedule.spaced(_1S))
    _, _, decision = _step(sched, None, sched.initial)
    assert isinstance(decision, Continue)
    assert decision.delay == _1S


def test_and_then_type_inference() -> None:
    """Hover over sched — should show Schedule[int | timedelta, Any, Never]."""
    sched = schedule.and_then(
        schedule.recurs(2),
        schedule.exponential(timedelta(milliseconds=10)),
    )
    assert sched is not None


# ============================================================================
# jittered
# ============================================================================


def test_jittered_multiplies_delay_by_factor() -> None:
    base_delay = timedelta(seconds=2)
    sched = schedule.jittered(schedule.spaced(base_delay), min_factor=0.0, max_factor=1.0)
    with patch("pyfect.schedule.random.uniform", return_value=0.5):
        _, _, decision = _step(sched, None, sched.initial)
    assert isinstance(decision, Continue)
    # 2s * (1 + 0.5) = 3s
    assert abs(decision.delay.total_seconds() - 3.0) < 0.001  # noqa: PLR2004


def test_jittered_min_factor_one_doubles_delay() -> None:
    base_delay = timedelta(seconds=1)
    sched = schedule.jittered(schedule.spaced(base_delay), min_factor=1.0, max_factor=1.0)
    with patch("pyfect.schedule.random.uniform", return_value=1.0):
        _, _, decision = _step(sched, None, sched.initial)
    assert isinstance(decision, Continue)
    # 1s * (1 + 1) = 2s
    assert abs(decision.delay.total_seconds() - 2.0) < 0.001  # noqa: PLR2004


def test_jittered_passes_through_done() -> None:
    sched = schedule.jittered(schedule.recurs(0), 0.0, 1.0)
    _, _, decision = _step(sched, None, sched.initial)
    assert isinstance(decision, Done)


def test_jittered_zero_delay_stays_zero() -> None:
    # Jitter of 0-delay (e.g. recurs) stays 0 regardless of factor
    sched = schedule.jittered(schedule.recurs(3), 0.0, 1.0)
    results = _steps(sched, 3)
    for _, d in results:
        if isinstance(d, Continue):
            assert d.delay == timedelta(0)


def test_jittered_preserves_out_and_state() -> None:
    sched = schedule.jittered(schedule.recurs(3), 0.0, 1.0)
    results = _steps(sched, 3)
    counts = [out for out, d in results if isinstance(d, Continue)]
    assert counts == [0, 1, 2]


def test_jittered_type_inference() -> None:
    """Hover over sched — should show Schedule[int, Any, Never]."""
    sched = schedule.jittered(schedule.recurs(5))
    assert sched is not None


# ============================================================================
# while_input
# ============================================================================


def test_while_input_continues_when_predicate_true() -> None:
    sched = schedule.while_input(schedule.forever, lambda s: s != "stop")
    results = _steps_with_inputs(sched, ["go", "go", "go"])
    assert all(isinstance(d, Continue) for _, d in results)


def test_while_input_stops_when_predicate_false() -> None:
    sched = schedule.while_input(schedule.forever, lambda s: s != "stop")
    results = _steps_with_inputs(sched, ["go", "stop", "go"])
    assert isinstance(results[0][1], Continue)
    assert isinstance(results[1][1], Done)
    assert len(results) == 2  # noqa: PLR2004


def test_while_input_stops_on_first_false() -> None:
    sched = schedule.while_input(schedule.forever, lambda n: n < 3)  # noqa: PLR2004
    results = _steps_with_inputs(sched, [0, 1, 2, 3, 4])
    assert len(results) == 4  # noqa: PLR2004  — 0,1,2 Continue; 3 Done
    assert isinstance(results[3][1], Done)


def test_while_input_works_with_typed_errors() -> None:
    class ConnectionError(Exception):
        pass

    class AuthError(Exception):
        pass

    # Only retry on ConnectionError, not AuthError
    sched = schedule.while_input(
        schedule.recurs(10),
        lambda e: isinstance(e, ConnectionError),
    )
    conn_err = ConnectionError()
    auth_err = AuthError()

    state = sched.initial
    state, _, d1 = _step(sched, conn_err, state)
    assert isinstance(d1, Continue)

    _, _, d2 = _step(sched, auth_err, state)
    assert isinstance(d2, Done)


def test_while_input_type_inference() -> None:
    """Hover over sched — should show Schedule[int, Any, Never]."""
    sched = schedule.while_input(schedule.forever, lambda x: x is not None)
    assert sched is not None


# ============================================================================
# while_output
# ============================================================================


def test_while_output_continues_while_predicate_true() -> None:
    sched = schedule.while_output(schedule.forever, lambda n: n < 3)  # noqa: PLR2004
    results = _steps(sched, 10)
    continues = [r for r in results if isinstance(r[1], Continue)]
    dones = [r for r in results if isinstance(r[1], Done)]
    assert len(continues) == 3  # noqa: PLR2004  — outputs 0, 1, 2 pass; 3 fails
    assert len(dones) == 1


def test_while_output_equivalent_to_recurs() -> None:
    # while_output(forever, n < 5) should behave like recurs(5)
    sched_while = schedule.while_output(schedule.forever, lambda n: n < 5)  # noqa: PLR2004
    sched_recurs = schedule.recurs(5)
    results_while = _steps(sched_while, 10)
    results_recurs = _steps(sched_recurs, 10)
    assert len(results_while) == len(results_recurs)


def test_while_output_stops_on_first_false() -> None:
    sched = schedule.while_output(schedule.forever, lambda n: n != 2)  # noqa: PLR2004
    results = _steps(sched, 10)
    # Outputs 0, 1 pass; output 2 triggers Done
    assert len(results) == 3  # noqa: PLR2004
    assert isinstance(results[2][1], Done)


def test_while_output_passes_through_done_from_inner() -> None:
    # Inner schedule already Done — while_output should not interfere
    sched = schedule.while_output(schedule.recurs(2), lambda _: True)
    results = _steps(sched, 10)
    continues = [r for r in results if isinstance(r[1], Continue)]
    dones = [r for r in results if isinstance(r[1], Done)]
    assert len(continues) == 2  # noqa: PLR2004
    assert len(dones) == 1


def test_while_output_type_inference() -> None:
    """Hover over sched — should show Schedule[int, Any, Never]."""
    sched = schedule.while_output(schedule.forever, lambda n: n < 10)  # noqa: PLR2004
    assert sched is not None


# ============================================================================
# tap_output
# ============================================================================


def test_tap_output_runs_side_effect() -> None:
    log: list[int] = []
    sched = schedule.tap_output(
        schedule.recurs(3),
        lambda n: effect.sync(lambda: log.append(n)),  # type: ignore[arg-type]
    )
    _steps(sched, 5)
    assert log == [0, 1, 2, 3]


def test_tap_output_does_not_change_decisions() -> None:
    log: list[int] = []
    base = schedule.recurs(3)
    tapped = schedule.tap_output(
        base,
        lambda n: effect.sync(lambda: log.append(n)),  # type: ignore[arg-type]
    )
    base_results = _steps(base, 5)
    tapped_results = _steps(tapped, 5)
    # Same number of steps and same decision types
    assert len(base_results) == len(tapped_results)
    for (_, bd), (_, td) in zip(base_results, tapped_results, strict=True):
        assert type(bd) is type(td)


def test_tap_output_runs_on_every_step_including_last() -> None:
    log: list[int] = []
    sched = schedule.tap_output(
        schedule.recurs(2),
        lambda n: effect.sync(lambda: log.append(n)),  # type: ignore[arg-type]
    )
    _steps(sched, 10)
    # Tap fires on all steps, including the Done step
    assert len(log) == 3  # noqa: PLR2004  — steps for count 0, 1, and the Done step


def test_tap_output_type_inference() -> None:
    """Hover over sched — should show Schedule[int, Any, Never]."""
    sched = schedule.tap_output(schedule.recurs(5), effect.succeed)
    assert sched is not None


# ============================================================================
# Schedule with requirements (R != Never)
# ============================================================================


@dataclass
class DelayConfig:
    delay: timedelta


def _make_service_schedule() -> Schedule[int, Any, DelayConfig]:
    """A schedule that reads its delay from a DelayConfig service."""

    def _step(now: datetime, _: Any, count: int) -> Any:
        return FlatMap(
            Service(DelayConfig),
            lambda cfg: Succeed((count + 1, count, Continue(cfg.delay))),
        )

    return Schedule(initial=0, step=_step)


def test_schedule_with_requirements_uses_service() -> None:
    sched = _make_service_schedule()
    cfg = DelayConfig(delay=timedelta(seconds=5))
    ctx = context.make((DelayConfig, cfg))

    _, out, decision = _step_provided(sched, None, sched.initial, ctx)

    assert out == 0
    assert isinstance(decision, Continue)
    assert decision.delay == timedelta(seconds=5)


def test_schedule_with_requirements_respects_service_value() -> None:
    sched = _make_service_schedule()

    for delay_s in [1, 3, 10]:
        cfg = DelayConfig(delay=timedelta(seconds=delay_s))
        ctx = context.make((DelayConfig, cfg))
        _, _, decision = _step_provided(sched, None, sched.initial, ctx)
        assert isinstance(decision, Continue)
        assert decision.delay == timedelta(seconds=delay_s)


def test_schedule_with_requirements_type_inference() -> None:
    """Hover over sched — should show Schedule[int, Any, DelayConfig]."""
    sched = _make_service_schedule()
    assert sched.initial == 0


def test_tap_output_with_service_requirement() -> None:
    """tap_output with a service-using tap propagates R to Schedule[Out, In, R | R2]."""

    @dataclass
    class Logger:
        calls: list[int]

        def log(self, n: int) -> None:
            self.calls.append(n)

    logger = Logger(calls=[])
    ctx = context.make((Logger, logger))

    sched = schedule.tap_output(
        schedule.recurs(3),
        lambda n: FlatMap(
            Service(Logger),
            lambda lg: effect.sync(lambda: lg.log(n)),
        ),
    )

    state = sched.initial
    for _ in range(4):
        step_eff = sched.step(_NOW, None, state)
        state, _, decision = effect.run_sync(pipe(step_eff, effect.provide(ctx)))
        if isinstance(decision, Done):
            break

    assert logger.calls == [0, 1, 2, 3]
