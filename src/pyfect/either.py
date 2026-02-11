"""
Either type for representing one of two exclusive values.

An Either[R, L] is either a Right[R], representing a success or primary value,
or a Left[L], representing a failure or alternative value. Unlike Effect, Either
is not lazy — it is a plain value you can pattern match on immediately, with no
runtime required.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Never, TypeIs, cast, overload

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
        ```python
        e = right(42)
        match e:
            case Right(value):
                print(f"Right: {value}")  # Right: 42
        ```
    """
    return Right(value)


def left[L, R = Never](value: L) -> Either[R, L]:
    """
    Create an Either with a Left value.

    Example:
        ```python
        e = left("oops")
        match e:
            case Left(value):
                print(f"Left: {value}")  # Left: oops
        ```
    """
    return Left(value)


# ============================================================================
# Guards
# ============================================================================


def is_right[R, L](either: Either[R, L]) -> TypeIs[Right[R]]:
    """
    Return True if the Either is a Right value.

    Example:
        ```python
        is_right(right(42))   # True
        is_right(left("oops")) # False
        ```
    """
    return isinstance(either, Right)


def is_left[R, L](either: Either[R, L]) -> TypeIs[Left[L]]:
    """
    Return True if the Either is a Left value.

    Example:
        ```python
        is_left(left("oops"))  # True
        is_left(right(42))     # False
        ```
    """
    return isinstance(either, Left)


# ============================================================================
# Mapping
# ============================================================================


def map[R, R2, L](f: Callable[[R], R2]) -> Callable[[Either[R, L]], Either[R2, L]]:
    """
    Transform the Right value of an Either.

    Applies f to the value if Right, passes Left through unchanged.

    Example:
        ```python
        pipe(right(1), map(lambda x: x + 1))     # Right(value=2)
        pipe(left("oops"), map(lambda x: x + 1)) # Left(value='oops')
        ```
    """

    def _map(e: Either[R, L]) -> Either[R2, L]:
        match e:
            case Right(value):
                return Right(f(value))
            case Left():
                return e

    return _map


def map_left[R, L, L2](f: Callable[[L], L2]) -> Callable[[Either[R, L]], Either[R, L2]]:
    """
    Transform the Left value of an Either.

    Applies f to the value if Left, passes Right through unchanged.

    Example:
        ```python
        pipe(left("oops"), map_left(lambda s: s + "!")) # Left(value='oops!')
        pipe(right(1), map_left(lambda s: s + "!"))     # Right(value=1)
        ```
    """

    def _map_left(e: Either[R, L]) -> Either[R, L2]:
        match e:
            case Left(value):
                return Left(f(value))
            case Right():
                return e

    return _map_left


def map_both[R, R2, L, L2](
    on_right: Callable[[R], R2],
    on_left: Callable[[L], L2],
) -> Callable[[Either[R, L]], Either[R2, L2]]:
    """
    Transform both the Right and Left values of an Either.

    Applies on_right if Right, on_left if Left.

    Example:
        ```python
        pipe(right(1), map_both(on_right=lambda n: n + 1, on_left=lambda s: s + "!"))
        # Right(value=2)
        pipe(left("oops"), map_both(on_right=lambda n: n + 1, on_left=lambda s: s + "!"))
        # Left(value='oops!')
        ```
    """

    def _map_both(e: Either[R, L]) -> Either[R2, L2]:
        match e:
            case Right(value):
                return Right(on_right(value))
            case Left(value):
                return Left(on_left(value))

    return _map_both


def flat_map[R, R2, L1, L2](
    f: Callable[[R], Either[R2, L2]],
) -> Callable[[Either[R, L1]], Either[R2, L1 | L2]]:
    """
    Chain a computation that itself returns an Either.

    Applies f to the Right value and returns the resulting Either directly.
    If Left, passes it through without calling f.

    The output Left type is the union of the input Left type and the
    Left type returned by f, since either source can produce a Left.

    Example:
        ```python
        def parse_int(s: str) -> Either[int, str]:
            try:
                return right(int(s))
            except ValueError:
                return left("not a number")

        pipe(right("42"), flat_map(parse_int))   # Right(value=42)
        pipe(right("xx"), flat_map(parse_int))   # Left(value='not a number')
        pipe(left("oops"), flat_map(parse_int))  # Left(value='oops')
        ```
    """

    def _flat_map(e: Either[R, L1]) -> Either[R2, L1 | L2]:
        match e:
            case Right(value):
                return cast(Either[R2, L1 | L2], f(value))
            case Left():
                return cast(Either[R2, L1 | L2], e)

    return _flat_map


# ============================================================================
# Combining
# ============================================================================


def zip_with[R1, R2, R3, L1, L2](
    e1: Either[R1, L1],
    e2: Either[R2, L2],
    f: Callable[[R1, R2], R3],
) -> Either[R3, L1 | L2]:
    """
    Combine two Either values using a function.

    If both are Right, applies f to their values and returns Right(result).
    If either is Left, returns the first Left encountered.

    Example:
        ```python
        zip_with(right("John"), right(25), lambda name, age: {"name": name, "age": age})
        # Right(value={'name': 'John', 'age': 25})
        zip_with(right("John"), left("no age"), lambda name, age: (name, age))
        # Left(value='no age')
        zip_with(left("no name"), right(25), lambda name, age: (name, age))
        # Left(value='no name')
        ```
    """
    match e1:
        case Right(a):
            match e2:
                case Right(b):
                    return Right(f(a, b))
                case Left():
                    return cast(Either[R3, L1 | L2], e2)
        case Left():
            return cast(Either[R3, L1 | L2], e1)


@overload
def all[R, L](eithers: list[Either[R, L]]) -> Either[list[R], L]: ...


@overload
def all[K, R, L](eithers: dict[K, Either[R, L]]) -> Either[dict[K, R], L]: ...


def all[R, L, K](
    eithers: list[Either[R, L]] | dict[K, Either[R, L]],
) -> Either[list[R], L] | Either[dict[K, R], L]:
    """
    Combine a list or dict of Eithers into a single Either.

    If all elements are Right, returns Right containing the collected values.
    If any element is Left, returns the first Left encountered.

    Note:
        For heterogeneous collections (elements with different Right types),
        the type checker will not infer the correct type automatically. You
        should provide an explicit type annotation and suppress the error:

        ```python
        eithers: list[Either[int | str, SomeError]] = [right(1), right("hello")]
        result: Either[list[int | str], SomeError] = all(eithers)  # type: ignore[arg-type]
        ```

    Example:
        ```python
        all([right("John"), right(25)])
        # Right(value=['John', 25])
        all({"name": right("John"), "age": right(25)})
        # Right(value={'name': 'John', 'age': 25})
        all([right(1), left("oops"), right(3)])
        # Left(value='oops')
        ```
    """
    if isinstance(eithers, dict):
        result_dict: dict[K, R] = {}  # type: ignore[valid-type]
        for key, e in eithers.items():
            match e:
                case Right(value):
                    result_dict[key] = value  # type: ignore[index]
                case Left():
                    return cast(Either[dict[K, R], L], e)
        return Right(result_dict)

    result_list: list[R] = []
    for e in eithers:
        match e:
            case Right(value):
                result_list.append(value)
            case Left():
                return cast(Either[list[R], L], e)
    return Right(result_list)


__all__ = [
    "Either",
    "Left",
    "Right",
    "all",
    "flat_map",
    "is_left",
    "is_right",
    "left",
    "map",
    "map_both",
    "map_left",
    "right",
    "zip_with",
]
