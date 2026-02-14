"""
Effect combinators for composing and transforming effects.

Combinators are functions that take effects and return new effects,
allowing you to build complex effect pipelines.
"""

from collections.abc import Callable
from typing import Any, Never, Protocol, cast

from pyfect.primitives import Effect, FlatMap, Ignore, Map, MapError, Tap, TapError

# ============================================================================
# Callable Protocols
#
# Each combinator returns a callable that is polymorphic in the input effect's
# E and R type parameters. Plain Callable[[...], ...] can't express this
# polymorphism, so we use Protocols with a generic __call__ instead.
# ============================================================================


class AsCallable[B](Protocol):
    def __call__[A, E, R](self, eff: Effect[A, E, R]) -> Effect[B, E, R]: ...


class IgnoreCallable(Protocol):
    def __call__[A, E, R](self, eff: Effect[A, E, R]) -> Effect[None, Never, R]: ...


class FlatMapCallable[A, B, E2 = Never, R2 = Never](Protocol):
    def __call__[E, R](self, eff: Effect[A, E, R]) -> Effect[B, E | E2, R | R2]: ...


class MapCallable[A, B](Protocol):
    def __call__[E, R](self, eff: Effect[A, E, R]) -> Effect[B, E, R]: ...


class MapErrorCallable[E, E2](Protocol):
    def __call__[A, R](self, eff: Effect[A, E, R]) -> Effect[A, E2, R]: ...


class TapCallable[A, E2 = Never, R2 = Never](Protocol):
    def __call__[E, R](self, eff: Effect[A, E, R]) -> Effect[A, E | E2, R | R2]: ...


class TapErrorCallable[E, E2 = Never, R2 = Never](Protocol):
    def __call__[A, R](self, eff: Effect[A, E, R]) -> Effect[A, E | E2, R | R2]: ...


# ============================================================================
# Combinators
# ============================================================================


def as_[B](
    value: B,
) -> AsCallable[B]:
    """
    Replace the success value with a constant value.

    Returns a function that takes an effect and returns a new effect
    that ignores the original success value and replaces it with the
    provided constant. The error and context types are preserved.

    This is equivalent to map(lambda _: value) but more explicit.

    Example:
        ```python
        from pyfect import effect, pipe

        # Using with pipe (curried style)
        result = pipe(
            effect.succeed(42),
            effect.as_("done")
        )
        effect.run_sync(result)  # "done"

        # Useful for ignoring complex results
        result = pipe(
            effect.sync(lambda: expensive_computation()),
            effect.as_(None)  # Discard the result
        )
        ```
    """

    def _apply(eff: Effect[Any, Any, Any]) -> Effect[Any, Any, Any]:
        return cast(Effect[Any, Any, Any], Map(eff, lambda _: value))

    return cast(AsCallable[B], _apply)


def ignore() -> IgnoreCallable:
    """
    Ignore both success and failure, always succeeding with None.

    This runs the effect for its side effects but discards the result,
    whether it succeeds or fails. The returned effect can never fail
    (error type is Never).

    Useful when you only care about the side effects of an effect and
    don't need to handle or process its outcome.

    Example:
        ```python
        from pyfect import effect, pipe

        # Ignore success
        result = pipe(
            effect.succeed(42),
            effect.ignore()
        )
        effect.run_sync(result)  # None

        # Ignore failure too
        result = pipe(
            effect.fail("error"),
            effect.ignore()
        )
        effect.run_sync(result)  # None (no error raised!)

        # Useful for fire-and-forget operations
        result = pipe(
            effect.try_sync(lambda: risky_operation()),
            effect.ignore()  # Don't care if it succeeds or fails
        )
        ```
    """
    return cast(IgnoreCallable, Ignore)


def flat_map[A, B, E2 = Never, R2 = Never](
    f: Callable[[A], Effect[B, E2, R2]],
) -> FlatMapCallable[A, B, E2, R2]:
    """
    Chain effects together (monadic bind).

    Returns a function that takes an effect and returns a new effect by
    applying f to the success value. Unlike map, f returns an Effect which
    is then flattened, avoiding nested effects.

    This is useful for sequencing operations where each step depends on the
    result of the previous one.

    Example:
        ```python
        from pyfect import effect, pipe

        def fetch_user(user_id: int) -> effect.Effect[str, str]:
            return effect.succeed(f"User{user_id}")

        # Chain effects where next depends on previous result
        result = pipe(
            effect.succeed(42),
            effect.flat_map(lambda id: fetch_user(id))
        )
        effect.run_sync(result)  # "User42"

        # Multiple chaining
        result = pipe(
            effect.succeed(1),
            effect.flat_map(lambda x: effect.succeed(x + 1)),
            effect.flat_map(lambda x: effect.succeed(x * 2))
        )
        effect.run_sync(result)  # 4
        ```
    """

    def _apply(eff: Effect[A, Any, Any]) -> Effect[B, Any, Any]:
        return cast(Effect[B, Any, Any], FlatMap(eff, f))

    return cast(FlatMapCallable[A, B, E2, R2], _apply)


