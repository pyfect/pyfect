"""
Core Effect primitives and operations.

This module contains the tagged union of effect primitives and functions
that operate on them. Import as `Effect` for the Effect TS-like API.
"""

from __future__ import annotations

import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, NoReturn, TypeVar, cast

# Type variables
A = TypeVar("A")
B = TypeVar("B")
E = TypeVar("E")
E2 = TypeVar("E2")
R = TypeVar("R")
R2 = TypeVar("R2")

# Never type for impossible errors
type Never = NoReturn


# ============================================================================
# Effect Primitives (Tagged Union)
# ============================================================================


@dataclass(frozen=True)
class Succeed[A, E, R]:
    """An effect that succeeds with a value."""

    value: A


@dataclass(frozen=True)
class Fail[A, E, R]:
    """An effect that fails with an error."""

    error: E


@dataclass(frozen=True)
class Sync[A, E, R]:
    """An effect that wraps a synchronous computation."""

    thunk: Callable[[], A]


@dataclass(frozen=True)
class Async[A, E, R]:
    """An effect that wraps an asynchronous computation."""

    thunk: Callable[[], Awaitable[A]]


@dataclass(frozen=True)
class TrySync[A, E, R]:
    """An effect that wraps a synchronous computation that might throw."""

    thunk: Callable[[], A]


@dataclass(frozen=True)
class TryAsync[A, E, R]:
    """An effect that wraps an asynchronous computation that might throw."""

    thunk: Callable[[], Awaitable[A]]


@dataclass(frozen=True)
class Suspend[A, E, R]:
    """An effect that delays effect creation until runtime."""

    thunk: Callable[[], Effect[A, E, R]]


@dataclass(frozen=True)
class Tap[A, E, R, R2]:
    """An effect that inspects the success value without modifying it."""

    effect: Effect[A, E, R]
    f: Callable[[A], Effect[Any, E, R2]]


@dataclass(frozen=True)
class TapError[A, E, R, R2]:
    """An effect that inspects the error value without modifying it."""

    effect: Effect[A, E, R]
    f: Callable[[E], Effect[Any, E, R2]]


# Type alias for the Effect union
type Effect[A, E, R] = (
    Succeed[A, E, R]
    | Fail[A, E, R]
    | Sync[A, E, R]
    | Async[A, E, R]
    | TrySync[A, E, R]
    | TryAsync[A, E, R]
    | Suspend[A, E, R]
    | Tap[A, E, R, Any]
    | TapError[A, E, R, Any]
)


# ============================================================================
# Exit (Result of running an effect)
# ============================================================================


@dataclass(frozen=True)
class ExitSuccess[A]:
    """Successful exit with a value."""

    value: A


@dataclass(frozen=True)
class ExitFailure[E]:
    """Failed exit with an error."""

    error: E


# Type alias for the Exit union
type Exit[A, E] = ExitSuccess[A] | ExitFailure[E]


# ============================================================================
# Constructors
# ============================================================================


def succeed[A](value: A) -> Effect[A, Never, None]:
    """
    Create an effect that succeeds with a value.

    Example:
        >>> effect = Effect.succeed(42)
    """
    return Succeed(value)


def fail[E](error: E) -> Effect[Never, E, None]:
    """
    Create an effect that fails with an error.

    Example:
        >>> effect = Effect.fail("Something went wrong")
    """
    return Fail(error)


def sync[A](thunk: Callable[[], A]) -> Effect[A, Never, None]:
    """
    Create an effect from a synchronous computation.

    The computation is not executed immediately - it's deferred until
    the effect is run by the runtime.

    Example:
        >>> effect = Effect.sync(lambda: print("Hello"))
        >>> # Nothing printed yet - it's just a description
        >>> # Will print when the effect is run
    """
    return Sync(thunk)


def async_[A](thunk: Callable[[], Awaitable[A]]) -> Effect[A, Never, None]:
    """
    Create an effect from an asynchronous computation.

    The computation is not executed immediately - it's deferred until
    the effect is run by the runtime.

    Note: Uses async_ (with underscore) since 'async' is a Python keyword.

    Example:
        >>> import asyncio
        >>> effect = Effect.async_(lambda: asyncio.sleep(1))
        >>> # Sleep doesn't happen yet - only when the effect is run
    """
    return Async(thunk)


def try_sync[A](thunk: Callable[[], A]) -> Effect[A, Exception, None]:
    """
    Create an effect from a synchronous computation that might throw.

    Exceptions are captured and converted to effect errors.

    Example:
        >>> effect = Effect.try_sync(lambda: int("not a number"))
        >>> result = Effect.run_sync_exit(effect)
        >>> # Returns ExitFailure(ValueError(...))
    """
    return TrySync(thunk)


