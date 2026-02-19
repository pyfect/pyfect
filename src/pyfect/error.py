"""
Error-handling combinators: catch_all, catch_some, catch_if.
"""

from collections.abc import Callable
from typing import Any, Never, Protocol, TypeGuard, cast, overload

from pyfect.either import Right
from pyfect.option import Nothing, Some
from pyfect.option import Option as option_Option
from pyfect.primitives import (
    Absorb,
    Effect,
    Fail,
    FlatMap,
    Succeed,
)

# ============================================================================
# Callable Protocols
# ============================================================================


class CatchAllCallable[E, A2, E2 = Never, R2 = Never](Protocol):
    def __call__[A, R](self, eff: Effect[A, E, R]) -> Effect[A | A2, E2, R | R2]: ...


class CatchSomeCallable[E, A2, E2 = Never, R2 = Never](Protocol):
    def __call__[A, R](self, eff: Effect[A, E, R]) -> Effect[A | A2, E, R | R2]: ...


class CatchIfCallable[E, A2, E2 = Never, R2 = Never](Protocol):
    def __call__[A, R](self, eff: Effect[A, E, R]) -> Effect[A | A2, E, R | R2]: ...


# ============================================================================
# Combinators
# ============================================================================


def catch_all[E, A2, E2 = Never, R2 = Never](
    f: Callable[[E], Effect[A2, E2, R2]],
) -> CatchAllCallable[E, A2, E2, R2]:
    """
    Recover from all errors by providing a fallback effect.

    Returns a function that takes an effect and returns a new effect.
    If the original effect fails, f is called with the error and its result
    is executed. If the original effect succeeds, f is never called.

    The resulting effect's error type is E2 (the error type of the fallback),
    since all E errors are handled. Use Effect[A2, Never, R2] as the fallback
    to produce an infallible effect.

    Example:
        ```python
        from pyfect import effect, pipe

        result = pipe(
            effect.fail("something went wrong"),
            effect.catch_all(lambda e: effect.succeed(f"Recovered: {e}")),
        )
        effect.run_sync(result)  # "Recovered: something went wrong"
        ```
    """

    def _apply(eff: Effect[Any, Any, Any]) -> Effect[Any, Any, Any]:
        def _handle(e: Any) -> Effect[Any, Any, Any]:
            if isinstance(e, Right):
                return Succeed(e.value)
            return f(e.value)  # type: ignore[attr-defined]

        return FlatMap(Absorb(eff), _handle)

    return cast(CatchAllCallable[E, A2, E2, R2], _apply)


@overload
def catch_some[E](
    f: Callable[[E], Nothing],
) -> CatchSomeCallable[E, Never, Never, Never]: ...


@overload
def catch_some[E, A2, E2 = Never, R2 = Never](
    f: Callable[[E], option_Option[Effect[A2, E2, R2]]],
) -> CatchSomeCallable[E, A2, E2, R2]: ...


def catch_some[E, A2, E2 = Never, R2 = Never](
    f: Callable[[E], option_Option[Effect[A2, E2, R2]]],
) -> CatchSomeCallable[E, A2, E2, R2]:
    """
    Recover from errors selectively by returning an Option.

    The handler f is called with the error. If it returns Some(effect),
    that effect is used for recovery. If it returns Nothing, the original
    error propagates unchanged.

    Unlike catch_all, the error type E is preserved in the output — errors
    not handled by the Option remain possible.

    Example:
        ```python
        from pyfect import effect, option, pipe

        result = pipe(
            effect.fail("oops"),
            effect.catch_some(lambda e:
                option.some(effect.succeed("recovered")) if e == "oops"
                else option.nothing()
            ),
        )
        effect.run_sync(result)  # "recovered"
        ```
    """

    def _apply(eff: Effect[Any, Any, Any]) -> Effect[Any, Any, Any]:
        def _handle(e: Any) -> Effect[Any, Any, Any]:
            if isinstance(e, Right):
                return Succeed(e.value)
            recovery = f(e.value)  # type: ignore[attr-defined]
            if isinstance(recovery, Some):
                return recovery.value
            return Fail(e.value)  # type: ignore[attr-defined]

        return FlatMap(Absorb(eff), _handle)

    return cast(CatchSomeCallable[E, A2, E2, R2], _apply)


@overload
def catch_if[E, E1, A2, E2 = Never, R2 = Never](
    # Named function with -> TypeGuard[E1] annotation required; lambdas always
    # infer as bool and will match the overload below instead.
    predicate: Callable[[E], TypeGuard[E1]],
    recover: Callable[[E1], Effect[A2, E2, R2]],
) -> CatchIfCallable[E, A2, E2, R2]: ...


@overload
def catch_if[E, A2, E2 = Never, R2 = Never](
    predicate: Callable[[E], bool],
    recover: Callable[[E], Effect[A2, E2, R2]],
) -> CatchIfCallable[E, A2, E2, R2]: ...


def catch_if[E, A2, E2 = Never, R2 = Never](  # type: ignore[misc]
    predicate: Callable[[E], bool],
    recover: Callable[[E], Effect[A2, E2, R2]],
) -> CatchIfCallable[E, A2, E2, R2]:
    """
    Recover from errors that match a predicate.

    If the predicate returns True for the error, the recovery effect is used.
    If it returns False, the original error propagates unchanged.

    The error type is preserved — the resulting effect still carries the
    original error type E, since unmatched errors remain possible.

    A TypeGuard predicate provides type-safe narrowing of the error passed
    to recover, but does not prune E from the output type.

    Example:
        ```python
        from pyfect import effect, pipe

        class HttpError: pass
        class ValidationError: pass

        result = pipe(
            effect.fail(HttpError()),
            effect.catch_if(
                lambda e: isinstance(e, HttpError),
                lambda _: effect.succeed("http recovered"),
            ),
        )
        effect.run_sync(result)  # "http recovered"
        ```
    """

    def _apply(eff: Effect[Any, Any, Any]) -> Effect[Any, Any, Any]:
        def _handle(e: Any) -> Effect[Any, Any, Any]:
            if isinstance(e, Right):
                return Succeed(e.value)
            if predicate(e.value):
                return recover(e.value)
            return Fail(e.value)

        return FlatMap(Absorb(eff), _handle)

    return cast(CatchIfCallable[E, A2, E2, R2], _apply)


__all__ = [
    "CatchAllCallable",
    "CatchIfCallable",
    "CatchSomeCallable",
    "catch_all",
    "catch_if",
    "catch_some",
]
