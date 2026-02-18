"""
Effect runtime - execution of effects to produce results.

Architecture: two internal fiber runners, both returning Exit[A, E]:
  - _run_sync_fiber  — synchronous, errors on async primitives
  - _run_async_fiber — async coroutine, handles all primitives

All public run_* functions are thin wrappers around these two.
Adding a new primitive requires touching only _run_sync_fiber and
_run_async_fiber. run_fork is a one-liner on top of _run_async_fiber.

Python's asyncio.Task IS a fiber — fork, join, cancel, and structured
concurrency (asyncio.TaskGroup) are provided natively. No need to
reimplement scheduling primitives that Python already ships.
"""

import asyncio
import contextlib
import time
from collections.abc import Awaitable
from typing import Any, Never, cast

from pyfect import context as context_module
from pyfect import either as either_module
from pyfect import exit
from pyfect.context import Context
from pyfect.exit import Exit
from pyfect.primitives import (
    Absorb,
    Async,
    Effect,
    Fail,
    FlatMap,
    Ignore,
    Map,
    MapError,
    MemoizedEffect,
    Provide,
    Service,
    Sleep,
    Succeed,
    Suspend,
    Sync,
    Tap,
    TapError,
    TryAsync,
    TrySync,
    ZipPar,
)

# ============================================================================
# Helper
# ============================================================================


def _unwrap[A, E](result: Exit[A, E]) -> A:
    """Extract the success value from an Exit, raising on failure."""
    if isinstance(result, exit.Success):
        return result.value
    error = result.error  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
    if isinstance(error, BaseException):
        raise error
    msg = f"effect failed: {error}"
    raise RuntimeError(msg)


# ============================================================================
# Internal fiber runners (context-aware, always return Exit)
# ============================================================================


def _run_sync_fiber[A, E](  # noqa: PLR0911, PLR0912, PLR0915
    effect: Effect[A, E, Any], ctx: Context[Any], memo: dict[int, Any]
) -> Exit[A, E]:
    match effect:
        case Succeed(value):
            return exit.succeed(value)
        case Sync(thunk):
            return exit.succeed(thunk())
        case Fail(error):
            return exit.fail(error)
        case Tap(inner_effect, f):
            inner_result = _run_sync_fiber(inner_effect, ctx, memo)
            if isinstance(inner_result, exit.Success):
                _unwrap(_run_sync_fiber(f(inner_result.value), ctx, memo))
                return exit.succeed(inner_result.value)
            return exit.fail(inner_result.error)  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
        case Map(inner_effect, f):
            inner_result = _run_sync_fiber(inner_effect, ctx, memo)
            if isinstance(inner_result, exit.Success):
                return exit.succeed(f(inner_result.value))
            return exit.fail(inner_result.error)  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
        case FlatMap(inner_effect, f):
            inner_result = _run_sync_fiber(inner_effect, ctx, memo)
            if isinstance(inner_result, exit.Success):
                return _run_sync_fiber(f(inner_result.value), ctx, memo)
            return exit.fail(inner_result.error)  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
        case Ignore(inner_effect):
            _run_sync_fiber(inner_effect, ctx, memo)  # type: ignore[unreachable]
            return exit.succeed(cast(A, None))
        case MapError(inner_effect, f):
            inner_result = _run_sync_fiber(inner_effect, ctx, memo)
            if isinstance(inner_result, exit.Success):
                return exit.succeed(inner_result.value)
            original = cast(Any, inner_result.error)  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
            transformed = f(original)
            if isinstance(transformed, BaseException) and isinstance(original, BaseException):
                transformed.__cause__ = original
            return exit.fail(transformed)
        case Absorb(inner_effect):
            inner_result = _run_sync_fiber(inner_effect, ctx, memo)  # type: ignore[unreachable]
            if isinstance(inner_result, exit.Success):
                return exit.succeed(cast(A, either_module.Right(inner_result.value)))
            return exit.succeed(cast(A, either_module.Left(inner_result.error)))  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
        case TapError(inner_effect, f):
            inner_result = _run_sync_fiber(inner_effect, ctx, memo)
            if isinstance(inner_result, exit.Success):
                return exit.succeed(inner_result.value)
            with contextlib.suppress(BaseException):
                _unwrap(_run_sync_fiber(f(cast(Any, inner_result.error)), ctx, memo))  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
            return exit.fail(inner_result.error)  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
        case Suspend(thunk):
            return _run_sync_fiber(thunk(), ctx, memo)
        case TrySync(thunk):
            try:
                return exit.succeed(thunk())
            except Exception as e:
                return exit.fail(cast(E, e))
        case Service(tag):
            return exit.succeed(context_module.get(ctx, tag))
        case Provide(inner_effect, new_ctx):
            return _run_sync_fiber(inner_effect, context_module.merge(ctx, new_ctx), memo)
        case MemoizedEffect(inner_effect, layer_id):
            if layer_id in memo:
                return exit.succeed(memo[layer_id])
            inner_result = _run_sync_fiber(inner_effect, ctx, memo)
            if isinstance(inner_result, exit.Success):
                memo[layer_id] = inner_result.value
                return exit.succeed(inner_result.value)
            return exit.fail(inner_result.error)  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
        case Sleep(duration):
            time.sleep(duration.total_seconds())  # type: ignore[unreachable]
            return exit.succeed(cast(A, None))
        case ZipPar(effects):
            results = []
            for eff in effects:
                inner: Exit[Any, Any] = _run_sync_fiber(eff, ctx, memo)
                if isinstance(inner, exit.Success):
                    results.append(inner.value)
                else:
                    return exit.fail(inner.error)  # type: ignore[attr-defined,return-value]
            return exit.succeed(cast(A, tuple(results)))
        case _:
            msg = f"Cannot run {type(effect).__name__} synchronously"
            raise RuntimeError(msg)


