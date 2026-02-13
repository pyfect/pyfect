"""
Core Effect primitives and operations.

This module contains the tagged union of effect primitives and functions
that operate on them. Import as `Effect` for the Effect TS-like API.
"""

from collections.abc import Awaitable, Callable
from typing import Never

import pyfect.either as either_module
import pyfect.option as option_module

# Re-export Exit types from exit module for backward compatibility
from pyfect.exit import Exit, Failure, Success

# Re-export Effect primitives from primitives module
from pyfect.primitives import (
    Async,
    Effect,
    Fail,
    FlatMap,
    Ignore,
    Map,
    MapError,
    Succeed,
    Suspend,
    Sync,
    Tap,
    TapError,
    TryAsync,
    TrySync,
)

# ============================================================================
# Constructors
# ============================================================================


def succeed[A, E = Never](value: A) -> Effect[A, E]:
    """
    Create an effect that succeeds with a value.

    Example:
        ```python
        eff = succeed(42)
        ```
    """
    return Succeed(value)


def fail[E, A = Never](error: E) -> Effect[A, E]:
    """
    Create an effect that fails with an error.

    Example:
        ```python
        eff = fail("Something went wrong")
        ```
    """
    return Fail(error)


def sync[A, E = Never](thunk: Callable[[], A]) -> Effect[A, E]:
    """
    Create an effect from a synchronous computation.

    The computation is not executed immediately - it's deferred until
    the effect is run by the runtime.

    Example:
        ```python
        eff = sync(lambda: print("Hello"))
        # Nothing printed yet - it's just a description
        # Will print when the effect is run
        ```
    """
    return Sync(thunk)


def async_[A, E = Never](thunk: Callable[[], Awaitable[A]]) -> Effect[A, E]:
    """
    Create an effect from an asynchronous computation.

    The computation is not executed immediately - it's deferred until
    the effect is run by the runtime.

    Note: Uses async_ (with underscore) since 'async' is a Python keyword.

    Example:
        ```python
        import asyncio
        eff = async_(lambda: asyncio.sleep(1))
        # Sleep doesn't happen yet - only when the effect is run
        ```
    """
    return Async(thunk)


def try_sync[A](thunk: Callable[[], A]) -> Effect[A, Exception]:
    """
    Create an effect from a synchronous computation that might throw.

    Exceptions are captured and converted to effect errors.

    Example:
        ```python
        eff = try_sync(lambda: int("not a number"))
        result = run_sync_exit(eff)  # Failure(ValueError(...))
        ```
    """
    return TrySync(thunk)


def try_async[A](thunk: Callable[[], Awaitable[A]]) -> Effect[A, Exception]:
    """
    Create an effect from an asynchronous computation that might throw.

    Exceptions are captured and converted to effect errors.

    Example:
        ```python
        import asyncio

        async def might_fail():
            await asyncio.sleep(0.1)
            raise ValueError("oops")

        eff = try_async(might_fail)
        result = await run_async_exit(eff)  # Failure(ValueError("oops"))
        ```
    """
    return TryAsync(thunk)


def suspend[A, E = Never, R = Never](thunk: Callable[[], Effect[A, E, R]]) -> Effect[A, E, R]:
    """
    Delay the creation of an effect until runtime.

    The thunk is called each time the effect is run, allowing for:
    - Lazy evaluation of effects
    - Re-execution of side effects on each run
    - Capturing fresh state each time

    Example:
        ```python
        i = 0
        # Bad - effect created once, i captured at creation
        bad = succeed((i := i + 1))
        run_sync(bad)  # 1
        run_sync(bad)  # 1 (same effect, same i)

        # Good - effect created fresh each run
        good = suspend(lambda: succeed((i := i + 1)))
        run_sync(good)  # 2
        run_sync(good)  # 3 (fresh effect, fresh i!)
        ```
    """
    return Suspend(thunk)


# ============================================================================
# Re-exports for backward compatibility
# ============================================================================

# ============================================================================
# Interop
# ============================================================================


def from_option[A, E](
    error: Callable[[], E],
) -> Callable[[option_module.Option[A]], Effect[A, E]]:
    """
    Convert an Option into an Effect.

    Some(value) becomes a successful effect with that value.
    Nothing becomes a failed effect using the provided error thunk.

    The error thunk is only called when the Option is Nothing.

    Example:
        ```python
        from pyfect import option, pipe
        pipe(option.some(42), from_option(lambda: "not found"))    # succeeds with 42
        pipe(option.nothing(), from_option(lambda: "not found"))   # fails with "not found"
        ```
    """

    def _from_option(opt: option_module.Option[A]) -> Effect[A, E]:
        match opt:
            case option_module.Some(value):
                return Succeed(value)
            case option_module.Nothing():
                return Fail(error())

    return _from_option


def from_either[R, L](e: either_module.Either[R, L]) -> Effect[R, L]:
    """
    Convert an Either into an Effect.

    Right(value) becomes a successful effect with that value.
    Left(value) becomes a failed effect with that value as the error.

    Example:
        ```python
        from pyfect import either
        from_either(either.right(42))    # succeeds with 42
        from_either(either.left("oops")) # fails with "oops"
        ```
    """
    match e:
        case either_module.Right(value):
            return Succeed(value)
        case either_module.Left(value):
            return Fail(value)


# Re-export combinators
from pyfect.combinators import as_, flat_map, ignore, map, map_error, tap, tap_error  # noqa: E402

# Re-export runtime
from pyfect.runtime import (  # noqa: E402
    run_async,
    run_async_exit,
    run_sync,
    run_sync_exit,
)

__all__ = [
    "Async",
    "Effect",
    "Exit",
    "Fail",
    "Failure",
    "FlatMap",
    "Ignore",
    "Map",
    "MapError",
    "Never",
    "Succeed",
    "Success",
    "Suspend",
    "Sync",
    "Tap",
    "TapError",
    "TryAsync",
    "TrySync",
    "as_",
    "async_",
    "fail",
    "flat_map",
    "from_either",
    "from_option",
    "ignore",
    "map",
    "map_error",
    "run_async",
    "run_async_exit",
    "run_sync",
    "run_sync_exit",
    "succeed",
    "suspend",
    "sync",
    "tap",
    "tap_error",
    "try_async",
    "try_sync",
]
