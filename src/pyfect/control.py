"""
Control flow combinators for Effect.

Provides if_, when, when_effect, unless, unless_effect, and zip.
"""

from collections.abc import Callable, Iterable
from enum import StrEnum
from typing import Any, Literal, Never, Protocol, cast, overload

import pyfect.either as either_module
import pyfect.option as option_module
from pyfect.primitives import Absorb, Effect, Fail, FlatMap, Map, Succeed, Suspend, ZipPar

# ============================================================================
# if_
# ============================================================================


@overload
def if_[A1, A2](  # pyright: ignore[reportOverlappingOverload]
    predicate: Effect[bool, Never, Never],
    *,
    on_true: Effect[A1, Never, Never],
    on_false: Effect[A2, Never, Never],
) -> Effect[A1 | A2, Never, Never]: ...


@overload
def if_[A1, A2, R1, R2, R3](  # type: ignore[overload-overlap]
    predicate: Effect[bool, Never, R1],
    *,
    on_true: Effect[A1, Never, R2],
    on_false: Effect[A2, Never, R3],
) -> Effect[A1 | A2, Never, R1 | R2 | R3]: ...


@overload
def if_[A1, A2, E1, E2, E3](
    predicate: Effect[bool, E1, Never],
    *,
    on_true: Effect[A1, E2, Never],
    on_false: Effect[A2, E3, Never],
) -> Effect[A1 | A2, E1 | E2 | E3, Never]: ...


@overload
def if_[A1, A2, E1, E2, E3, R1, R2, R3](
    predicate: Effect[bool, E1, R1],
    *,
    on_true: Effect[A1, E2, R2],
    on_false: Effect[A2, E3, R3],
) -> Effect[A1 | A2, E1 | E2 | E3, R1 | R2 | R3]: ...


def if_(
    predicate: Effect[Any, Any, Any],
    *,
    on_true: Effect[Any, Any, Any],
    on_false: Effect[Any, Any, Any],
) -> Effect[Any, Any, Any]:
    """
    Execute one of two effects based on the result of a boolean predicate effect.

    If the predicate succeeds with True, on_true is executed.
    If the predicate succeeds with False, on_false is executed.
    If the predicate fails, neither branch runs and the error propagates.

    Effects are already lazy descriptions, so no thunks are needed.

    Example:
        ```python
        from pyfect import effect

        flip = effect.if_(
            effect.sync(lambda: True),
            on_true=effect.sync(lambda: print("Heads")),
            on_false=effect.sync(lambda: print("Tails")),
        )
        effect.run_sync(flip)  # Heads
        ```
    """

    def branch(b: bool) -> Effect[Any, Any, Any]:
        return on_true if b else on_false

    return FlatMap(predicate, branch)


# ============================================================================
# when / unless
# ============================================================================


class WhenCallable(Protocol):
    def __call__[A, E, R](self, eff: Effect[A, E, R]) -> Effect[option_module.Option[A], E, R]: ...


def when(condition: Callable[[], bool]) -> WhenCallable:
    """
    Conditionally execute an effect based on a boolean thunk.

    If condition() is True, runs the effect and wraps the result in Some.
    If condition() is False, skips the effect and returns Nothing.

    Designed for use with pipe:

    Example:
        ```python
        from pyfect import effect, option, pipe

        def validate_weight(weight: float) -> effect.Effect[option.Option[float]]:
            return pipe(
                effect.succeed(weight),
                effect.when(lambda: weight >= 0),
            )

        effect.run_sync(validate_weight(100))   # Some(100)
        effect.run_sync(validate_weight(-5))    # Nothing()
        ```
    """

    def _apply(eff: Effect[Any, Any, Any]) -> Effect[Any, Any, Any]:
        return Suspend(
            lambda: (
                FlatMap(eff, lambda a: Succeed(option_module.some(a)))
                if condition()
                else Succeed(option_module.nothing())
            )
        )

    return cast(WhenCallable, _apply)