def try_async[A](thunk: Callable[[], Awaitable[A]]) -> Effect[A, Exception, None]:
    """
    Create an effect from an asynchronous computation that might throw.

    Exceptions are captured and converted to effect errors.

    Example:
        >>> import asyncio
        >>> async def might_fail():
        ...     await asyncio.sleep(0.1)
        ...     raise ValueError("oops")
        >>> effect = Effect.try_async(might_fail)
        >>> result = await Effect.run_async_exit(effect)
        >>> # Returns ExitFailure(ValueError("oops"))
    """
    return TryAsync(thunk)


def suspend[A, E, R](thunk: Callable[[], Effect[A, E, R]]) -> Effect[A, E, R]:
    """
    Delay the creation of an effect until runtime.

    The thunk is called each time the effect is run, allowing for:
    - Lazy evaluation of effects
    - Re-execution of side effects on each run
    - Capturing fresh state each time

    Example:
        >>> i = 0
        >>> # Bad - effect created once, i captured at creation
        >>> bad = effect.succeed((i := i + 1))
        >>> effect.run_sync(bad)  # 1
        >>> effect.run_sync(bad)  # 1 (same effect, same i)
        >>>
        >>> # Good - effect created fresh each run
        >>> good = effect.suspend(lambda: effect.succeed((i := i + 1)))
        >>> effect.run_sync(good)  # 2
        >>> effect.run_sync(good)  # 3 (fresh effect, fresh i!)
    """
    return Suspend(thunk)


# ============================================================================
# Combinators
# ============================================================================


def tap[A](
    f: Callable[[A], Effect[Any, Any, Any]],
) -> Callable[[Effect[A, Any, Any]], Effect[A, Any, Any]]:
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


def tap_error[E](
    f: Callable[[E], Effect[Any, Any, Any]],
) -> Callable[[Effect[Any, E, Any]], Effect[Any, E, Any]]:
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


# ============================================================================
# Runtime
# ============================================================================


def run_sync[A, E](effect: Effect[A, E, None]) -> A:
    """
    Execute a synchronous effect and return its value.

    This will pattern match on the effect primitives and execute them.
    Only works with synchronous effects (Succeed, Fail, Sync, Tap, TapError).

    Example:
        >>> effect = Effect.succeed(42)
        >>> result = Effect.run_sync(effect)
        >>> assert result == 42

    Raises:
        Exception: If the effect fails, raises the error
        RuntimeError: If the effect cannot be run synchronously
    """
    match effect:
        case Succeed(value):
            return value
        case Sync(thunk):
            return thunk()
        case Fail(error):
            if isinstance(error, BaseException):
                raise error
            msg = f"effect failed: {error}"
            raise RuntimeError(msg)
        case Tap(inner_effect, f):
            # Run the inner effect
            result = run_sync(inner_effect)
            # Run the tap function for side effects (ignore result)
            run_sync(f(result))
            # Return the original value
            return result
        case TapError(inner_effect, f):
            # Try to run the inner effect
            try:
                return run_sync(inner_effect)
            except BaseException as e:
                # Run the tap function for side effects (ignore result)
                with contextlib.suppress(BaseException):
                    run_sync(f(cast(Any, e)))
                # Re-raise the original error
                raise
        case Suspend(thunk):
            # Execute thunk to get effect, then run it
            return run_sync(thunk())
        case TrySync(thunk):
            # Execute thunk - exceptions propagate
            return thunk()
        case _:
            msg = f"Cannot run {type(effect).__name__} synchronously"
            raise RuntimeError(msg)


def run_async[A, E](effect: Effect[A, E, None]) -> Awaitable[A]:
    """
    Execute an effect asynchronously and return an awaitable.

    This can run both synchronous and asynchronous effects.

    Example:
        >>> import asyncio
        >>> effect = Effect.async_(lambda: asyncio.sleep(0.1))
        >>> result = await Effect.run_async(effect)

    Raises:
        Exception: If the effect fails, raises the error
        RuntimeError: If the effect cannot be run
    """

    async def execute() -> A:  # noqa: PLR0911
        match effect:
            case Succeed(value):
                return value
            case Sync(thunk):
                return thunk()
            case Async(thunk):
                return await thunk()
            case Fail(error):
                if isinstance(error, BaseException):
                    raise error
                msg = f"effect failed: {error}"
                raise RuntimeError(msg)
            case Tap(inner_effect, f):
                # Run the inner effect
                result = await run_async(inner_effect)
                # Run the tap function for side effects (ignore result)
                await run_async(f(result))
                # Return the original value
                return result
            case TapError(inner_effect, f):
                # Try to run the inner effect
                try:
                    return await run_async(inner_effect)
                except BaseException as e:
                    # Run the tap function for side effects (ignore result)
                    with contextlib.suppress(BaseException):
                        await run_async(f(cast(Any, e)))
                    # Re-raise the original error
                    raise
            case Suspend(thunk):
                # Execute thunk to get effect, then run it
                return await run_async(thunk())
            case TrySync(thunk):
                # Execute sync thunk - exceptions propagate
                return thunk()
            case TryAsync(thunk):
                # Execute async thunk - exceptions propagate
                return await thunk()
            case _:
                msg = f"Cannot run {type(effect).__name__}"
                raise RuntimeError(msg)

    return execute()


