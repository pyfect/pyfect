"""
Pipe utility for composing effects in a readable way.

Inspired by Effect TS pipe function.
"""

from collections.abc import Callable
from typing import TypeVar, overload

A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")
D = TypeVar("D")
E = TypeVar("E")
F = TypeVar("F")
G = TypeVar("G")
H = TypeVar("H")
I = TypeVar("I")  # noqa: E741
J = TypeVar("J")


# Overloads for type safety with different numbers of functions
@overload
def pipe[A](value: A, /) -> A: ...


@overload
def pipe(value: A, f1: Callable[[A], B], /) -> B: ...


@overload
def pipe(value: A, f1: Callable[[A], B], f2: Callable[[B], C], /) -> C: ...


@overload
def pipe(
    value: A, f1: Callable[[A], B], f2: Callable[[B], C], f3: Callable[[C], D], /
) -> D: ...


@overload
def pipe(
    value: A,
    f1: Callable[[A], B],
    f2: Callable[[B], C],
    f3: Callable[[C], D],
    f4: Callable[[D], E],
    /,
) -> E: ...


@overload
def pipe(
    value: A,
    f1: Callable[[A], B],
    f2: Callable[[B], C],
    f3: Callable[[C], D],
    f4: Callable[[D], E],
    f5: Callable[[E], F],
    /,
) -> F: ...


@overload
def pipe(
    value: A,
    f1: Callable[[A], B],
    f2: Callable[[B], C],
    f3: Callable[[C], D],
    f4: Callable[[D], E],
    f5: Callable[[E], F],
    f6: Callable[[F], G],
    /,
) -> G: ...


@overload
def pipe(
    value: A,
    f1: Callable[[A], B],
    f2: Callable[[B], C],
    f3: Callable[[C], D],
    f4: Callable[[D], E],
    f5: Callable[[E], F],
    f6: Callable[[F], G],
    f7: Callable[[G], H],
    /,
) -> H: ...


@overload
def pipe(
    value: A,
    f1: Callable[[A], B],
    f2: Callable[[B], C],
    f3: Callable[[C], D],
    f4: Callable[[D], E],
    f5: Callable[[E], F],
    f6: Callable[[F], G],
    f7: Callable[[G], H],
    f8: Callable[[H], I],
    /,
) -> I: ...


@overload
def pipe(
    value: A,
    f1: Callable[[A], B],
    f2: Callable[[B], C],
    f3: Callable[[C], D],
    f4: Callable[[D], E],
    f5: Callable[[E], F],
    f6: Callable[[F], G],
    f7: Callable[[G], H],
    f8: Callable[[H], I],
    f9: Callable[[I], J],
    /,
) -> J: ...


def pipe[A](value: A, *fns: Callable) -> object: # type: ignore
    """
    Compose functions left-to-right, passing the result of each to the next.

    This allows for readable effect composition similar to method chaining
    but using pure functions.

    Example:
        >>> from pyfect import effect, pipe
        >>> result = pipe(
        ...     effect.succeed(10),
        ...     effect.tap(lambda x: effect.sync(lambda: print(f"Value: {x}"))),
        ... )

    Args:
        value: The initial value
        *fns: Functions to apply in sequence

    Returns:
        The result of applying all functions in sequence
    """
    result = value
    for f in fns:
        result = f(result)
    return result


__all__ = ["pipe"]