def unless(condition: Callable[[], bool]) -> WhenCallable:
    """
    Conditionally execute an effect based on the negation of a boolean thunk.

    Equivalent to when(lambda: not condition()). If condition() is False,
    runs the effect and wraps the result in Some. If condition() is True,
    skips the effect and returns Nothing.

    Designed for use with pipe:

    Example:
        ```python
        from pyfect import effect, option, pipe

        def validate_weight(weight: float) -> effect.Effect[option.Option[float]]:
            return pipe(
                effect.succeed(weight),
                effect.unless(lambda: weight < 0),
            )

        effect.run_sync(validate_weight(100))   # Some(100)
        effect.run_sync(validate_weight(-5))    # Nothing()
        ```
    """

    def _apply(eff: Effect[Any, Any, Any]) -> Effect[Any, Any, Any]:
        return Suspend(
            lambda: (
                FlatMap(eff, lambda a: Succeed(option_module.some(a)))
                if not condition()
                else Succeed(option_module.nothing())
            )
        )

    return cast(WhenCallable, _apply)


# ============================================================================
# when_effect / unless_effect
# ============================================================================


class WhenEffectCallable[E2 = Never, R2 = Never](Protocol):
    def __call__[A, E1, R1](
        self, eff: Effect[A, E1, R1]
    ) -> Effect[option_module.Option[A], E1 | E2, R1 | R2]: ...


def when_effect[E2 = Never, R2 = Never](
    condition: Effect[bool, E2, R2],
) -> WhenEffectCallable[E2, R2]:
    """
    Conditionally execute an effect based on the result of another effect.

    Runs condition first. If it produces True, runs the effect and wraps the
    result in Some. If it produces False, skips the effect and returns Nothing.

    Designed for use with pipe:

    Example:
        ```python
        from pyfect import effect, option, pipe

        is_valid = effect.sync(lambda: True)

        result = pipe(
            effect.succeed(42),
            effect.when_effect(is_valid),
        )

        effect.run_sync(result)  # Some(42)
        ```
    """

    def _apply(eff: Effect[Any, Any, Any]) -> Effect[Any, Any, Any]:
        return FlatMap(
            condition,
            lambda b: (
                FlatMap(eff, lambda a: Succeed(option_module.some(a)))
                if b
                else Succeed(option_module.nothing())
            ),
        )

    return cast(WhenEffectCallable[E2, R2], _apply)


class UnlessEffectCallable[E2 = Never, R2 = Never](Protocol):
    def __call__[A, E1, R1](
        self, eff: Effect[A, E1, R1]
    ) -> Effect[option_module.Option[A], E1 | E2, R1 | R2]: ...


def unless_effect[E2 = Never, R2 = Never](
    condition: Effect[bool, E2, R2],
) -> UnlessEffectCallable[E2, R2]:
    """
    Conditionally execute an effect based on the negation of another effect's result.

    Runs condition first. If it produces False, runs the effect and wraps the
    result in Some. If it produces True, skips the effect and returns Nothing.

    Designed for use with pipe:

    Example:
        ```python
        from pyfect import effect, option, pipe

        is_invalid = effect.sync(lambda: False)

        result = pipe(
            effect.succeed(42),
            effect.unless_effect(is_invalid),
        )

        effect.run_sync(result)  # Some(42)
        ```
    """

    def _apply(eff: Effect[Any, Any, Any]) -> Effect[Any, Any, Any]:
        return FlatMap(
            condition,
            lambda b: (
                FlatMap(eff, lambda a: Succeed(option_module.some(a)))
                if not b
                else Succeed(option_module.nothing())
            ),
        )

    return cast(UnlessEffectCallable[E2, R2], _apply)


# ============================================================================
# zip
# ============================================================================


@overload
def zip_[A, B](  # pyright: ignore[reportOverlappingOverload]
    eff1: Effect[A, Never, Never],
    eff2: Effect[B, Never, Never],
    *,
    concurrent: bool = ...,
) -> Effect[tuple[A, B], Never, Never]: ...


