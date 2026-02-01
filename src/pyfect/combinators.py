"""
Effect combinators for composing and transforming effects.

Combinators are functions that take effects and return new effects,
allowing you to build complex effect pipelines.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import NoReturn

from pyfect.primitives import Effect, FlatMap, Ignore, Map, MapError, Tap, TapError

# Never type for impossible errors
type Never = NoReturn

# ============================================================================
# Combinators
# ============================================================================


def as_[A, B, E, R](
    value: B,
) -> Callable[[Effect[A, E, R]], Effect[B, E, R]]:
    """
    Replace the success value with a constant value.

    Returns a function that takes an effect and returns a new effect
    that ignores the original success value and replaces it with the
    provided constant. The error and context types are preserved.

    This is equivalent to map(lambda _: value) but more explicit.

    Example:
        >>> from pyfect import effect, pipe
        >>>
        >>> # Using with pipe (curried style)
        >>> result = pipe(
        ...     effect.succeed(42),
        ...     effect.as_("done")
        ... )
        >>> effect.run_sync(result)  # "done"
        >>>
        >>> # Useful for ignoring complex results
        >>> result = pipe(
        ...     effect.sync(lambda: expensive_computation()),
        ...     effect.as_(None)  # Discard the result
        ... )
    """
    return lambda effect: Map(effect, lambda _: value)


def ignore[A, E, R]() -> Callable[[Effect[A, E, R]], Effect[None, Never, R]]:
    """
    Ignore both success and failure, always succeeding with None.

    This runs the effect for its side effects but discards the result,
    whether it succeeds or fails. The returned effect can never fail
    (error type is Never).

    Useful when you only care about the side effects of an effect and
    don't need to handle or process its outcome.

    Example:
        >>> from pyfect import effect, pipe
        >>>
        >>> # Ignore success
        >>> result = pipe(
        ...     effect.succeed(42),
        ...     effect.ignore()
        ... )
        >>> effect.run_sync(result)  # None
        >>>
        >>> # Ignore failure too
        >>> result = pipe(
        ...     effect.fail("error"),
        ...     effect.ignore()
        ... )
        >>> effect.run_sync(result)  # None (no error raised!)
        >>>
        >>> # Useful for fire-and-forget operations
        >>> result = pipe(
        ...     effect.try_sync(lambda: risky_operation()),
        ...     effect.ignore()  # Don't care if it succeeds or fails
        ... )
    """
    return lambda effect: Ignore(effect)


def flat_map[A, B, E, R](
    f: Callable[[A], Effect[B, E, R]],
) -> Callable[[Effect[A, E, R]], Effect[B, E, R]]:
    """
    Chain effects together (monadic bind).

    Returns a function that takes an effect and returns a new effect by
    applying f to the success value. Unlike map, f returns an Effect which
    is then flattened, avoiding nested effects.

    This is useful for sequencing operations where each step depends on the
    result of the previous one.

    Example:
        >>> from pyfect import effect, pipe
        >>>
        >>> def fetch_user(user_id: int) -> effect.Effect[str, str, None]:
        ...     return effect.succeed(f"User{user_id}")
        >>>
        >>> # Chain effects where next depends on previous result
        >>> result = pipe(
        ...     effect.succeed(42),
        ...     effect.flat_map(lambda id: fetch_user(id))
        ... )
        >>> effect.run_sync(result)  # "User42"
        >>>
        >>> # Multiple chaining
        >>> result = pipe(
        ...     effect.succeed(1),
        ...     effect.flat_map(lambda x: effect.succeed(x + 1)),
        ...     effect.flat_map(lambda x: effect.succeed(x * 2))
        ... )
        >>> effect.run_sync(result)  # 4
    """
    return lambda effect: FlatMap(effect, f)


def map[A, B, E, R](
    f: Callable[[A], B],
) -> Callable[[Effect[A, E, R]], Effect[B, E, R]]:
    """
    Transform the success value of an effect.

    Returns a function that takes an effect and returns a new effect
    with the success value transformed by f. The error and context types
    are preserved.

    Example:
        >>> from pyfect import effect, pipe
        >>>
        >>> # Using with pipe (curried style)
        >>> result = pipe(
        ...     effect.succeed(42),
        ...     effect.map(lambda x: x * 2)
        ... )
        >>> effect.run_sync(result)  # 84
        >>>
        >>> # Direct usage
        >>> eff = effect.succeed(21)
        >>> mapped = effect.map(lambda x: x * 2)(eff)
        >>> effect.run_sync(mapped)  # 42
    """
    return lambda effect: Map(effect, f)


def map_error[A, E, E2, R](
    f: Callable[[E], E2],
) -> Callable[[Effect[A, E, R]], Effect[A, E2, R]]:
    """
    Transform the error type of an effect.

    Returns a function that takes an effect and returns a new effect
    with the error type transformed by f. The success value and context
    types are preserved.

    This is the counterpart to map - while map transforms success values,
    map_error transforms error values.

    Example:
        >>> from pyfect import effect, pipe
        >>>
        >>> # Transform error messages
        >>> result = pipe(
        ...     effect.fail("file not found"),
        ...     effect.map_error(lambda msg: f"Error: {msg}")
        ... )
        >>> # Will fail with "Error: file not found"
        >>>
        >>> # Convert string errors to custom error types
        >>> class MyError(Exception):
        ...     def __init__(self, msg: str):
        ...         self.message = msg
        >>>
        >>> result = pipe(
        ...     effect.fail("oops"),
        ...     effect.map_error(lambda msg: MyError(msg))
        ... )
    """
    return lambda effect: MapError(effect, f)


def tap[A, B, E, R](
    f: Callable[[A], Effect[B, E, R]],
) -> Callable[[Effect[A, E, R]], Effect[A, E, R]]:
    """
    Inspect the success value without modifying it.

    Returns a function that takes an effect and returns a new effect.
    The function f is called with the success value and returns an effect
    that is executed for its side effects. The original value is passed through.

    The tap function must return an effect with the same error type E and
    context type R as the input effect. The success type B is discarded.

    Works with both sync and async effects - the runtime handles it uniformly.

    Example:
        >>> from pyfect import effect, pipe
        >>>
        >>> # Using with pipe (curried style)
        >>> result = pipe(
        ...     effect.succeed(42),
        ...     effect.tap(lambda x: effect.sync(lambda: print(f"Value: {x}")))
        ... )
        >>>
        >>> # Direct usage
        >>> tap_fn = effect.tap(lambda x: effect.sync(lambda: print(x)))
        >>> result = tap_fn(effect.succeed(42))
    """
    return lambda effect: Tap(effect, f)


def tap_error[A, B, E, R](
    f: Callable[[E], Effect[B, E, R]],
) -> Callable[[Effect[A, E, R]], Effect[A, E, R]]:
    """
    Inspect the error value without modifying it.

    Returns a function that takes an effect and returns a new effect.
    The function f is called with the error value and returns an effect
    that is executed for its side effects. The original error is passed through.

    The tap_error function must return an effect with the same error type E and
    context type R as the input effect. The success type B is discarded.

    Example:
        >>> from pyfect import effect, pipe
        >>>
        >>> result = pipe(
        ...     effect.fail(ValueError("oops")),
        ...     effect.tap_error(lambda e: effect.sync(lambda: print(f"Error: {e}")))
        ... )
    """
    return lambda effect: TapError(effect, f)


__all__ = [
    "as_",
    "flat_map",
    "ignore",
    "map",
    "map_error",
    "tap",
    "tap_error",
]
