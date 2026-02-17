"""
Layer - a typed blueprint for constructing services.

Layer[Out, E, In] represents a blueprint that, given services In,
constructs services Out, possibly failing with E.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import count
from typing import Any, Never, Protocol, cast, overload

import pyfect.context as context_module
from pyfect.context import Context
from pyfect.primitives import (
    Effect,
    FlatMap,
    Map,
    MemoizedEffect,
    Provide,
    Succeed,
    Sync,
    Tap,
    TapError,
)

_layer_counter = count()


@dataclass(frozen=True)
class Layer[Out, E = Never, In = Never]:
    """A typed blueprint for constructing services.

    Out is the service (or union of services) produced.
    E is the possible error during construction.
    In is the required services needed to construct Out.
    """

    _effect: Effect[Context[Out], E, In]
    _id: int = field(default_factory=lambda: next(_layer_counter))

    def __post_init__(self) -> None:
        if not isinstance(self._effect, MemoizedEffect):
            object.__setattr__(self, "_effect", MemoizedEffect(self._effect, self._id))


class LayerProvideCallable[In, E2 = Never, InOuter = Never](Protocol):
    def __call__[Out, E1](self, inner: Layer[Out, E1, In]) -> Layer[Out, E1 | E2, InOuter]: ...


class LayerTapCallable[E2 = Never, R2 = Never](Protocol):
    def __call__[Out, E, In](self, layer_: Layer[Out, E, In]) -> Layer[Out, E | E2, In | R2]: ...


class LayerTapErrorCallable[E2 = Never, R2 = Never](Protocol):
    def __call__[Out, E, In](self, layer_: Layer[Out, E, In]) -> Layer[Out, E | E2, In | R2]: ...


# ============================================================================
# Constructors
# ============================================================================


def succeed[Out](tag: type[Out], impl: Out) -> Layer[Out, Never, Never]:
    """Create a layer from a ready-made service implementation.

    Use when the implementation needs no dependencies and no initialization.

    Example:
        ```python
        from pyfect import layer, effect, pipe

        config_layer = layer.succeed(Config, ConfigImpl("INFO", "postgres://..."))

        runnable = pipe(
            effect.service(Config),
            effect.provide(config_layer),
        )
        ```
    """
    return Layer(Succeed(context_module.make((tag, impl))))


@overload
def merge[Out1, Out2](  # pyright: ignore[reportOverlappingOverload]
    l1: Layer[Out1, Never, Never],
    l2: Layer[Out2, Never, Never],
) -> Layer[Out1 | Out2, Never, Never]: ...


@overload
def merge[Out1, E1, Out2, E2](  # type: ignore[overload-overlap]
    l1: Layer[Out1, E1, Never],
    l2: Layer[Out2, E2, Never],
) -> Layer[Out1 | Out2, E1 | E2, Never]: ...


@overload
def merge[Out1, In1, Out2, In2](
    l1: Layer[Out1, Never, In1],
    l2: Layer[Out2, Never, In2],
) -> Layer[Out1 | Out2, Never, In1 | In2]: ...


@overload
def merge[Out1, E1, In1, Out2, E2, In2](
    l1: Layer[Out1, E1, In1],
    l2: Layer[Out2, E2, In2],
) -> Layer[Out1 | Out2, E1 | E2, In1 | In2]: ...


def merge[Out1, E1, In1, Out2, E2, In2](
    l1: Layer[Out1, E1, In1],
    l2: Layer[Out2, E2, In2],
) -> Layer[Out1 | Out2, E1 | E2, In1 | In2]:
    """Combine two layers into one that produces both services.

    The resulting layer requires all dependencies of both layers and may
    fail with errors from either.

    Example:
        ```python
        from pyfect import layer, effect, pipe

        app_layer = layer.merge(
            layer.succeed(Config, ConfigImpl()),
            layer.succeed(Logger, LoggerImpl()),
        )
        # Layer[Config | Logger, Never, Never]

        runnable = pipe(
            effect.service(Config, Logger),
            effect.provide(app_layer),
        )
        ```
    """
    inner = cast(
        Effect[Context[Out1 | Out2], E1 | E2, In1 | In2],
        FlatMap(
            l1._effect,
            lambda ctx1: Map(l2._effect, lambda ctx2: context_module.merge(ctx1, ctx2)),
        ),
    )
    return cast(Layer[Out1 | Out2, E1 | E2, In1 | In2], Layer(inner))


def provide[In, E2 = Never, InOuter = Never](
    outer: Layer[In, E2, InOuter],
) -> LayerProvideCallable[In, E2, InOuter]:
    """Wire one layer's output into another's input requirement.

    Returns a function that takes an inner layer (which needs services In) and
    satisfies those requirements using the outer layer. The outer layer's own
    requirements (InOuter) become the new requirements of the result.

    Designed for use with pipe to chain dependency resolution:

    Example:
        ```python
        from pyfect import layer, effect, pipe

        logger_layer = layer.effect(
            Logger,
            pipe(effect.service(Config), effect.map(lambda c: Logger(c.level))),
        )
        # Layer[Logger, Never, Config]

        config_layer = layer.succeed(Config, ConfigImpl("INFO"))
        # Layer[Config, Never, Never]

        app_layer = pipe(
            logger_layer,
            layer.provide(config_layer),
        )
        # Layer[Logger, Never, Never]
        ```
    """

    def _apply(inner: Layer[Any, Any, Any]) -> Layer[Any, Any, Any]:
        eff = cast(
            Effect[Context[Any], Any, Any],
            FlatMap(
                outer._effect,
                lambda ctx_in: Provide(inner._effect, ctx_in),
            ),
        )
        return Layer(eff)

    return cast(LayerProvideCallable[In, E2, InOuter], _apply)


def launch[Out, E](layer_: Layer[Out, E, Never]) -> Effect[None, E, Never]:
    """Convert a fully-resolved layer into a runnable effect.

    Constructs all services in the layer and discards the resulting context.
    Use this when the layer exists purely for its construction side effects,
    such as starting a server or initialising background workers.

    Example:
        ```python
        from pyfect import layer, effect

        class HTTPServer:
            def __init__(self) -> None:
                print("Listening on http://localhost:3000")

        server_layer = layer.sync(HTTPServer, HTTPServer)

        effect.run_sync(layer.launch(server_layer))
        # Listening on http://localhost:3000
        ```
    """
    return Map(layer_._effect, lambda _: None)


def tap[Out, B, E2 = Never, R2 = Never](
    f: Callable[[Context[Out]], Effect[B, E2, R2]],
) -> LayerTapCallable[E2, R2]:
    """Peek at the built context when layer construction succeeds.

    Runs f for its side effects and passes the context through unchanged.
    If f fails, that failure propagates.

    Example:
        ```python
        from pyfect import layer, effect, pipe

        server_layer = pipe(
            layer.sync(HTTPServer, HTTPServer),
            layer.tap(lambda _ctx: effect.sync(lambda: print("server ready"))),
        )
        ```
    """

    def _apply(layer_: Layer[Any, Any, Any]) -> Layer[Any, Any, Any]:
        return Layer(cast(Effect[Context[Any], Any, Any], Tap(layer_._effect, f)))

    return cast(LayerTapCallable[E2, R2], _apply)


def tap_error[E, B, E2 = Never, R2 = Never](
    f: Callable[[E], Effect[B, E2, R2]],
) -> LayerTapErrorCallable[E2, R2]:
    """Peek at the error when layer construction fails.

    Runs f for its side effects and re-raises the original error unchanged.
    If f also fails, both errors merge.

    Example:
        ```python
        from pyfect import layer, effect, pipe

        server_layer = pipe(
            layer.effect(HTTPServer, effect.fail(IOError("port in use"))),
            layer.tap_error(lambda e: effect.sync(lambda: print(f"failed: {e}"))),
        )
        ```
    """

    def _apply(layer_: Layer[Any, Any, Any]) -> Layer[Any, Any, Any]:
        return Layer(cast(Effect[Context[Any], Any, Any], TapError(layer_._effect, f)))

    return cast(LayerTapErrorCallable[E2, R2], _apply)


def effect[Out, E, In](tag: type[Out], eff: Effect[Out, E, In]) -> Layer[Out, E, In]:
    """Create a layer from an effectful constructor.

    Use when the implementation requires dependencies from the context,
    async initialization, or construction that may fail.

    Example:
        ```python
        from pyfect import layer, effect, pipe

        logger_layer = layer.effect(
            Logger,
            pipe(
                effect.service(Config),
                effect.flat_map(lambda config: effect.succeed(Logger(config.level))),
            ),
        )
        # Layer[Logger, Never, Config]
        ```
    """
    return Layer(Map(eff, lambda impl: context_module.make((tag, impl))))


def sync[Out](tag: type[Out], thunk: Callable[[], Out]) -> Layer[Out, Never, Never]:
    """Create a layer from a synchronous constructor.

    Use when the implementation needs no dependencies but requires
    some initialization work.

    Example:
        ```python
        from pyfect import layer, effect, pipe

        logger_layer = layer.sync(Logger, lambda: Logger(level="INFO"))

        runnable = pipe(
            effect.service(Logger),
            effect.provide(logger_layer),
        )
        ```
    """
    return Layer(Map(Sync(thunk), lambda impl: context_module.make((tag, impl))))


def fresh[Out, E, In](layer_: Layer[Out, E, In]) -> Layer[Out, E, In]:
    """Return a new layer instance that does not share memoization with the original.

    Normally, layers are memoized by identity: if the same layer appears
    multiple times in the dependency graph it is constructed only once.
    Use fresh when you explicitly want a separate construction for each use.

    Example:
        ```python
        from pyfect import layer, effect, pipe

        # A is constructed twice — once for B, once for C
        app_layer = layer.merge(
            layer.provide(b_layer, layer.fresh(a_layer)),
            layer.provide(c_layer, layer.fresh(a_layer)),
        )
        ```
    """
    inner = layer_._effect
    if isinstance(inner, MemoizedEffect):
        inner = inner.effect
    return Layer(inner)


__all__ = [
    "Layer",
    "LayerProvideCallable",
    "LayerTapCallable",
    "LayerTapErrorCallable",
    "effect",
    "fresh",
    "launch",
    "merge",
    "provide",
    "succeed",
    "sync",
    "tap",
    "tap_error",
]