@overload
def zip_[A, B, E1, E2](  # type: ignore[overload-overlap]
    eff1: Effect[A, E1, Never],
    eff2: Effect[B, E2, Never],
    *,
    concurrent: bool = ...,
) -> Effect[tuple[A, B], E1 | E2, Never]: ...


@overload
def zip_[A, B, R1, R2](  # pyright: ignore[reportOverlappingOverload]
    eff1: Effect[A, Never, R1],
    eff2: Effect[B, Never, R2],
    *,
    concurrent: bool = ...,
) -> Effect[tuple[A, B], Never, R1 | R2]: ...


@overload
def zip_[A, B, E1, E2, R1, R2](
    eff1: Effect[A, E1, R1],
    eff2: Effect[B, E2, R2],
    *,
    concurrent: bool = ...,
) -> Effect[tuple[A, B], E1 | E2, R1 | R2]: ...


@overload
def zip_[A, B, C](  # pyright: ignore[reportOverlappingOverload]
    eff1: Effect[A, Never, Never],
    eff2: Effect[B, Never, Never],
    eff3: Effect[C, Never, Never],
    *,
    concurrent: bool = ...,
) -> Effect[tuple[A, B, C], Never, Never]: ...


@overload
def zip_[A, B, C, E1, E2, E3](  # type: ignore[overload-overlap]
    eff1: Effect[A, E1, Never],
    eff2: Effect[B, E2, Never],
    eff3: Effect[C, E3, Never],
    *,
    concurrent: bool = ...,
) -> Effect[tuple[A, B, C], E1 | E2 | E3, Never]: ...


@overload
def zip_[A, B, C, R1, R2, R3](  # pyright: ignore[reportOverlappingOverload]
    eff1: Effect[A, Never, R1],
    eff2: Effect[B, Never, R2],
    eff3: Effect[C, Never, R3],
    *,
    concurrent: bool = ...,
) -> Effect[tuple[A, B, C], Never, R1 | R2 | R3]: ...


@overload
def zip_[A, B, C, E1, E2, E3, R1, R2, R3](
    eff1: Effect[A, E1, R1],
    eff2: Effect[B, E2, R2],
    eff3: Effect[C, E3, R3],
    *,
    concurrent: bool = ...,
) -> Effect[tuple[A, B, C], E1 | E2 | E3, R1 | R2 | R3]: ...


@overload
def zip_[A, B, C, D](  # pyright: ignore[reportOverlappingOverload]
    eff1: Effect[A, Never, Never],
    eff2: Effect[B, Never, Never],
    eff3: Effect[C, Never, Never],
    eff4: Effect[D, Never, Never],
    *,
    concurrent: bool = ...,
) -> Effect[tuple[A, B, C, D], Never, Never]: ...


@overload
def zip_[A, B, C, D, E1, E2, E3, E4](  # type: ignore[overload-overlap]
    eff1: Effect[A, E1, Never],
    eff2: Effect[B, E2, Never],
    eff3: Effect[C, E3, Never],
    eff4: Effect[D, E4, Never],
    *,
    concurrent: bool = ...,
) -> Effect[tuple[A, B, C, D], E1 | E2 | E3 | E4, Never]: ...


@overload
def zip_[A, B, C, D, R1, R2, R3, R4](  # pyright: ignore[reportOverlappingOverload]
    eff1: Effect[A, Never, R1],
    eff2: Effect[B, Never, R2],
    eff3: Effect[C, Never, R3],
    eff4: Effect[D, Never, R4],
    *,
    concurrent: bool = ...,
) -> Effect[tuple[A, B, C, D], Never, R1 | R2 | R3 | R4]: ...


