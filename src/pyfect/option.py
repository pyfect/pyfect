"""
Option type for representing optional values.

An Option[A] is either Some[A], containing a value, or Nothing,
representing the absence of a value.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TypeIs, overload

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
        ```python
        opt = some(42)
        assert isinstance(opt, Some)
        ```
    """
    return Some(value)


def nothing() -> Nothing:
    """
    Create an Option representing the absence of a value.

    Returns the NOTHING singleton.

    Example:
        ```python
        opt = nothing()
        assert opt is NOTHING
        ```
    """
    return NOTHING


def from_optional[A](value: A | None) -> Option[A]:
    """
    Convert a Python optional value to an Option.

    None becomes Nothing, any other value becomes Some.

    Example:
        ```python
        from_optional(42)  # Some(value=42)
        from_optional(None)  # Nothing()
        ```
    """
    return NOTHING if value is None else Some(value)


def lift_predicate[A](predicate: Callable[[A], bool]) -> Callable[[A], Option[A]]:
    """
    Lift a predicate into a function that returns an Option.

    Returns a function that produces Some(value) if the predicate holds,
    or Nothing if it does not.

    Example:
        ```python
        parse_positive = lift_predicate(lambda n: n > 0)
        parse_positive(42)  # Some(value=42)
        parse_positive(-1)  # Nothing()
        ```
    """
    return lambda value: Some(value) if predicate(value) else NOTHING


# ============================================================================
# Guards
# ============================================================================


def is_some[A](option: Option[A]) -> TypeIs[Some[A]]:
    """
    Return True if the Option contains a value.

    Example:
        ```python
        is_some(some(42))  # True
        is_some(nothing())  # False
        ```
    """
    return isinstance(option, Some)


def is_nothing[A](option: Option[A]) -> TypeIs[Nothing]:
    """
    Return True if the Option is Nothing.

    Example:
        ```python
        is_nothing(nothing())  # True
        is_nothing(some(42))  # False
        ```
    """
    return isinstance(option, Nothing)


# ============================================================================
# Transformations
# ============================================================================


def map[A, B](f: Callable[[A], B]) -> Callable[[Option[A]], Option[B]]:
    """
    Transform the value inside an Option.

    Applies f to the value if Some, passes Nothing through unchanged.

    Example:
        ```python
        from pyfect import pipe
        pipe(some(42), map(lambda x: x * 2))  # Some(value=84)
        pipe(nothing(), map(lambda x: x * 2))  # Nothing()
        ```
    """

    def _map(opt: Option[A]) -> Option[B]:
        match opt:
            case Some(value):
                return Some(f(value))
            case Nothing():
                return NOTHING

    return _map


def flat_map[A, B](f: Callable[[A], Option[B]]) -> Callable[[Option[A]], Option[B]]:
    """
    Chain a computation that may itself return Nothing.

    Applies f to the value if Some, returning the resulting Option directly.
    If Nothing, returns Nothing without calling f.

    Example:
        ```python
        from pyfect import pipe
        def parse_int(s: str) -> Option[int]:
            try:
                return some(int(s))
            except ValueError:
                return nothing()
        pipe(some("42"), flat_map(parse_int))  # Some(value=42)
        pipe(some("xx"), flat_map(parse_int))  # Nothing()
        pipe(nothing(), flat_map(parse_int))  # Nothing()
        ```
    """

    def _flat_map(opt: Option[A]) -> Option[B]:
        match opt:
            case Some(value):
                return f(value)
            case Nothing():
                return NOTHING

    return _flat_map


def filter[A](predicate: Callable[[A], bool]) -> Callable[[Option[A]], Option[A]]:
    """
    Keep the value only if it satisfies the predicate.

    If Some and predicate returns True, returns the Option unchanged.
    If Some and predicate returns False, returns Nothing.
    If Nothing, returns Nothing.

    Example:
        ```python
        from pyfect import pipe
        pipe(some(42), filter(lambda x: x > 0))  # Some(value=42)
        pipe(some(-1), filter(lambda x: x > 0))  # Nothing()
        pipe(nothing(), filter(lambda x: x > 0))  # Nothing()
        ```
    """

    def _filter(opt: Option[A]) -> Option[A]:
        match opt:
            case Some(value):
                return opt if predicate(value) else NOTHING
            case Nothing():
                return NOTHING

    return _filter


# ============================================================================
# Extraction
# ============================================================================


def get_or_none[A](opt: Option[A]) -> A | None:
    """
    Return the value if Some, or None if Nothing.

    Useful for interoperating with code that uses None to represent
    the absence of a value.

    Example:
        ```python
        from pyfect import pipe
        pipe(some(42), get_or_none)  # 42
        pipe(nothing(), get_or_none)  # None
        ```
    """
    match opt:
        case Some(value):
            return value
        case Nothing():
            return None


