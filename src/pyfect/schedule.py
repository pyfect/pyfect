"""
Schedule - composable, typed recurrence policies.

A Schedule[Out, In, R] describes when and how often to repeat or retry
an effect. It consumes In values (the success value A for repeat, the
error E for retry) and produces Out values at each step, deciding whether
to continue (with a delay) or stop.

Schedules compose via union, intersect, and_then, and can be modified
with jittered, while_input, while_output, and tap_output.
"""

import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, ClassVar, Never, cast

from pyfect.primitives import Effect, FlatMap, Succeed


class _Phase(Enum):
    FIRST = auto()
    SECOND = auto()


# ============================================================================
# Decision types
# ============================================================================


@dataclass(frozen=True)
class Continue:
    """The schedule wants to continue after waiting for delay."""

    delay: timedelta


class Done:
    """The schedule has finished — no more recurrences. Singleton: Done() is Done()."""

    __slots__ = ()
    _instance: ClassVar["Done | None"] = None

    def __new__(cls) -> "Done":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "Done()"


ScheduleDecision = Continue | Done


# ============================================================================
# Schedule type
# ============================================================================


@dataclass(frozen=True)
class Schedule[Out, In = Any, R = Never]:
    """
    A composable, typed recurrence policy.

    Out: value produced at each step (e.g. recurrence count, current delay)
    In:  value consumed at each step (A for repeat, E for retry)
    R:   required services for the step effect (Never for all built-ins)

    The step function receives the current time, the latest In value, and
    the opaque internal state; it returns an Effect carrying the next state,
    the Out value, and a ScheduleDecision.

    Use effect.repeat or effect.retry to run a schedule against an effect.
    """

    initial: Any
    step: Callable[[datetime, Any, Any], Effect[tuple[Any, Any, ScheduleDecision], Never, R]]


# ============================================================================
# Built-in constructors
# ============================================================================


def _forever_step(_now: datetime, _: Any, count: int) -> Effect[Any, Never, Never]:
    return Succeed((count + 1, count, Continue(timedelta(0))))


forever: Schedule[int] = Schedule(initial=0, step=_forever_step)
"""Repeats indefinitely with no delay, producing the recurrence count."""


def _once_step(_now: datetime, _: Any, done: bool) -> Effect[Any, Never, Never]:
    if not done:
        return Succeed((True, None, Continue(timedelta(0))))
    return Succeed((True, None, Done()))


once: Schedule[None] = Schedule(initial=False, step=_once_step)
"""Recurs exactly once after the initial execution."""


def recurs(n: int) -> Schedule[int]:
    """Repeats n additional times after the initial execution, with no delay."""

    def _step(now: datetime, _: Any, count: int) -> Effect[Any, Never, Never]:
        if count < n:
            return Succeed((count + 1, count, Continue(timedelta(0))))
        return Succeed((count, count, Done()))

    return Schedule(initial=0, step=_step)


def spaced(duration: timedelta) -> Schedule[int]:
    """
    Repeats indefinitely, waiting duration after the end of each run.

    The delay is measured from when the previous run completed, so the
    total time between run starts is duration + execution time.
    """

    def _step(now: datetime, _: Any, count: int) -> Effect[Any, Never, Never]:
        return Succeed((count + 1, count, Continue(duration)))

    return Schedule(initial=0, step=_step)


def fixed(duration: timedelta) -> Schedule[int]:
    """
    Repeats at fixed wall-clock intervals.

    Unlike spaced, the delay accounts for execution time so runs target
    a consistent cadence. If a run takes longer than the interval, the
    next run starts immediately (no pileup).
    """

    def _step(
        now: datetime, _: Any, state: tuple[int, datetime | None]
    ) -> Effect[Any, Never, Never]:
        count, t0 = state
        ref = t0 if t0 is not None else now
        next_window = ref + (count + 1) * duration
        delay = max(timedelta(0), next_window - now)
        return Succeed(((count + 1, ref), count, Continue(delay)))

    return Schedule(initial=(0, None), step=_step)


def exponential(base: timedelta, factor: float = 2.0) -> Schedule[timedelta]:
    """
    Repeats with exponentially increasing delays.

    Delay at attempt n = base * factor^n. Default factor is 2 (doubling).
    """

    def _step(now: datetime, _: Any, attempt: int) -> Effect[Any, Never, Never]:
        delay = timedelta(seconds=base.total_seconds() * (factor**attempt))
        return Succeed((attempt + 1, delay, Continue(delay)))

    return Schedule(initial=0, step=_step)