async def _run_async_fiber[A, E](  # noqa: PLR0911, PLR0912, PLR0915
    effect: Effect[A, E, Any], ctx: Context[Any], memo: dict[int, Any]
) -> Exit[A, E]:
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
            inner_result = await _run_async_fiber(inner_effect, ctx, memo)
            if isinstance(inner_result, exit.Success):
                _unwrap(await _run_async_fiber(f(inner_result.value), ctx, memo))
                return exit.succeed(inner_result.value)
            return exit.fail(inner_result.error)  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
        case Map(inner_effect, f):
            inner_result = await _run_async_fiber(inner_effect, ctx, memo)
            if isinstance(inner_result, exit.Success):
                return exit.succeed(f(inner_result.value))
            return exit.fail(inner_result.error)  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
        case FlatMap(inner_effect, f):
            inner_result = await _run_async_fiber(inner_effect, ctx, memo)
            if isinstance(inner_result, exit.Success):
                return await _run_async_fiber(f(inner_result.value), ctx, memo)
            return exit.fail(inner_result.error)  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
        case Ignore(inner_effect):
            await _run_async_fiber(inner_effect, ctx, memo)  # type: ignore[unreachable]
            return exit.succeed(cast(A, None))
        case MapError(inner_effect, f):
            inner_result = await _run_async_fiber(inner_effect, ctx, memo)
            if isinstance(inner_result, exit.Success):
                return exit.succeed(inner_result.value)
            original = cast(Any, inner_result.error)  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
            transformed = f(original)
            if isinstance(transformed, BaseException) and isinstance(original, BaseException):
                transformed.__cause__ = original
            return exit.fail(transformed)
        case Absorb(inner_effect):
            inner_result = await _run_async_fiber(inner_effect, ctx, memo)  # type: ignore[unreachable]
            if isinstance(inner_result, exit.Success):
                return exit.succeed(cast(A, either_module.Right(inner_result.value)))
            return exit.succeed(cast(A, either_module.Left(inner_result.error)))  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
        case TapError(inner_effect, f):
            inner_result = await _run_async_fiber(inner_effect, ctx, memo)
            if isinstance(inner_result, exit.Success):
                return exit.succeed(inner_result.value)
            with contextlib.suppress(BaseException):
                _unwrap(await _run_async_fiber(f(cast(Any, inner_result.error)), ctx, memo))  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
            return exit.fail(inner_result.error)  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
        case Suspend(thunk):
            return await _run_async_fiber(thunk(), ctx, memo)
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
            return await _run_async_fiber(inner_effect, context_module.merge(ctx, new_ctx), memo)
        case MemoizedEffect(inner_effect, layer_id):
            if layer_id in memo:
                return exit.succeed(memo[layer_id])
            inner_result = await _run_async_fiber(inner_effect, ctx, memo)
            if isinstance(inner_result, exit.Success):
                memo[layer_id] = inner_result.value
                return exit.succeed(inner_result.value)
            return exit.fail(inner_result.error)  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
        case Sleep(duration):
            await asyncio.sleep(duration.total_seconds())  # type: ignore[unreachable]
            return exit.succeed(cast(A, None))
        case ZipPar(effects):
            fiber_results: list[Exit[Any, Any]] = list(
                await asyncio.gather(*(_run_async_fiber(e, ctx, memo) for e in effects))
            )
            values: list[Any] = []
            for r in fiber_results:
                if isinstance(r, exit.Success):
                    values.append(r.value)
                else:
                    return exit.fail(r.error)  # type: ignore[attr-defined,return-value]
            return exit.succeed(cast(A, tuple(values)))
        case _:  # pragma: no cover
            msg = f"Unknown effect type: {type(effect).__name__}"
            raise RuntimeError(msg)


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
    return _unwrap(_run_sync_fiber(effect, context_module.empty(), {}))


def run_async[A, E](effect: Effect[A, E, Never]) -> Awaitable[A]:
    """
    Execute an effect asynchronously and return an awaitable.

    Handles both synchronous and asynchronous primitives. The returned
    awaitable is a plain asyncio coroutine — compose it freely with
    asyncio.gather, asyncio.TaskGroup, or any other asyncio primitive.

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

    async def _go() -> A:
        return _unwrap(await _run_async_fiber(effect, context_module.empty(), {}))

    return _go()


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
    return _run_sync_fiber(effect, context_module.empty(), {})


def run_async_exit[A, E](effect: Effect[A, E, Never]) -> Awaitable[Exit[A, E]]:
    """
    Execute an effect asynchronously and return Exit instead of throwing.

    Returns an awaitable that resolves to Success on success or Failure on
    error. The returned coroutine never raises — errors are values. This
    makes it a natural building block for asyncio.create_task (run_fork).

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
    return _run_async_fiber(effect, context_module.empty(), {})


__all__ = [
    "run_async",
    "run_async_exit",
    "run_sync",
    "run_sync_exit",
]
