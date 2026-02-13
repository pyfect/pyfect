"""
Effect runtime - execution of effects to produce results.

This module contains the runtime functions that execute effects,
converting effect descriptions into actual computation.
"""

import contextlib
from collections.abc import Awaitable
from typing import Any, Never, cast

from pyfect import context as context_module
from pyfect import exit
from pyfect.context import Context
from pyfect.exit import Exit
from pyfect.primitives import (
    Async,
    Effect,
    Fail,
    FlatMap,
    Ignore,
    Map,
    MapError,
    Provide,
    Service,
    Succeed,
    Suspend,
    Sync,
    Tap,
    TapError,
    TryAsync,
    TrySync,
)

# ============================================================================
# Internal runners (context-aware)
# ============================================================================


def _run_sync[A, E](effect: Effect[A, E, Any], ctx: Context[Any]) -> A:  # noqa: PLR0911, PLR0912
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
            result = _run_sync(inner_effect, ctx)
            _run_sync(f(result), ctx)
            return result
        case Map(inner_effect, f):
            result = _run_sync(inner_effect, ctx)
            return f(result)
        case FlatMap(inner_effect, f):
            result = _run_sync(inner_effect, ctx)
            return _run_sync(f(result), ctx)
        case Ignore(inner_effect):
            with contextlib.suppress(BaseException):
                _run_sync(inner_effect, ctx)
            return cast(A, None)
        case MapError(inner_effect, f):
            inner_result = _run_sync_exit(inner_effect, ctx)
            match inner_result:
                case exit.Success(value):
                    return value
                case exit.Failure(error):
                    transformed = f(cast(Any, error))
                    if isinstance(transformed, BaseException):
                        if isinstance(error, BaseException):
                            raise transformed from error
                        raise transformed
                    msg = f"effect failed: {transformed}"
                    raise RuntimeError(msg)
        case TapError(inner_effect, f):
            try:
                return _run_sync(inner_effect, ctx)
            except BaseException as e:
                with contextlib.suppress(BaseException):
                    _run_sync(f(cast(Any, e)), ctx)
                raise
        case Suspend(thunk):
            return _run_sync(thunk(), ctx)
        case TrySync(thunk):
            return thunk()
        case Service(tag):
            return context_module.get(ctx, tag)
        case Provide(inner_effect, new_ctx):
            return _run_sync(inner_effect, new_ctx)
        case _:
            msg = f"Cannot run {type(effect).__name__} synchronously"
            raise RuntimeError(msg)


def _run_async[A, E](effect: Effect[A, E, Any], ctx: Context[Any]) -> Awaitable[A]:
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
                result = await _run_async(inner_effect, ctx)
                await _run_async(f(result), ctx)
                return result
            case Map(inner_effect, f):
                result = await _run_async(inner_effect, ctx)
                return f(result)
            case FlatMap(inner_effect, f):
                result = await _run_async(inner_effect, ctx)
                return await _run_async(f(result), ctx)
            case Ignore(inner_effect):
                with contextlib.suppress(BaseException):
                    await _run_async(inner_effect, ctx)
                return cast(A, None)
            case MapError(inner_effect, f):
                inner_result = await _run_async_exit(inner_effect, ctx)
                match inner_result:
                    case exit.Success(value):
                        return value
                    case exit.Failure(error):
                        transformed = f(cast(Any, error))
                        if isinstance(transformed, BaseException):
                            if isinstance(error, BaseException):
                                raise transformed from error
                            raise transformed
                        msg = f"effect failed: {transformed}"
                        raise RuntimeError(msg)
            case TapError(inner_effect, f):
                try:
                    return await _run_async(inner_effect, ctx)
                except BaseException as e:
                    with contextlib.suppress(BaseException):
                        await _run_async(f(cast(Any, e)), ctx)
                    raise
            case Suspend(thunk):
                return await _run_async(thunk(), ctx)
            case TrySync(thunk):
                return thunk()
            case TryAsync(thunk):
                return await thunk()
            case Service(tag):
                return context_module.get(ctx, tag)
            case Provide(inner_effect, new_ctx):
                return await _run_async(inner_effect, new_ctx)

    return execute()


