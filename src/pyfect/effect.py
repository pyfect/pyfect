"""
Core Effect primitives and operations.

This module contains the tagged union of effect primitives and functions
that operate on them. Import as `Effect` for the Effect TS-like API.
"""

from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any, Never, Protocol, cast, overload

import pyfect.either as either_module
import pyfect.option as option_module

# Re-export Effect primitives from primitives module
from pyfect.context import Context
from pyfect.control import (
    UnlessEffectCallable,
    WhenCallable,
    WhenEffectCallable,
    for_each,
    if_,
    loop,
    unless,
    unless_effect,
    when,
    when_effect,
    zip,
    zip_with,
)

# Re-export Exit types from exit module for backward compatibility
from pyfect.exit import Exit, Failure, Success
from pyfect.layer import Layer
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
    Sleep,
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


def succeed[A](value: A) -> Effect[A]:
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


@overload
def service[S1](tag: type[S1], /) -> Effect[S1, Never, S1]: ...


@overload
def service[S1, S2](tag1: type[S1], tag2: type[S2], /) -> Effect[tuple[S1, S2], Never, S1 | S2]: ...


@overload
def service[S1, S2, S3](
    tag1: type[S1], tag2: type[S2], tag3: type[S3], /
) -> Effect[tuple[S1, S2, S3], Never, S1 | S2 | S3]: ...


@overload
def service[S1, S2, S3, S4](
    tag1: type[S1], tag2: type[S2], tag3: type[S3], tag4: type[S4], /
) -> Effect[tuple[S1, S2, S3, S4], Never, S1 | S2 | S3 | S4]: ...


@overload
def service[S1, S2, S3, S4, S5](
    tag1: type[S1], tag2: type[S2], tag3: type[S3], tag4: type[S4], tag5: type[S5], /
) -> Effect[tuple[S1, S2, S3, S4, S5], Never, S1 | S2 | S3 | S4 | S5]: ...


@overload
def service[S1, S2, S3, S4, S5, S6](
    tag1: type[S1],
    tag2: type[S2],
    tag3: type[S3],
    tag4: type[S4],
    tag5: type[S5],
    tag6: type[S6],
    /,
) -> Effect[tuple[S1, S2, S3, S4, S5, S6], Never, S1 | S2 | S3 | S4 | S5 | S6]: ...


@overload
def service[S1, S2, S3, S4, S5, S6, S7](
    tag1: type[S1],
    tag2: type[S2],
    tag3: type[S3],
    tag4: type[S4],
    tag5: type[S5],
    tag6: type[S6],
    tag7: type[S7],
    /,
) -> Effect[tuple[S1, S2, S3, S4, S5, S6], Never, S1 | S2 | S3 | S4 | S5 | S6 | S7]: ...


@overload
def service[S1, S2, S3, S4, S5, S6, S7, S8](
    tag1: type[S1],
    tag2: type[S2],
    tag3: type[S3],
    tag4: type[S4],
    tag5: type[S5],
    tag6: type[S6],
    tag7: type[S7],
    tag8: type[S8],
    /,
) -> Effect[tuple[S1, S2, S3, S4, S5, S6], Never, S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8]: ...


@overload
def service[S1, S2, S3, S4, S5, S6, S7, S8, S9](
    tag1: type[S1],
    tag2: type[S2],
    tag3: type[S3],
    tag4: type[S4],
    tag5: type[S5],
    tag6: type[S6],
    tag7: type[S7],
    tag8: type[S8],
    tag9: type[S9],
    /,
) -> Effect[tuple[S1, S2, S3, S4, S5, S6], Never, S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | S9]: ...


@overload
def service[S1, S2, S3, S4, S5, S6, S7, S8, S9, S10](
    tag1: type[S1],
    tag2: type[S2],
    tag3: type[S3],
    tag4: type[S4],
    tag5: type[S5],
    tag6: type[S6],
    tag7: type[S7],
    tag8: type[S8],
    tag9: type[S9],
    tag10: type[S10],
    /,
) -> Effect[
    tuple[S1, S2, S3, S4, S5, S6], Never, S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | S9 | S10
]: ...


def service(*tags: type) -> Effect:  # type: ignore[type-arg, misc]
    """
    Create an effect that looks up one or more services from the context.

    For a single tag, returns the service instance directly.
    For multiple tags, returns a tuple of instances in the same order.
    The effect requires all provided tags as context.

    Example:
        ```python
        # Single service
        eff = service(Database)  # Effect[Database, Never, Database]

        # Multiple services
        eff = service(Database, Logger)  # Effect[tuple[Database, Logger], Never, Database | Logger]
        ```
    """
    if len(tags) == 1:
        return Service(tags[0])
    t1, t2, *rest = tags
    result: Effect = FlatMap(  # type: ignore[type-arg]
        Service(t1),
        lambda s1, t=t2: Map(Service(t), lambda s2: (s1, s2)),  # type: ignore[misc]
    )
    for tag in rest:
        result = FlatMap(result, lambda acc, t=tag: Map(Service(t), lambda s: (*acc, s)))  # type: ignore[misc]
    return result


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
        if isinstance(opt, option_module.Some):
            return Succeed(opt.value)
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
        case _:  # pragma: no cover
            msg = f"Unexpected Either variant: {type(e).__name__}"
            raise AssertionError(msg)