def fibonacci(base: timedelta) -> Schedule[timedelta]:
    """
    Repeats with delays following the Fibonacci sequence.

    Starting from (base, base), each step delay is the sum of the two
    previous delays: base, base, 2*base, 3*base, 5*base, ...
    """

    def _step(
        now: datetime, _: Any, state: tuple[timedelta, timedelta]
    ) -> Effect[Any, Never, Never]:
        a, b = state
        return Succeed(((b, a + b), a, Continue(a)))

    return Schedule(initial=(base, base), step=_step)


# ============================================================================
# Combinators
# ============================================================================


def union[Out1, Out2, In, R1, R2](
    s1: Schedule[Out1, In, R1],
    s2: Schedule[Out2, In, R2],
) -> Schedule[tuple[Out1, Out2], In, R1 | R2]:
    """
    Continue while either schedule wants to continue, using the shorter delay.

    Stops only when both schedules say Done. The canonical pattern —
    union(exponential(base), spaced(cap)) — gives exponential backoff
    that levels off at cap once delays grow past it.
    """

    def _step(now: datetime, input: Any, state: tuple[Any, Any]) -> Effect[Any, Never, R1 | R2]:
        s1_state, s2_state = state

        def _with_r2(r1: Any) -> Effect[Any, Never, R1 | R2]:
            def _merge(r2: Any) -> Effect[Any, Never, Never]:
                new_s1, out1, d1 = r1
                new_s2, out2, d2 = r2
                new_st = (new_s1, new_s2)
                out = (out1, out2)
                if isinstance(d1, Done) and isinstance(d2, Done):
                    return Succeed((new_st, out, Done()))
                if isinstance(d1, Done):
                    return Succeed((new_st, out, d2))
                if isinstance(d2, Done):
                    return Succeed((new_st, out, d1))
                return Succeed((new_st, out, Continue(min(d1.delay, d2.delay))))

            return FlatMap(s2.step(now, input, s2_state), _merge)

        return FlatMap(s1.step(now, input, s1_state), _with_r2)

    return Schedule(initial=(s1.initial, s2.initial), step=cast(Any, _step))


def intersect[Out1, Out2, In, R1, R2](
    s1: Schedule[Out1, In, R1],
    s2: Schedule[Out2, In, R2],
) -> Schedule[tuple[Out1, Out2], In, R1 | R2]:
    """
    Continue only while both schedules want to continue, using the longer delay.

    Stops as soon as either schedule says Done. The canonical retry pattern:
    intersect(exponential(base), recurs(n)) gives exponential backoff
    capped at n attempts.
    """

    def _step(now: datetime, input: Any, state: tuple[Any, Any]) -> Effect[Any, Never, R1 | R2]:
        s1_state, s2_state = state

        def _with_r2(r1: Any) -> Effect[Any, Never, R1 | R2]:
            def _merge(r2: Any) -> Effect[Any, Never, Never]:
                new_s1, out1, d1 = r1
                new_s2, out2, d2 = r2
                new_st = (new_s1, new_s2)
                out = (out1, out2)
                if isinstance(d1, Done) or isinstance(d2, Done):
                    return Succeed((new_st, out, Done()))
                return Succeed((new_st, out, Continue(max(d1.delay, d2.delay))))

            return FlatMap(s2.step(now, input, s2_state), _merge)

        return FlatMap(s1.step(now, input, s1_state), _with_r2)

    return Schedule(initial=(s1.initial, s2.initial), step=cast(Any, _step))


def and_then[Out1, Out2, In, R1, R2](
    s1: Schedule[Out1, In, R1],
    s2: Schedule[Out2, In, R2],
) -> Schedule[Out1 | Out2, In, R1 | R2]:
    """
    Run s1 fully, then switch to s2 for the remainder.

    When s1 says Done, s2's first step runs immediately at the transition
    point. Example: and_then(recurs(5), spaced(1s)) gives 5 immediate
    retries then retries every second indefinitely.
    """

    def _step(now: datetime, input: Any, state: tuple[_Phase, Any]) -> Effect[Any, Never, R1 | R2]:
        phase, s_state = state

        if phase == _Phase.FIRST:

            def _handle_first(r: Any) -> Effect[Any, Never, R1 | R2]:
                new_s1, out, decision = r
                if isinstance(decision, Done):

                    def _start_s2(r2: Any) -> Effect[Any, Never, Never]:
                        new_s2, out2, d2 = r2
                        return Succeed(((_Phase.SECOND, new_s2), out2, d2))

                    return FlatMap(s2.step(now, input, s2.initial), _start_s2)
                return Succeed(((_Phase.FIRST, new_s1), out, decision))

            return FlatMap(s1.step(now, input, s_state), _handle_first)

        def _handle_second(r: Any) -> Effect[Any, Never, Never]:
            new_s2, out, decision = r
            return Succeed(((_Phase.SECOND, new_s2), out, decision))

        return FlatMap(s2.step(now, input, s_state), _handle_second)

    return Schedule(initial=(_Phase.FIRST, s1.initial), step=cast(Any, _step))