def _run_sync_exit[A, E](effect: Effect[A, E, Any], ctx: Context[Any]) -> Exit[A, E]:  # noqa: PLR0911, PLR0912
    match effect:
        case Succeed(value):
            return exit.succeed(value)
        case Sync(thunk):
            return exit.succeed(thunk())
        case Fail(error):
            return exit.fail(error)
        case Tap(inner_effect, f):
            inner_result = _run_sync_exit(inner_effect, ctx)
            match inner_result:
                case exit.Success(value):
                    _run_sync(f(value), ctx)
                    return exit.succeed(value)
                case exit.Failure(error):
                    return exit.fail(error)
        case Map(inner_effect, f):
            inner_result = _run_sync_exit(inner_effect, ctx)
            match inner_result:
                case exit.Success(value):
                    return exit.succeed(f(value))
                case exit.Failure(error):
                    return exit.fail(error)
        case FlatMap(inner_effect, f):
            inner_result = _run_sync_exit(inner_effect, ctx)
            match inner_result:
                case exit.Success(value):
                    return _run_sync_exit(f(value), ctx)
                case exit.Failure(error):
                    return exit.fail(error)
        case Ignore(inner_effect):
            _run_sync_exit(inner_effect, ctx)
            return exit.succeed(cast(A, None))
        case MapError(inner_effect, f):
            inner_result = _run_sync_exit(inner_effect, ctx)
            match inner_result:
                case exit.Success(value):
                    return exit.succeed(value)
                case exit.Failure(error):
                    return exit.fail(f(cast(Any, error)))
        case TapError(inner_effect, f):
            inner_result = _run_sync_exit(inner_effect, ctx)
            match inner_result:
                case exit.Success(value):
                    return exit.succeed(value)
                case exit.Failure(error):
                    with contextlib.suppress(BaseException):
                        _run_sync(f(cast(Any, error)), ctx)
                    return exit.fail(error)
        case Suspend(thunk):
            return _run_sync_exit(thunk(), ctx)
        case TrySync(thunk):
            try:
                return exit.succeed(thunk())
            except Exception as e:
                return exit.fail(cast(E, e))
        case Service(tag):
            return exit.succeed(context_module.get(ctx, tag))
        case Provide(inner_effect, new_ctx):
            return _run_sync_exit(inner_effect, new_ctx)
        case _:
            msg = f"Cannot run {type(effect).__name__} synchronously"
            raise RuntimeError(msg)


def _run_async_exit[A, E](effect: Effect[A, E, Any], ctx: Context[Any]) -> Awaitable[Exit[A, E]]:
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
                inner_result = await _run_async_exit(inner_effect, ctx)
                match inner_result:
                    case exit.Success(value):
                        await _run_async(f(value), ctx)
                        return exit.succeed(value)
                    case exit.Failure(error):
                        return exit.fail(error)
            case Map(inner_effect, f):
                inner_result = await _run_async_exit(inner_effect, ctx)
                match inner_result:
                    case exit.Success(value):
                        return exit.succeed(f(value))
                    case exit.Failure(error):
                        return exit.fail(error)
            case FlatMap(inner_effect, f):
                inner_result = await _run_async_exit(inner_effect, ctx)
                match inner_result:
                    case exit.Success(value):
                        return await _run_async_exit(f(value), ctx)
                    case exit.Failure(error):
                        return exit.fail(error)
            case Ignore(inner_effect):
                await _run_async_exit(inner_effect, ctx)
                return exit.succeed(cast(A, None))
            case MapError(inner_effect, f):
                inner_result = await _run_async_exit(inner_effect, ctx)
                match inner_result:
                    case exit.Success(value):
                        return exit.succeed(value)
                    case exit.Failure(error):
                        return exit.fail(f(cast(Any, error)))
            case TapError(inner_effect, f):
                inner_result = await _run_async_exit(inner_effect, ctx)
                match inner_result:
                    case exit.Success(value):
                        return exit.succeed(value)
                    case exit.Failure(error):
                        with contextlib.suppress(BaseException):
                            await _run_async(f(cast(Any, error)), ctx)
                        return exit.fail(error)
            case Suspend(thunk):
                return await _run_async_exit(thunk(), ctx)
            case TrySync(thunk):
                try:
                    return exit.succeed(thunk())
                except Exception as e:
                    return exit.fail(cast(E, e))
            case TryAsync(thunk):
                try:
                    return exit.succeed(await thunk())
                except Exception as e:
                    return exit.fail(cast(E, e))
            case Service(tag):
                return exit.succeed(context_module.get(ctx, tag))
            case Provide(inner_effect, new_ctx):
                return await _run_async_exit(inner_effect, new_ctx)

    return execute()


# ============================================================================
# Public API
# ============================================================================


def run_sync[A, E](effect: Effect[A, E, Never]) -> A:
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
    return _run_sync(effect, context_module.empty())


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
    return _run_async(effect, context_module.empty())


def run_sync_exit[A, E](effect: Effect[A, E, Never]) -> Exit[A, E]:
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
    return _run_sync_exit(effect, context_module.empty())


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
    return _run_async_exit(effect, context_module.empty())


__all__ = [
    "run_async",
    "run_async_exit",
    "run_sync",
    "run_sync_exit",
]
