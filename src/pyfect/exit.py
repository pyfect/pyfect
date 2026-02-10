"""
Exit types and constructors.

Exit represents the result of running an effect - either success or failure.
This module provides the Exit union type and constructors for creating exits.
"""

from dataclasses import dataclass

# ============================================================================
# Exit Types
# ============================================================================


@dataclass(frozen=True)
class Success[A]:
    """Successful exit with a value."""

    value: A


@dataclass(frozen=True)
class Failure[E]:
    """Failed exit with an error."""

    error: E


# Type alias for the Exit union
type Exit[A, E] = Success[A] | Failure[E]


# ============================================================================
# Constructors
# ============================================================================


def succeed[A, E](value: A) -> Exit[A, E]:
    """
    Create a successful exit with a value.

    Example:
        >>> exit = Exit.succeed(42)
        >>> match exit:
        ...     case Success(value):
        ...         print(f"Success: {value}")
    """
    return Success(value)


def fail[A, E](error: E) -> Exit[A, E]:
    """
    Create a failed exit with an error.

    Example:
        >>> exit = Exit.fail("Something went wrong")
        >>> match exit:
        ...     case Failure(error):
        ...         print(f"Error: {error}")
    """
    return Failure(error)


__all__ = [
    "Exit",
    "Failure",
    "Success",
    "fail",
    "succeed",
]