@overload
def zip_[A, B, C, D, E1, E2, E3, E4, R1, R2, R3, R4](
    eff1: Effect[A, E1, R1],
    eff2: Effect[B, E2, R2],
    eff3: Effect[C, E3, R3],
    eff4: Effect[D, E4, R4],
    *,
    concurrent: bool = ...,
) -> Effect[tuple[A, B, C, D], E1 | E2 | E3 | E4, R1 | R2 | R3 | R4]: ...


@overload
def zip_[A, B, C, D, F](  # pyright: ignore[reportOverlappingOverload]
    eff1: Effect[A, Never, Never],
    eff2: Effect[B, Never, Never],
    eff3: Effect[C, Never, Never],
    eff4: Effect[D, Never, Never],
    eff5: Effect[F, Never, Never],
    *,
    concurrent: bool = ...,
) -> Effect[tuple[A, B, C, D, F], Never, Never]: ...


@overload
def zip_[A, B, C, D, F, E1, E2, E3, E4, E5](  # type: ignore[overload-overlap]
    eff1: Effect[A, E1, Never],
    eff2: Effect[B, E2, Never],
    eff3: Effect[C, E3, Never],
    eff4: Effect[D, E4, Never],
    eff5: Effect[F, E5, Never],
    *,
    concurrent: bool = ...,
) -> Effect[tuple[A, B, C, D, F], E1 | E2 | E3 | E4 | E5, Never]: ...


@overload
def zip_[A, B, C, D, F, R1, R2, R3, R4, R5](  # pyright: ignore[reportOverlappingOverload]
    eff1: Effect[A, Never, R1],
    eff2: Effect[B, Never, R2],
    eff3: Effect[C, Never, R3],
    eff4: Effect[D, Never, R4],
    eff5: Effect[F, Never, R5],
    *,
    concurrent: bool = ...,
) -> Effect[tuple[A, B, C, D, F], Never, R1 | R2 | R3 | R4 | R5]: ...


@overload
def zip_[A, B, C, D, F, E1, E2, E3, E4, E5, R1, R2, R3, R4, R5](
    eff1: Effect[A, E1, R1],
    eff2: Effect[B, E2, R2],
    eff3: Effect[C, E3, R3],
    eff4: Effect[D, E4, R4],
    eff5: Effect[F, E5, R5],
    *,
    concurrent: bool = ...,
) -> Effect[tuple[A, B, C, D, F], E1 | E2 | E3 | E4 | E5, R1 | R2 | R3 | R4 | R5]: ...


def zip_(  # type: ignore[misc]
    *effects: Effect[Any, Any, Any],
    concurrent: bool = False,
) -> Effect[tuple[Any, ...], Any, Any]:
    """
    Combine multiple effects into one that produces a tuple of their results.

    By default, effects run sequentially (left to right). Pass concurrent=True
    to run them concurrently via asyncio.gather (async runtime only; the sync
    runtime always runs sequentially).

    Fully typed for up to five effects; returns tuple[Any, ...] for six or more.

    Example (sequential):
        ```python
        from pyfect import effect

        program = effect.zip(effect.succeed(1), effect.succeed("hello"))
        effect.run_sync(program)  # (1, "hello")
        ```

    Example (concurrent):
        ```python
        import asyncio
        from datetime import timedelta
        from pyfect import effect, pipe

        task1 = pipe(effect.succeed(1), effect.delay(timedelta(milliseconds=200)))
        task2 = pipe(effect.succeed("hi"), effect.delay(timedelta(milliseconds=100)))

        program = effect.zip(task1, task2, concurrent=True)
        asyncio.run(effect.run_async(program))  # (1, "hi")
        ```
    """
    if not effects:
        msg = "zip requires at least one effect"
        raise ValueError(msg)

    if concurrent:
        return cast(Effect[tuple[Any, ...], Any, Any], ZipPar(effects))

    # Sequential: chain FlatMaps, accumulating into a growing tuple
    result: Effect[Any, Any, Any] = Map(effects[0], lambda a: (a,))
    for eff in effects[1:]:
        result = FlatMap(result, lambda t, e=eff: Map(e, lambda x, t=t: (*t, x)))  # type: ignore[misc]
    return result


