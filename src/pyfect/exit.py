"""
Exit types and constructors.

Exit represents the result of running an effect - either success or failure.
This module provides the Exit union type and constructors for creating exits.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Never, TypeIs, overload

# ============================================================================
# Exit Types
# ============================================================================


class Exit[A, E = Never]:
    """Base class for Exit variants.

    Using a base class (rather than a union type alias) allows type checkers
    to extract TypeVars A, E nominally from Exit[A, E] instances,
    which is required for correct TypeVar solving in heterogeneous collections
    and generic contexts.
    """

    __slots__ = ()


@dataclass(frozen=True)
class Success[A, E = Never](Exit[A, E]):
    """Successful exit with a value."""

    value: A


@dataclass(frozen=True)
class Failure[A = Never, E = Never](Exit[A, E]):
    """Failed exit with an error."""

    error: E


# ============================================================================
# Constructors
# ============================================================================


def succeed[A, E = Never](value: A) -> Exit[A, E]:
    """
    Create a successful exit with a value.

    Example:
        ```python
        exit = Exit.succeed(42)
        match exit:
            case Success(value):
                print(f"Success: {value}")
        ```
    """
    return Success(value)


def fail[E, A = Never](error: E) -> Exit[A, E]:
    """
    Create a failed exit with an error.

    Example:
        ```python
        exit = Exit.fail("Something went wrong")
        match exit:
            case Failure(error):
                print(f"Error: {error}")
        ```
    """
    return Failure(error)


# ============================================================================
# Type Guards
# ============================================================================


def is_success[A, E](exit: Exit[A, E]) -> TypeIs[Success[A, E]]:
    """
    Type guard to check if an Exit is Success.

    Example:
        ```python
        result = run_sync_exit(effect.succeed(42))
        if is_success(result):
            print(f"Value: {result.value}")  # Type checker knows result is Success
        ```
    """
    return isinstance(exit, Success)


def is_failure[A, E](exit: Exit[A, E]) -> TypeIs[Failure[A, E]]:
    """
    Type guard to check if an Exit is Failure.

    Example:
        ```python
        result = run_sync_exit(effect.fail("error"))
        if is_failure(result):
            print(f"Error: {result.error}")  # Type checker knows result is Failure
        ```
    """
    return isinstance(exit, Failure)


# ============================================================================
# Pattern Matching
# ============================================================================


@overload
def match_[A, E, B, C](
    *,
    on_success: Callable[[A], B],
    on_failure: Callable[[E], C],
) -> Callable[[Exit[A, E]], B | C]:
    """Curried version: returns a function that matches an Exit."""


@overload
def match_[A, B, C](
    exit: Exit[A, Never],
    *,
    on_success: Callable[[A], B],
    on_failure: Callable[[Never], C],
) -> B:
    """Data-first version for Success[A, Never]: always returns B."""


@overload
def match_[E, B, C](
    exit: Exit[Never, E],
    *,
    on_success: Callable[[Never], B],
    on_failure: Callable[[E], C],
) -> C:
    """Data-first version for Failure[Never, E]: always returns C."""


@overload
def match_[A, E, B, C](
    exit: Exit[A, E],
    *,
    on_success: Callable[[A], B],
    on_failure: Callable[[E], C],
) -> B | C:
    """Data-first version: matches an Exit directly."""


def match_[A, E, B, C](
    exit: Exit[A, E] | None = None,
    *,
    on_success: Callable[[A], B],
    on_failure: Callable[[E], C],
) -> B | C | Callable[[Exit[A, E]], B | C]:
    """
    Match on an Exit, handling both Success and Failure cases.

    Provides an alternative to pattern matching with guaranteed exhaustiveness.
    Supports both curried (for use in pipes) and data-first styles.

    Args:
        exit: Optional Exit to match on. If None, returns a curried function.
        on_success: Function to apply if the Exit is Success.
        on_failure: Function to apply if the Exit is Failure.

    Returns:
        If exit is provided: B | C (the result of applying the appropriate function).
        If exit is None: A function that takes an Exit and returns B | C.

    Example:
        ```python
        from pyfect import effect

        # Data-first style
        result = match_(
            effect.run_sync_exit(eff),
            on_success=lambda value: f"Got: {value}",
            on_failure=lambda error: f"Error: {error}"
        )
        ```
    """
    if exit is None:
        # Curried version
        def _match(ex: Exit[A, E]) -> B | C:
            if isinstance(ex, Success):
                return on_success(ex.value)
            return on_failure(ex.error)  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]

        return _match

    # Data-first version
    if isinstance(exit, Success):
        return on_success(exit.value)
    return on_failure(exit.error)  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]


__all__ = [
    "Exit",
    "Failure",
    "Success",
    "fail",
    "is_failure",
    "is_success",
    "match_",
    "succeed",
]
