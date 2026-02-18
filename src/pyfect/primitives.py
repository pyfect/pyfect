"""
Effect primitives - the tagged union of effect types.

This module contains the core dataclasses that represent different kinds
of effects, and the Effect base class that combines them all.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Never

from pyfect.either import Either

if TYPE_CHECKING:
    from pyfect.context import Context

# ============================================================================
# Effect base class
# ============================================================================


class Effect[A, E = Never, R = Never]:
    """Base class for all effect primitives.

    Using a base class (rather than a union type alias) allows type checkers
    to extract TypeVars A, E, R nominally from Effect[A, E, R] instances,
    which is required for correct TypeVar solving in multi-step pipe chains.
    """

    __slots__ = ()


# ============================================================================
# Effect Primitives
# ============================================================================


@dataclass(frozen=True)
class Succeed[A, E = Never, R = Never](Effect[A, E, R]):
    """An effect that succeeds with a value."""

    value: A


@dataclass(frozen=True)
class Fail[A = Never, E = Never, R = Never](Effect[A, E, R]):
    """An effect that fails with an error."""

    error: E


@dataclass(frozen=True)
class Sync[A, E = Never, R = Never](Effect[A, E, R]):
    """An effect that wraps a synchronous computation."""

    thunk: Callable[[], A]


@dataclass(frozen=True)
class Async[A, E = Never, R = Never](Effect[A, E, R]):
    """An effect that wraps an asynchronous computation."""

    thunk: Callable[[], Awaitable[A]]


@dataclass(frozen=True)
class TrySync[A, E = Never, R = Never](Effect[A, E, R]):
    """An effect that wraps a synchronous computation that might throw."""

    thunk: Callable[[], A]


@dataclass(frozen=True)
class TryAsync[A, E = Never, R = Never](Effect[A, E, R]):
    """An effect that wraps an asynchronous computation that might throw."""

    thunk: Callable[[], Awaitable[A]]


@dataclass(frozen=True)
class Suspend[A, E = Never, R = Never](Effect[A, E, R]):
    """An effect that delays effect creation until runtime."""

    thunk: "Callable[[], Effect[A, E, R]]"


@dataclass(frozen=True)
class Tap[A, E = Never, R = Never](Effect[A, E, R]):
    """An effect that inspects the success value without modifying it."""

    effect: "Effect[A, E, R]"
    f: "Callable[[A], Effect[Any, Any, Any]]"


@dataclass(frozen=True)
class TapError[A, E = Never, R = Never](Effect[A, E, R]):
    """An effect that inspects the error value without modifying it."""

    effect: "Effect[A, E, R]"
    f: "Callable[[E], Effect[Any, Any, Any]]"


@dataclass(frozen=True)
class Map[A, B, E = Never, R = Never](Effect[B, E, R]):
    """An effect that transforms the success value."""

    effect: "Effect[A, E, R]"
    f: Callable[[A], B]


@dataclass(frozen=True)
class FlatMap[A, B, E = Never, R = Never](Effect[B, E, R]):
    """An effect that chains effects together (monadic bind)."""

    effect: "Effect[A, E, R]"
    f: "Callable[[A], Effect[B, Any, Any]]"


@dataclass(frozen=True)
class Ignore[A = Never, E = Never, R = Never](Effect[None, Never, R]):
    """An effect that ignores both success and failure, always succeeding with None."""

    effect: "Effect[A, E, R]"


@dataclass(frozen=True)
class MapError[A, E, E2, R = Never](Effect[A, E2, R]):
    """An effect that transforms the error value."""

    effect: "Effect[A, E, R]"
    f: Callable[[E], E2]


@dataclass(frozen=True)
class Absorb[A, E = Never, R = Never](Effect[Either[A, E], Never, R]):
    """An effect that absorbs failures into the success channel as Either values.

    Converts Effect[A, E, R] into Effect[Either[A, E], Never, R]. A successful
    effect wraps its value in Right; a failed effect wraps its error in Left,
    turning the failure into a success value that never propagates.
    """

    effect: "Effect[A, E, R]"


@dataclass(frozen=True)
class Service[S](Effect[S, Never, S]):
    """An effect that looks up a service from the context."""

    tag: type[S]


@dataclass(frozen=True)
class Provide[A, E](Effect[A, E, Never]):
    """An effect that runs the inner effect with a provided context.

    Satisfies all requirements of the inner effect, so the resulting
    effect has R = Never.
    """

    effect: "Effect[A, E, Any]"
    context: "Context[Any]"


@dataclass(frozen=True)
class MemoizedEffect[A, E = Never, R = Never](Effect[A, E, R]):
    """Wraps a layer's effect so the runtime can memoize it by layer_id."""

    effect: "Effect[A, E, R]"
    layer_id: int


@dataclass(frozen=True)
class Sleep(Effect[None, Never, Never]):
    """An effect that delays execution by the given duration."""

    duration: timedelta


@dataclass(frozen=True)
class ZipPar[A = Never, E = Never, R = Never](Effect[A, E, R]):
    """An effect that runs multiple effects concurrently and zips results into a tuple."""

    effects: "tuple[Effect[Any, Any, Any], ...]"


__all__ = [
    "Absorb",
    "Async",
    "Effect",
    "Fail",
    "FlatMap",
    "Ignore",
    "Map",
    "MapError",
    "MemoizedEffect",
    "Provide",
    "Service",
    "Sleep",
    "Succeed",
    "Suspend",
    "Sync",
    "Tap",
    "TapError",
    "TryAsync",
    "TrySync",
    "ZipPar",
]
