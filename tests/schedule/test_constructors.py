"""Tests for built-in schedule constructors."""

from datetime import UTC, datetime, timedelta

import pytest

from pyfect import effect, schedule
from pyfect.schedule import Continue, Done

# ============================================================================
# Helpers
# ============================================================================

_NOW = datetime(2024, 1, 1, tzinfo=UTC)
_1S = timedelta(seconds=1)


def _step(sched, input_val, state, now=_NOW):
    """Run one step and return (new_state, out, decision)."""
    return effect.run_sync(sched.step(now, input_val, state))


def _steps(sched, n, input_val=None, now=_NOW):
    """Run up to n steps, stop early on Done. Returns list of (out, decision)."""
    state = sched.initial
    results = []
    for _ in range(n):
        state, out, decision = _step(sched, input_val, state, now)
        results.append((out, decision))
        if isinstance(decision, Done):
            break
    return results


# ============================================================================
# Done singleton
# ============================================================================


def test_done_is_singleton() -> None:
    assert Done() is Done()


def test_done_identity_after_multiple_instantiations() -> None:
    a, b, c = Done(), Done(), Done()
    assert a is b is c


def test_done_isinstance() -> None:
    assert isinstance(Done(), Done)


def test_done_repr() -> None:
    assert repr(Done()) == "Done()"


# ============================================================================
# forever
# ============================================================================


def test_forever_always_continues() -> None:
    results = _steps(schedule.forever, 10)
    assert all(isinstance(d, Continue) for _, d in results)
    assert len(results) == 10  # noqa: PLR2004


def test_forever_zero_delay() -> None:
    results = _steps(schedule.forever, 5)
    assert all(d.delay == timedelta(0) for _, d in results)


def test_forever_output_is_recurrence_count() -> None:
    results = _steps(schedule.forever, 5)
    assert [out for out, _ in results] == [0, 1, 2, 3, 4]


def test_forever_type_inference() -> None:
    """Hover over sched — should show Schedule[int]."""
    sched = schedule.forever
    _, out, _ = _step(sched, None, sched.initial)
    assert out == 0


# ============================================================================
# once
# ============================================================================


def test_once_first_step_continues() -> None:
    _, _, decision = _step(schedule.once, None, schedule.once.initial)
    assert isinstance(decision, Continue)
    assert decision.delay == timedelta(0)


def test_once_second_step_is_done() -> None:
    state, _, _ = _step(schedule.once, None, schedule.once.initial)
    _, _, decision = _step(schedule.once, None, state)
    assert isinstance(decision, Done)


def test_once_exactly_one_continue() -> None:
    results = _steps(schedule.once, 10)
    continues = [r for r in results if isinstance(r[1], Continue)]
    dones = [r for r in results if isinstance(r[1], Done)]
    assert len(continues) == 1
    assert len(dones) == 1


def test_once_type_inference() -> None:
    """Hover over sched — should show Schedule[None]."""
    sched = schedule.once
    assert sched.initial is False


# ============================================================================
# recurs
# ============================================================================


def test_recurs_zero_is_immediately_done() -> None:
    results = _steps(schedule.recurs(0), 5)
    assert len(results) == 1
    assert isinstance(results[0][1], Done)


def test_recurs_n_continues_exactly_n_times() -> None:
    for n in [1, 3, 5, 10]:
        results = _steps(schedule.recurs(n), n + 5)
        continues = [r for r in results if isinstance(r[1], Continue)]
        dones = [r for r in results if isinstance(r[1], Done)]
        assert len(continues) == n, f"recurs({n}) should Continue {n} times"
        assert len(dones) == 1


def test_recurs_no_delay() -> None:
    results = _steps(schedule.recurs(4), 4)
    for _, d in results:
        if isinstance(d, Continue):
            assert d.delay == timedelta(0)


def test_recurs_output_is_recurrence_count() -> None:
    results = _steps(schedule.recurs(4), 5)
    counts = [out for out, d in results if isinstance(d, Continue)]
    assert counts == [0, 1, 2, 3]


def test_recurs_type_inference() -> None:
    """Hover over sched — should show Schedule[int]."""
    sched = schedule.recurs(5)
    assert sched.initial == 0


# ============================================================================
# spaced
# ============================================================================


def test_spaced_always_continues() -> None:
    results = _steps(schedule.spaced(_1S), 8)
    assert len(results) == 8  # noqa: PLR2004
    assert all(isinstance(d, Continue) for _, d in results)


def test_spaced_delay_is_constant() -> None:
    d = timedelta(milliseconds=250)
    results = _steps(schedule.spaced(d), 5)
    for _, dec in results:
        assert isinstance(dec, Continue)
        assert dec.delay == d


def test_spaced_output_is_recurrence_count() -> None:
    results = _steps(schedule.spaced(_1S), 4)
    assert [out for out, _ in results] == [0, 1, 2, 3]