# ============================================================================
# zip_with
# ============================================================================


@overload
def zip_with[A, B, C](
    eff1: Effect[A, Never, Never],
    eff2: Effect[B, Never, Never],
    f: Callable[[A, B], C],
    *,
    concurrent: bool = ...,
) -> Effect[C, Never, Never]: ...


@overload
def zip_with[A, B, C, E1, E2](  # type: ignore[overload-overlap]
    eff1: Effect[A, E1, Never],
    eff2: Effect[B, E2, Never],
    f: Callable[[A, B], C],
    *,
    concurrent: bool = ...,
) -> Effect[C, E1 | E2, Never]: ...


@overload
def zip_with[A, B, C, R1, R2](
    eff1: Effect[A, Never, R1],
    eff2: Effect[B, Never, R2],
    f: Callable[[A, B], C],
    *,
    concurrent: bool = ...,
) -> Effect[C, Never, R1 | R2]: ...


@overload
def zip_with[A, B, C, E1, E2, R1, R2](
    eff1: Effect[A, E1, R1],
    eff2: Effect[B, E2, R2],
    f: Callable[[A, B], C],
    *,
    concurrent: bool = ...,
) -> Effect[C, E1 | E2, R1 | R2]: ...


def zip_with(  # type: ignore[misc]
    eff1: Effect[Any, Any, Any],
    eff2: Effect[Any, Any, Any],
    f: Callable[[Any, Any], Any],
    *,
    concurrent: bool = False,
) -> Effect[Any, Any, Any]:
    """
    Combine two effects and apply a function to their results.

    Runs both effects (sequentially by default, concurrently with concurrent=True)
    and applies f to their success values to produce a single result. The tuple
    intermediate is never exposed to the caller.

    Example:
        ```python
        from pyfect import effect

        result = effect.zip_with(
            effect.succeed(1),
            effect.succeed("hello"),
            lambda n, s: n + len(s),
        )
        effect.run_sync(result)  # 6
        ```
    """
    if concurrent:
        return Map(
            cast(Effect[tuple[Any, Any], Any, Any], ZipPar((eff1, eff2))),
            lambda t: f(t[0], t[1]),
        )
    return FlatMap(eff1, lambda a: Map(eff2, lambda b: f(a, b)))


# ============================================================================
# loop
# ============================================================================


@overload
def loop[S, S2, A, E, R](
    initial: S,
    *,
    while_: Callable[[S2], bool],
    step: Callable[[S], S2],
    body: Callable[[S2], Effect[A, E, R]],
    discard: Literal[False] = ...,
) -> Effect[list[A], E, R]: ...


@overload
def loop[S, S2, A, E, R](
    initial: S,
    *,
    while_: Callable[[S2], bool],
    step: Callable[[S], S2],
    body: Callable[[S2], Effect[A, E, R]],
    discard: Literal[True],
) -> Effect[None, E, R]: ...


