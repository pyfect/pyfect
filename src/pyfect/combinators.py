"""
Effect combinators for composing and transforming effects.

Combinators are functions that take effects and return new effects,
allowing you to build complex effect pipelines.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pyfect.primitives import Effect, Map, Tap, TapError

# ============================================================================
# Combinators
# ============================================================================


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


def tap[A, E, R](
    f: Callable[[A], Effect[Any, Any, Any]],
) -> Callable[[Effect[A, E, R]], Effect[A, E, R]]:
    """
    Inspect the success value without modifying it.

    Returns a function that takes an effect and returns a new effect.
    The function f is called with the success value and returns an effect
    that is executed for its side effects. The original value is passed through.

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


def tap_error[A, E, R](
    f: Callable[[E], Effect[Any, Any, Any]],
) -> Callable[[Effect[A, E, R]], Effect[A, E, R]]:
    """
    Inspect the error value without modifying it.

    Returns a function that takes an effect and returns a new effect.
    The function f is called with the error value and returns an effect
    that is executed for its side effects. The original error is passed through.

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
    "map",
    "tap",
    "tap_error",
]