def jittered[Out, In, R](
    schedule: Schedule[Out, In, R],
    min_factor: float = 0.0,
    max_factor: float = 1.0,
) -> Schedule[Out, In, R]:
    """
    Multiply each delay by a random factor in [1 + min_factor, 1 + max_factor].

    Prevents thundering-herd problems when many clients retry simultaneously.
    The recommended range is jittered(0.0, 1.0), which multiplies delays by
    a uniform random factor in [1.0, 2.0].
    """

    def _step(now: datetime, input: Any, state: Any) -> Effect[Any, Never, R]:
        def _add_jitter(r: Any) -> Effect[Any, Never, Never]:
            new_state, out, decision = r
            if isinstance(decision, Done):
                return Succeed((new_state, out, Done()))
            factor = 1.0 + random.uniform(min_factor, max_factor)
            jittered_delay = timedelta(seconds=decision.delay.total_seconds() * factor)
            return Succeed((new_state, out, Continue(jittered_delay)))

        return FlatMap(schedule.step(now, input, state), _add_jitter)

    return Schedule(initial=schedule.initial, step=cast(Any, _step))


def while_input[Out, In, R](
    schedule: Schedule[Out, In, R],
    predicate: Callable[[In], bool],
) -> Schedule[Out, In, R]:
    """
    Stop the schedule when predicate(input) returns False.

    For retry, In is the error E — this combinator lets you stop retrying
    on specific error types (e.g. stop on AuthError, keep retrying on
    ConnectionError).
    """

    def _step(now: datetime, input: Any, state: Any) -> Effect[Any, Never, R]:
        def _check(r: Any) -> Effect[Any, Never, Never]:
            new_state, out, decision = r
            if isinstance(decision, Done) or not predicate(input):
                return Succeed((new_state, out, Done()))
            return Succeed((new_state, out, decision))

        return FlatMap(schedule.step(now, input, state), _check)

    return Schedule(initial=schedule.initial, step=cast(Any, _step))


def while_output[Out, In, R](
    schedule: Schedule[Out, In, R],
    predicate: Callable[[Out], bool],
) -> Schedule[Out, In, R]:
    """
    Stop the schedule when predicate(output) returns False.

    Example: while_output(forever, lambda n: n < 5) is equivalent to
    recurs(5) but driven by the output value instead of a counter.
    """

    def _step(now: datetime, input: Any, state: Any) -> Effect[Any, Never, R]:
        def _check(r: Any) -> Effect[Any, Never, Never]:
            new_state, out, decision = r
            if isinstance(decision, Done) or not predicate(out):
                return Succeed((new_state, out, Done()))
            return Succeed((new_state, out, decision))

        return FlatMap(schedule.step(now, input, state), _check)

    return Schedule(initial=schedule.initial, step=cast(Any, _step))


def tap_output[Out, In, R, R2](
    schedule: Schedule[Out, In, R],
    f: Callable[[Out], Effect[Any, Never, R2]],
) -> Schedule[Out, In, R | R2]:
    """
    Run an effectful side effect on each output without modifying behavior.

    Useful for logging retry attempts or recording metrics at each step.
    """

    def _step(now: datetime, input: Any, state: Any) -> Effect[Any, Never, R | R2]:
        def _tap(r: Any) -> Effect[Any, Never, R2]:
            new_state, out, decision = r
            return FlatMap(f(out), lambda _: Succeed((new_state, out, decision)))

        return FlatMap(schedule.step(now, input, state), _tap)

    return Schedule(initial=schedule.initial, step=cast(Any, _step))


__all__ = [
    "Continue",
    "Done",
    "Schedule",
    "ScheduleDecision",
    "and_then",
    "exponential",
    "fibonacci",
    "fixed",
    "forever",
    "intersect",
    "jittered",
    "once",
    "recurs",
    "spaced",
    "tap_output",
    "union",
    "while_input",
    "while_output",
]