def loop(
    initial: Any,
    *,
    while_: Callable[[Any], bool],
    step: Callable[[Any], Any],
    body: Callable[[Any], Effect[Any, Any, Any]],
    discard: bool = False,
) -> Effect[Any, Any, Any]:
    """
    Repeatedly run an effect while a condition holds, collecting results.

    Starts with initial state and on each iteration:
    1. Checks while_(state) — stops if False
    2. Runs body(state) for its effect
    3. Advances state with step(state)

    By default, collects body results into a list. Pass discard=True to
    run for side effects only and return None.

    Example (collecting):
        ```python
        from pyfect import effect

        result = effect.loop(
            1,
            while_=lambda s: s <= 5,
            step=lambda s: s + 1,
            body=effect.succeed,
        )
        effect.run_sync(result)  # [1, 2, 3, 4, 5]
        ```

    Example (discarding):
        ```python
        from pyfect import effect

        result = effect.loop(
            1,
            while_=lambda s: s <= 3,
            step=lambda s: s + 1,
            body=lambda s: effect.sync(lambda: print(s)),
            discard=True,
        )
        effect.run_sync(result)  # prints 1, 2, 3 — returns None
        ```
    """
    if discard:

        def _run_discard(state: Any) -> Effect[Any, Any, Any]:
            if not while_(state):
                return cast(Effect[Any, Any, Any], Succeed(None))
            next_state = step(state)
            return FlatMap(  # type: ignore[misc]
                body(state),
                lambda _: Suspend(lambda: _run_discard(next_state)),
            )

        return Suspend(lambda: _run_discard(initial))

    def _run_collect(state: Any) -> Effect[Any, Any, Any]:
        if not while_(state):
            return cast(Effect[Any, Any, Any], Succeed([]))
        next_state = step(state)
        return FlatMap(  # type: ignore[misc]
            body(state),
            lambda a: FlatMap(
                Suspend(lambda: _run_collect(next_state)),
                lambda rest: Succeed([a, *rest]),
            ),
        )

    return Suspend(lambda: _run_collect(initial))


# ============================================================================
# for_each
# ============================================================================


@overload
def for_each[A, B, E, R](
    iterable: Iterable[A],
    body: Callable[[A, int], Effect[B, E, R]],
    *,
    discard: Literal[False] = ...,
    concurrent: bool = ...,
) -> Effect[list[B], E, R]: ...


@overload
def for_each[A, B, E, R](
    iterable: Iterable[A],
    body: Callable[[A, int], Effect[B, E, R]],
    *,
    discard: Literal[True],
    concurrent: bool = ...,
) -> Effect[None, E, R]: ...


def for_each(
    iterable: Iterable[Any],
    body: Callable[[Any, int], Effect[Any, Any, Any]],
    *,
    discard: bool = False,
    concurrent: bool = False,
) -> Effect[Any, Any, Any]:
    """
    Execute an effectful operation for each element in an iterable.

    Applies the provided body function to each element (with its index),
    producing a new effect that returns a list of results. If any effect
    fails, iteration stops immediately (short-circuiting) and the error
    propagates.

    By default, operations run sequentially. Pass concurrent=True to run
    them concurrently (async runtime only).

    Example (sequential, collecting):
        ```python
        from pyfect import effect

        result = effect.for_each(
            [1, 2, 3, 4, 5],
            lambda n, i: effect.succeed(n * 2),
        )
        effect.run_sync(result)  # [2, 4, 6, 8, 10]
        ```

    Example (discarding results):
        ```python
        from pyfect import effect

        result = effect.for_each(
            [1, 2, 3],
            lambda n, i: effect.sync(lambda: print(f"Index {i}: {n}")),
            discard=True,
        )
        effect.run_sync(result)  # prints, returns None
        ```

    Example (concurrent):
        ```python
        from pyfect import effect
        from datetime import timedelta

        result = effect.for_each(
            [1, 2, 3],
            lambda n, i: effect.succeed(n * 2),
            concurrent=True,
        )
        await effect.run_async(result)  # [2, 4, 6]
        ```
    """
    items = list(iterable)

    if concurrent:
        # Create all effects upfront
        effects = tuple(body(elem, idx) for idx, elem in enumerate(items))
        if not effects:
            return Succeed(None if discard else [])

        zipped = cast(Effect[tuple[Any, ...], Any, Any], ZipPar(effects))
        if discard:
            return Map(zipped, lambda _: None)
        return Map(zipped, list)

    # Sequential execution
    if discard:

        def _run_discard(index: int) -> Effect[Any, Any, Any]:
            if index >= len(items):
                return cast(Effect[Any, Any, Any], Succeed(None))
            return FlatMap(
                body(items[index], index),
                lambda _: Suspend(lambda: _run_discard(index + 1)),
            )

        return Suspend(lambda: _run_discard(0))

    def _run_collect(index: int) -> Effect[Any, Any, Any]:
        if index >= len(items):
            return cast(Effect[Any, Any, Any], Succeed([]))
        return FlatMap(
            body(items[index], index),
            lambda result: FlatMap(
                Suspend(lambda: _run_collect(index + 1)),
                lambda rest: Succeed([result, *rest]),
            ),
        )

    return Suspend(lambda: _run_collect(0))


