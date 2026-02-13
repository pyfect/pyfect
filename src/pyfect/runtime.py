"""
Effect runtime - execution of effects to produce results.

This module contains the runtime functions that execute effects,
converting effect descriptions into actual computation.
"""

import contextlib
from collections.abc import Awaitable
from typing import Any, Never, cast

from pyfect import exit
from pyfect.exit import Exit
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
# Runtime
# ============================================================================


def run_sync[A, E](effect: Effect[A, E, Never]) -> A:  # noqa: PLR0911, PLR0912
    """
    Execute a synchronous effect and return its value.

    Raises if the effect fails or contains async primitives.

    Example:
        ```python
        from pyfect import effect
        result = effect.run_sync(effect.succeed(42))  # 42
        ```

    Raises:
        BaseException: If the effect fails with an exception error value (re-raised as-is)
        RuntimeError: If the effect fails with a non-exception error value, or contains async
        primitives
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
        case FlatMap(inner_effect, f):
            # Run the inner effect, then run the effect returned by f
            result = run_sync(inner_effect)
            next_effect = f(result)
            return run_sync(next_effect)
        case Ignore(inner_effect):
            # Run the effect and ignore both success and failure
            with contextlib.suppress(BaseException):
                run_sync(inner_effect)
            return cast(A, None)
        case MapError(inner_effect, f):
            # Run the effect and transform errors
            inner_result = run_sync_exit(inner_effect)
            match inner_result:
                case exit.Success(value):
                    return value
                case exit.Failure(error):
                    # Transform the error and re-raise
                    transformed = f(cast(Any, error))
                    if isinstance(transformed, BaseException):
                        # Preserve exception chain if original error was an exception
                        if isinstance(error, BaseException):
                            raise transformed from error
                        raise transformed
                    msg = f"effect failed: {transformed}"
                    raise RuntimeError(msg)
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


def run_async[A, E](effect: Effect[A, E, Never]) -> Awaitable[A]:
    """
    Execute an effect asynchronously and return an awaitable.

    Handles both synchronous and asynchronous primitives.

    Example:
        ```python
        import asyncio
        from pyfect import effect
        result = await effect.run_async(effect.async_(lambda: asyncio.sleep(0.1)))
        ```

    Raises:
        BaseException: If the effect fails with an exception error value (re-raised as-is)
        RuntimeError: If the effect fails with a non-exception error value
    """

    async def execute() -> A:  # noqa: PLR0911, PLR0912
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
            case FlatMap(inner_effect, f):
                # Run the inner effect, then run the effect returned by f
                result = await run_async(inner_effect)
                next_effect = f(result)
                return await run_async(next_effect)
            case Ignore(inner_effect):
                # Run the effect and ignore both success and failure
                with contextlib.suppress(BaseException):
                    await run_async(inner_effect)
                return cast(A, None)
            case MapError(inner_effect, f):
                # Run the effect and transform errors
                inner_result = await run_async_exit(inner_effect)
                match inner_result:
                    case exit.Success(value):
                        return value
                    case exit.Failure(error):
                        # Transform the error and re-raise
                        transformed = f(cast(Any, error))
                        if isinstance(transformed, BaseException):
                            # Preserve exception chain if original error was an exception
                            if isinstance(error, BaseException):
                                raise transformed from error
                            raise transformed
                        msg = f"effect failed: {transformed}"
                        raise RuntimeError(msg)
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

    return execute()


def run_sync_exit[A, E](effect: Effect[A, E, Never]) -> Exit[A, E]:  # noqa: PLR0911, PLR0912
    """
    Execute a synchronous effect and return Exit instead of throwing.

    Returns Success on success or Failure on error.
    This keeps errors as values all the way through.

    Example:
        ```python
        result = effect.run_sync_exit(effect.succeed(42))
        match result:
            case effect.Success(value):
                print(f"Success: {value}")
            case effect.Failure(error):
                print(f"Error: {error}")
        ```

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
                case exit.Success(value):
                    # Run tap for side effects (ignore result)
                    run_sync(f(value))
                    return exit.succeed(value)
                case exit.Failure(error):
                    return exit.fail(error)
        case Map(inner_effect, f):
            # Run the inner effect and transform successful result
            inner_result = run_sync_exit(inner_effect)
            match inner_result:
                case exit.Success(value):
                    return exit.succeed(f(value))
                case exit.Failure(error):
                    return exit.fail(error)
        case FlatMap(inner_effect, f):
            # Run the inner effect, then run the effect returned by f
            inner_result = run_sync_exit(inner_effect)
            match inner_result:
                case exit.Success(value):
                    next_effect = f(value)
                    return run_sync_exit(next_effect)
                case exit.Failure(error):
                    return exit.fail(error)
        case Ignore(inner_effect):
            # Run the effect and ignore both success and failure
            run_sync_exit(inner_effect)  # Ignore the result
            return exit.succeed(cast(A, None))
        case MapError(inner_effect, f):
            # Run the effect and transform errors
            inner_result = run_sync_exit(inner_effect)
            match inner_result:
                case exit.Success(value):
                    return exit.succeed(value)
                case exit.Failure(error):
                    return exit.fail(f(cast(Any, error)))
        case TapError(inner_effect, f):
            # Run the inner effect
            inner_result = run_sync_exit(inner_effect)
            match inner_result:
                case exit.Success(value):
                    return exit.succeed(value)
                case exit.Failure(error):
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


def run_async_exit[A, E](effect: Effect[A, E, Never]) -> Awaitable[Exit[A, E]]:
    """
    Execute an effect asynchronously and return Exit instead of throwing.

    Returns Success on success or Failure on error.
    This can run both synchronous and asynchronous effects.

    Example:
        ```python
        result = await effect.run_async_exit(effect.succeed(42))
        match result:
            case effect.Success(value):
                print(f"Success: {value}")
            case effect.Failure(error):
                print(f"Error: {error}")
        ```
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
                    case exit.Success(value):
                        # Run tap for side effects (ignore result)
                        await run_async(f(value))
                        return exit.succeed(value)
                    case exit.Failure(error):
                        return exit.fail(error)
            case Map(inner_effect, f):
                # Run the inner effect and transform successful result
                inner_result = await run_async_exit(inner_effect)
                match inner_result:
                    case exit.Success(value):
                        return exit.succeed(f(value))
                    case exit.Failure(error):
                        return exit.fail(error)
            case FlatMap(inner_effect, f):
                # Run the inner effect, then run the effect returned by f
                inner_result = await run_async_exit(inner_effect)
                match inner_result:
                    case exit.Success(value):
                        next_effect = f(value)
                        return await run_async_exit(next_effect)
                    case exit.Failure(error):
                        return exit.fail(error)
            case Ignore(inner_effect):
                # Run the effect and ignore both success and failure
                await run_async_exit(inner_effect)  # Ignore the result
                return exit.succeed(cast(A, None))
            case MapError(inner_effect, f):
                # Run the effect and transform errors
                inner_result = await run_async_exit(inner_effect)
                match inner_result:
                    case exit.Success(value):
                        return exit.succeed(value)
                    case exit.Failure(error):
                        return exit.fail(f(cast(Any, error)))
            case TapError(inner_effect, f):
                # Run the inner effect
                inner_result = await run_async_exit(inner_effect)
                match inner_result:
                    case exit.Success(value):
                        return exit.succeed(value)
                    case exit.Failure(error):
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

    return execute()


__all__ = [
    "run_async",
    "run_async_exit",
    "run_sync",
    "run_sync_exit",
]
