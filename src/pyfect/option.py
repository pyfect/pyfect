"""
Option type for representing optional values.

An Option[A] is either Some[A], containing a value, or Nothing,
representing the absence of a value.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import NoReturn, TypeIs, overload

# ============================================================================
# Option Types
# ============================================================================


class Option[A]:
    """Base class for Option variants.

    Using a base class (rather than a union type alias) allows type checkers
    to extract TypeVar A nominally from Option[A] instances,
    which is required for correct TypeVar solving in multi-step pipe chains
    and heterogeneous collections.
    """

    __slots__ = ()


@dataclass(frozen=True)
class Some[A](Option[A]):
    """An Option containing a value."""

    value: A


class _NothingClass(Option):  # type: ignore[type-arg]
    """An Option representing the absence of a value.

    Inherits from Option without binding the type parameter,
    making it compatible with Option[A] for any A.
    """

    __slots__ = ("_initialized",)
    _instance = None

    def __new__(cls) -> "_NothingClass":
        if cls._instance is None:
            cls._instance = object.__new__(cls)
            cls._instance._initialized = True  # type: ignore[attr-defined]
        return cls._instance

    def __repr__(self) -> str:
        return "Nothing()"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _NothingClass)

    def __hash__(self) -> int:
        return hash("Nothing")


# Singleton instance and type alias for pattern matching
NOTHING = _NothingClass()
Nothing = _NothingClass


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


@overload
def from_optional(value: None) -> Nothing:
    """Convert None to Nothing."""


@overload
def from_optional[A](value: A | None) -> Option[A]:
    """Convert an optional value to an Option."""


def from_optional[A](value: A | None) -> Option[A]:
    """
    Convert a Python optional value to an Option.

    None becomes Nothing, any other value becomes Some.

    Type narrows when input is definitely None:
    - from_optional(None) returns Nothing
    - from_optional(maybe_value) returns Option[T] when maybe_value: T | None

    Example:
        ```python
        from_optional(42)  # Some(value=42)
        from_optional(None)  # Nothing (type narrowed!)
        maybe: int | None = get_value()
        from_optional(maybe)  # Option[int]
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
# Pattern Matching
# ============================================================================


@overload
def match_[A, B, C](
    *,
    on_some: Callable[[A], B],
    on_nothing: Callable[[], C],
) -> Callable[[Option[A]], B | C]:
    """Curried version: returns a function that matches an Option."""


@overload
def match_[A, B, C](
    option: Nothing,
    *,
    on_some: Callable[[A], B],
    on_nothing: Callable[[], C],
) -> C:
    """Data-first version for Nothing: always returns C."""


@overload
def match_[A, B, C](
    option: Option[A],
    *,
    on_some: Callable[[A], B],
    on_nothing: Callable[[], C],
) -> B | C:
    """Data-first version: matches an Option directly."""


def match_[A, B, C](
    option: Option[A] | None = None,
    *,
    on_some: Callable[[A], B],
    on_nothing: Callable[[], C],
) -> B | C | Callable[[Option[A]], B | C]:
    """
    Match on an Option, handling both Some and Nothing cases.

    Provides an alternative to pattern matching with guaranteed exhaustiveness.
    Supports both curried (for use in pipes) and data-first styles.

    Args:
        option: Optional Option to match on. If None, returns a curried function.
        on_some: Function to apply if the Option is Some.
        on_nothing: Thunk to call if the Option is Nothing.

    Returns:
        If option is provided: B | C (the result of applying the appropriate function).
        If option is None: A function that takes an Option and returns B | C.

    Example:
        ```python
        # Curried style (for use in pipes)
        pipe(
            some(42),
            match_(on_some=lambda n: f"Value: {n}", on_nothing=lambda: "Empty")
        )
        # 'Value: 42'

        # Data-first style
        result = match_(
            some(42),
            on_some=lambda n: f"Value: {n}",
            on_nothing=lambda: "Empty"
        )
        # 'Value: 42'
        ```
    """
    if option is None:
        # Curried version
        def _match(opt: Option[A]) -> B | C:
            if isinstance(opt, Some):
                return on_some(opt.value)
            return on_nothing()

        return _match

    # Data-first version
    if isinstance(option, Some):
        return on_some(option.value)
    return on_nothing()


# ============================================================================
# Transformations
# ============================================================================


def map_[A, B](f: Callable[[A], B]) -> Callable[[Option[A]], Option[B]]:
    """
    Transform the value inside an Option.

    Applies f to the value if Some, passes Nothing through unchanged.

    Example:
        ```python
        from pyfect import pipe
        pipe(some(42), map_(lambda x: x * 2))  # Some(value=84)
        pipe(nothing(), map_(lambda x: x * 2))  # Nothing()
        ```
    """

    def _map(opt: Option[A]) -> Option[B]:
        if isinstance(opt, Some):
            return Some(f(opt.value))
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
        if isinstance(opt, Some):
            return f(opt.value)
        return NOTHING

    return _flat_map


def filter_[A](predicate: Callable[[A], bool]) -> Callable[[Option[A]], Option[A]]:
    """
    Keep the value only if it satisfies the predicate.

    If Some and predicate returns True, returns the Option unchanged.
    If Some and predicate returns False, returns Nothing.
    If Nothing, returns Nothing.

    Example:
        ```python
        from pyfect import pipe
        pipe(some(42), filter_(lambda x: x > 0))  # Some(value=42)
        pipe(some(-1), filter_(lambda x: x > 0))  # Nothing()
        pipe(nothing(), filter_(lambda x: x > 0))  # Nothing()
        ```
    """

    def _filter(opt: Option[A]) -> Option[A]:
        if isinstance(opt, Some):
            return opt if predicate(opt.value) else NOTHING
        return NOTHING

    return _filter


# ============================================================================
# Extraction
# ============================================================================


@overload
def get_or_none[A](opt: Some[A]) -> A:
    """Return the value from Some, narrowed to A."""


@overload
def get_or_none(opt: Nothing) -> None:
    """Return None from Nothing, narrowed to None."""


@overload
def get_or_none[A](opt: Option[A]) -> A | None:
    """Return the value or None."""


def get_or_none[A](opt: Option[A]) -> A | None:
    """
    Return the value if Some, or None if Nothing.

    Useful for interoperating with code that uses None to represent
    the absence of a value.

    Type narrows when input is Nothing:
    - get_or_none(nothing()) returns None (type narrowed!)
    - get_or_none(some(42)) returns int | None
    - get_or_none(maybe_opt) returns int | None when maybe_opt: Option[int]

    Example:
        ```python
        from pyfect import pipe
        pipe(some(42), get_or_none)  # 42
        pipe(nothing(), get_or_none)  # None (type: None)
        ```
    """
    if opt is NOTHING:
        return None
    return opt.value  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]


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
        if isinstance(opt, Some):
            return opt.value
        return default()

    return _get_or_else


@overload
def get_or_raise(opt: Nothing) -> NoReturn:
    """Raise ValueError when called with Nothing."""


@overload
def get_or_raise[A](opt: Option[A]) -> A:
    """Return the value or raise ValueError."""


def get_or_raise[A](opt: Option[A]) -> A:
    """
    Return the value if Some, or raise ValueError if Nothing.

    Type narrows when input is Nothing:
    - get_or_raise(nothing()) has type NoReturn (always raises)
    - get_or_raise(some(42)) returns the value
    - get_or_raise(maybe_opt) returns A when maybe_opt: Option[A]

    Example:
        ```python
        get_or_raise(some(42))  # 42
        get_or_raise(nothing())  # raises ValueError (type: NoReturn)

        # Useful for control flow
        if is_nothing(opt):
            get_or_raise(opt)  # Type checker knows this never returns
            # Unreachable code
        ```
    """
    if isinstance(opt, Some):
        return opt.value
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
        if isinstance(opt, Some):
            return opt
        return alternative()

    return _or_else


@overload
def zip_with[A, B, C](
    opt_a: Nothing,
    opt_b: Option[B],
    f: Callable[[A, B], C],
) -> Nothing:
    """If first Option is Nothing, returns Nothing."""


@overload
def zip_with[A, B, C](
    opt_a: Option[A],
    opt_b: Nothing,
    f: Callable[[A, B], C],
) -> Nothing:
    """If second Option is Nothing, returns Nothing."""


@overload
def zip_with[A, B, C](
    opt_a: Option[A],
    opt_b: Option[B],
    f: Callable[[A, B], C],
) -> Option[C]:
    """General case: returns Option[C]."""


def zip_with[A, B, C](
    opt_a: Option[A],
    opt_b: Option[B],
    f: Callable[[A, B], C],
) -> Option[C]:
    """
    Combine two Options using a function.

    If both are Some, applies f to their values and returns Some(result).
    If either is Nothing, returns Nothing.

    Type narrows when either input is Nothing:
    - zip_with(nothing(), opt_b, f) returns Nothing
    - zip_with(opt_a, nothing(), f) returns Nothing
    - zip_with(opt_a, opt_b, f) returns Option[C] (general case)

    Example:
        ```python
        zip_with(some("John"), some(25), lambda name, age: {"name": name, "age": age})
        # Some(value={'name': 'John', 'age': 25})
        zip_with(some("John"), nothing(), lambda name, age: (name, age))
        # Nothing() (type: Nothing)
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
def all_[A](options: list[Option[A]]) -> Option[list[A]]: ...


