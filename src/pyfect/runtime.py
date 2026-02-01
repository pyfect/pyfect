"""
Effect runtime - execution of effects to produce results.

This module contains the runtime functions that execute effects,
converting effect descriptions into actual computation.
"""

from __future__ import annotations

import contextlib
from collections.abc import Awaitable
from typing import Any, cast

from pyfect import exit
from pyfect.exit import Exit
from pyfect.primitives import (
    Async,
    Effect,
    Fail,
    Map,
    Succeed,
    Suspend,
    Sync,
    Tap,
    TapError,
    TryAsync,
    TrySync,
)

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
        case Map(inner_effect, f):
            # Run the inner effect and transform the result
            result = run_sync(inner_effect)
            return f(result)
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
            case Map(inner_effect, f):
                # Run the inner effect and transform the result
                result = await run_async(inner_effect)
                return f(result)
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
            return exit.succeed(value)
        case Sync(thunk):
            return exit.succeed(thunk())
        case Fail(error):
            return exit.fail(error)
        case Tap(inner_effect, f):
            # Run the inner effect
            inner_result = run_sync_exit(inner_effect)
            match inner_result:
                case exit.ExitSuccess(value):
                    # Run tap for side effects (ignore result)
                    run_sync(f(value))
                    return exit.succeed(value)
                case exit.ExitFailure(error):
                    return exit.fail(error)
        case Map(inner_effect, f):
            # Run the inner effect and transform successful result
            inner_result = run_sync_exit(inner_effect)
            match inner_result:
                case exit.ExitSuccess(value):
                    return exit.succeed(f(value))
                case exit.ExitFailure(error):
                    return exit.fail(error)
        case TapError(inner_effect, f):
            # Run the inner effect
            inner_result = run_sync_exit(inner_effect)
            match inner_result:
                case exit.ExitSuccess(value):
                    return exit.succeed(value)
                case exit.ExitFailure(error):
                    # Run tap_error for side effects (ignore result)
                    with contextlib.suppress(BaseException):
                        run_sync(f(cast(Any, error)))
                    return exit.fail(error)
        case Suspend(thunk):
            # Execute thunk to get effect, then run it
            return run_sync_exit(thunk())
        case TrySync(thunk):
            # Execute and catch exceptions
            try:
                return exit.succeed(thunk())
            except Exception as e:
                return exit.fail(cast(E, e))
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
                return exit.succeed(value)
            case Sync(thunk):
                return exit.succeed(thunk())
            case Async(thunk):
                return exit.succeed(await thunk())
            case Fail(error):
                return exit.fail(error)
            case Tap(inner_effect, f):
                # Run the inner effect
                inner_result = await run_async_exit(inner_effect)
                match inner_result:
                    case exit.ExitSuccess(value):
                        # Run tap for side effects (ignore result)
                        await run_async(f(value))
                        return exit.succeed(value)
                    case exit.ExitFailure(error):
                        return exit.fail(error)
            case Map(inner_effect, f):
                # Run the inner effect and transform successful result
                inner_result = await run_async_exit(inner_effect)
                match inner_result:
                    case exit.ExitSuccess(value):
                        return exit.succeed(f(value))
                    case exit.ExitFailure(error):
                        return exit.fail(error)
            case TapError(inner_effect, f):
                # Run the inner effect
                inner_result = await run_async_exit(inner_effect)
                match inner_result:
                    case exit.ExitSuccess(value):
                        return exit.succeed(value)
                    case exit.ExitFailure(error):
                        # Run tap_error for side effects (ignore result)
                        with contextlib.suppress(BaseException):
                            await run_async(f(cast(Any, error)))
                        return exit.fail(error)
            case Suspend(thunk):
                # Execute thunk to get effect, then run it
                return await run_async_exit(thunk())
            case TrySync(thunk):
                # Execute sync thunk and catch exceptions
                try:
                    return exit.succeed(thunk())
                except Exception as e:
                    return exit.fail(cast(E, e))
            case TryAsync(thunk):
                # Execute async thunk and catch exceptions
                try:
                    return exit.succeed(await thunk())
                except Exception as e:
                    return exit.fail(cast(E, e))
            case _:
                msg = f"Cannot run {type(effect).__name__}"
                raise RuntimeError(msg)

    return execute()


__all__ = [
    "run_async",
    "run_async_exit",
    "run_sync",
    "run_sync_exit",
]
