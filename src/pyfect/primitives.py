"""
Effect primitives - the tagged union of effect types.

This module contains the core dataclasses that represent different kinds
of effects, and the Effect union type that combines them all.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

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

    thunk: "Callable[[], Effect[A, E, R]]"


@dataclass(frozen=True)
class Tap[A, E, R]:
    """An effect that inspects the success value without modifying it."""

    effect: "Effect[A, E, R]"
    f: "Callable[[A], Effect[Any, E, R]]"


@dataclass(frozen=True)
class TapError[A, E, R]:
    """An effect that inspects the error value without modifying it."""

    effect: "Effect[A, E, R]"
    f: "Callable[[E], Effect[Any, E, R]]"


@dataclass(frozen=True)
class Map[A, B, E, R]:
    """An effect that transforms the success value."""

    effect: "Effect[A, E, R]"
    f: Callable[[A], B]


@dataclass(frozen=True)
class FlatMap[A, B, E, R]:
    """An effect that chains effects together (monadic bind)."""

    effect: "Effect[A, E, R]"
    f: "Callable[[A], Effect[B, E, R]]"


@dataclass(frozen=True)
class Ignore[A, E, R]:
    """An effect that ignores both success and failure, always succeeding with None."""

    effect: "Effect[A, E, R]"


@dataclass(frozen=True)
class MapError[A, E, E2, R]:
    """An effect that transforms the error value."""

    effect: "Effect[A, E, R]"
    f: Callable[[E], E2]


# Type alias for the Effect union
type Effect[A, E, R] = (
    Succeed[A, E, R]
    | Fail[A, E, R]
    | Sync[A, E, R]
    | Async[A, E, R]
    | TrySync[A, E, R]
    | TryAsync[A, E, R]
    | Suspend[A, E, R]
    | Tap[A, E, R]
    | TapError[A, E, R]
    | Map[Any, A, E, R]
    | FlatMap[Any, A, E, R]
    | Ignore[Any, Any, R]
    | MapError[A, Any, E, R]
)


__all__ = [
    "Async",
    "Effect",
    "Fail",
    "FlatMap",
    "Ignore",
    "Map",
    "MapError",
    "Succeed",
    "Suspend",
    "Sync",
    "Tap",
    "TapError",
    "TryAsync",
    "TrySync",
]