# ============================================================================
# all
# ============================================================================


class AllMode(StrEnum):
    """Execution mode for effect.all.

    DEFAULT  — short-circuit on the first failure, return collected values.
    EITHER   — run all effects, wrap each result in Either (never fails).
    VALIDATE — run all effects, fail with error structure if any failed.
    """

    DEFAULT = "default"
    EITHER = "either"
    VALIDATE = "validate"


def _all_list_impl(
    effects: list[Effect[Any, Any, Any]],
    *,
    mode: str,
    concurrent: bool,
) -> Effect[Any, Any, Any]:
    if mode == AllMode.EITHER:
        absorb = [cast(Effect[Any, Any, Any], Absorb(eff)) for eff in effects]
        return for_each(absorb, lambda eff, _: eff, concurrent=concurrent)

    if mode == AllMode.VALIDATE:
        either_eff = _all_list_impl(effects, mode=AllMode.EITHER, concurrent=concurrent)

        def _check_list(eithers: list[Any]) -> Effect[Any, Any, Any]:
            if any(isinstance(e, either_module.Left) for e in eithers):
                errors = [
                    option_module.some(e.value)
                    if isinstance(e, either_module.Left)
                    else option_module.nothing()
                    for e in eithers
                ]
                return cast(Effect[Any, Any, Any], Fail(errors))
            return cast(Effect[Any, Any, Any], Succeed([e.value for e in eithers]))

        return FlatMap(either_eff, _check_list)

    # DEFAULT: run each effect, collect results, short-circuit on first failure
    return for_each(effects, lambda eff, _: eff, concurrent=concurrent)


def _all_dict_impl(
    effects: dict[Any, Effect[Any, Any, Any]],
    *,
    mode: str,
    concurrent: bool,
) -> Effect[Any, Any, Any]:
    items = list(effects.items())
    keys = [k for k, _ in items]
    effs = [v for _, v in items]

    if mode == AllMode.EITHER:
        absorb = [cast(Effect[Any, Any, Any], Absorb(eff)) for eff in effs]

        def _build_either(values: list[Any]) -> dict[Any, Any]:
            return dict(zip(keys, values, strict=True))

        return Map(for_each(absorb, lambda eff, _: eff, concurrent=concurrent), _build_either)

    if mode == AllMode.VALIDATE:
        either_eff = _all_dict_impl(effects, mode=AllMode.EITHER, concurrent=concurrent)

        def _check_dict(either_dict: dict[Any, Any]) -> Effect[Any, Any, Any]:
            if any(isinstance(v, either_module.Left) for v in either_dict.values()):
                return cast(
                    Effect[Any, Any, Any],
                    Fail(
                        {
                            k: option_module.some(v.value)
                            if isinstance(v, either_module.Left)
                            else option_module.nothing()
                            for k, v in either_dict.items()
                        }
                    ),
                )
            return cast(
                Effect[Any, Any, Any], Succeed({k: v.value for k, v in either_dict.items()})
            )

        return FlatMap(either_eff, _check_dict)

    # DEFAULT: run each effect, collect into dict, short-circuit on first failure
    def _build_default(values: list[Any]) -> dict[Any, Any]:
        return dict(zip(keys, values, strict=True))

    return Map(for_each(effs, lambda eff, _: eff, concurrent=concurrent), _build_default)


# ---- list overloads --------------------------------------------------------


@overload
def all_[A, E, R](
    effects: list[Effect[A, E, R]],
    *,
    mode: Literal["default", AllMode.DEFAULT] = ...,
    concurrent: bool = ...,
) -> Effect[list[A], E, R]: ...