@overload
def all_[K, A](options: dict[K, Option[A]]) -> Option[dict[K, A]]: ...


def all_[A, K](
    options: list[Option[A]] | dict[K, Option[A]],
) -> Option[list[A]] | Option[dict[K, A]]:  # type: ignore[misc]
    """
    Combine a list or dict of Options into a single Option.

    If all elements are Some, returns Some containing the collected values.
    If any element is Nothing, returns Nothing.

    Example:
        ```python
        all_([some("John"), some(25)])  # Some(value=['John', 25])
        all_({"name": some("John"), "age": some(25)})  # Some(value={'name': 'John', 'age': 25})
        all_([some(1), nothing(), some(3)])  # Nothing()
        ```
    """
    if isinstance(options, dict):
        result: dict[K, A] = {}  # type: ignore[valid-type]
        for key, opt in options.items():
            if isinstance(opt, Some):
                result[key] = opt.value  # type: ignore[index]
            else:
                return NOTHING
        return Some(result)

    values: list[A] = []
    for opt in options:
        if isinstance(opt, Some):
            values.append(opt.value)
        else:
            return NOTHING
    return Some(values)


__all__ = [
    "NOTHING",
    "Nothing",
    "Option",
    "Some",
    "all_",
    "filter_",
    "first_some_of",
    "flat_map",
    "from_optional",
    "get_or_else",
    "get_or_none",
    "get_or_raise",
    "is_nothing",
    "is_some",
    "lift_predicate",
    "map_",
    "match_",
    "nothing",
    "or_else",
    "some",
    "zip_with",
]
