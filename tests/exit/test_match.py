"""Tests for Exit match_ function."""

from pyfect import exit as exit_module


def test_match_success_data_first() -> None:
    """match_ should apply on_success to Success values (data-first style)."""
    result = exit_module.match_(
        exit_module.succeed(42),
        on_success=lambda value: f"Got: {value}",
        on_failure=lambda error: f"Error: {error}",
    )
    assert result == "Got: 42"


def test_match_failure_data_first() -> None:
    """match_ should apply on_failure to Failure values (data-first style)."""
    result = exit_module.match_(
        exit_module.fail("oops"),
        on_success=lambda value: f"Got: {value}",
        on_failure=lambda error: f"Error: {error}",
    )
    assert result == "Error: oops"


def test_match_with_different_return_types() -> None:
    """match_ should handle different return types for Success and Failure."""
    # on_success returns str, on_failure returns int
    result_success = exit_module.match_(
        exit_module.succeed("hello"),
        on_success=lambda s: s.upper(),
        on_failure=lambda e: len(str(e)),
    )
    assert result_success == "HELLO"

    result_failure = exit_module.match_(
        exit_module.fail("error"),
        on_success=lambda s: s.upper(),
        on_failure=len,
    )
    assert result_failure == 5  # noqa: PLR2004


def test_match_narrows_type_for_success() -> None:
    """match_ should narrow return type to B when input is Exit[A, Never]."""
    # When we know it's Success, result type should be just str, not str | int
    result: str = exit_module.match_(
        exit_module.succeed(42),
        on_success=lambda n: f"value: {n}",
        on_failure=lambda _: 0,
    )
    assert result == "value: 42"


def test_match_narrows_type_for_failure() -> None:
    """match_ should narrow return type to C when input is Exit[Never, E]."""
    # When we know it's Failure, result type should be just int, not str | int
    result: int = exit_module.match_(
        exit_module.fail("error"),
        on_success=lambda n: "value",
        on_failure=len,
    )
    assert result == 5  # noqa: PLR2004


def test_match_preserves_types() -> None:
    """match_ should preserve type information correctly."""
    # This test mainly validates type checking
    ex: exit_module.Exit[int, str] = exit_module.succeed(42)

    # Type checker should infer result as int | str
    result: int | str = exit_module.match_(
        ex,
        on_success=lambda n: n,  # int -> int
        on_failure=lambda e: e,  # str -> str
    )
    assert result == 42  # noqa: PLR2004


def test_match_success_curried() -> None:
    """match_ should work in curried style for Success values."""
    matcher = exit_module.match_(
        on_success=lambda value: f"Got: {value}",
        on_failure=lambda error: f"Error: {error}",
    )

    result = matcher(exit_module.succeed(42))
    assert result == "Got: 42"


def test_match_failure_curried() -> None:
    """match_ should work in curried style for Failure values."""
    matcher = exit_module.match_(
        on_success=lambda value: f"Got: {value}",
        on_failure=lambda error: f"Error: {error}",
    )

    result = matcher(exit_module.fail("oops"))
    assert result == "Error: oops"