@overload
def all_[A, E, R](
    effects: list[Effect[A, E, R]],
    *,
    mode: Literal["either", AllMode.EITHER],
    concurrent: bool = ...,
) -> Effect[list[either_module.Either[A, E]], Never, R]: ...


@overload
def all_[A, E, R](
    effects: list[Effect[A, E, R]],
    *,
    mode: Literal["validate", AllMode.VALIDATE],
    concurrent: bool = ...,
) -> Effect[list[A], list[option_module.Option[E]], R]: ...


# ---- dict overloads --------------------------------------------------------


@overload
def all_[K, A, E, R](
    effects: dict[K, Effect[A, E, R]],
    *,
    mode: Literal["default", AllMode.DEFAULT] = ...,
    concurrent: bool = ...,
) -> Effect[dict[K, A], E, R]: ...


@overload
def all_[K, A, E, R](
    effects: dict[K, Effect[A, E, R]],
    *,
    mode: Literal["either", AllMode.EITHER],
    concurrent: bool = ...,
) -> Effect[dict[K, either_module.Either[A, E]], Never, R]: ...


@overload
def all_[K, A, E, R](
    effects: dict[K, Effect[A, E, R]],
    *,
    mode: Literal["validate", AllMode.VALIDATE],
    concurrent: bool = ...,
) -> Effect[dict[K, A], dict[K, option_module.Option[E]], R]: ...


# ---- implementation --------------------------------------------------------


def all_(  # type: ignore[misc]
    effects: list[Effect[Any, Any, Any]] | dict[Any, Effect[Any, Any, Any]],
    *,
    mode: Literal["default", "either", "validate"] | AllMode = AllMode.DEFAULT,
    concurrent: bool = False,
) -> Effect[Any, Any, Any]:
    """
    Combine a list or dict of effects into a single effect.

    By default, effects run sequentially and short-circuit on the first failure.
    Pass concurrent=True to run effects concurrently (async runtime only).

    The mode controls how results and failures are collected:

    - DEFAULT (default): returns collected values, short-circuits on first failure.
    - EITHER: all effects run; each result is Right (success) or Left (failure).
      The combined effect never fails — errors land in the Left channel.
    - VALIDATE: all effects run; if all succeed, returns collected values.
      If any fail, the combined effect fails with the error structure (list or
      dict of Option[E] — Some(error) for failures, Nothing for successes).

    Supports list[Effect[A, E, R]] and dict[K, Effect[A, E, R]] inputs.

    Example (list, default):
        ```python
        from pyfect import effect

        result = effect.all([effect.succeed(1), effect.succeed(2)])
        effect.run_sync(result)  # [1, 2]
        ```

    Example (dict, either mode):
        ```python
        from pyfect import effect

        result = effect.all(
            {"a": effect.succeed(1), "b": effect.fail("oops")},
            mode=effect.AllMode.EITHER,
        )
        effect.run_sync(result)  # {"a": Right(1), "b": Left("oops")}
        ```

    Example (list, validate mode):
        ```python
        from pyfect import effect

        result = effect.all(
            [effect.succeed(1), effect.fail("oops"), effect.succeed(3)],
            mode=effect.AllMode.VALIDATE,
        )
        effect.run_sync_exit(result)
        # Failure([Nothing, Some("oops"), Nothing])
        ```
    """
    if isinstance(effects, dict):
        return _all_dict_impl(effects, mode=str(mode), concurrent=concurrent)
    return _all_list_impl(list(effects), mode=str(mode), concurrent=concurrent)


__all__ = [
    "AllMode",
    "UnlessEffectCallable",
    "WhenCallable",
    "WhenEffectCallable",
    "all_",
    "for_each",
    "if_",
    "loop",
    "unless",
    "unless_effect",
    "when",
    "when_effect",
    "zip_",
    "zip_with",
]