def get_or_else[A](default: Callable[[], A]) -> Callable[[Option[A]], A]:
    """
    Return the value if Some, or the result of calling default if Nothing.

    The default thunk is only evaluated when the Option is Nothing.

    Example:
        ```python
        from pyfect import pipe
        pipe(some(42), get_or_else(lambda: 0))  # 42
        pipe(nothing(), get_or_else(lambda: 0))  # 0
        ```
    """

    def _get_or_else(opt: Option[A]) -> A:
        match opt:
            case Some(value):
                return value
            case Nothing():
                return default()

    return _get_or_else


def get_or_raise[A](opt: Option[A]) -> A:
    """
    Return the value if Some, or raise ValueError if Nothing.

    Example:
        ```python
        get_or_raise(some(42))  # 42
        get_or_raise(nothing())  # raises ValueError: get_or_raise called on Nothing
        ```
    """
    match opt:
        case Some(value):
            return value
        case Nothing():
            msg = "get_or_raise called on Nothing"
            raise ValueError(msg)


# ============================================================================
# Fallback
# ============================================================================


def or_else[A](alternative: Callable[[], Option[A]]) -> Callable[[Option[A]], Option[A]]:
    """
    Return the Option unchanged if Some, or the result of calling alternative if Nothing.

    The alternative thunk is only evaluated when the Option is Nothing.

    Example:
        ```python
        from pyfect import pipe
        pipe(some(42), or_else(lambda: some(0)))  # Some(value=42)
        pipe(nothing(), or_else(lambda: some(0)))  # Some(value=0)
        pipe(nothing(), or_else(lambda: nothing()))  # Nothing()
        ```
    """

    def _or_else(opt: Option[A]) -> Option[A]:
        match opt:
            case Some():
                return opt
            case Nothing():
                return alternative()

    return _or_else


def zip_with[A, B, C](
    opt_a: Option[A],
    opt_b: Option[B],
    f: Callable[[A, B], C],
) -> Option[C]:
    """
    Combine two Options using a function.

    If both are Some, applies f to their values and returns Some(result).
    If either is Nothing, returns Nothing.

    Example:
        ```python
        zip_with(some("John"), some(25), lambda name, age: {"name": name, "age": age})
        # Some(value={'name': 'John', 'age': 25})
        zip_with(some("John"), nothing(), lambda name, age: (name, age))  # Nothing()
        ```
    """
    match opt_a, opt_b:
        case Some(a), Some(b):
            return Some(f(a, b))
        case _:
            return NOTHING


def first_some_of[A](options: Iterable[Option[A]]) -> Option[A]:
    """
    Return the first Some in an iterable, or Nothing if there are none.

    Short-circuits on the first Some found.

    Example:
        ```python
        first_some_of([nothing(), some(2), nothing(), some(3)])  # Some(value=2)
        first_some_of([nothing(), nothing()])  # Nothing()
        ```
    """
    for opt in options:
        if is_some(opt):
            return opt
    return NOTHING


@overload
def all[A](options: list[Option[A]]) -> Option[list[A]]: ...


@overload
def all[K, A](options: dict[K, Option[A]]) -> Option[dict[K, A]]: ...


def all[A, K](
    options: list[Option[A]] | dict[K, Option[A]],
) -> Option[list[A]] | Option[dict[K, A]]:  # type: ignore[misc]
    """
    Combine a list or dict of Options into a single Option.

    If all elements are Some, returns Some containing the collected values.
    If any element is Nothing, returns Nothing.

    Note:
        For heterogeneous collections (elements with different value types),
        the type checker will not infer the correct type automatically. You
        should provide an explicit type annotation and suppress the error:

        ```python
        options: list[Option[int | str]] = [some(1), some("hello")]
        result: Option[list[int | str]] = all(options)  # type: ignore[arg-type]
        ```

    Example:
        ```python
        all([some("John"), some(25)])  # Some(value=['John', 25])
        all({"name": some("John"), "age": some(25)})  # Some(value={'name': 'John', 'age': 25})
        all([some(1), nothing(), some(3)])  # Nothing()
        ```
    """
    if isinstance(options, dict):
        result: dict[K, A] = {}  # type: ignore[valid-type]
        for key, opt in options.items():
            match opt:
                case Some(value):
                    result[key] = value  # type: ignore[index]
                case Nothing():
                    return NOTHING
        return Some(result)

    values: list[A] = []
    for opt in options:
        match opt:
            case Some(value):
                values.append(value)
            case Nothing():
                return NOTHING
    return Some(values)


__all__ = [
    "NOTHING",
    "Nothing",
    "Option",
    "Some",
    "all",
    "filter",
    "first_some_of",
    "flat_map",
    "from_optional",
    "get_or_else",
    "get_or_none",
    "get_or_raise",
    "is_nothing",
    "is_some",
    "lift_predicate",
    "map",
    "nothing",
    "or_else",
    "some",
    "zip_with",
]