def run_sync_exit[A, E](effect: Effect[A, E, None]) -> Exit[A, E]:  # noqa: PLR0911, PLR0912
    """
    Execute a synchronous effect and return Exit instead of throwing.

    Returns ExitSuccess on success or ExitFailure on error.
    This keeps errors as values all the way through.

    Example:
        >>> result = effect.run_sync_exit(effect.succeed(42))
        >>> match result:
        ...     case effect.ExitSuccess(value):
        ...         print(f"Success: {value}")
        ...     case effect.ExitFailure(error):
        ...         print(f"Error: {error}")

    Raises:
        RuntimeError: If the effect cannot be run synchronously
    """
    match effect:
        case Succeed(value):
            return ExitSuccess(value)
        case Sync(thunk):
            return ExitSuccess(thunk())
        case Fail(error):
            return ExitFailure(error)
        case Tap(inner_effect, f):
            # Run the inner effect
            inner_result = run_sync_exit(inner_effect)
            match inner_result:
                case ExitSuccess(value):
                    # Run tap for side effects (ignore result)
                    run_sync(f(value))
                    return ExitSuccess(value)
                case ExitFailure(error):
                    return ExitFailure(error)
        case TapError(inner_effect, f):
            # Run the inner effect
            inner_result = run_sync_exit(inner_effect)
            match inner_result:
                case ExitSuccess(value):
                    return ExitSuccess(value)
                case ExitFailure(error):
                    # Run tap_error for side effects (ignore result)
                    with contextlib.suppress(BaseException):
                        run_sync(f(cast(Any, error)))
                    return ExitFailure(error)
        case Suspend(thunk):
            # Execute thunk to get effect, then run it
            return run_sync_exit(thunk())
        case TrySync(thunk):
            # Execute and catch exceptions
            try:
                return ExitSuccess(thunk())
            except Exception as e:
                return ExitFailure(cast(E, e))
        case _:
            msg = f"Cannot run {type(effect).__name__} synchronously"
            raise RuntimeError(msg)


def run_async_exit[A, E](effect: Effect[A, E, None]) -> Awaitable[Exit[A, E]]:
    """
    Execute an effect asynchronously and return Exit instead of throwing.

    Returns ExitSuccess on success or ExitFailure on error.
    This can run both synchronous and asynchronous effects.

    Example:
        >>> result = await effect.run_async_exit(effect.succeed(42))
        >>> match result:
        ...     case effect.ExitSuccess(value):
        ...         print(f"Success: {value}")
        ...     case effect.ExitFailure(error):
        ...         print(f"Error: {error}")

    Raises:
        RuntimeError: If the effect cannot be run
    """

    async def execute() -> Exit[A, E]:  # noqa: PLR0911, PLR0912
        match effect:
            case Succeed(value):
                return ExitSuccess(value)
            case Sync(thunk):
                return ExitSuccess(thunk())
            case Async(thunk):
                return ExitSuccess(await thunk())
            case Fail(error):
                return ExitFailure(error)
            case Tap(inner_effect, f):
                # Run the inner effect
                inner_result = await run_async_exit(inner_effect)
                match inner_result:
                    case ExitSuccess(value):
                        # Run tap for side effects (ignore result)
                        await run_async(f(value))
                        return ExitSuccess(value)
                    case ExitFailure(error):
                        return ExitFailure(error)
            case TapError(inner_effect, f):
                # Run the inner effect
                inner_result = await run_async_exit(inner_effect)
                match inner_result:
                    case ExitSuccess(value):
                        return ExitSuccess(value)
                    case ExitFailure(error):
                        # Run tap_error for side effects (ignore result)
                        with contextlib.suppress(BaseException):
                            await run_async(f(cast(Any, error)))
                        return ExitFailure(error)
            case Suspend(thunk):
                # Execute thunk to get effect, then run it
                return await run_async_exit(thunk())
            case TrySync(thunk):
                # Execute sync thunk and catch exceptions
                try:
                    return ExitSuccess(thunk())
                except Exception as e:
                    return ExitFailure(cast(E, e))
            case TryAsync(thunk):
                # Execute async thunk and catch exceptions
                try:
                    return ExitSuccess(await thunk())
                except Exception as e:
                    return ExitFailure(cast(E, e))
            case _:
                msg = f"Cannot run {type(effect).__name__}"
                raise RuntimeError(msg)

    return execute()


__all__ = [
    "Async",
    "Effect",
    "Exit",
    "ExitFailure",
    "ExitSuccess",
    "Fail",
    "Never",
    "Succeed",
    "Suspend",
    "Sync",
    "Tap",
    "TapError",
    "TryAsync",
    "TrySync",
    "async_",
    "fail",
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
