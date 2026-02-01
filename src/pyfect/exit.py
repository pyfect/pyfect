"""
Exit types and constructors.

Exit represents the result of running an effect - either success or failure.
This module provides the Exit union type and constructors for creating exits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NoReturn

# Never type for impossible errors
type Never = NoReturn


# ============================================================================
# Exit Types
# ============================================================================


@dataclass(frozen=True)
class ExitSuccess[A]:
    """Successful exit with a value."""

    value: A


@dataclass(frozen=True)
class ExitFailure[E]:
    """Failed exit with an error."""

    error: E


# Type alias for the Exit union
type Exit[A, E] = ExitSuccess[A] | ExitFailure[E]


# ============================================================================
# Constructors
# ============================================================================


def succeed[A, E](value: A) -> Exit[A, E]:
    """
    Create a successful exit with a value.

    Example:
        >>> exit = Exit.succeed(42)
        >>> match exit:
        ...     case ExitSuccess(value):
        ...         print(f"Success: {value}")
    """
    return ExitSuccess(value)


def fail[A, E](error: E) -> Exit[A, E]:
    """
    Create a failed exit with an error.

    Example:
        >>> exit = Exit.fail("Something went wrong")
        >>> match exit:
        ...     case ExitFailure(error):
        ...         print(f"Error: {error}")
    """
    return ExitFailure(error)


__all__ = [
    "Exit",
    "ExitFailure",
    "ExitSuccess",
    "Never",
    "fail",
    "succeed",
]
