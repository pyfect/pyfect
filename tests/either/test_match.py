"""Tests for Either match_ function."""

from pyfect import either
from pyfect.pipe import pipe


def test_match_right_data_first() -> None:
    """match_ should apply on_right to Right values (data-first style)."""
    result = either.match_(
        either.right(42),
        on_left=lambda e: f"Error: {e}",
        on_right=lambda n: f"Success: {n}",
    )
    assert result == "Success: 42"


def test_match_left_data_first() -> None:
    """match_ should apply on_left to Left values (data-first style)."""
    result = either.match_(
        either.left("oops"),
        on_left=lambda e: f"Error: {e}",
        on_right=lambda n: f"Success: {n}",
    )
    assert result == "Error: oops"


def test_match_right_curried() -> None:
    """match_ should apply on_right to Right values (curried style)."""
    result = pipe(
        either.right(42),
        either.match_(
            on_left=lambda e: f"Error: {e}",
            on_right=lambda n: f"Success: {n}",
        ),
    )
    assert result == "Success: 42"


def test_match_left_curried() -> None:
    """match_ should apply on_left to Left values (curried style)."""
    result = pipe(
        either.left("oops"),
        either.match_(
            on_left=lambda e: f"Error: {e}",
            on_right=lambda n: f"Success: {n}",
        ),
    )
    assert result == "Error: oops"


def test_match_with_different_return_types() -> None:
    """match_ should handle different return types for Left and Right."""
    # on_left returns int, on_right returns str
    result_right = either.match_(
        either.right("hello"),
        on_left=len,
        on_right=lambda s: s.upper(),
    )
    assert result_right == "HELLO"

    result_left = either.match_(
        either.left("error"),
        on_left=len,
        on_right=lambda s: s.upper(),
    )
    assert result_left == 5  # noqa: PLR2004


def test_match_with_complex_transformations() -> None:
    """match_ should handle complex transformations."""

    def process_success(n: int) -> dict[str, int]:
        return {"value": n, "doubled": n * 2}

    def process_error(e: str) -> dict[str, str]:
        return {"error": e, "timestamp": "now"}

    result = pipe(
        either.right(21),
        either.match_(
            on_left=process_error,
            on_right=process_success,
        ),
    )
    assert result == {"value": 21, "doubled": 42}


def test_match_in_pipeline() -> None:
    """match_ should work seamlessly in pipelines."""
    result = pipe(
        either.right(10),
        either.map_(lambda n: n * 2),
        either.map_(lambda n: n + 1),
        either.match_(
            on_left=lambda _: 0,
            on_right=lambda n: n,
        ),
    )
    assert result == 21  # noqa: PLR2004


def test_match_preserves_types() -> None:
    """match_ should preserve type information correctly."""
    # This test mainly validates type checking
    e: either.Either[int, str] = either.right(42)

    # Type checker should infer result as int | str
    result: int | str = either.match_(
        e,
        on_left=lambda l: l,  # str -> str  # noqa: E741
        on_right=lambda r: r,  # int -> int
    )
    assert result == 42  # noqa: PLR2004


def test_match_narrows_type_for_right_data_first() -> None:
    """match_ should narrow return type to C when input is Right[R, Never] (data-first)."""
    # When we know it's a Right, result type should be just str, not int | str
    result: str = either.match_(
        either.right(42),
        on_left=lambda l: 0,  # Never -> int  # noqa: E741
        on_right=lambda r: f"value: {r}",  # int -> str
    )
    assert result == "value: 42"


def test_match_narrows_type_for_left_data_first() -> None:
    """match_ should narrow return type to B when input is Left[Never, L] (data-first)."""
    # When we know it's a Left, result type should be just int, not int | str
    result: int = either.match_(
        either.left("error"),
        on_left=len,  # str -> int
        on_right=lambda r: "value",  # Never -> str
    )
    assert result == 5  # noqa: PLR2004