def test_spaced_type_inference() -> None:
    """Hover over sched — should show Schedule[int]."""
    sched = schedule.spaced(timedelta(seconds=2))
    assert sched.initial == 0


# ============================================================================
# fixed
# ============================================================================


def test_fixed_first_step_delay_equals_interval() -> None:
    sched = schedule.fixed(_1S)
    # T0 is set to _NOW on first call; next window = _NOW + 1s; elapsed = 0 → delay = 1s
    _, _, decision = _step(sched, None, sched.initial, now=_NOW)
    assert isinstance(decision, Continue)
    assert decision.delay == _1S


def test_fixed_accounts_for_execution_time() -> None:
    sched = schedule.fixed(_1S)
    # First step sets T0 = _NOW
    state, _, _ = _step(sched, None, sched.initial, now=_NOW)
    # Effect took 0.8s; next window = T0 + 2s = _NOW + 2s; delay = 2s - 0.8s = 1.2s
    t_after = _NOW + timedelta(milliseconds=800)
    _, _, decision = _step(sched, None, state, now=t_after)
    assert isinstance(decision, Continue)
    assert abs(decision.delay.total_seconds() - 1.2) < 0.001  # noqa: PLR2004


def test_fixed_no_pileup_when_overdue() -> None:
    sched = schedule.fixed(_1S)
    state, _, _ = _step(sched, None, sched.initial, now=_NOW)
    # Effect took 2.5s — overran two windows; next fire is immediate
    t_overdue = _NOW + timedelta(seconds=2, milliseconds=500)
    _, _, decision = _step(sched, None, state, now=t_overdue)
    assert isinstance(decision, Continue)
    assert decision.delay == timedelta(0)


def test_fixed_always_continues() -> None:
    results = _steps(schedule.fixed(timedelta(milliseconds=50)), 6)
    assert all(isinstance(d, Continue) for _, d in results)


def test_fixed_type_inference() -> None:
    """Hover over sched — should show Schedule[int]."""
    sched = schedule.fixed(timedelta(seconds=1))
    count, t0 = sched.initial
    assert count == 0
    assert t0 is None


# ============================================================================
# exponential
# ============================================================================


def test_exponential_default_factor_doubles_each_step() -> None:
    base = timedelta(milliseconds=10)
    results = _steps(schedule.exponential(base), 6)
    delays = [d.delay.total_seconds() for _, d in results]
    base_s = base.total_seconds()
    expected = [base_s * (2**i) for i in range(6)]
    assert delays == pytest.approx(expected)


def test_exponential_custom_factor() -> None:
    base = timedelta(seconds=1)
    results = _steps(schedule.exponential(base, factor=3.0), 4)
    delays = [d.delay.total_seconds() for _, d in results]
    assert delays == pytest.approx([1.0, 3.0, 9.0, 27.0])


def test_exponential_output_is_current_delay() -> None:
    results = _steps(schedule.exponential(timedelta(milliseconds=10)), 4)
    for out, decision in results:
        assert isinstance(decision, Continue)
        assert out == decision.delay


def test_exponential_always_continues() -> None:
    results = _steps(schedule.exponential(timedelta(milliseconds=1)), 8)
    assert all(isinstance(d, Continue) for _, d in results)


def test_exponential_type_inference() -> None:
    """Hover over sched — should show Schedule[timedelta]."""
    sched = schedule.exponential(timedelta(milliseconds=10))
    assert sched.initial == 0


# ============================================================================
# fibonacci
# ============================================================================


def test_fibonacci_sequence() -> None:
    base = timedelta(seconds=1)
    results = _steps(schedule.fibonacci(base), 7)
    delays = [d.delay.total_seconds() for _, d in results]
    assert delays == pytest.approx([1, 1, 2, 3, 5, 8, 13])


def test_fibonacci_output_is_current_delay() -> None:
    results = _steps(schedule.fibonacci(timedelta(milliseconds=100)), 5)
    for out, decision in results:
        assert isinstance(decision, Continue)
        assert out == decision.delay


def test_fibonacci_always_continues() -> None:
    results = _steps(schedule.fibonacci(timedelta(milliseconds=1)), 8)
    assert all(isinstance(d, Continue) for _, d in results)


def test_fibonacci_starts_at_base_twice() -> None:
    base = timedelta(seconds=2)
    results = _steps(schedule.fibonacci(base), 3)
    delays = [d.delay for _, d in results]
    assert delays[0] == base
    assert delays[1] == base  # second step is also base


def test_fibonacci_type_inference() -> None:
    """Hover over sched — should show Schedule[timedelta]."""
    sched = schedule.fibonacci(timedelta(seconds=1))
    a, b = sched.initial
    assert a == b == timedelta(seconds=1)
