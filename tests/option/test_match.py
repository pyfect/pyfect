"""Tests for Option match_ function."""

from pyfect import option
from pyfect.pipe import pipe


def test_match_some_data_first() -> None:
    """match_ should apply on_some to Some values (data-first style)."""
    result = option.match_(
        option.some(42),
        on_some=lambda n: f"Value: {n}",
        on_nothing=lambda: "Empty",
    )
    assert result == "Value: 42"


def test_match_nothing_data_first() -> None:
    """match_ should apply on_nothing to Nothing (data-first style)."""
    result = option.match_(
        option.nothing(),
        on_some=lambda n: f"Value: {n}",
        on_nothing=lambda: "Empty",
    )
    assert result == "Empty"


def test_match_some_curried() -> None:
    """match_ should apply on_some to Some values (curried style)."""
    result = pipe(
        option.some(42),
        option.match_(
            on_some=lambda n: f"Value: {n}",
            on_nothing=lambda: "Empty",
        ),
    )
    assert result == "Value: 42"


def test_match_nothing_curried() -> None:
    """match_ should apply on_nothing to Nothing (curried style)."""
    result = pipe(
        option.nothing(),
        option.match_(
            on_some=lambda n: f"Value: {n}",
            on_nothing=lambda: "Empty",
        ),
    )
    assert result == "Empty"


def test_match_with_different_return_types() -> None:
    """match_ should handle different return types for Some and Nothing."""
    # on_some returns str, on_nothing returns int
    result_some = option.match_(
        option.some("hello"),
        on_some=lambda s: s.upper(),
        on_nothing=lambda: 0,
    )
    assert result_some == "HELLO"

    result_nothing = option.match_(
        option.nothing(),
        on_some=lambda s: s.upper(),  # pyright: ignore[reportAttributeAccessIssue]
        on_nothing=lambda: 0,
    )
    assert result_nothing == 0


def test_match_with_complex_transformations() -> None:
    """match_ should handle complex transformations."""

    def process_value(n: int) -> dict[str, int]:
        return {"value": n, "doubled": n * 2}

    def process_empty() -> dict[str, str]:
        return {"error": "no value"}

    result = pipe(
        option.some(21),
        option.match_(
            on_some=process_value,
            on_nothing=process_empty,
        ),
    )
    assert result == {"value": 21, "doubled": 42}


def test_match_in_pipeline() -> None:
    """match_ should work seamlessly in pipelines."""
    result = pipe(
        option.some(10),
        option.map_(lambda n: n * 2),
        option.map_(lambda n: n + 1),
        option.match_(
            on_some=lambda n: n,
            on_nothing=lambda: 0,
        ),
    )
    assert result == 21  # noqa: PLR2004


def test_match_preserves_types() -> None:
    """match_ should preserve type information correctly."""
    # This test mainly validates type checking
    opt = option.some(42)

    # Type checker should infer result as int | str
    result = option.match_(
        opt,
        on_some=lambda n: n,  # int -> int
        on_nothing=lambda: "empty",  # () -> str
    )
    assert result == 42  # noqa: PLR2004


def test_match_on_nothing_is_lazy() -> None:
    """on_nothing should only be called when the Option is Nothing."""
    calls = []

    def track_call() -> str:
        calls.append("nothing")
        return "empty"

    # on_nothing should not be called for Some
    option.match_(
        option.some(42),
        on_some=lambda n: n,
        on_nothing=track_call,
    )
    assert len(calls) == 0

    # on_nothing should be called for Nothing
    option.match_(
        option.nothing(),
        on_some=lambda n: n,
        on_nothing=track_call,
    )
    assert len(calls) == 1


def test_match_narrows_type_for_nothing() -> None:
    """match_ should narrow return type to C when input is Nothing."""
    # When we know it's Nothing, result type should be just int, not str | int
    result: int = option.match_(
        option.nothing(),
        on_some=lambda n: f"value: {n}",  # A -> str
        on_nothing=lambda: 0,  # () -> int
    )
    assert result == 0
