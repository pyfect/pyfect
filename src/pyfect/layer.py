"""
Layer - a typed blueprint for constructing services.

Layer[Out, E, In] represents a blueprint that, given services In,
constructs services Out, possibly failing with E.
"""

from dataclasses import dataclass
from typing import Never

import pyfect.context as context_module
from pyfect.context import Context
from pyfect.primitives import Effect, Succeed


@dataclass(frozen=True)
class Layer[Out, E = Never, In = Never]:
    """A typed blueprint for constructing services.

    Out is the service (or union of services) produced.
    E is the possible error during construction.
    In is the required services needed to construct Out.
    """

    _effect: Effect[Context[Out], E, In]


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


__all__ = [
    "Layer",
    "succeed",
]
