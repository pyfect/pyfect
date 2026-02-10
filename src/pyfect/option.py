"""
Option type for representing optional values.

An Option[A] is either Some[A], containing a value, or Nothing,
representing the absence of a value.
"""

from dataclasses import dataclass
from typing import TypeIs

# ============================================================================
# Option Types
# ============================================================================


@dataclass(frozen=True)
class Some[A]:
    """An Option containing a value."""

    value: A


@dataclass(frozen=True)
class Nothing:
    """An Option representing the absence of a value."""


# Singleton - reuse instead of instantiating Nothing each time
NOTHING = Nothing()

# Type alias for the Option union
type Option[A] = Some[A] | Nothing


# ============================================================================
# Constructors
# ============================================================================


def some[A](value: A) -> Option[A]:
    """
    Create an Option containing a value.

    Example:
        >>> opt = some(42)
        >>> assert isinstance(opt, Some)
    """
    return Some(value)


def nothing() -> Nothing:
    """
    Create an Option representing the absence of a value.

    Returns the NOTHING singleton.

    Example:
        >>> opt = nothing()
        >>> assert opt is NOTHING
    """
    return NOTHING


# ============================================================================
# Guards
# ============================================================================


def is_some[A](option: Option[A]) -> TypeIs[Some[A]]:
    """
    Return True if the Option contains a value.

    Example:
        >>> is_some(some(42))
        True
        >>> is_some(nothing())
        False
    """
    return isinstance(option, Some)


def is_nothing[A](option: Option[A]) -> TypeIs[Nothing]:
    """
    Return True if the Option is Nothing.

    Example:
        >>> is_nothing(nothing())
        True
        >>> is_nothing(some(42))
        False
    """
    return isinstance(option, Nothing)


__all__ = [
    "NOTHING",
    "Nothing",
    "Option",
    "Some",
    "is_nothing",
    "is_some",
    "nothing",
    "some",
]
