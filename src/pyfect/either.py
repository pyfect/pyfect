"""
Either type for representing one of two exclusive values.

An Either[R, L] is either a Right[R], representing a success or primary value,
or a Left[L], representing a failure or alternative value. Unlike Effect, Either
is not lazy — it is a plain value you can pattern match on immediately, with no
runtime required.
"""

from dataclasses import dataclass
from typing import Never, TypeIs

# ============================================================================
# Either Types
# ============================================================================


@dataclass(frozen=True)
class Right[R]:
    """An Either containing a Right (success) value."""

    value: R


@dataclass(frozen=True)
class Left[L]:
    """An Either containing a Left (failure) value."""

    value: L


# Type alias for the Either union
type Either[R, L = Never] = Right[R] | Left[L]


# ============================================================================
# Constructors
# ============================================================================


def right[R, L = Never](value: R) -> Either[R, L]:
    """
    Create an Either with a Right value.

    Example:
        >>> e = right(42)
        >>> match e:
        ...     case Right(value):
        ...         print(f"Right: {value}")
        Right: 42
    """
    return Right(value)


def left[L, R = Never](value: L) -> Either[R, L]:
    """
    Create an Either with a Left value.

    Example:
        >>> e = left("oops")
        >>> match e:
        ...     case Left(value):
        ...         print(f"Left: {value}")
        Left: oops
    """
    return Left(value)


# ============================================================================
# Guards
# ============================================================================


def is_right[R, L](either: Either[R, L]) -> TypeIs[Right[R]]:
    """
    Return True if the Either is a Right value.

    Example:
        >>> is_right(right(42))
        True
        >>> is_right(left("oops"))
        False
    """
    return isinstance(either, Right)


def is_left[R, L](either: Either[R, L]) -> TypeIs[Left[L]]:
    """
    Return True if the Either is a Left value.

    Example:
        >>> is_left(left("oops"))
        True
        >>> is_left(right(42))
        False
    """
    return isinstance(either, Left)


__all__ = [
    "Either",
    "Left",
    "Right",
    "is_left",
    "is_right",
    "left",
    "right",
]
