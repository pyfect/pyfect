"""
Core Effect primitives and operations.

This module contains the tagged union of effect primitives and functions
that operate on them. Import as `Effect` for the Effect TS-like API.
"""

from datetime import timedelta
from typing import Any, Never, Protocol, cast

from pyfect.context import Context
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
# provide and delay live here — they depend on Context, Layer, and Sleep
# ============================================================================


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


# ============================================================================
# Re-exports — everything accessible as effect.<name>
# ============================================================================

from pyfect.constructors import (  # noqa: E402
    async_,
    fail,
    service,
    succeed,
    suspend,
    sync,
    try_async,
    try_sync,
)
from pyfect.control import (  # noqa: E402
    AllMode,
    UnlessEffectCallable,
    WhenCallable,
    WhenEffectCallable,
    all_,
    for_each,
    if_,
    loop,
    unless,
    unless_effect,
    when,
    when_effect,
    zip_,
    zip_with,
)
from pyfect.error import (  # noqa: E402
    CatchAllCallable,
    CatchIfCallable,
    CatchSomeCallable,
    catch_all,
    catch_if,
    catch_some,
)
from pyfect.exit import Exit, Failure, Success  # noqa: E402
from pyfect.interop import (  # noqa: E402
    either,
    from_either,
    from_option,
    option,
)
from pyfect.runtime import (  # noqa: E402
    run_async,
    run_async_exit,
    run_sync,
    run_sync_exit,
)
from pyfect.transform import (  # noqa: E402
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
    map_,
    map_error,
    tap,
    tap_error,
)

__all__ = [
    "AllMode",
    "AsCallable",
    "Async",
    "CatchAllCallable",
    "CatchIfCallable",
    "CatchSomeCallable",
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
    "all_",
    "as_",
    "async_",
    "catch_all",
    "catch_if",
    "catch_some",
    "delay",
    "either",
    "fail",
    "flat_map",
    "for_each",
    "from_either",
    "from_option",
    "if_",
    "ignore",
    "loop",
    "map_",
    "map_error",
    "option",
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
    "zip_",
    "zip_with",
]
