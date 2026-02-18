"""Tests for Either all."""

from pyfect import either
from pyfect.either import Left, Right

# ============================================================================
# list variant
# ============================================================================


def test_all_list_all_rights() -> None:
    result = either.all_([either.right("John"), either.right(25)])
    assert result == Right(["John", 25])


def test_all_list_returns_first_left() -> None:
    result = either.all_([either.right(1), either.left("oops"), either.left("other")])
    assert result == Left("oops")


def test_all_list_left_at_start() -> None:
    result = either.all_([either.left("oops"), either.right(1)])
    assert result == Left("oops")


def test_all_empty_list() -> None:
    result: either.Either[list[int], str] = either.all_([])
    assert result == Right([])


# ============================================================================
# dict variant
# ============================================================================


def test_all_dict_all_rights() -> None:
    result = either.all_({"name": either.right("John"), "age": either.right(25)})
    assert result == Right({"name": "John", "age": 25})


def test_all_dict_returns_first_left() -> None:
    result = either.all_({"name": either.left("no name"), "age": either.right(25)})
    assert result == Left("no name")


def test_all_empty_dict() -> None:
    result: either.Either[dict[str, int], str] = either.all_({})
    assert result == Right({})