def map[A, B](
    f: Callable[[A], B],
) -> MapCallable[A, B]:
    """
    Transform the success value of an effect.

    Returns a function that takes an effect and returns a new effect
    with the success value transformed by f. The error and context types
    are preserved.

    Example:
        ```python
        from pyfect import effect, pipe

        # Using with pipe (curried style)
        result = pipe(
            effect.succeed(42),
            effect.map(lambda x: x * 2)
        )
        effect.run_sync(result)  # 84

        # Direct usage
        eff = effect.succeed(21)
        mapped = effect.map(lambda x: x * 2)(eff)
        effect.run_sync(mapped)  # 42
        ```
    """

    def _apply(eff: Effect[A, Any, Any]) -> Effect[B, Any, Any]:
        return cast(Effect[B, Any, Any], Map(eff, f))

    return cast(MapCallable[A, B], _apply)


def map_error[E, E2](
    f: Callable[[E], E2],
) -> MapErrorCallable[E, E2]:
    """
    Transform the error type of an effect.

    Returns a function that takes an effect and returns a new effect
    with the error type transformed by f. The success value and context
    types are preserved.

    This is the counterpart to map - while map transforms success values,
    map_error transforms error values.

    Example:
        ```python
        from pyfect import effect, pipe

        # Transform error messages
        result = pipe(
            effect.fail("file not found"),
            effect.map_error(lambda msg: f"Error: {msg}")
        )
        # Will fail with "Error: file not found"

        # Convert string errors to custom error types
        class MyError(Exception):
            def __init__(self, msg: str):
                self.message = msg

        result = pipe(
            effect.fail("oops"),
            effect.map_error(lambda msg: MyError(msg))
        )
        ```
    """

    def _apply(eff: Effect[Any, E, Any]) -> Effect[Any, E2, Any]:
        return cast(Effect[Any, E2, Any], MapError(eff, f))

    return cast(MapErrorCallable[E, E2], _apply)


def tap[A, B, E2 = Never, R2 = Never](
    f: Callable[[A], Effect[B, E2, R2]],
) -> TapCallable[A, E2, R2]:
    """
    Inspect the success value without modifying it.

    Returns a function that takes an effect and returns a new effect.
    The function f is called with the success value and returns an effect
    that is executed for its side effects. The original value is passed through.

    The tap function may have a different error type E2; any error it produces
    merges with the outer E type. The context type R must match. The success
    type B is discarded.

    Works with both sync and async effects - the runtime handles it uniformly.

    Example:
        ```python
        from pyfect import effect, pipe

        # Using with pipe (curried style)
        result = pipe(
            effect.succeed(42),
            effect.tap(lambda x: effect.sync(lambda: print(f"Value: {x}")))
        )

        # Direct usage
        tap_fn = effect.tap(lambda x: effect.sync(lambda: print(x)))
        result = tap_fn(effect.succeed(42))
        ```
    """

    def _apply(eff: Effect[A, Any, Any]) -> Effect[A, Any, Any]:
        return cast(Effect[A, Any, Any], Tap(eff, f))

    return cast(TapCallable[A, E2, R2], _apply)


def tap_error[E, B, E2 = Never, R2 = Never](
    f: Callable[[E], Effect[B, E2, R2]],
) -> TapErrorCallable[E, E2, R2]:
    """
    Inspect the error value without modifying it.

    Returns a function that takes an effect and returns a new effect.
    The function f is called with the error value and returns an effect
    that is executed for its side effects. The original error is passed through.

    The tap_error function may have a different error type E2; any error it
    produces merges with the outer E type. The context type R must match.
    The success type B is discarded.

    Example:
        ```python
        from pyfect import effect, pipe

        result = pipe(
            effect.fail(ValueError("oops")),
            effect.tap_error(lambda e: effect.sync(lambda: print(f"Error: {e}")))
        )
        ```
    """

    def _apply(eff: Effect[Any, E, Any]) -> Effect[Any, Any, Any]:
        return cast(Effect[Any, Any, Any], TapError(eff, f))

    return cast(TapErrorCallable[E, E2, R2], _apply)


__all__ = [
    "AsCallable",
    "FlatMapCallable",
    "IgnoreCallable",
    "MapCallable",
    "MapErrorCallable",
    "TapCallable",
    "TapErrorCallable",
    "as_",
    "flat_map",
    "ignore",
    "map",
    "map_error",
    "tap",
    "tap_error",
]
