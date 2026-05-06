"""
Effect repetition — repeat effects according to a Schedule.
"""

from datetime import UTC, datetime
from typing import Any, Never, Protocol, cast

from pyfect.primitives import Effect, FlatMap, Sleep, Succeed, Suspend
from pyfect.schedule import Done, Schedule


def _now() -> datetime:
    return datetime.now(tz=UTC)


# ============================================================================
# repeat
# ============================================================================


class RepeatCallable[R2](Protocol):
    """Pipe-form of repeat — bind a schedule to any effect."""

    def __call__[A, E, R](self, eff: Effect[A, E, R]) -> Effect[A, E, R | R2]: ...


def _repeat_impl[A, E, R, R2](
    effect: Effect[A, E, R],
    schedule: Schedule[Any, Any, R2],
) -> Effect[A, E, R | R2]:
    def _run(state: Any) -> Effect[A, E, R | R2]:
        return cast(
            Effect[A, E, R | R2],
            FlatMap(effect, lambda a: _step(a, state)),
        )

    def _step(a: Any, state: Any) -> Effect[A, E, R | R2]:
        return cast(
            Effect[A, E, R | R2],
            FlatMap(schedule.step(_now(), a, state), lambda r: _decide(r, a)),
        )

    def _decide(r: Any, last: Any) -> Effect[A, E, R | R2]:
        new_state, _, decision = r
        if isinstance(decision, Done):
            return cast(Effect[A, E, R | R2], Succeed(last))

        def _after_sleep(_: None) -> Effect[A, E, R | R2]:
            return cast(Effect[A, E, R | R2], Suspend(lambda: _run(new_state)))

        return cast(
            Effect[A, E, R | R2],
            FlatMap(cast(Effect[None, Never, Never], Sleep(decision.delay)), _after_sleep),
        )

    return cast(Effect[A, E, R | R2], FlatMap(effect, lambda a: _step(a, schedule.initial)))


def repeat[In, R2](schedule: Schedule[Any, In, R2]) -> RepeatCallable[R2]:
    """
    Repeat an effect according to a schedule, returning the last success value.

    The effect runs initially, then the schedule decides whether to continue.
    Stops on the first failure, propagating the error. On completion, returns
    the last value produced by the effect.

    Designed for use with pipe:

    Example:
        ```python
        from pyfect import effect, schedule
        from pyfect.pipe import pipe

        program = pipe(
            effect.sync(lambda: print("tick")),
            effect.repeat(schedule.recurs(2)),
        )
        effect.run_sync(program)  # prints "tick" 3 times, returns None
        ```
    """

    def _apply(eff: Any) -> Any:
        return _repeat_impl(eff, schedule)

    return cast(RepeatCallable[R2], _apply)


__all__ = [
    "RepeatCallable",
    "repeat",
]