class DelayCallable(Protocol):
    def __call__[A, E, R](self, eff: Effect[A, E, R]) -> Effect[A, E, R]: ...


def delay(duration: timedelta) -> DelayCallable:
    """
    Delay the execution of an effect by the given duration.

    The delay runs first using a non-blocking sleep (asyncio.sleep in async
    runtimes, time.sleep in the sync runtime), then the original effect runs.
    The value, error, and requirement types are preserved unchanged.

    Designed for use with pipe:

    Example:
        ```python
        from datetime import timedelta
        from pyfect import effect, pipe

        program = pipe(
            effect.succeed(42),
            effect.delay(timedelta(seconds=2)),
        )

        effect.run_sync(program)  # waits 2 seconds, then returns 42
        ```
    """

    def _apply(eff: Effect[Any, Any, Any]) -> Effect[Any, Any, Any]:
        return FlatMap(cast(Effect[None, Never, Never], Sleep(duration)), lambda _: eff)

    return cast(DelayCallable, _apply)


class ProvideCallable[R, E2 = Never](Protocol):
    def __call__[A, E1](self, eff: Effect[A, E1, R]) -> Effect[A, E1 | E2, Never]: ...


def provide[R, E2 = Never](  # type: ignore[misc]
    ctx_or_layer: Context[R] | Layer[R, E2, Never],
) -> ProvideCallable[R, E2]:
    """
    Provide a context or a layer to an effect, satisfying all its requirements.

    Designed to be used with pipe:

    Example (with context):
        ```python
        from pyfect import effect, context, pipe

        runnable = pipe(
            program,
            effect.provide(context.make((Database, db_impl))),
        )
        effect.run_sync(runnable)
        ```

    Example (with layer):
        ```python
        from pyfect import effect, layer, pipe

        db_layer = layer.succeed(Database, db_impl)

        runnable = pipe(
            program,
            effect.provide(db_layer),
        )
        effect.run_sync(runnable)
        ```
    """
    if isinstance(ctx_or_layer, Layer):
        layer_eff = ctx_or_layer._effect

        def _apply_layer(eff: Effect[Any, Any, Any]) -> Effect[Any, Any, Any]:
            return FlatMap(layer_eff, lambda ctx: Provide(eff, ctx))  # type: ignore[return-value]

        return cast(ProvideCallable[R, E2], _apply_layer)

    def _apply_ctx(eff: Effect[Any, Any, Any]) -> Effect[Any, Any, Any]:
        return Provide(eff, ctx_or_layer)  # type: ignore[arg-type]

    return cast(ProvideCallable[R, E2], _apply_ctx)


# Re-export combinators
from pyfect.combinators import (  # noqa: E402
    AsCallable,
    FlatMapCallable,
    IgnoreCallable,
    MapCallable,
    MapErrorCallable,
    TapCallable,
    TapErrorCallable,
    as_,
    flat_map,
    ignore,
    map,
    map_error,
    tap,
    tap_error,
)

# Re-export runtime
from pyfect.runtime import (  # noqa: E402
    run_async,
    run_async_exit,
    run_sync,
    run_sync_exit,
)

__all__ = [
    "AsCallable",
    "Async",
    "DelayCallable",
    "Effect",
    "Exit",
    "Fail",
    "Failure",
    "FlatMap",
    "FlatMapCallable",
    "Ignore",
    "IgnoreCallable",
    "Layer",
    "Map",
    "MapCallable",
    "MapError",
    "MapErrorCallable",
    "Never",
    "Provide",
    "ProvideCallable",
    "Service",
    "Sleep",
    "Succeed",
    "Success",
    "Suspend",
    "Sync",
    "Tap",
    "TapCallable",
    "TapError",
    "TapErrorCallable",
    "TryAsync",
    "TrySync",
    "UnlessEffectCallable",
    "WhenCallable",
    "WhenEffectCallable",
    "as_",
    "async_",
    "delay",
    "fail",
    "flat_map",
    "for_each",
    "from_either",
    "from_option",
    "if_",
    "ignore",
    "loop",
    "map",
    "map_error",
    "provide",
    "run_async",
    "run_async_exit",
    "run_sync",
    "run_sync_exit",
    "service",
    "succeed",
    "suspend",
    "sync",
    "tap",
    "tap_error",
    "try_async",
    "try_sync",
    "unless",
    "unless_effect",
    "when",
    "when_effect",
    "zip",
    "zip_with",
]
